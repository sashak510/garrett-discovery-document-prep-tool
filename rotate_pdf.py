#!/usr/bin/env python3
"""
Remove PDF rotation metadata (page.rotation) so all pages are saved upright.
Keeps text/vector content intact.

Requires: pip install pymupdf
"""

import fitz  # PyMuPDF
import os


def remove_metadata(input_path, output_path):
    doc = fitz.open(input_path)

    for page in doc:
        try:
            # Reset rotation metadata to 0
            page.set_rotation(0)
        except Exception:
            pass  # Some PyMuPDF versions don't need this

    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()


def main():
    # 🔧 Hardcoded file paths
    input_pdf = "/Users/sashakarniyuk/Downloads/Upwork/Coding/garrett-discovery-document-prep-tool/Test Files 2/native rotated landscape 90.pdf"
    output_pdf = "/Users/sashakarniyuk/Downloads/Upwork/Coding/garrett-discovery-document-prep-tool/rotated_output.pdf"

    if not os.path.exists(input_pdf):
        print(f"❌ Input file not found: {input_pdf}")
        return

    print(f"🔄 Removing rotation metadata from: {input_pdf}")
    remove_metadata(input_pdf, output_pdf)
    print(f"✅ Saved cleaned PDF to: {output_pdf}")


if __name__ == "__main__":
    main()
