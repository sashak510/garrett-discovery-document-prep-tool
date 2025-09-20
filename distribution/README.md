# Garrett Discovery Document Prep Tool - Distribution

This directory contains tools for creating both source code and installer distributions.

## Quick Start

### Build Both Distributions
```bash
python distribution/create_distributions.py
```

### Build Only Source Package
```bash
# Creates complete source code package
python distribution/create_distributions.py  # (script will build both)
```

### Build Only Installer
```bash
# Requires PyInstaller and NSIS
python build/build_windows.py
```

## Distribution Types

### 1. Source Code Package (for Developers)
- **File**: `Garrett-Discovery-Document-Prep-Tool-Source-v1.0.0.zip`
- **Contains**: Complete source code, build tools, tests, documentation
- **For**: Developers who want to modify/customize the software
- **Usage**: Extract ZIP and follow documentation in `docs/` directory

### 2. Windows Installer (for End Users)
- **File**: `GarrettDiscoveryDocumentPrepTool-1.0.0-Setup.exe`
- **Contains**: Compiled application with installer
- **For**: End users who just want to use the software
- **Usage**: Double-click and follow installation prompts

## Directory Structure

```
distribution/
├── create_distributions.py          # Main distribution builder
├── output/                          # Generated distribution files
├── source_package/                  # Temporary source package build dir
├── installer_package/               # Temporary installer package build dir
└── README.md                       # This file
```

## Requirements

### For Building Distributions
- Python 3.9+
- Dependencies listed in requirements.txt

### For Building Windows Installer
- PyInstaller: `pip install pyinstaller[build]`
- NSIS (for Windows installer): Download from https://nsis.sourceforge.io/

## Build Process

1. **Clean previous builds**
2. **Create source package** with all necessary files
3. **Build Windows installer** using PyInstaller and NSIS
4. **Create documentation** for both packages
5. **Generate distribution summary**

## What Gets Included

### Source Package Includes:
- ✅ Complete source code (`src/`)
- ✅ Build scripts (`build/`)
- ✅ Test suite (`tests/`)
- ✅ Assets and resources (`assets/`)
- ✅ Documentation and guides
- ✅ Package configuration files

### Source Package Excludes:
- ❌ Temporary development files
- ❌ Test output files
- ❌ Backup files
- ❌ Development artifacts

### Installer Package Includes:
- ✅ Compiled Windows executable
- ✅ Professional NSIS installer
- ✅ All required assets and resources
- ✅ Uninstaller
- ✅ Desktop and Start Menu shortcuts

## Usage Instructions

### For Your Development Team
1. Build the source package: `python distribution/create_distributions.py`
2. Send the ZIP file to your client
3. They get full source code ownership

### For End Users
1. Build the installer: `python build/build_windows.py`
2. Send the .exe file to end users
3. They get a simple, professional installation

## Customization

### Adding Files to Distribution
Edit `distribution/create_distributions.py` and modify the `source_files` list in the `create_source_package()` method.

### Modifying Documentation
Update the documentation templates in the `create_source_package()` and `create_installer_package()` methods.

## Support

For distribution issues or customization needs, refer to the main project documentation or contact the development team.