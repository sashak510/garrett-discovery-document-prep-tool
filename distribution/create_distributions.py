#!/usr/bin/env python3
"""
Distribution Builder for Garrett Discovery Document Prep Tool
Creates both installer and source code distributions
"""

import os
import sys
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime
import subprocess

class DistributionBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.dist_dir = self.project_root / "distribution" / "output"
        self.source_dir = self.project_root / "distribution" / "source_package"
        self.installer_dir = self.project_root / "distribution" / "installer_package"

        # Create directories
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.installer_dir.mkdir(parents=True, exist_ok=True)

    def print_header(self):
        print("=" * 70)
        print("    Garrett Discovery Document Prep Tool - Distribution Builder")
        print("=" * 70)
        print(f"Project Root: {self.project_root}")
        print(f"Output Directory: {self.dist_dir}")
        print()

    def clean_directories(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning previous build artifacts...")

        # Clean source package directory
        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)
        self.source_dir.mkdir(parents=True, exist_ok=True)

        # Clean installer package directory
        if self.installer_dir.exists():
            shutil.rmtree(self.installer_dir)
        self.installer_dir.mkdir(parents=True, exist_ok=True)

        print("✅ Build artifacts cleaned")

    def create_source_package(self):
        """Create complete source code package"""
        print("📦 Creating source code package...")

        # Version info
        version = "1.0.0"
        package_name = f"Garrett-Discovery-Document-Prep-Tool-Source-v{version}"

        # Copy essential source files
        source_files = [
            "src/",
            "assets/",
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "README.md",
            "LICENSE",
            ".gitignore",
            "build/",
            "tests/",
            "pytest.ini"
        ]

        for item in source_files:
            source_path = self.project_root / item
            if source_path.exists():
                if source_path.is_file():
                    shutil.copy2(source_path, self.source_dir / item)
                else:
                    shutil.copytree(source_path, self.source_dir / item)

        # Create documentation
        docs_dir = self.source_dir / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Installation guide
        install_guide = f"""# Garrett Discovery Document Prep Tool - Installation Guide

## Version {version}

### For End Users (Simple Installation)
1. Run the installer: `GarrettDiscoveryTool-Setup.exe`
2. Follow the installation prompts
3. Launch from Start Menu or Desktop shortcut

### For Developers (Source Code Installation)
1. Install Python 3.9+ from python.org
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python src/main.py
   ```

### Building Your Own Installer
1. Install build dependencies:
   ```bash
   pip install pyinstaller[build]
   ```
2. Run the build script:
   ```bash
   python build/build_windows.py
   ```

### Customization Guide
The code is fully customizable. Key files to modify:
- `src/main.py` - Main application and UI
- `src/document_processor.py` - Core processing logic
- `src/pipelines/` - Document processing pipelines
- `src/error_handling.py` - Error management
- `src/config.py` - Configuration settings

### Support
For technical support or custom development, contact your development team.

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(docs_dir / "INSTALLATION.md", 'w') as f:
            f.write(install_guide)

        # Developer guide
        dev_guide = f"""# Developer Guide - Garrett Discovery Document Prep Tool

## Architecture Overview

### Core Components
- **main.py**: PyQt6 GUI application and main entry point
- **document_processor.py**: Central processing coordinator
- **pipelines/**: Modular document processing pipelines
- **error_handling.py**: Comprehensive error management
- **memory_manager.py**: Resource management and monitoring

### Processing Pipelines
The application uses intelligent pipeline routing:

1. **TextPipeline**: Word documents, text files
2. **NativePDFPipeline**: PDFs with text content
3. **ScanImagePipeline**: Scanned documents requiring OCR

### Adding New Document Types
1. Create new pipeline class inheriting from `BasePipeline`
2. Implement required abstract methods
3. Add detection logic to `document_processor.py`
4. Update file scanner if needed

### Modifying Line Numbering
- **VectorLineNumberer**: Vector-based line numbering
- **BatesNumberer**: Bates stamping and numbering
- Configuration in `config.py`

### Building and Testing
```bash
# Run tests
pytest

# Build installer
python build/build_windows.py

# Run from source
python src/main.py
```

### Dependencies
- PyQt6 for GUI
- PyMuPDF for PDF processing
- ReportLab for PDF generation
- pytesseract for OCR
- PIL for image processing

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(docs_dir / "DEVELOPER_GUIDE.md", 'w') as f:
            f.write(dev_guide)

        # Create package info
        package_info = {
            "name": "Garrett Discovery Document Prep Tool",
            "version": version,
            "build_date": datetime.now().isoformat(),
            "description": "Professional document processing tool for legal discovery",
            "requires_python": ">=3.9",
            "platforms": ["Windows", "macOS", "Linux"],
            "license": "Client Proprietary",
            "includes_source": True,
            "files_included": [
                "Complete source code",
                "Build scripts and tools",
                "Test suite",
                "Documentation",
                "Assets and resources"
            ]
        }

        with open(self.source_dir / "package_info.json", 'w') as f:
            json.dump(package_info, f, indent=2)

        # Create ZIP archive
        zip_path = self.dist_dir / f"{package_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.source_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(self.source_dir)
                    zipf.write(file_path, arcname)

        print(f"✅ Source package created: {zip_path}")
        return zip_path

    def build_installer(self):
        """Build Windows installer"""
        print("🔨 Building Windows installer...")

        # Check if build script exists
        build_script = self.project_root / "build" / "build_windows.py"
        if not build_script.exists():
            print("❌ Build script not found. Creating build directory...")
            build_dir = self.project_root / "build"
            build_dir.mkdir(exist_ok=True)
            print("Please run the Windows build script manually after setting up PyInstaller.")
            return None

        # Run build script
        try:
            result = subprocess.run([
                sys.executable, str(build_script)
            ], cwd=self.project_root, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print("✅ Installer build completed")

                # Find the built installer
                build_output = self.project_root / "build" / "windows" / "dist"
                if build_output.exists():
                    for file in build_output.glob("*Setup.exe"):
                        # Copy to distribution directory
                        dest_path = self.dist_dir / file.name
                        shutil.copy2(file, dest_path)
                        print(f"✅ Installer copied to: {dest_path}")
                        return dest_path

                print("⚠️  Build completed but installer file not found")
                return None
            else:
                print(f"❌ Build failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("❌ Build timed out")
            return None
        except Exception as e:
            print(f"❌ Build error: {e}")
            return None

    def create_installer_package(self, installer_path):
        """Create complete installer package with documentation"""
        if not installer_path or not installer_path.exists():
            print("⚠️  Skipping installer package - no installer found")
            return

        print("📦 Creating installer package...")

        # Copy installer
        shutil.copy2(installer_path, self.installer_dir / installer_path.name)

        # Create documentation
        docs_dir = self.installer_dir / "docs"
        docs_dir.mkdir(exist_ok=True)

        # User guide
        user_guide = f"""# Garrett Discovery Document Prep Tool - User Guide

## Quick Start

1. **Installation**: Double-click `GarrettDiscoveryTool-Setup.exe`
2. **Launch**: Find "Garrett Discovery Document Prep Tool" in Start Menu
3. **Process Documents**: Select input/output folders and click "Start Processing"

## Features

### Smart Document Processing
- **Automatic Detection**: Identifies document type and applies optimal processing
- **Line Numbering**: Professional legal line numbering in red text
- **Bates Numbering**: Legal document stamping with custom prefixes
- **Rotation Correction**: Automatically fixes rotated documents

### Supported Formats
- **PDF Files**: Native text extraction and image-based processing
- **Word Documents**: Direct conversion with formatting preserved
- **Text Files**: Clean conversion to PDF with line numbering
- **TIFF Images**: OCR processing with text extraction

### User Interface
- **Dark/Light Theme**: Toggle with Ctrl+D
- **Keyboard Shortcuts**: Professional shortcuts for all actions
- **Progress Tracking**: Real-time progress indicators
- **Comprehensive Logging**: Detailed processing logs

## System Requirements
- **Windows 10 or later**
- **4GB RAM minimum (8GB recommended)**
- **500MB disk space**

## Getting Help
- Press F1 for keyboard shortcuts
- Check the processing log for detailed information
- Contact support for technical assistance

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(docs_dir / "USER_GUIDE.md", 'w') as f:
            f.write(user_guide)

        # Create package info
        package_info = {
            "name": "Garrett Discovery Document Prep Tool",
            "version": "1.0.0",
            "build_date": datetime.now().isoformat(),
            "description": "Professional document processing tool for legal discovery",
            "platform": "Windows",
            "installer_type": "NSIS Installer",
            "includes_source": False,
            "user_level": "End User",
            "installation": "Standard Windows installer with uninstall support"
        }

        with open(self.installer_dir / "package_info.json", 'w') as f:
            json.dump(package_info, f, indent=2)

        print("✅ Installer package created")

    def create_distribution_summary(self, source_package, installer_package):
        """Create summary of all distributions"""
        print("📋 Creating distribution summary...")

        summary = {
            "build_date": datetime.now().isoformat(),
            "version": "1.0.0",
            "distributions": {}
        }

        if source_package and source_package.exists():
            summary["distributions"]["source_package"] = {
                "file": source_package.name,
                "size_mb": round(source_package.stat().st_size / (1024 * 1024), 2),
                "description": "Complete source code with build tools",
                "intended_for": "Developers and technical teams",
                "includes": ["Source code", "Build scripts", "Tests", "Documentation"]
            }

        if installer_package and installer_package.exists():
            summary["distributions"]["installer_package"] = {
                "file": installer_package.name,
                "size_mb": round(installer_package.stat().st_size / (1024 * 1024), 2),
                "description": "Ready-to-use Windows installer",
                "intended_for": "End users and non-technical staff",
                "includes": ["Compiled application", "Assets", "Uninstaller"]
            }

        summary["usage_instructions"] = {
            "source_package": "Extract ZIP file and follow documentation in docs/ directory",
            "installer_package": "Double-click the .exe file and follow installation prompts",
            "support": "Contact development team for assistance"
        }

        summary_path = self.dist_dir / "distribution_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"✅ Distribution summary created: {summary_path}")

        # Print summary
        print("\n" + "=" * 70)
        print("🎉 DISTRIBUTION CREATION COMPLETED!")
        print("=" * 70)
        print(f"📁 Output directory: {self.dist_dir}")
        print()

        for dist_type, info in summary["distributions"].items():
            print(f"📦 {dist_type.replace('_', ' ').title()}:")
            print(f"   📄 File: {info['file']}")
            print(f"   📏 Size: {info['size_mb']:.1f} MB")
            print(f"   👥 For: {info['intended_for']}")
            print(f"   📝 Description: {info['description']}")
            print()

        print("🚀 Ready for distribution!")

    def run_full_build(self):
        """Run complete distribution build"""
        self.print_header()

        try:
            self.clean_directories()

            # Build source package
            source_package = self.create_source_package()

            # Build installer
            installer_package = self.build_installer()

            # Create installer package
            if installer_package:
                self.create_installer_package(installer_package)

            # Create summary
            self.create_distribution_summary(source_package, installer_package)

            return True

        except Exception as e:
            print(f"❌ Distribution build failed: {e}")
            return False

def main():
    """Main function"""
    builder = DistributionBuilder()
    success = builder.run_full_build()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()