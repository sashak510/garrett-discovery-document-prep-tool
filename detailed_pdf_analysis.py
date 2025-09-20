#!/usr/bin/env python3
"""
Detailed analysis to understand the true nature of these problematic PDFs
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF

def analyze_pdf_structure(pdf_path):
    """Deep dive into PDF structure"""
    print(f"\n🔍 Deep Analysis: {os.path.basename(pdf_path)}")
    print("-" * 50)

    try:
        doc = fitz.open(pdf_path)
        page = doc[0]

        print(f"📄 Basic Info:")
        print(f"   - Size: {page.rect.width:.0f} x {page.rect.height:.0f}")
        print(f"   - Rotation: {page.rotation}°")
        print(f"   - Is landscape: {page.rect.width > page.rect.height}")

        # Check different text extraction methods
        print(f"\n📝 Text Analysis:")
        text_methods = [
            ("get_text()", lambda p: p.get_text()),
            ("get_text('text')", lambda p: p.get_text("text")),
            ("get_text('blocks')", lambda p: p.get_text("blocks")),
            ("get_text('words')", lambda p: p.get_text("words")),
            ("get_text('html')", lambda p: p.get_text("html")),
            ("get_text('xhtml')", lambda p: p.get_text("xhtml")),
            ("get_text('xml')", lambda p: p.get_text("xml")),
        ]

        for method_name, method_func in text_methods:
            try:
                result = method_func(page)
                if isinstance(result, str):
                    length = len(result.strip())
                    print(f"   - {method_name}: {length} chars")
                    if length > 0 and length < 200:
                        print(f"     Sample: {result[:100]}...")
                elif isinstance(result, list):
                    print(f"   - {method_name}: {len(result)} items")
            except Exception as e:
                print(f"   - {method_name}: Error - {e}")

        # Image analysis
        print(f"\n🖼️  Image Analysis:")
        images = page.get_images()
        print(f"   - Total images: {len(images)}")

        for i, img in enumerate(images):
            print(f"   - Image {i}: xref={img[0]}, width={img[2]}, height={img[3]}")

            # Try to get image details
            try:
                pix = fitz.Pixmap(doc, img[0])
                print(f"     - Pixmap: {pix.width}x{pix.height}, colorspace={pix.colorspace.name}")
                pix = None  # Clean up
            except Exception as e:
                print(f"     - Pixmap error: {e}")

        # Content stream analysis
        print(f"\n📋 Content Stream Analysis:")
        try:
            content = page.get_contents()
            if content:
                print(f"   - Has content stream: Yes")
                # Try to read content stream
                try:
                    stream = doc.xref_stream(content)
                    print(f"   - Stream length: {len(stream)} bytes")
                    # Look for PDF operators that indicate vector content
                    stream_str = stream.decode('latin-1', errors='ignore')
                    vector_ops = ['m', 'l', 'c', 'h', 'S', 's', 'f', 'F', 'B', 'b', 'W', 'w', 'j', 'J', 'M', 'd', 'ri', 'i', 'gs', 'sh', 'cs', 'sc', 'scn', 'CS', 'SC', 'SCN', 'g', 'G', 'rg', 'RG', 'k', 'K', 'sh', 'BI', 'ID', 'EI', 'Do', 'q', 'Q', 'cm', 'Tc', 'Tw', 'Tz', 'TL', 'Tf', 'Tr', 'Ts', 'BT', 'ET', 'Td', 'TD', 'Tm', 'T*', 'Tj', 'TJ', "'", '"']

                    found_ops = []
                    for op in vector_ops:
                        if op in stream_str:
                            found_ops.append(op)

                    if found_ops:
                        print(f"   - Vector ops found: {', '.join(found_ops[:10])}{'...' if len(found_ops) > 10 else ''}")

                    # Check for image vs vector content
                    if 'BI' in stream_str and 'ID' in stream_str and 'EI' in stream_str:
                        print(f"   - Contains inline images")
                    if 'Do' in stream_str:
                        print(f"   - Contains XObject references")
                    if any(op in stream_str for op in ['m', 'l', 'c', 'h']):
                        print(f"   - Contains path operations (vector)")

                except Exception as e:
                    print(f"   - Stream analysis failed: {e}")
            else:
                print(f"   - Has content stream: No")
        except Exception as e:
            print(f"   - Content stream error: {e}")

        # Page resources
        print(f"\n📦 Page Resources:")
        try:
            resources = page.get_xobjects()
            print(f"   - XObjects: {len(resources)}")

            fonts = page.get_fonts()
            print(f"   - Fonts: {len(fonts)}")
            for font in fonts[:3]:  # First 3 fonts
                print(f"     - {font[1]} (size: {font[2]})")

        except Exception as e:
            print(f"   - Resources error: {e}")

        doc.close()

    except Exception as e:
        print(f"❌ Analysis failed: {e}")

def test_export_methods(pdf_path):
    """Test different export methods"""
    print(f"\n🖨️  Export Method Test: {os.path.basename(pdf_path)}")
    print("-" * 40)

    try:
        import tempfile
        original_doc = fitz.open(pdf_path)
        original_page = original_doc[0]
        original_rotation = original_page.rotation

        print(f"📋 Original rotation: {original_rotation}°")

        # Method 1: Direct page copy (what we used before)
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                temp_path = tmp.name

            output_doc = fitz.open()
            new_page = output_doc.new_page(
                width=original_page.rect.width,
                height=original_page.rect.height
            )
            new_page.show_pdf_page(original_page.rect, original_doc, 0)
            output_doc.save(temp_path, garbage=4, deflate=True, clean=True)
            output_doc.close()

            # Check result
            test_doc = fitz.open(temp_path)
            test_rotation = test_doc[0].rotation
            test_doc.close()

            print(f"✅ Direct copy: {test_rotation}° (size: {os.path.getsize(temp_path):,} bytes)")
            os.unlink(temp_path)

        except Exception as e:
            print(f"❌ Direct copy failed: {e}")

        # Method 2: Copy with transformation matrix
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                temp_path = tmp.name

            output_doc = fitz.open()
            new_page = output_doc.new_page(
                width=original_page.rect.width,
                height=original_page.rect.height
            )

            # Apply transformation matrix to normalize rotation
            matrix = fitz.Matrix(1, 1)
            if original_rotation == 90:
                matrix = fitz.Matrix(0, 1, -1, 0, original_page.rect.height, 0)
            elif original_rotation == 180:
                matrix = fitz.Matrix(-1, 0, 0, -1, original_page.rect.width, original_page.rect.height)
            elif original_rotation == 270:
                matrix = fitz.Matrix(0, -1, 1, 0, 0, original_page.rect.width)

            new_page.show_pdf_page(original_page.rect, original_doc, 0, matrix=matrix)
            output_doc.save(temp_path, garbage=4, deflate=True, clean=True)
            output_doc.close()

            # Check result
            test_doc = fitz.open(temp_path)
            test_rotation = test_doc[0].rotation
            test_doc.close()

            print(f"✅ Matrix transform: {test_rotation}° (size: {os.path.getsize(temp_path):,} bytes)")
            os.unlink(temp_path)

        except Exception as e:
            print(f"❌ Matrix transform failed: {e}")

        original_doc.close()

    except Exception as e:
        print(f"❌ Export test failed: {e}")

def main():
    """Main analysis function"""
    print("🔍 Detailed PDF Structure Analysis")
    print("=" * 60)

    test_files = [
        "Test Files 2/Rotations/native rotated landscape 90.pdf",
        "Test Files 2/Rotations/native rotated landscape 180.pdf",
        "Test Files 2/Rotations/native rotated landscape 270.pdf"
    ]

    for file_path in test_files:
        analyze_pdf_structure(file_path)
        test_export_methods(file_path)
        print("\n" + "="*60)

if __name__ == "__main__":
    main()