#!/usr/bin/env python3
"""
Summary analysis of the key differences between PDF file types
"""

def analyze_differences():
    print("🔍 PDF File Type Analysis Summary")
    print("=" * 60)

    print("""
📋 KEY FINDINGS:

🎯 NATIVE ROTATED FILES (The problematic ones):
   • Size: ~126KB each (medium size)
   • Creator: Mozilla/5.0 (Chrome browser) → macOS Quartz PDFContext
   • Page size: 842x595 or 595x842 (A4 dimensions)
   • Content: 1 image + 0 text characters + 1 text block (type 1)
   • Text block bbox: [28.5, 77.0, 814.5, 519.1] (content area)
   • Issue: These appear to be web pages/screenshots saved as PDFs with rotation metadata

🎯 LANDSCAPE ROTATED FILES (Working correctly):
   • Size: ~1.7KB each (very small - text only)
   • Creator: ReportLab PDF Library (programmatically generated)
   • Page size: 792x612 (Letter dimensions)
   • Content: 0 images + 31-32 text characters + 1 text block (type 0)
   • Text block bbox: Small area for actual text content
   • Working: These are pure text PDFs with rotation applied

🎯 SCANNED FILES (Working correctly):
   • Size: ~5.9MB each (very large - high resolution scans)
   • Creator: (empty) → macOS Quartz PDFContext
   • Page size: 2532x1783 or 1783x2532 (high resolution)
   • Content: 1 image + 0 text characters + 1 text block (type 1)
   • Text block bbox: [0.0, 0.0, 2532.0, 1783.0] (full page)
   • Working: These are pure image scans

🎯 LANDSCAPE CONTENT ROTATED FILES (Working correctly):
   • Size: ~1.7KB each (very small - text only)
   • Creator: ReportLab PDF Library (programmatically generated)
   • Page size: 792x612 (Letter dimensions)
   • Content: 0 images + 39-40 text characters + 1 text block (type 0)
   • Working: These are pure text PDFs with rotated content

🔍 THE CRITICAL DIFFERENCE:

The NATIVE ROTATED files are different because:

1. **Origin**: Created from web content (Chrome) → saved as PDF → rotated
2. **Content Structure**: Have both an image AND a text block, but the text block contains 0 actual text characters
3. **Text Block Type**: Type 1 (image-based) vs Type 0 (text-based) in working files
4. **Size Medium**: Not pure text (like landscape) and not pure image (like scanned)

🛠️ WHY THE DETECTION FAILED:

Original pipeline logic:
   • NativePDF: avg_text_per_page > 100 OR (no images + has text)
   • ScanImage: everything else

For native rotated files:
   • avg_text_per_page = 0 (doesn't meet > 100 threshold)
   • Has images (1) AND has text blocks (1) but 0 text chars
   → Falls through to ScanImage pipeline

🎯 THE FIX APPLIED:

Added rotation detection to pipeline logic:
   • If ANY page has rotation != 0° → Force NativePDF pipeline
   • This ensures rotation correction is applied

✅ RESULT: All files now correctly processed and oriented to 0°
""")

if __name__ == "__main__":
    analyze_differences()