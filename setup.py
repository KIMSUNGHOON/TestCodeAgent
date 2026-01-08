"""Setup configuration for Agentic Coder

Installation:
    # Development mode (editable install)
    pip install -e .

    # Production install
    pip install .

    # With development dependencies
    pip install -e ".[dev]"
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

# Read requirements from requirements.txt
requirements_file = Path(__file__).parent / "backend" / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                requirements.append(line)

# Add CLI-specific dependencies
cli_requirements = [
    "rich>=13.0.0",          # Terminal UI with rich formatting
    "click>=8.0.0",          # CLI framework (optional, using argparse for now)
    "prompt-toolkit>=3.0.0", # Advanced input handling
]

# Merge requirements (avoid duplicates)
all_requirements = requirements + [
    req for req in cli_requirements
    if not any(req.split(">=")[0] in r for r in requirements)
]

setup(
    name="agentic-coder",
    version="1.0.0",
    description="Enterprise-grade AI coding assistant with unified workflow architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Agentic Coder Team",
    author_email="",
    url="https://github.com/KIMSUNGHOON/agentic-coder",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
    python_requires=">=3.9",
    install_requires=all_requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
            "mypy>=1.0.0",
        ],
        "cli": cli_requirements,
    },
    entry_points={
        "console_scripts": [
            "agentic-coder=cli.__main__:main",
        ],
    },
    scripts=["bin/agentic-coder"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="ai coding assistant llm cli interactive",
    project_urls={
        "Documentation": "https://github.com/KIMSUNGHOON/agentic-coder/blob/main/README.md",
        "Source": "https://github.com/KIMSUNGHOON/agentic-coder",
        "Tracker": "https://github.com/KIMSUNGHOON/agentic-coder/issues",
    },
)
