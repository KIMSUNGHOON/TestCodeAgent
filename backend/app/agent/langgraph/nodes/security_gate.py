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

    # OWASP Top 10 patterns
    VULNERABILITY_PATTERNS = {
        "sql_injection": {
            "patterns": [
                r"execute\s*\(\s*['\"].*%s.*['\"]\s*%",  # String formatting in SQL
                r"f['\"]SELECT.*FROM.*\{.*\}",  # f-strings with SELECT in SQL (case insensitive handled by re.IGNORECASE)
                r"cursor\.execute\s*\([^)]*\+[^)]*\)",  # String concatenation in SQL
            ],
            "severity": "critical",
            "description": "Potential SQL injection vulnerability",
            "recommendation": "Use parameterized queries with placeholders (?)"
        },
        "command_injection": {
            "patterns": [
                r"os\.system\s*\(",
                r"subprocess\.call\s*\([^)]*shell\s*=\s*True",
                r"eval\s*\(",
                r"exec\s*\(",
            ],
            "severity": "critical",
            "description": "Potential command injection vulnerability",
            "recommendation": "Avoid shell=True, use subprocess with list arguments"
        },
        "path_traversal": {
            "patterns": [
                r'[\'"]\.\./',  # "../" in strings
                r'[\'"]\.\.[/\\]',  # ".." with path separators
                r"open\s*\([^)]*\.\.",  # open() with ".."
            ],
            "severity": "high",
            "description": "Potential path traversal vulnerability",
            "recommendation": "Use FileValidator to sanitize paths"
        },
        "hardcoded_secrets": {
            "patterns": [
                r"password\s*=\s*['\"][^'\"]+['\"]",
                r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",
                r"secret\s*=\s*['\"][^'\"]+['\"]",
                r"token\s*=\s*['\"][^'\"]+['\"]",
            ],
            "severity": "high",
            "description": "Potential hardcoded secret",
            "recommendation": "Use environment variables or secure vaults"
        },
        "xss": {
            "patterns": [
                r"innerHTML\s*=",
                r"dangerouslySetInnerHTML",
                r"document\.write\s*\(",
            ],
            "severity": "medium",
            "description": "Potential XSS vulnerability",
            "recommendation": "Use safe DOM manipulation methods"
        }
    }

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

        for vuln_type, config in SecurityScanner.VULNERABILITY_PATTERNS.items():
            for pattern in config["patterns"]:
                matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
                for match in matches:
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
