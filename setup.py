#!/usr/bin/env python3
"""
Setup configuration for Garrett Discovery Document Prep Tool
Professional Windows application packaging and distribution
"""

from setuptools import setup, find_packages
import sys
import os
from pathlib import Path

# Read version from version file or default
VERSION = "1.0.0"
try:
    if Path("src/version.py").exists():
        sys.path.insert(0, "src")
        from version import VERSION
except ImportError:
    pass

# Read long description from README
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        LONG_DESCRIPTION = fh.read()
except FileNotFoundError:
    LONG_DESCRIPTION = """
    Garrett Discovery Document Prep Tool

    Professional document processing tool for legal discovery with intelligent pipeline routing,
    line numbering, and bates stamping. Supports PDF, Word, Text, and TIFF files with
    automatic OCR and rotation correction.
    """

# Package data for non-Python files
PACKAGE_DATA = {
    "src": [
        "assets/*.*",
        "assets/icons/*.*",
        "assets/fonts/*.*",
        "config/*.*",
    ],
}

# Entry points for different installation methods
ENTRY_POINTS = {
    "console_scripts": [
        "garrett-discovery-tool=src.main:main",
    ],
    "gui_scripts": [
        "garrett-discovery-gui=src.main:main",
    ],
}

setup(
    name="garrett-discovery-document-prep-tool",
    version=VERSION,
    author="Garrett Discovery",
    author_email="info@garrettdiscovery.com",
    description="Professional document processing tool for legal discovery",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/garrettdiscovery/document-prep-tool",

    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data=PACKAGE_DATA,
    include_package_data=True,

    # Python version requirement
    python_requires=">=3.9",

    # Dependencies from requirements.txt
    install_requires=[
        "PyMuPDF>=1.24.0",
        "PyPDF2>=3.0.1",
        "reportlab>=4.1.0",
        "pillow>=10.4.0",
        "pytesseract>=0.3.13",
        "imutils>=0.5.4",
        "python-docx>=1.1.2",
        "openpyxl>=3.1.3",
        "psutil>=5.9.8",
        "PyQt6>=6.6.0",
        "pywin32>=307;platform_system=='Windows'",
    ],

    # Optional dependencies for enhanced functionality
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "build": [
            "PyInstaller>=5.0.0",
            "setuptools>=65.0.0",
            "wheel>=0.40.0",
            "build>=0.10.0",
        ],
        "ocr": [
            "tesseract>=5.0.0",
        ],
    },

    # Entry points for application launch
    entry_points=ENTRY_POINTS,

    # Application metadata
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Legal Industry",
        "Topic :: Office/Business :: Legal",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Environment :: X11 Applications :: Qt",
    ],

    # Keywords for package discovery
    keywords="legal discovery document processing bates numbering line numbering ocr pdf",

    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/garrettdiscovery/document-prep-tool/issues",
        "Source": "https://github.com/garrettdiscovery/document-prep-tool",
        "Documentation": "https://github.com/garrettdiscovery/document-prep-tool/wiki",
    },

    # ZIP safety considerations
    zip_safe=False,

    # Test suite configuration
    test_suite="tests",
    tests_require=[
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-qt>=4.0.0",
    ],

    # Windows-specific configuration
    options={
        "bdist_wheel": {
            "universal": False,  # Platform-specific wheels
        },
        "install": {
            "optimize": 1,  # Optimize bytecode
        },
    },
)