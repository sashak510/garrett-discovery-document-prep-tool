#!/usr/bin/env python3
"""
Move landscape_content_rotated files to failures folder
"""

import os
import shutil

def move_content_rotated_to_failures():
    """Move landscape_content_rotated files to failures folder"""
    print("📁 Moving Content-Rotated Files to Failures")
    print("=" * 50)

    # Source and destination folders
    source_folder = "Test Files 2/Rotations"
    output_folder = "Test files_Processed"
    failures_folder = os.path.join(output_folder, "Failures")

    # Ensure failures folder exists
    os.makedirs(failures_folder, exist_ok=True)

    # Files to move
    content_rotated_files = [
        "landscape_content_rotated_90.pdf",
        "landscape_content_rotated_180.pdf",
        "landscape_content_rotated_270.pdf"
    ]

    moved_files = []
    failed_files = []

    for filename in content_rotated_files:
        source_path = os.path.join(source_folder, filename)
        failure_path = os.path.join(failures_folder, filename)

        print(f"📄 Processing: {filename}")

        if not os.path.exists(source_path):
            print(f"   ❌ Source file not found")
            failed_files.append(filename)
            continue

        try:
            # Copy to failures folder
            shutil.copy2(source_path, failure_path)
            print(f"   ✅ Moved to failures folder")
            moved_files.append(filename)

        except Exception as e:
            print(f"   ❌ Failed to move: {e}")
            failed_files.append(filename)

    # Summary
    print(f"\n📊 Summary:")
    print(f"✅ Successfully moved: {len(moved_files)} files")
    print(f"❌ Failed to move: {len(failed_files)} files")

    if moved_files:
        print(f"\n📁 Files moved to {failures_folder}:")
        for filename in moved_files:
            print(f"   • {filename}")

    print(f"\n📂 Failures folder contents:")
    if os.path.exists(failures_folder):
        files = os.listdir(failures_folder)
        for file in sorted(files):
            print(f"   • {file}")

    return len(moved_files) > 0

if __name__ == "__main__":
    success = move_content_rotated_to_failures()
    if success:
        print(f"\n🎉 Successfully moved content-rotated files to failures!")
    else:
        print(f"\n⚠️  No files were moved.")