#!/usr/bin/env python3
"""
Integration test to process rotation files with normalization in the main output folder
"""

import sys
import os
import shutil
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF
from document_processor import GDIDocumentProcessor

def normalize_rotation_via_export(input_path, output_path):
    """
    Normalize PDF rotation by exporting through PyMuPDF
    This method preserves quality and handles hybrid (image+HTML) PDFs
    """
    try:
        doc = fitz.open(input_path)

        # Check if rotation normalization is needed
        needs_correction = any(page.rotation != 0 for page in doc)

        if not needs_correction:
            doc.close()
            return False, "No rotation correction needed"

        # Create output document
        output_doc = fitz.open()

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Create new page with same dimensions
            new_page = output_doc.new_page(
                width=page.rect.width,
                height=page.rect.height
            )

            # Copy page content (this automatically normalizes rotation)
            new_page.show_pdf_page(page.rect, doc, page_num)

        # Save with optimization
        output_doc.save(output_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        doc.close()

        return True, "Rotation normalization successful"

    except Exception as e:
        return False, f"Normalization failed: {str(e)}"

def run_integration_test():
    """Run integration test with normalization in main output folder"""
    print("🔄 Integration Test: Rotation Normalization in Main Processing")
    print("=" * 70)

    # Setup paths
    source_folder = "Test Files 2/Rotations"
    output_folder = "Test files_Processed"

    # Clear and recreate output folder
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    # Test files
    test_files = [
        "native rotated landscape 90.pdf",
        "native rotated landscape 180.pdf",
        "native rotated landscape 270.pdf"
    ]

    print(f"📂 Source: {source_folder}")
    print(f"📂 Output: {output_folder}")
    print()

    results = []

    for filename in test_files:
        input_path = os.path.join(source_folder, filename)
        temp_normalized_path = os.path.join(output_folder, f"temp_normalized_{filename}")

        print(f"📄 Processing: {filename}")

        if not os.path.exists(input_path):
            print(f"   ❌ Source file not found")
            continue

        try:
            # Step 1: Normalize rotation first
            print(f"   🔧 Step 1: Normalizing rotation...")
            success, message = normalize_rotation_via_export(input_path, temp_normalized_path)

            if not success:
                print(f"   ❌ Normalization failed: {message}")
                continue

            # Check normalized file
            norm_doc = fitz.open(temp_normalized_path)
            norm_rotation = norm_doc[0].rotation
            norm_doc.close()

            print(f"   ✅ Normalized to: {norm_rotation}°")

            # Step 2: Process with DocumentProcessor (add line numbers, bates, etc.)
            print(f"   📝 Step 2: Adding line numbers and processing...")

            # Initialize processor
            processor = GDIDocumentProcessor(
                source_folder=output_folder,  # Use output folder as source for normalized files
                output_folder=output_folder,
                bates_prefix="TEST",
                bates_start_number=1,
                file_naming_start=1,
                logger_manager=None  # Simple mode
            )

            # Process just this one file
            result = processor.process_document(Path(temp_normalized_path))

            if result['success']:
                final_filename = f"normalized_{filename}"
                final_path = os.path.join(output_folder, final_filename)

                # Rename to final name
                if os.path.exists(result['final_path']):
                    shutil.move(result['final_path'], final_path)

                print(f"   ✅ Processing complete: {final_filename}")
                print(f"   📏 Lines added: {result['lines_added']}")
                print(f"   🏷️  Bates: TEST0001")

                results.append({
                    'filename': filename,
                    'final_filename': final_filename,
                    'original_rotation': 'unknown',
                    'normalized_rotation': norm_rotation,
                    'success': True
                })

            else:
                print(f"   ❌ Processing failed: {result.get('error', 'Unknown error')}")

            # Clean up temp file
            try:
                os.unlink(temp_normalized_path)
            except:
                pass

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                'filename': filename,
                'success': False,
                'error': str(e)
            })

        print()

    # Summary
    print("📊 Integration Test Summary")
    print("-" * 40)

    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]

    print(f"✅ Successfully processed: {len(successful)} files")
    print(f"❌ Failed: {len(failed)} files")

    if successful:
        print(f"\n📈 Successful Results:")
        for result in successful:
            print(f"   • {result['filename']} → {result['final_filename']}")

    if failed:
        print(f"\n❌ Failed Results:")
        for result in failed:
            print(f"   • {result['filename']}: {result.get('error', 'Unknown error')}")

    # Check final files
    print(f"\n🔍 Final Files in Output Folder:")
    if os.path.exists(output_folder):
        files = [f for f in os.listdir(output_folder) if f.endswith('.pdf') and not f.startswith('temp_')]
        for file in sorted(files):
            file_path = os.path.join(output_folder, file)
            try:
                doc = fitz.open(file_path)
                rotation = doc[0].rotation
                size = os.path.getsize(file_path)
                doc.close()
                print(f"   • {file}: {rotation}°, {size:,} bytes")
            except Exception as e:
                print(f"   • {file}: Error checking - {e}")

    return len(successful) > 0

if __name__ == "__main__":
    success = run_integration_test()
    if success:
        print("\n🎉 Integration test completed successfully!")
    else:
        print("\n⚠️  Integration test completed with issues.")