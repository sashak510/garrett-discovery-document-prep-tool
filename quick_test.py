#!/usr/bin/env python3
"""
Quick Test Script for Garrett Discovery Document Prep Tool
Simple command-line testing without the GUI
"""

import os
import sys
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from document_processor import GDIDocumentProcessor
from file_scanner import FileScanner
from pdf_converter import PDFConverter
from line_numbering import LineNumberer
from bates_numbering import BatesNumberer
from logger_manager import LoggerManager
from universal_line_numbering import UniversalLineNumberer


def log_callback(message):
    """Simple log callback for testing"""
    print(f"[LOG] {message}")


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Garrett Discovery Document Prep Tool - Quick Test')
    parser.add_argument('--limit', '-l', type=int, default=None,
                       help='Number of files to process (default: all files)')

    args = parser.parse_args()

    print("=== Garrett Discovery Document Prep Tool - Quick Test ===")
    print("Updated with universal 28-line grid numbering and enhanced features")
    print()

    # Fixed configuration
    source_folder = "Test files"
    output_folder = "Test files_Processed"
    bates_prefix = "TEST"
    file_limit = args.limit

    # Default values
    bates_start_number = 1
    file_naming_start = 1

    print(f"Source folder: {source_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Bates prefix: {bates_prefix}")
    print(f"Bates start: {bates_start_number:04d}")
    print(f"File naming start: {file_naming_start:04d}")
    if file_limit:
        print(f"File limit: {file_limit} files")
    else:
        print(f"File limit: All files")
    print()
    print("Features tested:")
    print("✅ Universal 28-line grid numbering")
    print("✅ Original file preservation (prefix: original_<number>__<filename>)")
    print("✅ Filename display bottom left")
    print("✅ Bates numbering bottom right")
    print("✅ Memory management and error handling")
    print()

    # Check if source folder exists
    if not os.path.exists(source_folder):
        print(f"ERROR: Source folder '{source_folder}' does not exist!")
        print("Please ensure the source folder is present.")
        return
    
    # Create output folder if it doesn't exist and clear existing files
    if os.path.exists(output_folder):
        print(f"Clearing existing output folder: {output_folder}")
        for item in Path(output_folder).glob('*'):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
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
            bates_numberer=bates_numberer,
            file_limit=file_limit
        )
        
        print("Starting document processing...")
        print("-" * 50)
        
        # Process all documents
        success = processor.process_all_documents()
        
        print("-" * 50)
        if success:
            print("✅ Document processing completed successfully!")
            print("\nResults:")
            print("📄 Processed PDFs with 28-line grid numbering")
            print("📁 Original files preserved with 'original_' prefix")
            print("🏷️  Bates numbers applied (bottom right)")
            print("📝 Filenames displayed (bottom left)")
        else:
            print("❌ Document processing completed with errors.")

        print(f"\nCheck the '{output_folder}' folder for processed documents.")
        print("Look for:")
        print("- Final PDFs with line numbers (e.g., 0001_filename.pdf)")
        print("- Original files (e.g., original_0001__filename.docx)")
        print("- Failure files in 'Failures' subfolder (if any)")
        
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
