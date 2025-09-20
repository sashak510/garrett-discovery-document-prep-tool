#!/usr/bin/env python3
"""
Quick check to see what's actually happening with rotation normalization
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF

def check_rotations():
    """Check rotations of original vs normalized files"""
    print("🔍 Quick Rotation Check")
    print("=" * 40)

    # Check the actual problematic files
    test_files = [
        ("Test Files 2/Rotations/native rotated landscape 90.pdf", "Test files_Processed/normalized_native rotated landscape 90.pdf"),
        ("Test Files 2/Rotations/native rotated landscape 180.pdf", "Test files_Processed/normalized_native rotated landscape 180.pdf"),
        ("Test Files 2/Rotations/native rotated landscape 270.pdf", "Test files_Processed/normalized_native rotated landscape 270.pdf")
    ]

    for original_path, normalized_path in test_files:
        print(f"\n📄 {os.path.basename(original_path)}")

        # Check original
        try:
            doc = fitz.open(original_path)
            orig_rotation = doc[0].rotation
            orig_size = os.path.getsize(original_path)
            doc.close()
            print(f"   Original: {orig_rotation}°, {orig_size:,} bytes")
        except Exception as e:
            print(f"   Original: Error - {e}")
            continue

        # Check normalized
        try:
            doc = fitz.open(normalized_path)
            norm_rotation = doc[0].rotation
            norm_size = os.path.getsize(normalized_path)
            doc.close()
            print(f"   Normalized: {norm_rotation}°, {norm_size:,} bytes")

            if norm_rotation == 0:
                print(f"   ✅ SUCCESS: Fixed!")
            else:
                print(f"   ❌ FAILED: Still {norm_rotation}°")

        except Exception as e:
            print(f"   Normalized: Error - {e}")

if __name__ == "__main__":
    check_rotations()