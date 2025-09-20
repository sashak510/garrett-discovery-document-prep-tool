#!/usr/bin/env python3
"""
Check the specific problematic files mentioned by user
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF

def main():
    print("🔍 Checking Problematic Files")
    print("=" * 40)

    # Check the specific files mentioned
    problematic_files = [
        "Test Files 2/Rotations/landscape_content_rotated_270.pdf",
        "Test Files 2/Rotations/landscape_content_rotated_90.pdf",
        "Test Files 2/Rotations/landscape_content_rotated_180.pdf"
    ]

    for file_path in problematic_files:
        print(f"\n📄 {os.path.basename(file_path)}")

        if not os.path.exists(file_path):
            print(f"   ❌ File not found")
            continue

        try:
            doc = fitz.open(file_path)
            page = doc[0]

            print(f"   Size: {page.rect.width:.0f}x{page.rect.height:.0f}")
            print(f"   Rotation: {page.rotation}°")
            print(f"   Is landscape: {page.rect.width > page.rect.height}")

            # Check text content
            text = page.get_text()
            print(f"   Text length: {len(text.strip())} chars")
            if len(text.strip()) > 0:
                print(f"   Text sample: {text[:50]}...")

            # Check images
            images = page.get_images()
            print(f"   Images: {len(images)}")

            doc.close()

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Also check the processed version mentioned
    print(f"\n📄 Checking processed version:")
    processed_file = "Test files_Processed/0002_landscape_content_rotated_270_NativePDF.pdf"

    if os.path.exists(processed_file):
        try:
            doc = fitz.open(processed_file)
            page = doc[0]
            print(f"   Size: {page.rect.width:.0f}x{page.rect.height:.0f}")
            print(f"   Rotation: {page.rotation}°")
            doc.close()
        except Exception as e:
            print(f"   ❌ Error checking processed file: {e}")
    else:
        print(f"   ❌ Processed file not found")

if __name__ == "__main__":
    main()