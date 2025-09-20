"""
Dependency checker for graceful degradation when optional dependencies are missing
"""

import importlib
import sys
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class DependencyStatus(Enum):
    """Status of a dependency"""
    AVAILABLE = "available"
    MISSING = "missing"
    VERSION_MISMATCH = "version_mismatch"
    FUNCTIONALITY_LIMITED = "functionality_limited"


@dataclass
class DependencyInfo:
    """Information about a dependency"""
    name: str
    module_name: str
    required: bool = False
    min_version: Optional[str] = None
    fallback_modules: Optional[List[str]] = None
    description: str = ""
    impact_if_missing: str = ""


class DependencyChecker:
    """Check and manage optional dependencies with graceful degradation"""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback or print
        self._dependency_status: Dict[str, DependencyStatus] = {}
        self._available_features: Dict[str, bool] = {}

        # Define core dependencies
        self.dependencies = {
            "pymupdf": DependencyInfo(
                name="PyMuPDF",
                module_name="fitz",
                required=True,
                min_version="1.24.0",
                description="PDF processing and manipulation",
                impact_if_missing="Application cannot process PDF files"
            ),
            "pillow": DependencyInfo(
                name="Pillow",
                module_name="PIL",
                required=True,
                min_version="10.0.0",
                description="Image processing",
                impact_if_missing="Cannot process image files or perform OCR"
            ),
            "pytesseract": DependencyInfo(
                name="PyTesseract",
                module_name="pytesseract",
                required=False,
                min_version="0.3.10",
                description="OCR text extraction",
                impact_if_missing="Cannot extract text from scanned documents"
            ),
            "python_docx": DependencyInfo(
                name="python-docx",
                module_name="docx",
                required=False,
                description="Microsoft Word document processing",
                impact_if_missing="Cannot process .docx files"
            ),
            "openpyxl": DependencyInfo(
                name="openpyxl",
                module_name="openpyxl",
                required=False,
                description="Microsoft Excel document processing",
                impact_if_missing="Cannot process .xlsx files"
            ),
            "psutil": DependencyInfo(
                name="psutil",
                module_name="psutil",
                required=False,
                min_version="5.9.0",
                description="System monitoring and memory management",
                impact_if_missing="Limited memory monitoring and system resource management"
            ),
            "reportlab": DependencyInfo(
                name="ReportLab",
                module_name="reportlab",
                required=True,
                min_version="4.0.0",
                description="PDF generation and manipulation",
                impact_if_missing="Cannot generate line-numbered PDFs"
            ),
            "pywin32": DependencyInfo(
                name="pywin32",
                module_name="win32com.client",
                required=False,
                description="Windows desktop shortcut creation",
                impact_if_missing="Desktop shortcuts won't be created during installation (manual setup required)"
            )
        }

    def check_dependencies(self) -> Dict[str, DependencyStatus]:
        """Check all dependencies and return their status"""
        self.log_callback("Checking application dependencies...")

        for dep_name, dep_info in self.dependencies.items():
            status = self._check_single_dependency(dep_info)
            self._dependency_status[dep_name] = status

            # Log the result
            if status == DependencyStatus.AVAILABLE:
                self.log_callback(f"✅ {dep_info.name}: Available")
            elif status == DependencyStatus.MISSING:
                if dep_info.required:
                    self.log_callback(f"❌ {dep_info.name}: Missing (Required) - {dep_info.impact_if_missing}")
                else:
                    self.log_callback(f"⚠️  {dep_info.name}: Missing (Optional) - {dep_info.impact_if_missing}")
            elif status == DependencyStatus.VERSION_MISMATCH:
                self.log_callback(f"⚠️  {dep_info.name}: Version mismatch")
            elif status == DependencyStatus.FUNCTIONALITY_LIMITED:
                self.log_callback(f"⚠️  {dep_info.name}: Available but with limited functionality")

        self._determine_available_features()
        return self._dependency_status

    def _check_single_dependency(self, dep_info: DependencyInfo) -> DependencyStatus:
        """Check a single dependency"""
        try:
            # Try to import the module
            module = importlib.import_module(dep_info.module_name)

            # Check version if specified
            if dep_info.min_version:
                version = self._get_module_version(module)
                if version and self._compare_versions(version, dep_info.min_version) < 0:
                    return DependencyStatus.VERSION_MISMATCH

            return DependencyStatus.AVAILABLE

        except ImportError:
            # Check for fallback modules
            if dep_info.fallback_modules:
                for fallback_module in dep_info.fallback_modules:
                    try:
                        importlib.import_module(fallback_module)
                        return DependencyStatus.FUNCTIONALITY_LIMITED
                    except ImportError:
                        continue

            return DependencyStatus.MISSING
        except Exception as e:
            self.log_callback(f"Error checking {dep_info.name}: {str(e)}")
            return DependencyStatus.FUNCTIONALITY_LIMITED

    def _get_module_version(self, module) -> Optional[str]:
        """Get version of a module"""
        try:
            if hasattr(module, '__version__'):
                return module.__version__
            elif hasattr(module, 'VERSION'):
                return module.VERSION
            else:
                # Try common version attributes
                for attr in ['version', 'Version', 'get_version()']:
                    if hasattr(module, attr):
                        version = getattr(module, attr)
                        if callable(version):
                            version = version()
                        return str(version)
        except Exception:
            pass
        return None

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings
        Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        def normalize_version(v):
            return [int(x) for x in v.split('.')]

        try:
            v1_parts = normalize_version(version1)
            v2_parts = normalize_version(version2)

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return -1
                elif v1 > v2:
                    return 1
            return 0
        except Exception:
            return 0  # Assume equal if comparison fails

    def _determine_available_features(self):
        """Determine what features are available based on dependencies"""
        self._available_features = {
            "pdf_processing": self._dependency_status.get("pymupdf") == DependencyStatus.AVAILABLE,
            "image_processing": self._dependency_status.get("pillow") == DependencyStatus.AVAILABLE,
            "ocr_functionality": self._dependency_status.get("pytesseract") == DependencyStatus.AVAILABLE,
            "word_processing": self._dependency_status.get("python_docx") == DependencyStatus.AVAILABLE,
            "excel_processing": self._dependency_status.get("openpyxl") == DependencyStatus.AVAILABLE,
            "system_monitoring": self._dependency_status.get("psutil") == DependencyStatus.AVAILABLE,
            "pdf_generation": self._dependency_status.get("reportlab") == DependencyStatus.AVAILABLE,
            "windows_integration": self._dependency_status.get("pywin32") == DependencyStatus.AVAILABLE
        }

    def is_feature_available(self, feature_name: str) -> bool:
        """Check if a specific feature is available"""
        return self._available_features.get(feature_name, False)

    def get_available_features(self) -> Dict[str, bool]:
        """Get all available features"""
        return self._available_features.copy()

    def get_missing_required_dependencies(self) -> List[str]:
        """Get list of missing required dependencies"""
        missing = []
        for dep_name, dep_info in self.dependencies.items():
            if dep_info.required and self._dependency_status.get(dep_name) == DependencyStatus.MISSING:
                missing.append(dep_info.name)
        return missing

    def can_start_application(self) -> bool:
        """Check if the application can start with available dependencies"""
        missing_required = self.get_missing_required_dependencies()
        return len(missing_required) == 0

    def get_functionality_report(self) -> str:
        """Generate a report of available functionality"""
        report = ["Application Functionality Report", "=" * 40, ""]

        # Check required dependencies
        missing_required = self.get_missing_required_dependencies()
        if missing_required:
            report.append("❌ Missing Required Dependencies:")
            for dep in missing_required:
                report.append(f"   • {dep}")
            report.append("")
            report.append("Application cannot start without these dependencies.")
            report.append("Please install them using: pip install -r requirements.txt")
            return "\n".join(report)

        # Available features
        report.append("✅ Available Features:")
        for feature, available in self._available_features.items():
            status = "✅" if available else "❌"
            feature_name = feature.replace("_", " ").title()
            report.append(f"   {status} {feature_name}")

        # Optional dependencies status
        report.append("")
        report.append("Optional Dependencies:")
        for dep_name, dep_info in self.dependencies.items():
            if not dep_info.required:
                status = self._dependency_status.get(dep_name)
                if status == DependencyStatus.AVAILABLE:
                    report.append(f"   ✅ {dep_info.name}: Available")
                elif status == DependencyStatus.MISSING:
                    report.append(f"   ⚠️  {dep_info.name}: Missing")
                    report.append(f"      Impact: {dep_info.impact_if_missing}")

        return "\n".join(report)

    def import_with_fallback(self, module_name: str, fallback_message: Optional[str] = None):
        """Import a module with graceful fallback"""
        try:
            return importlib.import_module(module_name)
        except ImportError:
            if fallback_message:
                self.log_callback(fallback_message)
            return None

    def require_feature(self, feature_name: str, operation_name: str) -> bool:
        """Check if a required feature is available and log if not"""
        if not self.is_feature_available(feature_name):
            self.log_callback(f"Cannot {operation_name}: Required feature '{feature_name}' is not available")
            return False
        return True