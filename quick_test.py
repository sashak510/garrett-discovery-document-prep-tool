#!/usr/bin/env python3
"""
Quick Test Script for Garrett Discovery Document Prep Tool
Simple command-line testing without the GUI
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from document_processor import GDIDocumentProcessor
from file_scanner import FileScanner
from pdf_converter import PDFConverter
from line_numbering import LineNumberer
from bates_numbering import BatesNumberer
from logger_manager import LoggerManager


def log_callback(message):
    """Simple log callback for testing"""
    print(f"[LOG] {message}")


def main():
    """Main test function"""
    print("=== Garrett Discovery Document Prep Tool - Quick Test ===")
    
    # Test configuration
    source_folder = "Test files"
    output_folder = "Test files_Processed"
    bates_prefix = ""
    bates_start_number = 1
    file_naming_start = 1
    
    print(f"Source folder: {source_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Bates prefix: {bates_prefix}")
    print(f"Bates start: {bates_start_number:04d}")
    print(f"File naming start: {file_naming_start:04d}")
    print()
    
    # Check if source folder exists
    if not os.path.exists(source_folder):
        print(f"ERROR: Source folder '{source_folder}' does not exist!")
        print("Please ensure the 'Test files' folder is present.")
        return
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        # Initialize components
        print("Initializing components...")
        file_scanner = FileScanner()
        pdf_converter = PDFConverter()
        line_numberer = LineNumberer()
        bates_numberer = BatesNumberer()
        logger_manager = LoggerManager()
        
        # Initialize document processor
        print("Creating document processor...")
        processor = GDIDocumentProcessor(
            source_folder=source_folder,
            bates_prefix=bates_prefix,
            bates_start_number=bates_start_number,
            file_naming_start=file_naming_start,
            output_folder=output_folder,
            log_callback=log_callback,
            line_numberer=line_numberer,
            bates_numberer=bates_numberer
        )
        
        print("Starting document processing...")
        print("-" * 50)
        
        # Process all documents
        success = processor.process_all_documents()
        
        print("-" * 50)
        if success:
            print("✅ Document processing completed successfully!")
        else:
            print("❌ Document processing completed with errors.")
            
        print(f"\nCheck the '{output_folder}' folder for processed documents.")
        
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
