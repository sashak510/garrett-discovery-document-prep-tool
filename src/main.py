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

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
import logging
import json
from pathlib import Path
from datetime import datetime

# Import our custom modules
from document_processor import GDIDocumentProcessor
from file_scanner import FileScanner
from pdf_converter import PDFConverter
from line_numbering import LineNumberer
from bates_numbering import BatesNumberer
from logger_manager import LoggerManager


class GDIDocumentPrepGUI:
    def __init__(self, root):
        self.root = root
        
        # Hide window initially to prevent glitching during setup
        self.root.withdraw()
        
        # Set window icon EARLY for better taskbar integration
        self._set_window_icon()
        
        self.root.title("Garrett Discovery Document Prep Tool")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Config file path
        self.config_file = Path(__file__).parent.parent / "config.json"
        
        # Variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        # File naming variables
        self.file_naming_start = tk.StringVar(value="0001")
        
        # Bates numbering variables  
        self.bates_prefix = tk.StringVar(value="")
        self.bates_start_number = tk.StringVar(value="0001")
        self.processing = False
        self.processor = None  # Reference to the document processor
        
        # Settings variables (colors are now hardcoded)
        # Line numbers: Nice red color, Times New Roman font
        # Bates numbers: Black color, Times New Roman font
        
        # Dark mode state
        self.dark_mode = tk.BooleanVar(value=False)
        
        # Settings removed - colors are hardcoded in base pipeline
        
        # Load saved settings (file naming and bates only)
        self._load_settings()
        
        # Initialize components
        self.file_scanner = FileScanner()
        self.pdf_converter = PDFConverter()
        self.line_numberer = LineNumberer()
        self.bates_numberer = BatesNumberer()
        self.logger_manager = LoggerManager()
        
        # Apply loaded settings to components (but not dark mode yet - widgets don't exist)
        self._apply_loaded_settings()
        
        self.setup_ui()
        
        # Apply dark mode after UI is created
        self.apply_dark_mode()
        
        # Update dark mode button image after UI is created
        if hasattr(self, 'dark_mode_button') and hasattr(self, 'night_mode_off_image') and hasattr(self, 'night_mode_on_image'):
            if self.dark_mode.get():
                self.dark_mode_button.configure(image=self.night_mode_on_image)
                self.dark_mode_button.image = self.night_mode_on_image
            else:
                self.dark_mode_button.configure(image=self.night_mode_off_image)
                self.dark_mode_button.image = self.night_mode_off_image
        
        # Center window and show it cleanly
        self._center_window()
        self.root.deiconify()
        
        # Save settings when window is closed
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def setup_ui(self):
        """Set up the user interface"""
        # Main frame - reduced padding for more compact look
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title and settings - more compact
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 12), sticky=(tk.W, tk.E))
        title_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(title_frame, text="Garrett Discovery Document Prep Tool", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Settings removed - colors are hardcoded in base pipeline
        
        # Dark mode toggle button with image
        try:
            # Try to load the night mode images from assets directory
            self.night_mode_off_image = tk.PhotoImage(file="assets/night-mode.png")
            self.night_mode_on_image = tk.PhotoImage(file="assets/night-mode (1).png")
            # Resize if needed
            self.night_mode_off_image = self.night_mode_off_image.subsample(32, 32)
            self.night_mode_on_image = self.night_mode_on_image.subsample(32, 32)
            
            # Create dark mode button with initial image
            self.dark_mode_button = ttk.Button(title_frame, 
                                             image=self.night_mode_off_image, 
                                             width=4,
                                             command=self.toggle_dark_mode)
            # Keep references to prevent garbage collection
            self.dark_mode_button.image = self.night_mode_off_image
        except (tk.TclError, FileNotFoundError):
            # Fallback to text if images not found
            self.dark_mode_button = ttk.Button(title_frame, text="🌙", width=4,
                                             command=self.toggle_dark_mode)
        self.dark_mode_button.grid(row=0, column=2, sticky=tk.E, padx=(0, 0))
        
        # Input folder selection - more compact
        ttk.Label(main_frame, text="Input Folder:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.input_entry = ttk.Entry(main_frame, textvariable=self.input_folder, width=45)
        self.input_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(8, 4), pady=3)
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_input_folder).grid(row=1, column=2, pady=3, padx=(4, 0))
        
        # Output folder selection - more compact
        ttk.Label(main_frame, text="Output Folder:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_folder, width=45)
        self.output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(8, 4), pady=3)
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_output_folder).grid(row=2, column=2, pady=3, padx=(4, 0))
        
        # File naming settings
        self.file_naming_frame = ttk.LabelFrame(main_frame, text="File Naming", padding="6")
        self.file_naming_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=6)
        self.file_naming_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.file_naming_frame, text="Starting Number:").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.file_naming_entry = ttk.Entry(self.file_naming_frame, textvariable=self.file_naming_start, width=8)
        self.file_naming_entry.grid(row=0, column=1, sticky=tk.W, padx=(6, 0), pady=1)
        self.file_naming_entry.bind('<FocusOut>', lambda e: self._save_settings())
        
        # Bates numbering settings - more compact
        self.bates_frame = ttk.LabelFrame(main_frame, text="Bates Numbering Settings", padding="6")
        self.bates_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=6)
        self.bates_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.bates_frame, text="Prefix (optional):").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.prefix_entry = ttk.Entry(self.bates_frame, textvariable=self.bates_prefix, width=8)
        self.prefix_entry.grid(row=0, column=1, sticky=tk.W, padx=(6, 0), pady=1)
        self.prefix_entry.bind('<FocusOut>', lambda e: self._save_settings())
        
        ttk.Label(self.bates_frame, text="Starting Number:").grid(row=1, column=0, sticky=tk.W, pady=1)
        self.number_entry = ttk.Entry(self.bates_frame, textvariable=self.bates_start_number, width=8)
        self.number_entry.grid(row=1, column=1, sticky=tk.W, padx=(6, 0), pady=1)
        self.number_entry.bind('<FocusOut>', lambda e: self._save_settings())
        
        # Progress section - more compact
        self.progress_frame = ttk.LabelFrame(main_frame, text="Processing Progress", padding="6")
        self.progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=6)
        self.progress_frame.columnconfigure(0, weight=1)
        self.progress_frame.rowconfigure(1, weight=1)
        
        # Progress bar - more compact
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
        
        # Log display with horizontal scrollbar - more compact
        self.log_display = scrolledtext.ScrolledText(self.progress_frame, height=12, width=65, wrap=tk.NONE, state='disabled')
        self.log_display.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add horizontal scrollbar
        self.h_scrollbar = ttk.Scrollbar(self.progress_frame, orient=tk.HORIZONTAL, command=self.log_display.xview)
        self.h_scrollbar.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self.log_display.config(xscrollcommand=self.h_scrollbar.set)
        
        # Control buttons - more compact
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=6)
        
        self.process_button = ttk.Button(button_frame, text="Start Processing", 
                                       command=self.start_processing)
        self.process_button.pack(side=tk.LEFT, padx=3)
        
        self.pause_button = ttk.Button(button_frame, text="Pause", 
                                     command=self.pause_processing, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=3)
        
        ttk.Button(button_frame, text="Clear Log", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(button_frame, text="Open Folder", 
                  command=self.open_output_folder).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(button_frame, text="Exit", 
                  command=self.root.quit).pack(side=tk.LEFT, padx=3)
        
        # Configure grid weights for main_frame
        main_frame.rowconfigure(4, weight=1)
        
    def _center_window(self):
        """Center the window on screen"""
        # Force window to update and calculate actual size
        self.root.update_idletasks()
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Get window dimensions (use requested size if actual size not available)
        window_width = self.root.winfo_reqwidth()
        window_height = self.root.winfo_reqheight()
        
        # If requested size is too small, use minimum size
        if window_width < 800:
            window_width = 800
        if window_height < 600:
            window_height = 600
            
        # Calculate center position
        x = max(0, (screen_width - window_width) // 2)
        y = max(0, (screen_height - window_height) // 2)
        
        # Ensure window doesn't go off screen
        if x + window_width > screen_width:
            x = screen_width - window_width
        if y + window_height > screen_height:
            y = screen_height - window_height
            
        # Set position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
    def _set_window_icon(self):
        """Set the window icon for both the window and taskbar"""
        try:
            # Windows-specific taskbar icon fix
            if sys.platform == "win32":
                import ctypes
                # Set the application ID to ensure taskbar icon works
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GDIDocumentPrep.1.0")
            
            # Set the taskbar and window icon using ICO file
            icon_path = Path(__file__).parent.parent / "assets" / "app_icon.ico"
            
            if icon_path.exists():
                # Set window icon using iconbitmap (most reliable for taskbar)
                self.root.iconbitmap(str(icon_path))
                
                # Also set using iconphoto for additional compatibility
                try:
                    # Load PNG version for iconphoto
                    png_path = Path(__file__).parent.parent / "assets" / "app_icon.png"
                    if png_path.exists():
                        icon_image = tk.PhotoImage(file=str(png_path))
                        self.root.iconphoto(True, icon_image)
                        # Keep a reference to prevent garbage collection
                        self.icon_image = icon_image
                except:
                    pass
                    
            else:
                # Fallback - PNG only
                png_path = Path(__file__).parent.parent / "assets" / "app_icon.png"
                if png_path.exists():
                    icon_image = tk.PhotoImage(file=str(png_path))
                    self.root.iconphoto(True, icon_image)
                    self.icon_image = icon_image
                    
        except Exception as e:
            # Continue without icon - not critical for functionality
            print(f"Note: Could not set application icon: {e}")
            pass
        
    def browse_input_folder(self):
        """Open input folder selection dialogue"""
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_folder.set(folder)
            
            # Auto-create output folder path as input_folder + '_Processed'
            input_path = Path(folder)
            auto_output_path = input_path.parent / f"{input_path.name}_Processed"
            
            # Always update output folder to match the new input folder
            # Convert to forward slashes for consistency with input folder display
            self.output_folder.set(str(auto_output_path).replace('\\', '/'))
            
    def browse_output_folder(self):
        """Open output folder selection dialogue"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            
    def log_message(self, message):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Update GUI in main thread
        self.root.after(0, lambda: self._update_log_display(formatted_message))
        
    def _update_log_display(self, message):
        """Update log display (must be called from main thread)"""
        # Temporarily enable editing to insert message
        self.log_display.config(state='normal')
        self.log_display.insert(tk.END, message)
        self.log_display.see(tk.END)
        # Disable editing again
        self.log_display.config(state='disabled')
        
    def clear_log(self):
        """Clear the log display"""
        # Temporarily enable editing to clear content
        self.log_display.config(state='normal')
        self.log_display.delete(1.0, tk.END)
        # Disable editing again
        self.log_display.config(state='disabled')
        
    def open_output_folder(self):
        """Open the output folder in Windows Explorer"""
        if not self.output_folder.get():
            messagebox.showwarning("Warning", "No output folder selected.")
            return
            
        output_path = Path(self.output_folder.get())
        if not output_path.exists():
            messagebox.showwarning("Warning", f"Output folder does not exist: {output_path}")
            return
            
        try:
            # Use Windows-specific command to open folder
            if sys.platform == "win32":
                os.startfile(str(output_path))
            else:
                # For other platforms, try to open with default file manager
                import subprocess
                subprocess.run(['xdg-open', str(output_path)])
                
            self.log_message(f"Opened output folder: {output_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open output folder: {str(e)}")
            self.log_message(f"Error opening output folder: {str(e)}")
        
    def start_processing(self):
        """Start the document preparation"""
        if not self.input_folder.get():
            messagebox.showerror("Error", "Please select an input folder.")
            return
            
        if not self.output_folder.get():
            messagebox.showerror("Error", "Please select an output folder.")
            return
            
        if not os.path.exists(self.input_folder.get()):
            messagebox.showerror("Error", "Input folder does not exist.")
            return
            
        # Create output folder if it doesn't exist
        try:
            os.makedirs(self.output_folder.get(), exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output folder: {str(e)}")
            return
            
        # Validate file naming starting number
        try:
            file_start = int(self.file_naming_start.get())
        except ValueError:
            messagebox.showerror("Error", "File naming starting number must be a valid number.")
            return
            
        try:
            int(self.bates_start_number.get())
        except ValueError:
            messagebox.showerror("Error", "Starting number must be a valid integer.")
            return
            
        # Apply current settings before processing
        self._apply_loaded_settings()
        
        # Start processing in background thread
        self.processing = True
        self.process_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.progress_bar.start()
        
        # Create and start processing thread
        self.processing_thread = threading.Thread(target=self._process_documents)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def pause_processing(self):
        """Pause the document preparation"""
        self.processing = False
        # Tell the processor to stop as well
        if self.processor:
            self.processor.stop_processing()
        self.log_message("Pausing processing...")
        
    def _process_documents(self):
        """Main document preparation logic (runs in background thread)"""
        try:
            source_folder = self.input_folder.get()
            output_folder = self.output_folder.get()
            file_naming_start = int(self.file_naming_start.get())
            bates_prefix = self.bates_prefix.get().strip()
            bates_start = int(self.bates_start_number.get())
            
            self.log_message("Starting document preparation...")
            self.log_message(f"Input folder: {source_folder}")
            self.log_message(f"Output folder: {output_folder}")
            self.log_message(f"File naming starts: {file_naming_start:04d}")
            self.log_message(f"Bates prefix: {bates_prefix if bates_prefix else '(none)'}")
            self.log_message(f"Bates starting number: {bates_start:04d}")
            
            # Initialize document preparation processor with configured components
            self.processor = GDIDocumentProcessor(
                source_folder=source_folder,
                bates_prefix=bates_prefix,
                bates_start_number=bates_start,
                file_naming_start=file_naming_start,
                output_folder=output_folder,
                log_callback=self.log_message,
                line_numberer=self.line_numberer,  # Pass configured instance
                bates_numberer=self.bates_numberer  # Pass configured instance
            )
            
            # Run the processing
            success = self.processor.process_all_documents()
            
            if success and self.processing:
                self.log_message("Document preparation completed successfully!")
                messagebox.showinfo("Success", "Document preparation completed successfully!")
            elif not self.processing:
                self.log_message("Processing was paused by user.")
            else:
                self.log_message("Processing completed with errors. Check log for details.")
                messagebox.showwarning("Warning", "Processing completed with errors. Check log for details.")
                
        except Exception as e:
            error_msg = f"An error occurred during processing: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
            
        finally:
            # Reset UI state
            self.root.after(0, self._reset_ui_state)
            
    def _reset_ui_state(self):
        """Reset UI state after processing (must be called from main thread)"""
        self.processing = False
        self.processor = None  # Clear processor reference
        self.process_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        
    def _load_settings(self):
        """Load saved settings from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                # Load file naming settings
                if 'file_naming_start' in config:
                    self.file_naming_start.set(config['file_naming_start'])
                    
                # Load bates settings
                if 'bates_prefix' in config:
                    self.bates_prefix.set(config['bates_prefix'])
                    
                if 'bates_start_number' in config:
                    self.bates_start_number.set(config['bates_start_number'])
                    
                # Color settings are now hardcoded - no need to load them
                    
                # Load dark mode setting
                if 'dark_mode' in config:
                    self.dark_mode.set(config['dark_mode'])
                    
        except Exception as e:
            # If config file is corrupted or can't be read, just use defaults
            print(f"Note: Could not load settings: {e}")
            pass
            
    def _save_settings(self):
        """Save current settings to config file"""
        try:
            config = {
                'file_naming_start': self.file_naming_start.get(),
                'bates_prefix': self.bates_prefix.get(),
                'bates_start_number': self.bates_start_number.get(),
                'dark_mode': self.dark_mode.get()
            }
            
            # Create directory if it doesn't exist
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            # Don't show error to user - settings saving is not critical
            print(f"Note: Could not save settings: {e}")
            pass
            
    def _apply_loaded_settings(self):
        """Apply settings to components after loading"""
        try:
            # Colors are now hardcoded in the modules
            # Line numbers: Nice red color (0.8, 0.0, 0.0), Times New Roman font
            # Bates numbers: Black color (0, 0, 0), Times New Roman font
            
            # Update dark mode button image if images are loaded (dark mode will be applied after UI creation)
            if hasattr(self, 'dark_mode_button') and hasattr(self, 'night_mode_off_image') and hasattr(self, 'night_mode_on_image'):
                if self.dark_mode.get():
                    self.dark_mode_button.configure(image=self.night_mode_on_image)
                    self.dark_mode_button.image = self.night_mode_on_image
                else:
                    self.dark_mode_button.configure(image=self.night_mode_off_image)
                    self.dark_mode_button.image = self.night_mode_off_image
            
        except Exception as e:
            # If settings are invalid, use defaults
            print(f"Note: Could not apply settings, using defaults: {e}")
            import traceback
            traceback.print_exc()
            pass
            
    # Settings menu removed - colors are hardcoded in base pipeline
            
    def toggle_dark_mode(self):
        """Toggle dark mode on/off"""
        try:
            # Toggle the dark mode state
            self.dark_mode.set(not self.dark_mode.get())
            
            # Update the button image based on the new state
            if hasattr(self, 'night_mode_off_image') and hasattr(self, 'night_mode_on_image'):
                if self.dark_mode.get():
                    # Dark mode is ON - use the "on" image
                    self.dark_mode_button.configure(image=self.night_mode_on_image)
                    self.dark_mode_button.image = self.night_mode_on_image
                else:
                    # Dark mode is OFF - use the "off" image
                    self.dark_mode_button.configure(image=self.night_mode_off_image)
                    self.dark_mode_button.image = self.night_mode_off_image
            
            # Apply dark mode styling
            self.apply_dark_mode()
            
            # Save the dark mode preference
            self._save_settings()
            
        except Exception as e:
            self.log_message(f"Error toggling dark mode: {e}")
            
    def apply_dark_mode(self):
        """Apply dark mode styling to the interface"""
        try:
            if self.dark_mode.get():
                # Cursor-like dark mode colors
                self.root.configure(bg="#1e1e1e")  # Main background - very dark grey
                
                # Configure ttk style for dark mode
                style = ttk.Style()
                style.theme_use('clam')  # Use clam theme as base
                
                # Dark theme colors
                style.configure('TLabel', 
                               background="#1e1e1e", 
                               foreground="#d4d4d4")  # Light grey text
                
                style.configure('TEntry', 
                               fieldbackground="#3c3c3c", 
                               background="#3c3c3c",
                               foreground="#d4d4d4",
                               bordercolor="#5a5a5a",
                               lightcolor="#5a5a5a",
                               darkcolor="#5a5a5a")
                
                style.configure('TButton', 
                               background="#0e639c", 
                               foreground="#ffffff",
                               bordercolor="#0e639c",
                               lightcolor="#0e639c",
                               darkcolor="#0e639c")
                
                style.map('TButton',
                         background=[('active', '#1177bb')])
                
                style.configure('TFrame', 
                               background="#1e1e1e")
                
                style.configure('TLabelFrame', 
                               background="#1e1e1e", 
                               foreground="#d4d4d4",
                               bordercolor="#3c3c3c",
                               lightcolor="#1e1e1e",
                               darkcolor="#1e1e1e")
                
                style.configure('TLabelFrame.Label', 
                               background="#1e1e1e", 
                               foreground="#d4d4d4")
                
                # Force all existing frames to update their background
                self._update_frame_backgrounds("#1e1e1e")
                
                # Force update specific LabelFrames that might not be updating
                self._force_labelframe_update()
                
                # Directly configure specific widgets that aren't updating
                self._configure_specific_widgets_dark()
                
                # Configure the log text widget
                if hasattr(self, 'log_display'):
                    self.log_display.configure(
                        bg="#1e1e1e",
                        fg="#d4d4d4",
                        insertbackground="#d4d4d4",
                        selectbackground="#264f78",
                        selectforeground="#ffffff",
                        highlightthickness=0,
                        relief="flat"
                    )
                    
                    # Also configure the scrollbar that comes with ScrolledText
                    try:
                        # Get the scrollbar from ScrolledText and configure it
                        scrollbar = self.log_display.vbar
                        if scrollbar:
                            scrollbar.configure(
                                bg="#3c3c3c",
                                troughcolor="#1e1e1e",
                                activebackground="#5a5a5a",
                                highlightthickness=0
                            )
                    except:
                        pass
                
                # Configure progress bar
                style.configure('TProgressbar',
                               background="#0e639c",
                               troughcolor="#3c3c3c",
                               bordercolor="#3c3c3c",
                               lightcolor="#0e639c",
                               darkcolor="#0e639c")
                
                # Configure scrollbars
                style.configure('TScrollbar',
                               background="#3c3c3c",
                               troughcolor="#1e1e1e",
                               bordercolor="#3c3c3c",
                               arrowcolor="#d4d4d4",
                               lightcolor="#3c3c3c",
                               darkcolor="#3c3c3c")
                style.map('TScrollbar',
                         background=[('active', '#5a5a5a')],
                         troughcolor=[('active', '#1e1e1e')])
                
            else:
                # Light mode colors (default)
                self.root.configure(bg="#f0f0f0")
                
                # Reset to default theme
                style = ttk.Style()
                style.theme_use('clam')
                
                # Light theme colors
                style.configure('TLabel', 
                               background="#f0f0f0", 
                               foreground="#000000")
                
                style.configure('TEntry', 
                               fieldbackground="#ffffff", 
                               background="#ffffff",
                               foreground="#000000")
                
                style.configure('TButton', 
                               background="#e1e1e1", 
                               foreground="#000000")
                
                style.configure('TFrame', 
                               background="#f0f0f0")
                
                style.configure('TLabelFrame', 
                               background="#f0f0f0", 
                               foreground="#000000",
                               bordercolor="#d0d0d0",
                               lightcolor="#f0f0f0",
                               darkcolor="#f0f0f0")
                
                style.configure('TLabelFrame.Label', 
                               background="#f0f0f0", 
                               foreground="#000000")
                
                # Force all existing frames to update their background
                self._update_frame_backgrounds("#f0f0f0")
                
                # Force update specific LabelFrames that might not be updating
                self._force_labelframe_update()
                
                # Directly configure specific widgets that aren't updating
                self._configure_specific_widgets_light()
                
                # Configure the log text widget
                if hasattr(self, 'log_display'):
                    self.log_display.configure(
                        bg="#ffffff",
                        fg="#000000",
                        insertbackground="#000000",
                        selectbackground="#0078d4",
                        selectforeground="#ffffff",
                        highlightthickness=0,
                        relief="flat"
                    )
                
                # Configure progress bar
                style.configure('TProgressbar',
                               background="#0078d4",
                               troughcolor="#e1e1e1")
                
                # Configure scrollbars
                style.configure('TScrollbar',
                               background="#e1e1e1",
                               troughcolor="#f0f0f0",
                               bordercolor="#d0d0d0",
                               arrowcolor="#000000",
                               lightcolor="#e1e1e1",
                               darkcolor="#e1e1e1")
                style.map('TScrollbar',
                         background=[('active', '#d0d0d0')])
            
            # Force refresh of all existing widgets
            self.root.update_idletasks()
            
            mode_text = "Dark Mode ON" if self.dark_mode.get() else "Dark Mode OFF"
            self.log_message(f"Interface: {mode_text}")
            
        except Exception as e:
            self.log_message(f"Error applying dark mode: {e}")

    def _update_frame_backgrounds(self, color):
        """Force update all frame backgrounds to the specified color"""
        try:
            # Update main window
            self.root.configure(bg=color)
            
            # Recursively update all child widgets
            def update_widget_bg(widget):
                try:
                    if hasattr(widget, 'configure'):
                        widget.configure(bg=color)
                except:
                    pass
                for child in widget.winfo_children():
                    update_widget_bg(child)
            
            update_widget_bg(self.root)
        except Exception as e:
            print(f"Error updating frame backgrounds: {e}")

    def _force_labelframe_update(self):
        """Force update LabelFrame backgrounds specifically"""
        try:
            # Find all LabelFrames and force their background update
            def find_labelframes(widget):
                labelframes = []
                if isinstance(widget, ttk.LabelFrame):
                    labelframes.append(widget)
                for child in widget.winfo_children():
                    labelframes.extend(find_labelframes(child))
                return labelframes
            
            labelframes = find_labelframes(self.root)
            for lf in labelframes:
                try:
                    # Just refresh the widget without changing style
                    lf.update_idletasks()
                except:
                    pass
        except Exception as e:
            print(f"Error forcing LabelFrame update: {e}")

    def _configure_specific_widgets_dark(self):
        """Directly configure specific widgets that aren't updating with ttk styles"""
        try:
            # Configure entry widgets directly
            if hasattr(self, 'input_entry'):
                self.input_entry.configure(style='TEntry')
            if hasattr(self, 'output_entry'):
                self.output_entry.configure(style='TEntry')
            if hasattr(self, 'prefix_entry'):
                self.prefix_entry.configure(style='TEntry')
            if hasattr(self, 'number_entry'):
                self.number_entry.configure(style='TEntry')
            
            # Configure LabelFrames directly (remove style to avoid layout errors)
            if hasattr(self, 'file_naming_frame'):
                pass  # Let it use default styling
            if hasattr(self, 'bates_frame'):
                pass  # Let it use default styling
            if hasattr(self, 'progress_frame'):
                pass  # Let it use default styling
            
            # Configure scrollbars directly
            if hasattr(self, 'h_scrollbar'):
                self.h_scrollbar.configure(style='TScrollbar')
                
        except Exception as e:
            print(f"Error configuring specific widgets: {e}")

    def _configure_specific_widgets_light(self):
        """Directly configure specific widgets for light mode"""
        try:
            # Configure entry widgets directly
            if hasattr(self, 'input_entry'):
                self.input_entry.configure(style='TEntry')
            if hasattr(self, 'output_entry'):
                self.output_entry.configure(style='TEntry')
            if hasattr(self, 'prefix_entry'):
                self.prefix_entry.configure(style='TEntry')
            if hasattr(self, 'number_entry'):
                self.number_entry.configure(style='TEntry')
            
            # Configure LabelFrames directly (remove style to avoid layout errors)
            if hasattr(self, 'file_naming_frame'):
                pass  # Let it use default styling
            if hasattr(self, 'bates_frame'):
                pass  # Let it use default styling
            if hasattr(self, 'progress_frame'):
                pass  # Let it use default styling
            
            # Configure scrollbars directly
            if hasattr(self, 'h_scrollbar'):
                self.h_scrollbar.configure(style='TScrollbar')
                
        except Exception as e:
            print(f"Error configuring specific widgets for light mode: {e}")

    def _on_closing(self):
        """Handle window closing event"""
        # Save settings before closing
        self._save_settings()
        
        # Stop any running processing
        if self.processing:
            self.pause_processing()
            
        # Destroy the window
        self.root.destroy()


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = GDIDocumentPrepGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
