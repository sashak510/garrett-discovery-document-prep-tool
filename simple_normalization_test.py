#!/usr/bin/env python3
"""
Simple test to create rotation-normalized files in the main output folder
"""

import sys
import os
import shutil
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF

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

def main():
    """Create normalized files in the main output folder"""
    print("🔄 Creating Rotation-Normalized Files in Main Output Folder")
    print("=" * 70)

    # Setup paths
    source_folder = "Test Files 2/Rotations"
    output_folder = "Test files_Processed"

    # Clear output folder
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    # Test files (the problematic ones)
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
        output_path = os.path.join(output_folder, f"normalized_{filename}")

        print(f"📄 Processing: {filename}")

        if not os.path.exists(input_path):
            print(f"   ❌ Source file not found")
            continue

        try:
            # Get original info
            doc = fitz.open(input_path)
            original_rotation = doc[0].rotation
            original_size = os.path.getsize(input_path)
            original_dimensions = f"{doc[0].rect.width:.0f}x{doc[0].rect.height:.0f}"
            doc.close()

            print(f"   📋 Original: {original_rotation}°, {original_dimensions}, {original_size:,} bytes")

            # Normalize rotation
            success, message = normalize_rotation_via_export(input_path, output_path)

            if success:
                # Get normalized info
                norm_doc = fitz.open(output_path)
                norm_rotation = norm_doc[0].rotation
                norm_size = os.path.getsize(output_path)
                norm_dimensions = f"{norm_doc[0].rect.width:.0f}x{norm_doc[0].rect.height:.0f}"
                norm_doc.close()

                print(f"   ✅ Normalized: {norm_rotation}°, {norm_dimensions}, {norm_size:,} bytes")
                print(f"   📏 Size ratio: {norm_size/original_size:.2f}x")

                # Verify success
                if norm_rotation == 0:
                    print(f"   🎯 SUCCESS: Rotation corrected!")
                else:
                    print(f"   ⚠️  WARNING: Rotation not fully corrected")

                results.append({
                    'filename': filename,
                    'original_rotation': original_rotation,
                    'normalized_rotation': norm_rotation,
                    'original_size': original_size,
                    'normalized_size': norm_size,
                    'size_ratio': norm_size/original_size,
                    'success': norm_rotation == 0
                })

            else:
                print(f"   ❌ Normalization failed: {message}")
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': message
                })

        except Exception as e:
            print(f"   ❌ Error processing: {e}")
            results.append({
                'filename': filename,
                'success': False,
                'error': str(e)
            })

        print()

    # Summary
    print("📊 Summary Report")
    print("-" * 30)

    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]

    print(f"✅ Successfully normalized: {len(successful)} files")
    print(f"❌ Failed: {len(failed)} files")

    if successful:
        print(f"\n📈 Successful Results:")
        for result in successful:
            print(f"   • {result['filename']}: {result['original_rotation']}° → {result['normalized_rotation']}° ({result['size_ratio']:.2f}x size)")

    if failed:
        print(f"\n❌ Failed Results:")
        for result in failed:
            print(f"   • {result['filename']}: {result.get('error', 'Unknown error')}")

    # List final files
    print(f"\n🔍 Final Files in {output_folder}:")
    if os.path.exists(output_folder):
        files = [f for f in os.listdir(output_folder) if f.endswith('.pdf')]
        for file in sorted(files):
            file_path = os.path.join(output_folder, file)
            try:
                doc = fitz.open(file_path)
                rotation = doc[0].rotation
                size = os.path.getsize(file_path)
                dimensions = f"{doc[0].rect.width:.0f}x{doc[0].rect.height:.0f}"
                doc.close()
                print(f"   • {file}: {rotation}°, {dimensions}, {size:,} bytes")
            except Exception as e:
                print(f"   • {file}: Error checking - {e}")

    print(f"\n📁 Normalized files ready in: {output_folder}")
    return len(successful) > 0

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Test completed successfully! Files are ready for review.")
    else:
        print("\n⚠️  Test completed with issues.")