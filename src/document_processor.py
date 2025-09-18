"""
Garrett Discovery Document Prep Tool - Main Processing Module
Main processing logic that coordinates all document preparation operations
"""

import os
import shutil
import time
from pathlib import Path
import tempfile
from datetime import datetime
import csv

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from file_scanner import FileScanner
from pdf_converter import PDFConverter
from line_numbering import LineNumberer
from bates_numbering import BatesNumberer
from logger_manager import LoggerManager
from pipelines.text_pipeline import TextPipeline
from pipelines.native_pdf_pipeline import NativePDFPipeline
from pipelines.scan_image_pipeline import ScanImagePipeline
from error_handling import ErrorHandler, ValidationError, ProcessingError
from memory_manager import MemoryManager, MemoryConfig
from universal_line_numbering import UniversalLineNumberer


class GDIDocumentProcessor:
    """Main document preparation processor that coordinates all operations"""
    
    def __init__(self, source_folder, bates_prefix, bates_start_number=1, file_naming_start=1, output_folder=None,
                 log_callback=None, line_numberer=None, bates_numberer=None, file_limit=None):
        """
        Initialize the document preparation processor
        
        Args:
            source_folder (str): Source folder to process
            bates_prefix (str): Prefix for bates numbering
            bates_start_number (int): Starting bates number
            file_naming_start (int): Starting number for file naming (defaults to 1)
            output_folder (str): Optional output folder (defaults to Processed folder in source parent)
            log_callback: Optional callback for logging messages
            line_numberer: Pre-configured LineNumberer instance (optional)
            bates_numberer: Pre-configured BatesNumberer instance (optional)
            file_limit (int): Optional limit on number of files to process (None for all)
        """
        self.source_folder = Path(source_folder)
        self.bates_prefix = bates_prefix
        self.bates_start_number = bates_start_number
        self.file_naming_start = file_naming_start
        self.log_callback = log_callback
        self.file_limit = file_limit
        
        # Create output folder path
        if output_folder:
            # Output folder
            self.processed_folder = Path(output_folder)
        else:
            # Default behavior - create Processed folder in parent of source
            self.processed_folder = self.source_folder.parent / "Processed"
        
        self.failures_folder = self.processed_folder / "Failures"
        
        # Initialize error handler
        self.error_handler = ErrorHandler(log_callback=log_callback)

        # Initialize memory manager with optimized configuration
        memory_config = MemoryConfig(
            max_memory_percent=75.0,  # Conservative limit for stability
            warning_percent=60.0,     # Early warning
            batch_size=3,             # Small batches for large files
            max_file_size_mb=50,      # Reasonable file size limit
            enable_monitoring=True,   # Enable memory monitoring
            cleanup_interval=5        # Clean up every 5 files
        )
        self.memory_manager = MemoryManager(memory_config, log_callback)

        # Initialize components
        self.file_scanner = FileScanner(log_callback=log_callback)
        self.pdf_converter = PDFConverter(log_callback=log_callback)

        # Use pre-configured instances if provided, otherwise create new ones
        if line_numberer:
            self.line_numberer = line_numberer
            # Ensure the log callback is set
            self.line_numberer.log_callback = log_callback
        else:
            self.line_numberer = LineNumberer(log_callback=log_callback)

        if bates_numberer:
            self.bates_numberer = bates_numberer
            # Ensure the log callback is set
            self.bates_numberer.log_callback = log_callback
        else:
            self.bates_numberer = BatesNumberer(log_callback=log_callback)

        self.logger_manager = LoggerManager(log_callback=log_callback)

        # Initialize universal line numbering system
        self.universal_line_numberer = UniversalLineNumberer(log_callback=log_callback)

        # Initialize pipelines with universal line numbering system
        self.text_pipeline = TextPipeline(self.line_numberer, self.bates_numberer, self.logger_manager, self.universal_line_numberer)
        self.native_pdf_pipeline = NativePDFPipeline(self.line_numberer, self.bates_numberer, self.logger_manager, self.universal_line_numberer)
        self.scan_image_pipeline = ScanImagePipeline(self.line_numberer, self.bates_numberer, self.logger_manager, self.universal_line_numberer)
        
        # Processing state
        self.found_files = []
        self.copied_files = []
        self.unsupported_files = []
        self.converted_files = []
        self.final_pdfs = []
        self.current_line_number = 1
        self.current_bates_number = bates_start_number
        self.current_file_number = file_naming_start  # Track file numbering for successful processing only
        
        # Processing should continue flag
        self.should_continue = True
        
    def log(self, message):
        """Log a message"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
            
    def stop_processing(self):
        """Stop the processing"""
        self.should_continue = False
        self.log("Processing stop requested")
        
    def process_all_documents(self):
        """
        Execute the complete document processing workflow with separate pipelines

        Returns:
            bool: True if processing completed successfully
        """
        try:
            # Validate input parameters before starting
            validation_errors = self.error_handler.validate_input_parameters(
                self.bates_prefix,
                self.bates_start_number,
                self.file_naming_start,
                self.source_folder
            )

            if validation_errors:
                error_msg = "Input validation failed:\\n" + "\\n".join(validation_errors)
                self.logger_manager.log_processing_error("System", error_msg, "validation")
                if self.log_callback:
                    self.log_callback(f"❌ {error_msg}")
                return False

            # Start logging session
            self.logger_manager.start_processing_session(
                str(self.source_folder),
                self.bates_prefix,
                self.bates_start_number
            )

            # Start memory monitoring
            with self.memory_manager.memory_monitoring():

                # Step 1: Scan for files
                if not self.should_continue:
                    return False
                if not self._scan_files():
                    return False

                # Step 2: Create folder structure
                if not self.should_continue:
                    return False
                if not self._create_folder_structure():
                    return False

                # Step 3: Copy and rename files
                if not self.should_continue:
                    return False
                if not self._copy_and_rename_files():
                    return False

                # Step 4: Analyze PDF layouts for potential issues
                if not self.should_continue:
                    return False
                self._analyze_layouts()

                # Step 5: Separate processing by file type
                if not self.should_continue:
                    return False
                if not self._process_by_type():
                    return False

                # Step 6: Create log files with calculated statistics
                if not self.should_continue:
                    return False
                stats = self.logger_manager.finalize_session()
                if not self._create_log_files():
                    return False

                # Step 7: Create CSV log file with processing details (DISABLED)
                # if not self.should_continue:
                #     return False
                # if not self._create_csv_log():
                #     return False

                # Step 8: Clean up copied files from processed folder
                if not self.should_continue:
                    return False
                self._cleanup_copied_files()

            # Memory monitoring automatically stops here
                
            self.log(f"Process complete - {stats['total_files_processed']} files processed")
            
            return True
            
        except Exception as e:
            self.log(f"Fatal error during processing: {str(e)}")
            self.logger_manager.log_processing_error("", str(e), "main_processing")
            return False
            
    def _scan_files(self):
        """Scan source folder for supported files"""
        try:
            self.found_files = self.file_scanner.scan_directory(str(self.source_folder))
            
            if not self.found_files:
                self.log("No supported files found in source folder")
                return False
            
            # Sort files by name to ensure consistent numbering order
            self.found_files.sort(key=lambda x: x['name'].lower())
                
            # Log scan results
            self.logger_manager.log_files_scanned(self.found_files)
            
            summary = self.file_scanner.get_file_summary()
            self.log(f"Found {summary['total_files']} supported files ({summary['total_size_mb']:.2f} MB)")
            
            return True
            
        except Exception as e:
            self.log(f"Error scanning files: {str(e)}")
            return False
            
    def _create_folder_structure(self):
        """Create output and Failures folders with enhanced error handling"""
        try:
            # Validate folder paths before creation
            if not self.error_handler.validate_filename_safety(self.processed_folder.name):
                raise ValidationError(f"Invalid output folder name: {self.processed_folder.name}")

            if not self.error_handler.validate_filename_safety(self.failures_folder.name):
                raise ValidationError(f"Invalid failures folder name: {self.failures_folder.name}")

            # Create output folder with error handling
            self.error_handler.safe_create_directory(self.processed_folder)
            self.log(f"Created output folder: {self.processed_folder}")

            # Create Failures subfolder with error handling
            self.error_handler.safe_create_directory(self.failures_folder)
            self.log(f"Created Failures folder: {self.failures_folder}")

            # Verify folders were created successfully
            if not self.processed_folder.exists():
                raise ValidationError(f"Failed to create output folder: {self.processed_folder}")

            if not self.failures_folder.exists():
                raise ValidationError(f"Failed to create failures folder: {self.failures_folder}")

            return True

        except (ValidationError, ProcessingError) as e:
            self.log(f"❌ Validation error creating folder structure: {str(e)}")
            self.logger_manager.log_processing_error("System", str(e), "folder_creation")
            return False
        except Exception as e:
            self.log(f"❌ Unexpected error creating folder structure: {str(e)}")
            self.logger_manager.log_processing_error("System", str(e), "folder_creation")
            return False
            
    def _copy_and_rename_files(self):
        """Copy files to processed folder without numbering (numbering happens only on successful processing)"""
        try:
            self.copied_files = []
            self.unsupported_files = []
            file_counter = self.file_naming_start  # Keep track for successful processing only
            unsupported_counter = 5000  # Start unsupported files at 5000
            
            # Apply file limit if specified
            files_to_process = self.found_files
            if self.file_limit and self.file_limit > 0:
                files_to_process = self.found_files[:self.file_limit]
                self.log(f"Processing limited to {len(files_to_process)} files (limit: {self.file_limit})")
            else:
                self.log(f"Copying {len(self.found_files)} files to processed folder (numbering will be applied only to successfully processed files)")

            for file_info in files_to_process:
                if not self.should_continue:
                    return False
                    
                source_path = Path(file_info['path'])
                
                # Enhanced file accessibility check
                file_access_info = self.error_handler.validate_file_accessibility(source_path)
                if not file_access_info['accessible']:
                    self.logger_manager.log_file_not_copied(
                        str(source_path),
                        f"File not accessible: {file_access_info['error']}"
                    )
                    continue

                try:
                    # Copy file with original name (no numbering yet)
                    original_name = source_path.name

                    # Validate filename safety
                    if not self.error_handler.validate_filename_safety(original_name):
                        raise ValidationError(f"Invalid filename: {original_name}")

                    destination = self.processed_folder / original_name

                    # Copy file with enhanced error handling
                    self.error_handler.safe_copy_file(source_path, destination)

                    # For non-PDF files, also copy as "original" with prefix
                    if file_info.get('extension', '').lower() not in ['.pdf']:
                        file_counter = len([f for f in self.copied_files if f.get('file_number')]) + self.file_naming_start
                        original_prefix_name = f"original_{file_counter:04d}__{original_name}"
                        original_destination = self.processed_folder / original_prefix_name

                        # Copy as original file
                        self.error_handler.safe_copy_file(source_path, original_destination)
                        self.log(f"Preserved original: {original_prefix_name}")

                    # Track copied file (without file number yet)
                    copied_info = file_info.copy()
                    copied_info['copied_path'] = str(destination)
                    copied_info['original_path'] = str(source_path)
                    copied_info['file_number'] = None  # Will be assigned only on successful processing
                    copied_info['original_name'] = original_name
                    self.copied_files.append(copied_info)

                    self.log(f"Copied: {original_name}")

                except Exception as e:
                    self.logger_manager.log_file_not_copied(
                        str(source_path),
                        f"Copy error: {str(e)}"
                    )
                    continue
            
            # Now handle unsupported files
            self.log("Scanning for unsupported files...")
            unsupported_files = self._find_unsupported_files()
            
            for unsupported_file in unsupported_files:
                if not self.should_continue:
                    return False
                    
                source_path = Path(unsupported_file)
                
                try:
                    # Generate new filename with 5000+ prefix
                    original_name = source_path.name
                    new_name = f"{unsupported_counter:04d}_{original_name}"
                    destination = self.processed_folder / new_name
                    
                    # Copy file
                    shutil.copy2(source_path, destination)
                    
                    # Track unsupported file
                    unsupported_info = {
                        'path': str(source_path),
                        'copied_path': str(destination),
                        'original_path': str(source_path),
                        'file_number': unsupported_counter,
                        'type': 'unsupported',
                        'extension': source_path.suffix.lower()
                    }
                    self.unsupported_files.append(unsupported_info)
                    
                    self.log(f"Copied unsupported: {original_name} -> {new_name}")
                    unsupported_counter += 1
                    
                except Exception as e:
                    self.log(f"Error copying unsupported file {original_name}: {str(e)}")
                    continue
                    
            self.log(f"Successfully copied {len(self.copied_files)} supported files to processed folder")
            if self.unsupported_files:
                self.log(f"Successfully copied {len(self.unsupported_files)} unsupported files to processed folder")
            return True
            
        except Exception as e:
            self.log(f"Error copying files: {str(e)}")
            return False
            
    def _find_unsupported_files(self):
        """Find all unsupported files in the source directory"""
        unsupported_files = []
        
        try:
            # Walk through all subdirectories
            for root, dirs, files in os.walk(self.source_folder):
                # Skip hidden directories and common system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                          d.lower() not in ['__pycache__', 'node_modules', '.git']]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # Check if file extension is NOT supported
                    if file_path.suffix.lower() not in self.file_scanner.SUPPORTED_EXTENSIONS:
                        # Skip hidden files and system files
                        if not file.startswith('.') and not file.startswith('~'):
                            unsupported_files.append(file_path)
                            
        except Exception as e:
            self.log(f"Error scanning for unsupported files: {str(e)}")
            
        return unsupported_files
            
    def _process_by_type(self):
        """Process files using type-specific pipelines"""
        try:
            # Separate files by type
            high_accuracy_files = []  # Word, Text files
            complex_files = []        # PDF, TIFF files
            
            for file_info in self.copied_files:
                file_type = file_info.get('type', 'unknown')
                if file_type in ['word', 'text']:
                    high_accuracy_files.append(file_info)
                elif file_type in ['pdf', 'image']:  # image includes TIFF
                    complex_files.append(file_info)
                else:
                    self.log(f"Unknown file type: {file_type} for {file_info['copied_path']}")
                    
            self.log(f"Pipeline 1 (Text-based): {len(high_accuracy_files)} Word/Text files - 100% accurate line detection")
            self.log(f"Pipeline 2 (PDF/Image): {len(complex_files)} PDF/TIFF files - OCR/readable text detection")
            
            self.final_pdfs = []
            
            # Process high accuracy files: Line numbers + Bates → PDF
            if high_accuracy_files:
                if not self._process_high_accuracy_files(high_accuracy_files):
                    return False
                    
            # Process complex files: PDF → Line numbers + Bates
            if complex_files:
                if not self._process_complex_files(complex_files):
                    return False
                    
            return True
            
        except Exception as e:
            self.log(f"Error in type-specific processing: {str(e)}")
            return False
            
    def _process_high_accuracy_files(self, high_accuracy_files):
        """Process Word/Text files: Line numbers + Bates → PDF conversion"""
        try:
            self.log("Processing high accuracy files (Word/Text)...")
            processed_files = []
            
            for file_info in high_accuracy_files:
                if not self.should_continue:
                    return False
                    
                source_path = Path(file_info['copied_path'])
                file_type = file_info.get('type', 'unknown')
                
                try:
                    # Step 1: Use TextPipeline for processing (without file numbering yet)
                    pipeline_type = self._get_clean_pipeline_type('text_based')
                    temp_filename = f"temp_{source_path.stem}_{pipeline_type}.pdf"
                    temp_path = self.processed_folder / temp_filename
                    
                    # Use TextPipeline for processing
                    pipeline_result = self.text_pipeline.process_document(
                        source_path, temp_path, "0000", self.bates_prefix, self.bates_start_number
                    )
                    
                    if pipeline_result['success']:
                        # Assign file number only on successful processing
                        file_number = self._assign_file_number(file_info)
                        file_sequential_number = f"{file_number:04d}"
                        
                        # Generate final filename with assigned file number
                        original_stem = source_path.stem
                        final_filename = f"{file_sequential_number}_{original_stem}_{pipeline_type}.pdf"
                        final_path = self.processed_folder / final_filename
                        
                        # Rename the temp file to the final filename
                        shutil.move(str(temp_path), str(final_path))
                        
                        # Track processed file  
                        processed_info = file_info.copy()
                        processed_info['pdf_path'] = str(final_path)
                        processed_info['bates_number'] = file_sequential_number
                        processed_info['bates_numeric'] = self.bates_start_number
                        processed_info['line_start'] = 1 if pipeline_result['lines_added'] > 0 else None
                        processed_info['line_end'] = pipeline_result['lines_added'] if pipeline_result['lines_added'] > 0 else None
                        processed_info['lines_added'] = pipeline_result['lines_added']
                        processed_info['final_path'] = str(final_path)
                        processed_info['processing_pipeline'] = 'text_based'
                        
                        processed_files.append(processed_info)
                        
                        # Log success
                        line_range = f"1-{pipeline_result['lines_added']}" if pipeline_result['lines_added'] > 0 else "no lines"
                        bates_str = f"{self.bates_prefix}{self.bates_start_number:04d}"
                        bates_range = pipeline_result.get('bates_range', bates_str)
                        self.logger_manager.log_file_processed(str(final_path), bates_str, line_range, bates_range)
                        
                        self.log(f"✅ {file_type.title()}: {source_path.name} → {pipeline_result['lines_added']} lines → {final_filename}")
                        
                        # Clean up the copied source file since it's been converted to PDF
                        if source_path.exists():
                            source_path.unlink()
                    else:
                        # Clean up temp file if it exists
                        if temp_path.exists():
                            temp_path.unlink()
                        self._move_to_failures(source_path, f"TextPipeline processing failed: {pipeline_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    self._move_to_failures(source_path, f"High accuracy processing error: {str(e)}")
                    continue
                    
            self.final_pdfs.extend(processed_files)
            self.log(f"Text-based pipeline completed: {len(processed_files)} files processed")
            return True
            
        except Exception as e:
            self.log(f"Error in text-based pipeline: {str(e)}")
            return False
            
    def _process_complex_files(self, complex_files):
        """Process PDF/TIFF files: Convert to PDF → Smart Detection → Line numbers + Bates"""
        try:
            self.log("Processing complex files (PDF/TIFF)...")
            processed_files = []
            
            for file_info in complex_files:
                if not self.should_continue:
                    return False
                    
                source_path = Path(file_info['copied_path'])
                file_type = file_info.get('type', 'unknown')
                
                try:
                    # Step 1: Convert to PDF (if not already PDF)
                    pdf_name = source_path.stem + '.pdf'
                    pdf_path = self.processed_folder / pdf_name
                    
                    if file_type == 'pdf':
                        # Move PDF to correct location and classify it
                        shutil.move(source_path, pdf_path)
                        conversion_success = True
                        # Classify the PDF to get proper document type
                        doc_category, doc_subtype, confidence = self.pdf_converter.classify_document_type(str(pdf_path))
                        doc_type = doc_subtype
                        processing_notes = f"PDF classified as {doc_category}/{doc_subtype}"
                    else:
                        # Convert TIFF/other to PDF
                        self.log(f"DEBUG: Converting {file_type} file {source_path.name} to PDF")
                        result = self.pdf_converter.convert_to_pdf(
                            str(source_path), str(pdf_path), perform_ocr=True
                        )
                        self.log(f"DEBUG: Conversion result: {result}")
                        
                        if isinstance(result, tuple):
                            conversion_success, doc_type, processing_notes = result
                        else:
                            conversion_success = result
                            doc_type = file_type
                            processing_notes = "Standard conversion"
                    
                    if not conversion_success:
                        self._move_to_failures(source_path, f"Failed to convert {file_type} to PDF")
                        continue
                        
                    # Step 2: Smart Detection - Analyze PDF content to determine best pipeline
                    smart_pipeline_type, smart_notes = self._smart_detect_pipeline(str(pdf_path))
                    self.log(f"Smart detection for {pdf_path.name}: {smart_pipeline_type} - {smart_notes}")
                    
                    # Step 3: Use smart-detected pipeline for processing (without file numbering yet)
                    pipeline_type = smart_pipeline_type
                    temp_filename = f"temp_{pdf_path.stem}_{pipeline_type}.pdf"
                    temp_path = pdf_path.parent / temp_filename
                    
                    # Step 4: Use smart-detected pipeline for processing
                    if smart_pipeline_type == 'ScanImage':
                        # Use ScanImagePipeline for scanned/image documents
                        pipeline_result = self.scan_image_pipeline.process_document(
                            pdf_path, temp_path, "0000", self.bates_prefix, self.bates_start_number
                        )
                    elif smart_pipeline_type == 'NativePDF':
                        # Use NativePDFPipeline for native PDF documents
                        pipeline_result = self.native_pdf_pipeline.process_document(
                            pdf_path, temp_path, "0000", self.bates_prefix, self.bates_start_number
                        )
                    else:
                        # Default to ScanImagePipeline for unknown types
                        pipeline_result = self.scan_image_pipeline.process_document(
                            pdf_path, temp_path, "0000", self.bates_prefix, self.bates_start_number
                        )
                    
                    if pipeline_result['success']:
                        # Assign file number only on successful processing
                        file_number = self._assign_file_number(file_info)
                        file_sequential_number = f"{file_number:04d}"
                        
                        # Generate final filename with assigned file number
                        original_stem = pdf_path.stem
                        final_filename = f"{file_sequential_number}_{original_stem}_{pipeline_type}.pdf"
                        final_path = pdf_path.parent / final_filename
                        
                        # Rename the temp file to the final filename
                        shutil.move(str(temp_path), str(final_path))
                        
                        # Track processed file
                        processed_info = file_info.copy()
                        processed_info['pdf_path'] = str(final_path)
                        processed_info['bates_number'] = file_sequential_number
                        processed_info['bates_numeric'] = self.bates_start_number
                        processed_info['line_start'] = 1 if pipeline_result['lines_added'] > 0 else None
                        processed_info['line_end'] = pipeline_result['lines_added'] if pipeline_result['lines_added'] > 0 else None
                        processed_info['lines_added'] = pipeline_result['lines_added']
                        processed_info['final_path'] = str(final_path)
                        processed_info['processing_pipeline'] = pipeline_result['pipeline_type']
                        processed_info['document_type'] = doc_type
                        processed_info['processing_notes'] = processing_notes
                        
                        processed_files.append(processed_info)
                        
                        # Log success
                        line_range = f"1-{pipeline_result['lines_added']}" if pipeline_result['lines_added'] > 0 else "no lines"
                        bates_full = f"{self.bates_prefix}{self.bates_start_number:04d}"
                        bates_range = pipeline_result.get('bates_range', bates_full)
                        self.logger_manager.log_file_processed(str(final_path), bates_full, line_range, bates_range)
                        
                        self.log(f"✅ {file_type.upper()}: {source_path.name} → {pipeline_result['lines_added']} lines → {final_filename}")
                        
                        # Clean up: Delete original TIFF file after successful conversion to PDF
                        if file_type == 'image' and source_path.exists():
                            source_path.unlink()
                            self.log(f"🗑️  Cleaned up original TIFF: {source_path.name}")
                        # Keep original PDF files - don't delete them
                    else:
                        # Clean up temp file if it exists
                        if temp_path.exists():
                            temp_path.unlink()
                        # Pipeline processing failed
                        self._move_to_failures(pdf_path, f"Pipeline processing failed for {file_type}: {pipeline_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    self._move_to_failures(source_path, f"Complex processing error: {str(e)}")
                    continue
                    
            self.final_pdfs.extend(processed_files)
            self.log(f"Complex pipeline completed: {len(processed_files)} files processed")
            return True
            
        except Exception as e:
            self.log(f"Error in complex pipeline: {str(e)}")
            return False
            
    def _extract_word_text(self, word_path):
        """Extract text content with formatting from Word document"""
        try:
            try:
                from docx import Document
            except ImportError:
                return False, "python-docx not available"
                
            doc = Document(word_path)
            formatted_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    # Extract paragraph with formatting metadata
                    para_info = {
                        'text': paragraph.text,
                        'style': paragraph.style.name if paragraph.style else 'Normal',
                        'runs': []
                    }
                    
                    # Extract run-level formatting (bold, italic, underline)
                    for run in paragraph.runs:
                        if run.text.strip():
                            run_info = {
                                'text': run.text,
                                'bold': run.bold if run.bold is not None else False,
                                'italic': run.italic if run.italic is not None else False,
                                'underline': run.underline if run.underline is not None else False,
                                'font_size': run.font.size.pt if run.font.size else None
                            }
                            para_info['runs'].append(run_info)
                    
                    formatted_content.append(para_info)
                    
            return True, formatted_content
            
        except Exception as e:
            return False, f"Word extraction error: {str(e)}"
            
    def _extract_text_content(self, text_path):
        """Extract text content from text file"""
        try:
            with open(text_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return True, content
            
        except Exception as e:
            return False, f"Text extraction error: {str(e)}"
            
    def _analyze_layouts(self):
        """
        Analyze PDF layouts to detect unusual patterns that may affect line numbering
        Also detects landscape pages and moves them to Failures folder
        """
        try:
            layout_issues_found = 0
            total_pdfs_analyzed = 0
            landscape_files_moved = 0
            
            # Analyze all PDF files in processed folder
            pdf_files = list(self.processed_folder.glob("*.pdf"))
            
            if not pdf_files:
                self.log("📄 No PDF files found for layout analysis")
                return
            
            self.log(f"🔍 Analyzing {len(pdf_files)} PDF files for unusual layouts...")
            
            for pdf_file in pdf_files:
                if not self.should_continue:
                    break
                    
                try:
                    # Check if PDF is landscape first
                    is_landscape, landscape_pages = self._check_landscape_pages(str(pdf_file))
                    
                    if is_landscape:
                        # Move landscape file to failures
                        self._move_to_failures(pdf_file, f"Landscape document detected - {landscape_pages} landscape pages")
                        landscape_files_moved += 1
                        self.log(f"🔄 Moved to Failures: {pdf_file.name} (landscape document)")
                        
                        # Remove from copied_files so it won't be processed by pipelines
                        self.copied_files = [f for f in self.copied_files if Path(f.get('copied_path', '')).name != pdf_file.name]
                        
                        continue
                    
                    # Analyze PDF content and get layout warnings
                    content_type, confidence, warnings = self.pdf_converter._analyze_pdf_content(str(pdf_file))
                    total_pdfs_analyzed += 1
                    
                    if warnings:
                        layout_issues_found += 1
                        self.log(f"⚠️  Layout analysis for {pdf_file.name}:")
                        for warning in warnings:
                            self.log(f"   {warning}")
                    else:
                        self.log(f"✅ {pdf_file.name}: Standard layout detected")
                        
                except Exception as e:
                    self.log(f"❌ Failed to analyze {pdf_file.name}: {str(e)}")
            
            # Summary
            if landscape_files_moved > 0:
                self.log(f"")
                self.log(f"📊 LANDSCAPE DETECTION SUMMARY:")
                self.log(f"   • {landscape_files_moved} landscape documents moved to Failures folder")
                self.log(f"   • Landscape documents are not supported for line numbering")
                self.log(f"")
            
            if layout_issues_found > 0:
                self.log(f"")
                self.log(f"📊 LAYOUT ANALYSIS SUMMARY:")
                self.log(f"   • {total_pdfs_analyzed} PDFs analyzed")
                self.log(f"   • {layout_issues_found} PDFs have unusual layouts")
                self.log(f"   • {total_pdfs_analyzed - layout_issues_found} PDFs have standard layouts")
                self.log(f"")
                self.log(f"💡 RECOMMENDATIONS:")
                self.log(f"   • Files with unusual layouts may need manual review")
                self.log(f"   • Line numbering may be less accurate for rotated/multi-column content")
                self.log(f"   • Empty files with existing numbers will get additional line numbers")
                self.log(f"")
            else:
                self.log(f"✅ All {total_pdfs_analyzed} PDFs have standard layouts - optimal line numbering expected")
                
        except Exception as e:
            self.log(f"⚠️  Layout analysis failed: {str(e)}")
            # Don't fail the entire process for layout analysis issues

    def _get_clean_pipeline_type(self, pipeline):
        """Convert pipeline type to clean filename-friendly format"""
        if pipeline == 'text_based':
            return 'Text'
        elif pipeline == 'complex':
            return 'NativePDF'
        else:
            return 'Unknown'
    
    def _check_landscape_pages(self, pdf_path):
        """
        Check if a PDF has landscape pages
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            tuple: (is_landscape, landscape_pages_count)
        """
        try:
            if not fitz:
                self.log("PyMuPDF not available - cannot check landscape pages")
                return False, 0
                
            doc = fitz.open(pdf_path)
            landscape_pages = 0
            total_pages = len(doc)
            
            for page_num in range(total_pages):
                page = doc[page_num]
                if self._is_landscape_page(page):
                    landscape_pages += 1
            
            # Consider it a landscape document if more than 75% of pages are landscape
            # Less aggressive threshold to avoid moving normal PDFs to failures
            is_landscape = landscape_pages > total_pages * 0.75
            
            doc.close()
            
            return is_landscape, landscape_pages
            
        except Exception as e:
            self.log(f"Error checking landscape pages: {str(e)}")
            return False, 0
    
    def _is_landscape_page(self, page):
        """
        Detect if a page is in landscape orientation
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            bool: True if page is landscape (width > height)
        """
        page_rect = page.rect
        return page_rect.width > page_rect.height

    def _smart_detect_pipeline(self, pdf_path):
        """
        Smart detection to determine the best pipeline for a PDF document
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            tuple: (pipeline_type, detection_notes)
        """
        try:
            # Auto-assign TIFF files to ScanImage pipeline
            if pdf_path.lower().endswith('.tiff') or pdf_path.lower().endswith('.tif'):
                return 'ScanImage', 'TIFF file - automatically assigned to ScanImage pipeline'
            
            if not fitz:
                return 'ScanImage', 'PyMuPDF not available - defaulting to ScanImage'
                
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Analyze each page
            page_analyses = []
            for page_num in range(total_pages):
                page = doc[page_num]
                page_analysis = self._analyze_page_content(page, page_num)
                page_analyses.append(page_analysis)
            
            doc.close()
            
            # Determine overall document type based on page analyses
            return self._determine_document_type(page_analyses, pdf_path)
            
        except Exception as e:
            self.log(f"Smart detection failed for {pdf_path}: {str(e)}")
            return 'ScanImage', f'Detection failed - defaulting to ScanImage: {str(e)}'
    
    def _analyze_page_content(self, page, page_num):
        """
        Analyze a single page to determine its content type
        
        Args:
            page: PyMuPDF page object
            page_num (int): Page number (0-based)
            
        Returns:
            dict: Page analysis results
        """
        try:
            # Get text content
            text = page.get_text().strip()
            text_length = len(text)
            
            # Get images
            images = page.get_images()
            image_count = len(images)
            
            # Get form fields (widgets)
            widgets = list(page.widgets())
            form_field_count = len(widgets)
            
            # Get drawings/vector content
            drawings = page.get_drawings()
            drawing_count = len(drawings)
            
            # Check for rotation metadata
            rotation = page.rotation
            
            # For scanned PDFs, check if page has content but no extractable text
            # This indicates it's likely a scanned image
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            
            # Get text blocks to better understand content
            text_blocks = page.get_text("dict")
            text_block_count = len(text_blocks.get("blocks", []))
            
            # More sophisticated scanned detection
            # A page is likely scanned if:
            # 1. It has images AND minimal text, OR
            # 2. It has substantial drawing content (vector graphics) AND minimal text, OR  
            # 3. It has no text blocks but has images/drawings (pure image page)
            has_substantial_images = image_count > 0
            has_substantial_drawings = drawing_count > 10  # Many vector elements suggest scanned content
            has_minimal_text = text_length < 50
            has_no_text_blocks = text_block_count == 0
            
            is_likely_scanned = (
                (has_substantial_images and has_minimal_text) or
                (has_substantial_drawings and has_minimal_text) or
                (has_no_text_blocks and (has_substantial_images or has_substantial_drawings))
            )
            
            # Determine page type based on content
            if form_field_count > 0:
                page_type = 'form'
            elif text_length > 100:  # Substantial text content
                if image_count > 0:
                    page_type = 'mixed'
                else:
                    page_type = 'text'
            elif is_likely_scanned:
                page_type = 'scanned'
            elif text_length > 0 or text_block_count > 0:
                # Has some text content - treat as text page even if minimal
                page_type = 'text'
            else:
                page_type = 'empty'
            
            return {
                'page_num': page_num,
                'page_type': page_type,
                'text_length': text_length,
                'image_count': image_count,
                'form_field_count': form_field_count,
                'drawing_count': drawing_count,
                'rotation': rotation,
                'has_substantial_text': text_length > 100,
                'has_images': image_count > 0,
                'has_forms': form_field_count > 0,
                'is_likely_scanned': is_likely_scanned,
                'text_block_count': text_block_count,
                'page_area': page_area
            }
            
        except Exception as e:
            return {
                'page_num': page_num,
                'page_type': 'error',
                'error': str(e),
                'text_length': 0,
                'image_count': 0,
                'form_field_count': 0,
                'drawing_count': 0,
                'rotation': 0,
                'has_substantial_text': False,
                'has_images': False,
                'has_forms': False,
                'is_likely_scanned': False,
                'text_block_count': 0,
                'page_area': 0
            }
    
    def _determine_document_type(self, page_analyses, pdf_path):
        """
        Determine the overall document type and best pipeline based on page analyses
        
        Args:
            page_analyses (list): List of page analysis results
            pdf_path (str): Path to the PDF file
            
        Returns:
            tuple: (pipeline_type, detection_notes)
        """
        try:
            total_pages = len(page_analyses)
            if total_pages == 0:
                return 'ScanImage', 'No pages found - defaulting to ScanImage'
            
            # Count page types
            page_types = [analysis['page_type'] for analysis in page_analyses]
            type_counts = {}
            for page_type in page_types:
                type_counts[page_type] = type_counts.get(page_type, 0) + 1
            
            # Count content characteristics
            text_pages = sum(1 for analysis in page_analyses if analysis['has_substantial_text'])
            image_pages = sum(1 for analysis in page_analyses if analysis['has_images'])
            form_pages = sum(1 for analysis in page_analyses if analysis['has_forms'])
            scanned_pages = sum(1 for analysis in page_analyses if analysis['page_type'] == 'scanned')
            likely_scanned_pages = sum(1 for analysis in page_analyses if analysis.get('is_likely_scanned', False))
            
            # Determine document type with more conservative approach
            if form_pages > 0:
                # Document has form fields
                if text_pages > image_pages:
                    pipeline_type = 'NativePDF'
                    notes = f'Hybrid document with forms and text ({form_pages} form pages, {text_pages} text pages)'
                else:
                    pipeline_type = 'ScanImage'
                    notes = f'Hybrid document with forms and images ({form_pages} form pages, {image_pages} image pages)'
            elif text_pages > total_pages * 0.5:  # More than 50% text pages
                pipeline_type = 'NativePDF'
                notes = f'Text-based document ({text_pages}/{total_pages} pages have substantial text)'
            elif scanned_pages > total_pages * 0.7:  # More than 70% clearly scanned pages
                pipeline_type = 'ScanImage'
                notes = f'Scanned document ({scanned_pages}/{total_pages} scanned pages)'
            elif text_pages > 0:  # Has any substantial text pages - prefer NativePDF
                # Check if any page has substantial text (not just minimal text)
                substantial_text_pages = sum(1 for analysis in page_analyses if analysis['text_length'] > 200)
                if substantial_text_pages > 0:
                    pipeline_type = 'NativePDF'
                    notes = f'Native PDF with substantial text content ({substantial_text_pages} pages with >200 chars, {text_pages} total text pages)'
                else:
                    pipeline_type = 'ScanImage'
                    notes = f'Hybrid document with minimal text content ({text_pages} text pages, {image_pages} image pages, {scanned_pages} scanned pages)'
            elif image_pages > total_pages * 0.8:  # More than 80% image pages (higher threshold)
                pipeline_type = 'ScanImage'
                notes = f'Image-based document ({image_pages}/{total_pages} pages have images)'
            else:
                # No text pages at all - likely scanned
                pipeline_type = 'ScanImage'
                notes = f'Document with no extractable text ({image_pages} image pages, {scanned_pages} scanned pages)'
            
            # Add rotation information if relevant
            rotated_pages = sum(1 for analysis in page_analyses if analysis['rotation'] != 0)
            if rotated_pages > 0:
                notes += f', {rotated_pages} rotated pages'
            
            return pipeline_type, notes
            
        except Exception as e:
            return 'ScanImage', f'Document type determination failed: {str(e)}'

    def _convert_formatted_content_to_pdf(self, formatted_content, pdf_path):
        """Convert Word content with formatting to PDF preserving styles"""
        try:
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.units import inch
                from reportlab.lib.enums import TA_LEFT, TA_CENTER
            except ImportError:
                self.log("ReportLab not available for formatted conversion")
                return False
                
            # Handle empty content
            if not formatted_content:
                doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
                styles = getSampleStyleSheet()
                story = [Paragraph("[Empty Document]", styles['Normal'])]
                doc.build(story)
                return True
                
            # Create PDF with formatting preservation
            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                                    topMargin=inch, bottomMargin=inch,
                                    leftMargin=inch, rightMargin=inch)
            styles = getSampleStyleSheet()
            story = []
            
            for para_info in formatted_content:
                style_name = para_info['style']
                
                # Map Word styles to ReportLab styles
                if 'Heading 1' in style_name:
                    style = styles['Heading1']
                elif 'Heading 2' in style_name:
                    style = styles['Heading2']
                elif 'Heading 3' in style_name:
                    style = styles['Heading3']
                elif 'Title' in style_name:
                    style = styles['Title']
                else:
                    style = styles['Normal']
                
                # Build formatted text with runs
                if para_info['runs']:
                    # Construct paragraph with inline formatting
                    formatted_text = ""
                    for run in para_info['runs']:
                        run_text = run['text']
                        
                        # Apply formatting tags
                        if run['bold']:
                            run_text = f"<b>{run_text}</b>"
                        if run['italic']:
                            run_text = f"<i>{run_text}</i>"
                        if run['underline']:
                            run_text = f"<u>{run_text}</u>"
                            
                        formatted_text += run_text
                        
                    para = Paragraph(formatted_text, style)
                else:
                    # Fallback to plain text
                    para = Paragraph(para_info['text'], style)
                    
                story.append(para)
                story.append(Spacer(1, 6))  # Small space between paragraphs
                    
            doc.build(story)
            return True
            
        except Exception as e:
            self.log(f"Formatted content to PDF conversion error: {str(e)}")
            return False
            
    def _convert_clean_text_to_pdf(self, text_content, pdf_path):
        """Convert clean text to PDF preserving formatting"""
        try:
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
                from reportlab.lib.units import inch
                from reportlab.lib.enums import TA_LEFT
            except ImportError:
                self.log("ReportLab not available for text conversion")
                return False
                
            # Handle empty or whitespace-only content
            if not text_content or not text_content.strip():
                # Create a minimal PDF with just one line for empty documents
                doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
                styles = getSampleStyleSheet()
                story = [Paragraph("[Empty Document]", styles['Normal'])]
                doc.build(story)
                return True
                
            # Create PDF with better formatting preservation
            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                                    topMargin=inch, bottomMargin=inch,
                                    leftMargin=inch, rightMargin=inch)
            styles = getSampleStyleSheet()
            
            # Create a monospace style for better formatting preservation
            mono_style = ParagraphStyle(
                'MonoNormal',
                parent=styles['Normal'],
                fontName='Courier',  # Monospace font
                fontSize=10,
                leading=12,
                alignment=TA_LEFT,
                spaceAfter=0,
                spaceBefore=0
            )
            
            story = []
            lines = text_content.split('\n')
            
            for line in lines:
                if line.strip():
                    # Escape HTML characters and preserve spaces
                    escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    escaped_line = escaped_line.replace(' ', '&nbsp;')  # Preserve spaces
                    para = Paragraph(escaped_line, mono_style)
                    story.append(para)
                else:
                    # Add small spacer for empty lines
                    story.append(Spacer(1, 6))
                    
            doc.build(story)
            return True
            
        except Exception as e:
            self.log(f"Clean text to PDF conversion error: {str(e)}")
            return False
            
    def _assign_file_number(self, file_info):
        """Assign a file number to a successfully processed file"""
        file_number = self.current_file_number
        self.current_file_number += 1
        file_info['file_number'] = file_number
        return file_number
    
    def _move_to_failures(self, file_path, reason):
        """Move file to failures folder and log the reason"""
        try:
            failure_path = self.failures_folder / file_path.name
            shutil.move(file_path, failure_path)
            self.log(f"❌ Moved to failures: {file_path.name} - {reason}")
            self.logger_manager.log_conversion_failure(str(file_path), reason, "processing")
        except Exception as e:
            self.log(f"Error moving to failures: {str(e)}")
            if file_path.exists():
                file_path.unlink()
    
    def _cleanup_copied_files(self):
        """Clean up copied files from processed folder after successful processing"""
        try:
            if not hasattr(self, 'copied_files') or not self.copied_files:
                return
                
            files_removed = 0
            for file_info in self.copied_files:
                try:
                    copied_file_path = Path(file_info.get('copied_path', ''))
                    if copied_file_path.exists():
                        copied_file_path.unlink()
                        files_removed += 1
                        self.log(f"🧹 Cleaned up temporary file: {copied_file_path.name}")
                except Exception as e:
                    self.log(f"⚠️  Could not clean up {file_info.get('copied_path', 'unknown')}: {str(e)}")
            
            if files_removed > 0:
                self.log(f"✅ Cleaned up {files_removed} temporary files from processed folder")
            
        except Exception as e:
            self.log(f"Error during cleanup: {str(e)}")
            
    def _create_log_files(self):
        """Create comprehensive log files"""
        try:
            # Save processing summary report for legal review
            summary_path = self.logger_manager.create_summary_report(str(self.processed_folder))
            if summary_path:
                self.log(f"Processing summary saved: {Path(summary_path).name}")
                
            # Save detailed JSON log (for technical troubleshooting only)
            json_log_path = self.logger_manager.save_log_file(str(self.processed_folder))
            if json_log_path:
                self.log(f"Technical log saved: {Path(json_log_path).name}")
                
            return True
            
        except Exception as e:
            self.log(f"Error creating log files: {str(e)}")
            return False
            
    def _create_csv_log(self):
        """Create CSV log file with detailed processing information"""
        try:
            if not fitz:
                self.log("PyMuPDF not available - cannot create CSV log")
                return False
            
            # CSV filename (without datetime)
            csv_filename = f"quick_log.csv"
            csv_path = self.processed_folder / csv_filename
            
            # CSV headers
            headers = [
                'filename',
                'gutter_width_inches', 
                'pipeline_type',
                'page_height_inches',
                'page_width_inches', 
                'total_pages',
                'total_lines',
                'file_size_mb',
                'bates_number',
                'processing_date',
                'status'
            ]
            
            rows = []
            
            # Process each final PDF
            if hasattr(self, 'final_pdfs') and self.final_pdfs:
                for pdf_info in self.final_pdfs:
                    pdf_path = Path(pdf_info.get('final_path', ''))
                    if not pdf_path.exists() or not pdf_path.name.endswith('.pdf'):
                        continue
                    
                    try:
                        # Get file info
                        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                        filename = pdf_path.name
                        
                        # Extract bates number
                        bates_number = pdf_info.get('bates_number', 'Unknown')
                        
                        # Get PDF details
                        doc = fitz.open(str(pdf_path))
                        total_pages = len(doc)
                        
                        # Get page dimensions
                        if total_pages > 0:
                            first_page = doc[0]
                            width_inches = first_page.rect.width / 72
                            height_inches = first_page.rect.height / 72
                        else:
                            width_inches = 0
                            height_inches = 0
                        
                        # Determine pipeline type
                        pipeline = pdf_info.get('processing_pipeline', 'unknown')
                        if pipeline == 'text_based':
                            pipeline_type = 'Text-based (Word/Text)'
                        elif pipeline == 'complex':
                            doc_type = pdf_info.get('document_type', 'unknown')
                            # Debug: print the doc_type for files being processed
                            if filename.startswith('0015_'):
                                print(f"DEBUG: File {filename} has doc_type: {doc_type}")
                            if doc_type in ['scanned', 'image_based', 'tiff', 'pdf_image']:
                                pipeline_type = 'Scan/Image'
                            else:
                                pipeline_type = 'Native PDF'
                        else:
                            pipeline_type = pipeline
                        
                        # Get line count
                        total_lines = pdf_info.get('lines_added', 0)
                        if not isinstance(total_lines, int):
                            total_lines = 0
                        
                        # Get gutter width from universal line numbering system
                        gutter_width_inches = self.universal_line_numberer.legal_gutter_width / 72
                        
                        doc.close()
                        
                        # Create row
                        row = {
                            'filename': filename,
                            'gutter_width_inches': round(gutter_width_inches, 3),
                            'pipeline_type': pipeline_type,
                            'page_height_inches': round(height_inches, 2),
                            'page_width_inches': round(width_inches, 2),
                            'total_pages': total_pages,
                            'total_lines': total_lines,
                            'file_size_mb': round(file_size_mb, 2),
                            'bates_number': bates_number,
                            'processing_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': 'Success'
                        }
                        
                        rows.append(row)
                        
                    except Exception as e:
                        self.log(f"Error processing PDF {pdf_path.name} for CSV: {e}")
                        rows.append({
                            'filename': pdf_path.name,
                            'gutter_width_inches': 'Error',
                            'pipeline_type': 'Error', 
                            'page_height_inches': 'Error',
                            'page_width_inches': 'Error',
                            'total_pages': 'Error',
                            'total_lines': 'Error',
                            'file_size_mb': 'Error',
                            'bates_number': 'Error',
                            'processing_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': f'Error: {str(e)}'
                        })
            
            # Write CSV file
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            
            # Also save copy in root folder
            root_csv_path = Path.cwd() / csv_filename
            with open(root_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            
            self.log(f"CSV log created: {csv_filename} (in output folder and root)")
            
            # Print summary
            if rows:
                successful_files = [r for r in rows if r['status'] == 'Success']
                total_lines_all = sum(r['total_lines'] for r in successful_files if isinstance(r['total_lines'], int))
                total_pages_all = sum(r['total_pages'] for r in successful_files if isinstance(r['total_pages'], int))
                total_size_all = sum(r['file_size_mb'] for r in successful_files if isinstance(r['file_size_mb'], (int, float)))
                
                self.log(f"CSV Log Summary: {len(successful_files)} successful files, {total_lines_all} total lines, {total_pages_all} total pages, {total_size_all:.2f} MB total size")
            
            return True
            
        except Exception as e:
            self.log(f"Error creating CSV log: {str(e)}")
            return False
            
    def get_processing_summary(self):
        """Get summary of processing results"""
        return {
            'source_folder': str(self.source_folder),
            'processed_folder': str(self.processed_folder),
            'bates_prefix': self.bates_prefix,
            'bates_range': f"{self.bates_prefix}{self.bates_start_number:04d}-{self.bates_prefix}{self.current_bates_number-1:04d}",
            'line_range': f"Each document: 1-N (per document restart)",
            'files_found': len(self.found_files),
            'files_copied': len(self.copied_files),
            'files_converted': len(self.converted_files),
            'files_processed': len(self.final_pdfs),
            'statistics': self.logger_manager.get_processing_statistics()
        }


