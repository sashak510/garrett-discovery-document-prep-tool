#!/usr/bin/env python3
"""
Quick verification script to check all processed files have 0° rotation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF

def check_all_rotations():
    """Check rotation of all processed files"""
    print("🔍 Final Rotation Verification")
    print("=" * 40)

    processed_dir = "Test files_Processed"
    all_good = True

    for filename in sorted(os.listdir(processed_dir)):
        if filename.endswith('.pdf') and not filename.startswith('original_') and not filename.startswith('temp_'):
            filepath = os.path.join(processed_dir, filename)

            try:
                doc = fitz.open(filepath)
                rotations = []

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    rotations.append(page.rotation)

                doc.close()

                # Check if all pages have 0° rotation
                if all(rot == 0 for rot in rotations):
                    print(f"✅ {filename}: All pages at 0°")
                else:
                    print(f"❌ {filename}: Rotations found: {rotations}")
                    all_good = False

            except Exception as e:
                print(f"❌ Error checking {filename}: {e}")
                all_good = False

    print("\n" + "=" * 40)
    if all_good:
        print("🎉 SUCCESS: All processed files are correctly oriented to 0°!")
    else:
        print("⚠️  WARNING: Some files still have rotation issues")

    return all_good

if __name__ == "__main__":
    check_all_rotations()