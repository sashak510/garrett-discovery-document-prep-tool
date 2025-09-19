#!/usr/bin/env python3
"""
Final PDF Processing Tool - Non-Searchable Line Numbers
Professional approach with visible but non-searchable line numbers
"""

import os
import sys
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vector_line_numbering import VectorLineNumberer


def log_callback(message):
    """Simple log callback for processing"""
    print(f"[LOG] {message}")


def main():
    """Main processing function"""
    parser = argparse.ArgumentParser(description='Professional PDF Processing Tool - Non-Searchable Line Numbers')
    parser.add_argument('--limit', '-l', type=int, default=None,
                       help='Number of files to process (default: all files)')
    parser.add_argument('--prefix', '-p', type=str, default="DOC",
                       help='Bates number prefix (default: DOC)')

    args = parser.parse_args()

    print("🎯 PROFESSIONAL PDF PROCESSING TOOL")
    print("=" * 50)
    print("Non-searchable line numbers • Professional legal standard")
    print()

    # Configuration
    source_folder = "Test Files 2"
    output_folder = "Test files_Processed_Final"
    bates_prefix = args.prefix
    file_limit = args.limit

    print(f"📁 Source folder: {source_folder}")
    print(f"📁 Output folder: {output_folder}")
    print(f"🏷️  Bates prefix: {bates_prefix}")
    if file_limit:
        print(f"📊 File limit: {file_limit} files")
    else:
        print(f"📊 File limit: All files")
    print()
    
    print("🎯 KEY FEATURES:")
    print("   ✅ Line numbers 1-28 (visible but NOT searchable)")
    print("   ✅ White gutter background for clean appearance")
    print("   ✅ Bates numbers (searchable)")
    print("   ✅ Filename display (searchable)")
    print("   ✅ Professional legal document standard")
    print("   ✅ Small file sizes with vector quality")
    print()

    # Check if source folder exists
    if not os.path.exists(source_folder):
        print(f"❌ Source folder '{source_folder}' does not exist!")
        print("Available test folders:")
        for item in Path(".").iterdir():
            if item.is_dir() and "test" in item.name.lower():
                print(f"   {item}")
        return
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        # Initialize processor
        print("🔧 Initializing non-searchable line numbering processor...")
        processor = VectorLineNumberer(log_callback=log_callback)
        
        # Get PDF files
        pdf_files = list(Path(source_folder).glob("*.pdf"))
        
        if not pdf_files:
            print(f"❌ No PDF files found in {source_folder}")
            return
        
        # Apply file limit
        if file_limit:
            pdf_files = pdf_files[:file_limit]
            print(f"📊 Processing {len(pdf_files)} files (limited)")
        else:
            print(f"📊 Processing {len(pdf_files)} files")
        
        print("-" * 50)
        
        successful_files = 0
        failed_files = 0
        current_bates = 1
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n📄 Processing {i}/{len(pdf_files)}: {pdf_file.name}")
            
            # Create output filename
            output_file = Path(output_folder) / f"{i:04d}_{pdf_file.stem}_processed.pdf"
            
            # Process with non-searchable line numbers + searchable bates/filename
            success = processor.add_bates_and_filename(
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
            print(f"\n✅ Processing completed successfully!")
            print(f"📁 Output folder: {output_folder}")
            print("\n🔍 Each processed PDF contains:")
            print("   • Line numbers 1-28 (red, left gutter) - NON-SEARCHABLE")
            print("   • White gutter background for clean appearance")
            print("   • Bates numbers (black, bottom right) - SEARCHABLE")
            print("   • Filename display (gray, bottom left) - SEARCHABLE")
            print("   • Professional legal document standard")
            
            print(f"\n🎯 VERIFICATION:")
            print(f"   Run a PDF search for line numbers (1, 2, 3, etc.)")
            print(f"   ✅ Expected: Very few or no hits (non-searchable)")
            print(f"   Run a PDF search for '{bates_prefix}'")
            print(f"   ✅ Expected: Found in bates numbers (searchable)")
        
        # Show any errors
        errors = processor.get_errors()
        if errors:
            print(f"\n⚠️  {len(errors)} errors occurred:")
            for error in errors:
                print(f"   • {error['type']}: {error['error']}")
        
        print(f"\n🎉 Final output ready in: {output_folder}")
        
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()