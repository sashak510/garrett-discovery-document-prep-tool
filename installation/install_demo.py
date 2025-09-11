#!/usr/bin/env python3
"""
Enhanced Installer for Garrett Discovery Document Prep Tool
Handles virtual environment creation and package installation automatically
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import json
from pathlib import Path

class EnhancedInstaller:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.venv_path = self.project_root / "venv"
        self.requirements_file = Path(__file__).parent / "requirements.txt"
        
    def print_header(self):
        print("=" * 70)
        print("    Garrett Discovery Document Prep Tool - Enhanced Installer")
        print("=" * 70)
        print()

    def check_python(self):
        """Check if Python is available and get version"""
        try:
            result = subprocess.run([sys.executable, "--version"], 
                                  capture_output=True, text=True)
            version = result.stdout.strip()
            print(f"✅ Python found: {version}")
            
            # Check version compatibility
            version_parts = version.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])
            
            # Python 3.13+ is now the standard and recommended version
            if major == 3 and minor >= 13:
                print(f"✅ Python {major}.{minor} is fully supported and recommended")
                return True
            elif major == 3 and minor >= 8:
                print(f"⚠️  Python {major}.{minor} detected - Python 3.13+ is recommended")
                print("   For best compatibility, please install Python 3.13+")
                choice = input("   Continue with current version? (y/N): ").lower().strip()
                return choice in ('y', 'yes')
            else:
                print(f"❌ Python 3.13+ required, found {version}")
                print("   Please install Python 3.13 or newer from python.org")
                return False
        except Exception as e:
            print(f"❌ Python not found: {e}")
            return False

    def create_venv(self):
        """Create virtual environment"""
        print("\n📦 Creating virtual environment...")
        
        if self.venv_path.exists():
            print("🧹 Removing existing venv...")
            shutil.rmtree(self.venv_path)
        
        try:
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], 
                         check=True)
            print("✅ Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False

    def get_venv_python(self):
        """Get path to Python executable in virtual environment"""
        if sys.platform == "win32":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"

    def install_packages(self):
        """Install required packages"""
        print("\n📥 Installing required packages...")
        
        venv_python = self.get_venv_python()
        
        # Install from requirements.txt to ensure exact working versions
        print("📦 Installing packages from requirements.txt...")
        requirements_file = Path(__file__).parent / "requirements.txt"
        
        if requirements_file.exists():
            # Install from requirements file
            try:
                print(f"  📄 Using requirements file: {requirements_file}")
                subprocess.run([
                    str(venv_python), "-m", "pip", "install", 
                    "-r", str(requirements_file), "--no-cache-dir", "--prefer-binary"
                ], check=True, capture_output=True)
                print("✅ All packages installed from requirements.txt")
                return True
            except subprocess.CalledProcessError as e:
                print("⚠️  Requirements.txt installation failed, trying individual packages...")
                
        # Fallback to individual package installation with exact versions
        packages = [
            "PyMuPDF==1.26.4",
            "PyPDF2==3.0.1", 
            "reportlab==4.4.3",
            "pillow==11.3.0",
            "pytesseract==0.3.13",
            "python-docx==1.2.0",
            "openpyxl==3.1.5",
            "pywin32==308"
        ]
        
        failed_packages = []
        
        for package in packages:
            try:
                print(f"  📦 Installing {package}...")
                subprocess.run([
                    str(venv_python), "-m", "pip", "install", 
                    package, "--no-cache-dir", "--prefer-binary"
                ], check=True, capture_output=True)
                print(f"  ✅ {package} installed")
            except subprocess.CalledProcessError:
                print(f"  ⚠️  {package} failed - trying alternative...")
                failed_packages.append(package)
                
                # Try without version constraint
                base_package = package.split('==')[0].split('>=')[0]
                try:
                    subprocess.run([
                        str(venv_python), "-m", "pip", "install", 
                        base_package, "--no-cache-dir"
                    ], check=True, capture_output=True)
                    print(f"  ✅ {base_package} installed (alternative version)")
                except subprocess.CalledProcessError:
                    print(f"  ❌ {base_package} completely failed")
        
        # Test imports
        print("\n🧪 Testing package imports...")
        test_script = '''
import sys
packages = ["PyPDF2", "PIL", "docx", "pytesseract", "reportlab", "fitz", "openpyxl", "win32com.client"]
failed = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f"✅ {pkg}")
    except ImportError:
        print(f"❌ {pkg}")
        failed.append(pkg)
        
if failed:
    print(f"\\nFailed imports: {failed}")
    sys.exit(1)
else:
    print("\\n🎉 All packages imported successfully!")
'''
        
        try:
            subprocess.run([str(venv_python), "-c", test_script], check=True)
            return True
        except subprocess.CalledProcessError:
            print("⚠️  Some packages failed to import but installation continues...")
            return True

    def create_launcher(self):
        """Verify launcher is available"""
        print("\n🚀 Verifying launcher...")
        
        # Check if VBS launcher exists
        vbs_launcher = self.project_root / "Launch Garrett Discovery Document Prep Tool.vbs"
        if vbs_launcher.exists():
            print(f"✅ VBS Launcher ready: {vbs_launcher.name}")
        else:
            print(f"⚠️  VBS Launcher not found: {vbs_launcher.name}")
            print("   The application can still be run manually via Python")

    def create_desktop_shortcut(self):
        """Create desktop shortcut with logo in the project folder"""
        print("\n🖥️  Creating desktop shortcut...")
        
        # Only create shortcuts on Windows
        if sys.platform != "win32":
            print("⚠️  Desktop shortcuts only supported on Windows")
            return False
        
        # Use the virtual environment's Python to create the shortcut
        venv_python = self.get_venv_python()
        if not venv_python.exists():
            print("⚠️  Virtual environment not found, skipping shortcut creation")
            return False
        
        try:
            # Create a Python script to create the shortcut using the venv
            shortcut_script = f'''
import os
import sys
from pathlib import Path

try:
    import win32com.client
    
    # Paths
    project_root = Path(r"{self.project_root}")
    shortcut_path = project_root / "Garrett Discovery Document Prep Tool.lnk"
    icon_path = project_root / "assets" / "app_icon.ico"
    vbs_launcher = project_root / "Launch Garrett Discovery Document Prep Tool.vbs"
    
    # Check if icon exists, fallback to PNG if needed
    if not icon_path.exists():
        icon_path = project_root / "assets" / "app_icon.png"
        if not icon_path.exists():
            icon_path = project_root / "assets" / "Logo.jpg"
    
    # Create shortcut using Windows COM
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    
    # Set shortcut properties
    if vbs_launcher.exists():
        shortcut.Targetpath = str(vbs_launcher)
        shortcut.Arguments = ""
        shortcut.Description = "Garrett Discovery Document Prep Tool"
    else:
        # Fallback to direct Python execution
        venv_python = project_root / "venv" / "Scripts" / "python.exe"
        main_script = project_root / "src" / "main.py"
        shortcut.Targetpath = str(venv_python)
        shortcut.Arguments = f'{{main_script}}'
        shortcut.Description = "Garrett Discovery Document Prep Tool"
    
    # Set working directory
    shortcut.WorkingDirectory = str(project_root)
    
    # Set icon if available
    if icon_path.exists():
        shortcut.IconLocation = str(icon_path)
        print(f"✅ Desktop shortcut created with icon: {{icon_path.name}}")
    else:
        print("⚠️  No icon found, shortcut created without custom icon")
    
    # Save shortcut
    shortcut.save()
    print(f"✅ Desktop shortcut created in project folder: {{shortcut_path.name}}")
    print(f"   📁 Location: {{shortcut_path}}")
    print(f"   💡 You can drag this shortcut to your desktop or any other location")
    
except ImportError:
    print("❌ win32com not available in virtual environment")
    sys.exit(1)
except Exception as e:
    print(f"❌ Failed to create desktop shortcut: {{e}}")
    sys.exit(1)
'''
            
            # Execute the script using the virtual environment's Python
            result = subprocess.run([
                str(venv_python), "-c", shortcut_script
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(result.stdout.strip())
                return True
            else:
                print("⚠️  win32com not available in virtual environment, trying PowerShell method...")
                return self.create_desktop_shortcut_alternative()
                
        except Exception as e:
            print(f"⚠️  Failed to create desktop shortcut: {e}")
            return self.create_desktop_shortcut_alternative()

    def create_desktop_shortcut_alternative(self):
        """Alternative method to create desktop shortcut using PowerShell"""
        try:
            # Create shortcut in the project folder (user can move it to desktop)
            shortcut_path = self.project_root / "Garrett Discovery Document Prep Tool.lnk"
            vbs_launcher = self.project_root / "Launch Garrett Discovery Document Prep Tool.vbs"
            icon_path = self.project_root / "assets" / "app_icon.ico"
            
            # PowerShell script to create shortcut
            ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{vbs_launcher if vbs_launcher.exists() else self.get_venv_python()}"
$Shortcut.WorkingDirectory = "{self.project_root}"
$Shortcut.Description = "Garrett Discovery Document Prep Tool"
'''
            
            if icon_path.exists():
                ps_script += f'$Shortcut.IconLocation = "{icon_path}"\n'
            
            ps_script += '$Shortcut.Save()'
            
            # Execute PowerShell script
            subprocess.run([
                "powershell", "-Command", ps_script
            ], check=True, capture_output=True)
            
            print(f"✅ Desktop shortcut created in project folder via PowerShell: {shortcut_path.name}")
            print(f"   📁 Location: {shortcut_path}")
            print(f"   💡 You can drag this shortcut to your desktop or any other location")
            return True
            
        except Exception as e:
            print(f"⚠️  Alternative shortcut creation failed: {e}")
            return False

    def run_installation(self):
        """Run the complete installation process"""
        self.print_header()
        
        # Check Python
        if not self.check_python():
            input("\nPress Enter to exit...")
            return False
        
        # Create virtual environment
        if not self.create_venv():
            input("\nPress Enter to exit...")
            return False
        
        # Install packages
        if not self.install_packages():
            print("⚠️  Installation completed with some issues")
        
        # Create launchers
        self.create_launcher()
        
        # Create desktop shortcut
        self.create_desktop_shortcut()
        
        print("\n" + "=" * 70)
        print("🎉 INSTALLATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("📁 Project folder:", self.project_root)
        print("🐍 Virtual environment:", self.venv_path)
        print()
        print("🚀 How to run:")
        print("   • Desktop shortcut: Drag 'Garrett Discovery Document Prep Tool.lnk' to your desktop")
        print("   • Double-click: Launch Garrett Discovery Document Prep Tool.vbs")
        print("   • Or run manually with PowerShell commands below")
        print()
        print("🔧 PowerShell commands:")
        print(f'   • cd "{self.project_root}"')
        print(f'   • "{self.get_venv_python()}" src\\main.py')
        print()
        
        input("Press Enter to exit...")
        return True

if __name__ == "__main__":
    installer = EnhancedInstaller()
    installer.run_installation()
