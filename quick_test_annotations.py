#!/usr/bin/env python3
"""
Quick Test Script for Annotation-based PDF Processing
Clean, professional approach using PDF annotation system
"""

import os
import sys
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from annotation_line_numbering import AnnotationLineNumberer


def log_callback(message):
    """Simple log callback for testing"""
    print(f"[LOG] {message}")


def main():
    """Main test function using annotation approach"""
    parser = argparse.ArgumentParser(description='PDF Processing Tool - Annotation-based Line Numbering')
    parser.add_argument('--limit', '-l', type=int, default=None,
                       help='Number of files to process (default: all files)')

    args = parser.parse_args()

    print("🔍 PDF PROCESSING TOOL - ANNOTATION APPROACH")
    print("=" * 50)
    print("Professional PDF annotation-based line numbering")
    print()

    # Configuration
    source_folder = "Test Files 2"
    output_folder = "Test files_Processed_Annotations_Clean"
    bates_prefix = "CLEAN"
    file_limit = args.limit

    print(f"Source folder: {source_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Bates prefix: {bates_prefix}")
    if file_limit:
        print(f"File limit: {file_limit} files")
    else:
        print(f"File limit: All files")
    print()
    
    print("🎯 ANNOTATION APPROACH ADVANTAGES:")
    print("   ✅ Professional legal standard")
    print("   ✅ Line numbers are searchable and selectable")
    print("   ✅ Non-removable and permanent")
    print("   ✅ Preserves original content completely")
    print("   ✅ Small file sizes")
    print("   ✅ Industry standard approach")
    print()

    # Check if source folder exists
    if not os.path.exists(source_folder):
        print(f"❌ Source folder '{source_folder}' does not exist!")
        return
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        # Initialize annotation numberer
        print("Initializing annotation-based processor...")
        numberer = AnnotationLineNumberer(log_callback=log_callback)
        
        # Get PDF files
        pdf_files = list(Path(source_folder).glob("*.pdf"))
        
        if not pdf_files:
            print(f"❌ No PDF files found in {source_folder}")
            return
        
        # Apply file limit
        if file_limit:
            pdf_files = pdf_files[:file_limit]
            print(f"Processing {len(pdf_files)} files (limited)")
        else:
            print(f"Processing {len(pdf_files)} files")
        
        print("-" * 50)
        
        successful_files = 0
        failed_files = 0
        current_bates = 1
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n📄 Processing {i}/{len(pdf_files)}: {pdf_file.name}")
            
            # Create output filename
            output_file = Path(output_folder) / f"{i:04d}_{pdf_file.stem}_annotated.pdf"
            
            # Process with annotations (line numbers + bates + filename)
            success = numberer.add_bates_and_filename(
                str(pdf_file),
                str(output_file),
                bates_prefix=bates_prefix,
                bates_number=current_bates,
                filename=pdf_file.stem
            )
            
            if success:
                successful_files += 1
                current_bates += 1  # Increment for next file
                print(f"   ✅ Success: {output_file.name}")
            else:
                failed_files += 1
                print(f"   ❌ Failed: {pdf_file.name}")

        print("-" * 50)
        print(f"\n📊 PROCESSING SUMMARY:")
        print(f"   Total files: {len(pdf_files)}")
        print(f"   Successful: {successful_files}")
        print(f"   Failed: {failed_files}")
        print(f"   Success rate: {(successful_files/len(pdf_files)*100):.1f}%")
        
        if successful_files > 0:
            print(f"\n✅ Processing completed!")
            print(f"📁 Check output folder: {output_folder}")
            print("\n🔍 Each processed PDF contains:")
            print("   • Line numbers 1-28 (red, left side)")
            print("   • Bates numbers (black, bottom right)")
            print("   • Filename display (gray, bottom left)")
            print("   • All as professional PDF annotations")
        
        # Show any errors
        errors = numberer.get_errors()
        if errors:
            print(f"\n⚠️  {len(errors)} errors occurred:")
            for error in errors:
                print(f"   {error['type']}: {error['error']}")
        
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()