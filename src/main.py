#!/usr/bin/env python3
"""
Garrett Discovery Document Prep Tool
A Windows GUI application for processing documents with bates numbering and line numbering.

Requirements:
- Select folder for processing
- Scan for PDF, TIFF, Word, and text files
- Convert to PDF with OCR
- Add line numbers and bates numbering
- Generate comprehensive logs
"""

import sys
import os
import json
import threading
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar, QFrame,
    QGroupBox, QFileDialog, QMessageBox, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QObject, QTimer, QSize
)
from PyQt6.QtGui import (
    QIcon, QFont, QPixmap, QPainter, QPalette, QColor,
    QAction, QKeySequence, QCursor
)

# Import our custom modules
from .document_processor import GDIDocumentProcessor
from .file_scanner import FileScanner
from .pdf_converter import PDFConverter
from .bates_numbering import BatesNumberer
from .logger_manager import LoggerManager
from .error_handling import ErrorHandler, ValidationError
from .dependency_checker import DependencyChecker


class ProcessingWorker(QObject):
    """Worker thread for document processing to prevent UI freezing"""

    # Signals for communication with main thread
    progress_update = pyqtSignal(int, str)  # progress percentage, current file
    log_message = pyqtSignal(str)
    processing_complete = pyqtSignal(bool, str)  # success, message
    error_occurred = pyqtSignal(str)

    def __init__(self, processor):
        super().__init__()
        self.processor = processor
        self._is_running = False
        self._should_stop = False

    def run_processing(self):
        """Run the document processing"""
        self._is_running = True
        self._should_stop = False

        try:
            success = self.processor.process_all_documents()
            if success and not self._should_stop:
                self.processing_complete.emit(True, "Document preparation completed successfully!")
            elif self._should_stop:
                self.processing_complete.emit(False, "Processing was stopped by user.")
            else:
                self.processing_complete.emit(False, "Processing completed with errors.")
        except Exception as e:
            self.error_occurred.emit(f"An error occurred during processing: {str(e)}")
        finally:
            self._is_running = False

    def stop_processing(self):
        """Stop the processing"""
        self._should_stop = True
        if hasattr(self.processor, 'stop_processing'):
            self.processor.stop_processing()

    def is_running(self) -> bool:
        return self._is_running


class GDIDocumentPrepGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window setup
        self.setWindowTitle("Garrett Discovery Document Prep Tool")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 600)

        # Variables
        self.input_folder = ""
        self.output_folder = ""
        self.file_naming_start = "0001"
        self.bates_prefix = ""
        self.bates_start_number = "0001"
        self.is_processing = False
        self.processor = None
        self.dark_mode = False

        # Config file path
        self.config_file = Path(__file__).parent.parent / "config.json"

        # Processing thread
        self.processing_worker = None
        self.processing_thread = None

# Import our custom modules
from .document_processor import GDIDocumentProcessor
from .file_scanner import FileScanner
from .pdf_converter import PDFConverter
from .bates_numbering import BatesNumberer
from .logger_manager import LoggerManager
from .error_handling import ErrorHandler, ValidationError
from .dependency_checker import DependencyChecker

        # Setup UI first (needed for logging)
        self.setup_ui()

        # Check dependencies after UI is ready
        self.dependency_checker = DependencyChecker(log_callback=self.log_message)
        dependency_status = self.dependency_checker.check_dependencies()

        # If required dependencies are missing, show error and exit
        if not self.dependency_checker.can_start_application():
            missing_deps = self.dependency_checker.get_missing_required_dependencies()
            error_msg = f"Required dependencies missing: {', '.join(missing_deps)}\n\nPlease install the required dependencies using the installer."
            QMessageBox.critical(self, "Missing Dependencies", error_msg)
            sys.exit(1)

        # Load saved settings
        self._load_settings()

        # Apply theme
        self.apply_theme()

        # Show startup info
        self._show_startup_info()

        # Center window
        self.center_window()

        # Set window icon
        self.set_app_icon()

        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()

    def setup_keyboard_shortcuts(self):
        """Configure keyboard shortcuts for better accessibility"""
        # Create actions for keyboard shortcuts
        # Ctrl+O for opening input folder
        input_folder_action = QAction("Open Input Folder", self)
        input_folder_action.setShortcut(QKeySequence("Ctrl+O"))
        input_folder_action.triggered.connect(self.browse_input_folder)
        self.addAction(input_folder_action)

        # Ctrl+S for opening output folder
        output_folder_action = QAction("Open Output Folder", self)
        output_folder_action.setShortcut(QKeySequence("Ctrl+S"))
        output_folder_action.triggered.connect(self.browse_output_folder)
        self.addAction(output_folder_action)

        # Ctrl+Enter or F5 to start processing
        start_processing_action = QAction("Start Processing", self)
        start_processing_action.setShortcut(QKeySequence("Ctrl+Return"))
        start_processing_action.triggered.connect(self.start_processing)
        self.addAction(start_processing_action)

        f5_action = QAction("Start Processing", self)
        f5_action.setShortcut(QKeySequence("F5"))
        f5_action.triggered.connect(self.start_processing)
        self.addAction(f5_action)

        # Ctrl+P or Escape to pause/resume processing
        pause_action = QAction("Pause/Resume", self)
        pause_action.setShortcut(QKeySequence("Ctrl+P"))
        pause_action.triggered.connect(self.pause_processing)
        self.addAction(pause_action)

        escape_action = QAction("Pause/Resume", self)
        escape_action.setShortcut(QKeySequence("Escape"))
        escape_action.triggered.connect(self.pause_processing)
        self.addAction(escape_action)

        # Ctrl+L to clear log
        clear_log_action = QAction("Clear Log", self)
        clear_log_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_log_action.triggered.connect(self.clear_log)
        self.addAction(clear_log_action)

        # Ctrl+D to toggle dark mode
        toggle_theme_action = QAction("Toggle Theme", self)
        toggle_theme_action.setShortcut(QKeySequence("Ctrl+D"))
        toggle_theme_action.triggered.connect(self.toggle_theme)
        self.addAction(toggle_theme_action)

        # Ctrl+W or Ctrl+Q to exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+W"))
        exit_action.triggered.connect(self.close)
        self.addAction(exit_action)

        exit_action2 = QAction("Exit", self)
        exit_action2.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action2.triggered.connect(self.close)
        self.addAction(exit_action2)

        # F1 for help
        help_action = QAction("Help", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self.show_help)
        self.addAction(help_action)

    def show_help(self):
        """Show help dialog with keyboard shortcuts"""
        help_text = """Garrett Discovery Document Prep Tool - Keyboard Shortcuts

File Operations:
• Ctrl+O: Browse for input folder
• Ctrl+S: Browse for output folder

Processing:
• Ctrl+Enter or F5: Start processing
• Ctrl+P or Escape: Pause/Resume processing
• Ctrl+L: Clear log

Interface:
• Ctrl+D: Toggle dark/light theme
• Tab: Navigate between fields
• Shift+Tab: Navigate backwards

Application:
• F1: Show this help
• Ctrl+W or Ctrl+Q: Exit application

Tips:
• Use Tab to navigate between input fields
• Press Enter to trigger default button actions
• All fields are validated before processing
• Settings are automatically saved"""

        # Create help dialog
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("Keyboard Shortcuts Help")
        help_dialog.setTextFormat(Qt.TextFormat.RichText)
        help_dialog.setText(help_text.replace('\n', '<br>'))
        help_dialog.exec()

    def setup_ui(self):
        """Set up the user interface"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Create header
        header_widget = self.create_header()
        main_layout.addWidget(header_widget)

        # Create form section
        form_widget = self.create_form_section()
        main_layout.addWidget(form_widget)

        # Create progress section
        progress_widget = self.create_progress_section()
        main_layout.addWidget(progress_widget)

        # Create button section
        button_widget = self.create_button_section()
        main_layout.addWidget(button_widget)

        # Create status bar
        self.statusBar().showMessage("Ready")

    def create_header(self):
        """Create the header section"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title_label = QLabel("Garrett Discovery Document Prep Tool")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Compact theme toggle button with enhanced icons
        self.theme_button = QPushButton("☀️")  # Start with sun for light mode
        self.theme_button.setFixedSize(40, 40)
        self.theme_button.setToolTip("Toggle dark/light theme (Ctrl+D)")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Compact professional styling for theme button
        self.theme_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                color: #333333;
                font-size: 20px;
                font-weight: bold;
                padding: 2px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                transition: all 0.2s ease;
            }
            QPushButton:hover {
                border-color: #0078d4;
                background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
                box-shadow: 0 3px 6px rgba(0, 120, 212, 0.2);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                border-color: #005a9e;
                background: linear-gradient(135deg, #e6f3ff 0%, #d4e9ff 100%);
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
                transform: translateY(0px);
            }
        """)

        header_layout.addWidget(self.theme_button)

        return header_widget

    def create_form_section(self):
        """Create the form input section"""
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)
        form_layout.setSpacing(10)

        # Input folder
        form_layout.addWidget(QLabel("Input Folder:"), 0, 0)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Select input folder...")
        form_layout.addWidget(self.input_edit, 0, 1)

        self.input_browse_btn = QPushButton("Browse")
        self.input_browse_btn.clicked.connect(self.browse_input_folder)
        form_layout.addWidget(self.input_browse_btn, 0, 2)

        # Output folder
        form_layout.addWidget(QLabel("Output Folder:"), 1, 0)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output folder...")
        form_layout.addWidget(self.output_edit, 1, 1)

        self.output_browse_btn = QPushButton("Browse")
        self.output_browse_btn.clicked.connect(self.browse_output_folder)
        form_layout.addWidget(self.output_browse_btn, 1, 2)

        # File naming settings
        file_naming_group = QGroupBox("File Naming")
        file_naming_layout = QHBoxLayout(file_naming_group)

        file_naming_layout.addWidget(QLabel("Starting Number:"))
        self.file_naming_edit = QLineEdit()
        self.file_naming_edit.setFixedWidth(80)
        self.file_naming_edit.setText("0001")
        file_naming_layout.addWidget(self.file_naming_edit)
        file_naming_layout.addStretch()

        form_layout.addWidget(file_naming_group, 2, 0, 1, 3)

        # Bates numbering settings
        bates_group = QGroupBox("Bates Numbering Settings")
        bates_layout = QGridLayout(bates_group)

        bates_layout.addWidget(QLabel("Prefix (optional):"), 0, 0)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("e.g., ABC")
        bates_layout.addWidget(self.prefix_edit, 0, 1)

        bates_layout.addWidget(QLabel("Starting Number:"), 1, 0)
        self.number_edit = QLineEdit()
        self.number_edit.setFixedWidth(80)
        self.number_edit.setText("0001")
        bates_layout.addWidget(self.number_edit, 1, 1)

        form_layout.addWidget(bates_group, 3, 0, 1, 3)

        # Set column stretch
        form_layout.setColumnStretch(1, 1)

        return form_widget

    def create_progress_section(self):
        """Create the progress and logging section"""
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(10)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Log display
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 10, 10, 10)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Monaco", 9))  # Use Monaco on macOS instead of Consolas
        log_layout.addWidget(self.log_display)

        progress_layout.addWidget(log_group)

        return progress_widget

    def create_button_section(self):
        """Create the button control section"""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        # Process button
        self.process_button = QPushButton("Start Processing")
        self.process_button.clicked.connect(self.start_processing)
        button_layout.addWidget(self.process_button)

        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_processing)
        button_layout.addWidget(self.pause_button)

        button_layout.addStretch()

        # Clear log button
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_log_btn)

        # Open folder button
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        button_layout.addWidget(self.open_folder_btn)

        return button_widget

    def center_window(self):
        """Center the window on screen"""
        # Get screen dimensions
        screen = self.screen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # Get window dimensions
        window_width = self.width()
        window_height = self.height()

        # Use minimum size if actual size is too small
        if window_width < 800:
            window_width = 800
        if window_height < 600:
            window_height = 600

        # Calculate center position
        x = max(0, (screen_width - window_width) // 2)
        y = max(0, (screen_height - window_height) // 2)

        # Set position
        self.move(x, y)
        
    def set_app_icon(self):
        """Set the application icon"""
        try:
            # Windows-specific taskbar icon fix
            if sys.platform == "win32":
                import ctypes
                # Set the application ID to ensure taskbar icon works
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GDIDocumentPrep.1.0")

            # Set the window icon
            icon_path = Path(__file__).parent.parent / "assets" / "app_icon.ico"

            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
            else:
                # Fallback - PNG only
                png_path = Path(__file__).parent.parent / "assets" / "app_icon.png"
                if png_path.exists():
                    self.setWindowIcon(QIcon(str(png_path)))

        except Exception as e:
            # Continue without icon - not critical for functionality
            print(f"Note: Could not set application icon: {e}")
        
        # Initialize components
        self.file_scanner = FileScanner(log_callback=self.log_message)
        self.pdf_converter = PDFConverter(log_callback=self.log_message)
        self.bates_numberer = BatesNumberer(log_callback=self.log_message)
        self.logger_manager = LoggerManager(log_callback=self.log_message)
        self.error_handler = ErrorHandler(log_callback=self.log_message)

    def browse_input_folder(self):
        """Open input folder selection dialogue"""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            try:
                # Sanitize the input path
                sanitized_path = Path(folder).resolve()

                # Validate folder accessibility
                if not sanitized_path.exists() or not sanitized_path.is_dir():
                    QMessageBox.critical(self, "Error", "Selected folder is not accessible or doesn't exist.")
                    return

                self.input_edit.setText(str(sanitized_path))

                # Auto-create output folder path as input_folder + '_Processed'
                auto_output_path = sanitized_path.parent / f"{sanitized_path.name}_Processed"
                self.output_edit.setText(str(auto_output_path))

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error selecting folder: {str(e)}")

    def browse_output_folder(self):
        """Open output folder selection dialogue"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            try:
                # Sanitize the input path
                sanitized_path = Path(folder).resolve()

                # Validate folder accessibility (write required for output)
                if not sanitized_path.exists() or not sanitized_path.is_dir():
                    QMessageBox.critical(self, "Error", "Selected output folder is not accessible or doesn't exist.")
                    return

                self.output_edit.setText(str(sanitized_path))

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error selecting folder: {str(e)}")

    def start_processing(self):
        """Start the document preparation"""
        # Get values from UI controls
        input_folder = self.input_edit.text()
        output_folder = self.output_edit.text()
        file_naming_start = self.file_naming_edit.text()
        bates_prefix = self.prefix_edit.text()
        bates_start_number = self.number_edit.text()

        if not input_folder:
            QMessageBox.critical(self, "Error", "Please select an input folder.")
            return

        if not output_folder:
            QMessageBox.critical(self, "Error", "Please select an output folder.")
            return

        if not os.path.exists(input_folder):
            QMessageBox.critical(self, "Error", "Input folder does not exist.")
            return

        # Create output folder if it doesn't exist
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot create output folder: {str(e)}")
            return

        # Validate file naming starting number
        try:
            file_start = int(file_naming_start)
        except ValueError:
            QMessageBox.critical(self, "Error", "File naming starting number must be a valid number.")
            return

        try:
            int(bates_start_number)
        except ValueError:
            QMessageBox.critical(self, "Error", "Starting number must be a valid integer.")
            return

        # Store values
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.file_naming_start = file_naming_start
        self.bates_prefix = bates_prefix
        self.bates_start_number = bates_start_number

        # Initialize processor with current settings
        self.processor = GDIDocumentProcessor(
            source_folder=self.input_folder,
            bates_prefix=self.bates_prefix,
            bates_start_number=int(self.bates_start_number),
            file_naming_start=int(self.file_naming_start),
            output_folder=self.output_folder,
            log_callback=self.log_message,
            bates_numberer=self.bates_numberer
        )

        # Setup processing worker and thread
        self.processing_worker = ProcessingWorker(self.processor)
        self.processing_thread = QThread()
        self.processing_worker.moveToThread(self.processing_thread)

        # Connect signals
        self.processing_thread.started.connect(self.processing_worker.run_processing)
        self.processing_worker.progress_update.connect(self.update_progress)
        self.processing_worker.log_message.connect(self.log_message)
        self.processing_worker.processing_complete.connect(self.processing_finished)
        self.processing_worker.error_occurred.connect(self.processing_error)

        # Update UI state
        self.is_processing = True
        self.process_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Start processing
        self.processing_thread.start()

    def update_progress(self, progress: int, message: str):
        """Update progress bar and status"""
        self.progress_bar.setValue(progress)
        self.statusBar().showMessage(message)

    def processing_finished(self, success: bool, message: str):
        """Handle processing completion"""
        self.is_processing = False
        self.process_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Processing Complete", message)

    def processing_error(self, error_message: str):
        """Handle processing errors"""
        self.is_processing = False
        self.process_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", error_message)

    def pause_processing(self):
        """Pause/Resume the document preparation"""
        if self.is_processing:
            # Stop processing
            if self.processing_worker:
                self.processing_worker.stop_processing()
            self.is_processing = False
            self.pause_button.setText("Resume")
            self.log_message("Processing paused")
        else:
            # Resume processing (would need to implement resume logic)
            self.log_message("Resume functionality not yet implemented")

    def clear_log(self):
        """Clear the log display"""
        self.log_display.clear()

    def open_output_folder(self):
        """Open the output folder in system file manager"""
        output_folder = self.output_edit.text()
        if not output_folder:
            QMessageBox.warning(self, "Warning", "No output folder selected.")
            return

        output_path = Path(output_folder)
        if not output_path.exists():
            QMessageBox.warning(self, "Warning", f"Output folder does not exist: {output_path}")
            return

        try:
            if sys.platform == "win32":
                os.startfile(str(output_path))
            else:
                import subprocess
                subprocess.run(['xdg-open', str(output_path)])

            self.log_message(f"Opened output folder: {output_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open output folder: {str(e)}")
            self.log_message(f"Error opening output folder: {str(e)}")

    def log_message(self, message: str):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.log_display.append(formatted_message)

    def toggle_theme(self):
        """Toggle between light and dark themes with professional icons and smooth transitions"""
        self.dark_mode = not self.dark_mode
        self.apply_theme()

        # Professional theme icons with better visibility and meaning
        if self.dark_mode:
            # Elegant crescent moon for dark mode (when switching to dark)
            self.theme_button.setText("🌙")
        else:
            # Bright sun for light mode (when switching to light)
            self.theme_button.setText("☀️")

        # Compact theme-aware styling with enhanced visual feedback
        if self.dark_mode:
            button_style = """
                QPushButton {
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-radius: 20px;
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 2px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                    transition: all 0.2s ease;
                }
                QPushButton:hover {
                    border-color: rgba(255, 255, 255, 0.5);
                    background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
                    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.4);
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    border-color: rgba(255, 255, 255, 0.7);
                    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
                    transform: translateY(0px);
                }
            """
        else:
            button_style = """
                QPushButton {
                    border: 2px solid #e0e0e0;
                    border-radius: 20px;
                    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                    color: #333333;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 2px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    transition: all 0.2s ease;
                }
                QPushButton:hover {
                    border-color: #0078d4;
                    background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
                    box-shadow: 0 3px 6px rgba(0, 120, 212, 0.2);
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    border-color: #005a9e;
                    background: linear-gradient(135deg, #e6f3ff 0%, #d4e9ff 100%);
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
                    transform: translateY(0px);
                }
            """

        self.theme_button.setStyleSheet(button_style)

        # Log the theme change
        theme_name = "Dark Mode" if self.dark_mode else "Light Mode"
        self.log_message(f"Switched to {theme_name}")

    def apply_theme(self):
        """Apply the current theme"""
        if self.dark_mode:
            # Dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QLineEdit {
                    background-color: #404040;
                    border: 1px solid #555555;
                    color: #ffffff;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #0078d4;
                    border: none;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QPushButton:disabled {
                    background-color: #555555;
                    color: #888888;
                }
                QGroupBox {
                    border: 1px solid #555555;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #555555;
                    color: #d4d4d4;
                    font-family: Monaco, monospace;
                }
                QProgressBar {
                    border: 1px solid #555555;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #404040;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QWidget {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QLineEdit {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    color: #000000;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #e1e1e1;
                    border: 1px solid #cccccc;
                    color: #000000;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #888888;
                }
                QGroupBox {
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    color: #000000;
                    font-family: Monaco, monospace;
                }
                QProgressBar {
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                }
            """)

    def _show_startup_info(self):
        """Show startup information about available features"""
        self.log_message("Application started successfully")
        self.log_message("Available features:")

        features = self.dependency_checker.get_available_features()
        for feature, available in features.items():
            status = "✅" if available else "❌"
            feature_name = feature.replace("_", " ").title()
            self.log_message(f"   {status} {feature_name}")

        # Show any warnings about missing optional dependencies
        missing_optional = []
        for dep_name, dep_info in self.dependency_checker.dependencies.items():
            if not dep_info.required and self.dependency_checker._dependency_status.get(dep_name) == "missing":
                missing_optional.append(dep_info.name)

        if missing_optional:
            self.log_message("⚠️  Optional dependencies not available:")
            for dep in missing_optional:
                dep_info = self.dependency_checker.dependencies[dep_name]
                self.log_message(f"   • {dep}: {dep_info.impact_if_missing}")

        self.log_message("Ready to process documents")

    def closeEvent(self, event):
        """Handle window closing event"""
        # Stop any running processing
        if self.is_processing and self.processing_worker:
            self.processing_worker.stop_processing()

        # Clean up thread
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.quit()
            self.processing_thread.wait()

        event.accept()

    def _load_settings(self):
        """Load saved settings from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)

                # Load file naming settings
                if 'file_naming_start' in config:
                    self.file_naming_edit.setText(config['file_naming_start'])

                # Load bates settings
                if 'bates_prefix' in config:
                    self.prefix_edit.setText(config['bates_prefix'])

                if 'bates_start_number' in config:
                    self.number_edit.setText(config['bates_start_number'])

                # Load dark mode setting
                if 'dark_mode' in config:
                    self.dark_mode = config['dark_mode']
                    # Set appropriate icon based on loaded theme
                    self.theme_button.setText("🌞" if self.dark_mode else "🌙")

        except Exception as e:
            # If config file is corrupted or can't be read, just use defaults
            print(f"Note: Could not load settings: {e}")

    def _save_settings(self):
        """Save current settings to config file"""
        try:
            config = {
                'file_naming_start': self.file_naming_edit.text(),
                'bates_prefix': self.prefix_edit.text(),
                'bates_start_number': self.number_edit.text(),
                'dark_mode': self.dark_mode
            }

            # Create directory if it doesn't exist
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            # Don't show error to user - settings saving is not critical
            print(f"Note: Could not save settings: {e}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    # Set application info
    app.setApplicationName("Garrett Discovery Document Prep Tool")
    app.setApplicationVersion("1.0")

    # Create and show main window
    window = GDIDocumentPrepGUI()
    window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
