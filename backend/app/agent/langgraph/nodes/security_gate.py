"""Security Gate Node for OWASP and path validation

Scans for common vulnerabilities and ensures sandboxing compliance.
"""

import logging
import re
from typing import Dict, List
from app.agent.langgraph.schemas.state import QualityGateState, SecurityFinding
from app.agent.langgraph.tools.file_validator import FileValidator

logger = logging.getLogger(__name__)


class SecurityScanner:
    """OWASP-based security vulnerability scanner"""

    # File extensions that should be scanned for each vulnerability type
    SCANNABLE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
        "backend": [".py", ".java", ".go", ".rs", ".rb", ".php", ".cs"],
        "web": [".js", ".jsx", ".ts", ".tsx", ".html", ".htm"],
        "config": [".json", ".yaml", ".yml", ".env", ".ini", ".cfg"],
    }

    # File extensions to SKIP entirely (documentation, styles, etc.)
    SKIP_EXTENSIONS = [".md", ".txt", ".css", ".scss", ".less", ".svg", ".png", ".jpg", ".gif"]

    # OWASP Top 10 patterns with file type context
    VULNERABILITY_PATTERNS = {
        "sql_injection": {
            "patterns": [
                r"execute\s*\(\s*['\"].*%s.*['\"]\s*%",  # String formatting in SQL
                r"f['\"]SELECT.*FROM.*\{.*\}",  # f-strings with SELECT in SQL
                r"cursor\.execute\s*\([^)]*\+[^)]*\)",  # String concatenation in SQL
            ],
            "severity": "critical",
            "description": "Potential SQL injection vulnerability",
            "recommendation": "Use parameterized queries with placeholders (?)",
            "file_types": ["backend"],  # Only scan backend files
        },
        "command_injection_python": {
            "patterns": [
                r"os\.system\s*\(",
                r"subprocess\.call\s*\([^)]*shell\s*=\s*True",
                r"subprocess\.run\s*\([^)]*shell\s*=\s*True",
                r"subprocess\.Popen\s*\([^)]*shell\s*=\s*True",
            ],
            "severity": "critical",
            "description": "Potential command injection vulnerability (Python)",
            "recommendation": "Avoid shell=True, use subprocess with list arguments",
            "file_types": ["python"],  # Only scan Python files
        },
        "dangerous_eval_python": {
            "patterns": [
                r"\beval\s*\(",  # eval() call
                r"\bexec\s*\(",  # exec() call
            ],
            "exclude_patterns": [
                r"ast\.literal_eval\s*\(",  # ast.literal_eval is safe
                r"literal_eval\s*\(",  # imported literal_eval is also safe
            ],
            "severity": "high",
            "description": "Dangerous eval/exec usage in Python",
            "recommendation": "Use ast.literal_eval() for safe evaluation",
            "file_types": ["python"],  # Only scan Python files - JS eval is different
        },
        "path_traversal": {
            "patterns": [
                r"open\s*\([^)]*\.\.[/\\]",  # open() with ".."
                r"Path\s*\([^)]*\.\.[/\\]",  # Path() with ".."
            ],
            "severity": "high",
            "description": "Potential path traversal vulnerability",
            "recommendation": "Use FileValidator to sanitize paths",
            "file_types": ["backend"],
        },
        "hardcoded_secrets": {
            "patterns": [
                r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{4,}['\"]",  # Min 4 chars
                r"api[_-]?key\s*=\s*['\"][^'\"]{8,}['\"]",  # Min 8 chars for API keys
                r"(?:secret|token)\s*=\s*['\"][^'\"]{8,}['\"]",  # Min 8 chars
            ],
            "severity": "high",
            "description": "Potential hardcoded secret",
            "recommendation": "Use environment variables or secure vaults",
            "file_types": ["backend", "config"],
        },
        "xss_javascript": {
            "patterns": [
                r"innerHTML\s*=\s*[^;]*\+",  # innerHTML with concatenation
                r"dangerouslySetInnerHTML",
                r"document\.write\s*\([^)]*\+",  # document.write with concatenation
            ],
            "severity": "medium",
            "description": "Potential XSS vulnerability",
            "recommendation": "Use safe DOM manipulation methods or sanitize input",
            "file_types": ["web"],
        }
    }

    @staticmethod
    def get_file_type(filename: str) -> str:
        """Determine the file type category based on extension"""
        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

        if ext in SecurityScanner.SCANNABLE_EXTENSIONS["python"]:
            return "python"
        elif ext in SecurityScanner.SCANNABLE_EXTENSIONS["javascript"]:
            return "javascript"
        elif ext in SecurityScanner.SCANNABLE_EXTENSIONS["web"]:
            return "web"
        elif ext in SecurityScanner.SCANNABLE_EXTENSIONS["config"]:
            return "config"
        elif ext in SecurityScanner.SKIP_EXTENSIONS:
            return "skip"
        else:
            return "backend"  # Default to backend for unknown types

    @staticmethod
    def should_scan_for_vuln(file_type: str, vuln_file_types: List[str]) -> bool:
        """Check if this file type should be scanned for a specific vulnerability

        Args:
            file_type: The detected file type (e.g., "python", "javascript", "web")
            vuln_file_types: List of target file types for this vulnerability

        Returns:
            True if this file should be scanned for this vulnerability
        """
        if file_type == "skip":
            return False

        # Direct match
        if file_type in vuln_file_types:
            return True

        # Check if file type is a subcategory of target type
        # E.g., "python" files should be scanned for "backend" vulnerabilities
        for target_type in vuln_file_types:
            if target_type in SecurityScanner.SCANNABLE_EXTENSIONS:
                # Get extensions for this file type
                file_type_exts = SecurityScanner.SCANNABLE_EXTENSIONS.get(file_type, [])
                target_exts = SecurityScanner.SCANNABLE_EXTENSIONS.get(target_type, [])
                # Check if there's any overlap (e.g., .py is in both python and backend)
                if any(ext in target_exts for ext in file_type_exts):
                    return True

        return False

    @staticmethod
    def scan_code(code: str, filename: str) -> List[SecurityFinding]:
        """Scan code for security vulnerabilities

        Args:
            code: Source code to scan
            filename: Name of file being scanned

        Returns:
            List of security findings
        """
        findings: List[SecurityFinding] = []

        # Determine file type
        file_type = SecurityScanner.get_file_type(filename)

        # Skip non-code files (documentation, styles, images)
        if file_type == "skip":
            logger.debug(f"⏭️  Skipping security scan for {filename} (non-code file)")
            return findings

        for vuln_type, config in SecurityScanner.VULNERABILITY_PATTERNS.items():
            # Check if this vulnerability type applies to this file type
            vuln_file_types = config.get("file_types", ["backend"])
            if not SecurityScanner.should_scan_for_vuln(file_type, vuln_file_types):
                continue

            exclude_patterns = config.get("exclude_patterns", [])

            for pattern in config["patterns"]:
                try:
                    matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        # Check if this match should be excluded
                        match_start = match.start()
                        match_end = match.end()

                        # Get surrounding context (50 chars before and after)
                        context_start = max(0, match_start - 50)
                        context_end = min(len(code), match_end + 50)
                        context = code[context_start:context_end]

                        # Check if any exclude pattern matches in context
                        is_excluded = False
                        for exclude_pattern in exclude_patterns:
                            if re.search(exclude_pattern, context, re.IGNORECASE):
                                is_excluded = True
                                logger.debug(f"Excluding match '{match.group()}' due to safe pattern: {exclude_pattern}")
                                break

                        if is_excluded:
                            continue

                        # Calculate line number
                        line_number = code[:match.start()].count('\n') + 1

                        finding = SecurityFinding(
                            severity=config["severity"],
                            category=vuln_type,
                            description=config["description"],
                            file_path=filename,
                            line_number=line_number,
                            recommendation=config["recommendation"]
                        )
                        findings.append(finding)
                except re.error as e:
                    logger.warning(f"Regex error scanning {filename} for {vuln_type}: {e}")

        return findings


def security_gate_node(state: QualityGateState) -> Dict:
    """Security Gate: Scan for vulnerabilities and validate paths

    Performs:
    1. OWASP Top 10 pattern matching
    2. Path traversal detection
    3. Hardcoded secret detection
    4. Workspace sandboxing validation

    Args:
        state: Current workflow state

    Returns:
        State updates with security findings
    """
    logger.info("🔒 Security Gate Node: Scanning for vulnerabilities...")

    workspace_root = state["workspace_root"]
    validator = FileValidator(workspace_root)

    findings: List[SecurityFinding] = []

    # Scan coder output if available
    coder_output = state.get("coder_output")
    if coder_output and "artifacts" in coder_output:
        for artifact in coder_output["artifacts"]:
            filename = artifact.get("filename", "unknown")
            content = artifact.get("content", "")

            # Validate file path
            is_valid, error, _ = validator.validate_path(filename)
            if not is_valid:
                findings.append(SecurityFinding(
                    severity="critical",
                    category="path_traversal",
                    description=f"Path validation failed: {error}",
                    file_path=filename,
                    line_number=None,
                    recommendation="Ensure all paths are within workspace"
                ))

            # Scan code for vulnerabilities
            code_findings = SecurityScanner.scan_code(content, filename)
            findings.extend(code_findings)

    # Determine if security passed
    critical_findings = [f for f in findings if f["severity"] in ["critical", "high"]]
    security_passed = len(critical_findings) == 0

    # Log results
    if findings:
        logger.warning(f"⚠️  Found {len(findings)} security findings:")
        for finding in findings:
            logger.warning(f"   [{finding['severity']}] {finding['category']}: {finding['description']}")
            if finding['file_path']:
                logger.warning(f"      File: {finding['file_path']}:{finding['line_number']}")
    else:
        logger.info("✅ No security issues found")

    if security_passed:
        logger.info("✅ Security Gate PASSED")
    else:
        logger.error(f"❌ Security Gate FAILED: {len(critical_findings)} critical/high findings")

    return {
        "current_node": "security_gate",
        "security_findings": findings,
        "security_passed": security_passed,
    }
