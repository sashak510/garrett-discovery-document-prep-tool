#!/usr/bin/env python3
"""
Test script to detect vector PDFs and test PDF export/print functionality
"""

import sys
import os
import tempfile
import shutil
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF

def is_vector_pdf(doc):
    """
    Check if a PDF is primarily vector-based
    """
    total_pages = len(doc)
    vector_pages = 0

    for page_num in range(total_pages):
        page = doc[page_num]

        # Get page content as text (returns empty for pure vector docs)
        text = page.get_text()
        text_length = len(text.strip())

        # Get images
        images = page.get_images()
        image_count = len(images)

        # Try to get vector content by checking drawing operations
        try:
            # Get page content stream
            content = page.get_text("blocks")
            # For vector docs, this often returns the drawing operations
            has_drawing_ops = len(content) > 0
        except:
            has_drawing_ops = False

        # Vector indicators:
        # - No extractable text OR very minimal text
        # - No images OR few images
        # - Has drawing operations
        is_vector = (text_length < 10 and image_count == 0) or (text_length < 10 and has_drawing_ops)

        if is_vector:
            vector_pages += 1

    # Consider it a vector PDF if most pages are vector-based
    return vector_pages > total_pages * 0.8

def get_detailed_vector_info(doc):
    """Get detailed information about vector content"""
    info = {
        'pages': len(doc),
        'vector_indicators': []
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_info = {
            'page_num': page_num + 1,
            'text_length': len(page.get_text().strip()),
            'image_count': len(page.get_images()),
            'rotation': page.rotation,
            'size': f"{page.rect.width:.0f}x{page.rect.height:.0f}",
            'has_content_stream': page.get_contents() is not None
        }

        # Check for vector-specific content
        try:
            # Try different text extraction methods
            text_blocks = page.get_text("blocks")
            text_dict = page.get_text("dict")
            text_raw = page.get_text("rawdict")

            page_info['text_blocks_count'] = len(text_blocks)
            page_info['text_dict_blocks'] = len(text_dict.get('blocks', []))
            page_info['text_raw_blocks'] = len(text_raw.get('blocks', []))

            # Vector docs often have empty text blocks but non-zero block counts
            if page_info['text_length'] < 10 and page_info['text_blocks_count'] > 0:
                page_info['likely_vector'] = True
            else:
                page_info['likely_vector'] = False

        except Exception as e:
            page_info['extraction_error'] = str(e)
            page_info['likely_vector'] = True  # Assume vector if extraction fails

        info['vector_indicators'].append(page_info)

    return info

def test_pdf_export(pdf_path, output_path):
    """
    Test exporting PDF by printing/saving to maintain vector quality
    """
    try:
        doc = fitz.open(pdf_path)

        # Create a new document for export
        output_doc = fitz.open()

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Create a new page with same dimensions
            new_page = output_doc.new_page(
                width=page.rect.width,
                height=page.rect.height
            )

            # Copy the page content
            # Method 1: Direct page copy
            try:
                new_page.show_pdf_page(page.rect, doc, page_num)
            except Exception as e:
                print(f"   Direct copy failed: {e}")

                # Method 2: Copy as image (fallback)
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for quality
                    new_page.insert_image(page.rect, pixmap=pix)
                except Exception as e2:
                    print(f"   Image copy also failed: {e2}")
                    return False

        # Save the exported document
        output_doc.save(output_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        doc.close()

        return True

    except Exception as e:
        print(f"   Export failed: {e}")
        return False

def test_vector_files():
    """Test vector detection and export on problematic files"""
    print("🔍 Vector PDF Detection and Export Test")
    print("=" * 60)

    # Test the problematic native rotated files
    test_files = [
        "Test Files 2/Rotations/native rotated landscape 90.pdf",
        "Test Files 2/Rotations/native rotated landscape 180.pdf",
        "Test Files 2/Rotations/native rotated landscape 270.pdf"
    ]

    for file_path in test_files:
        print(f"\n📄 Testing: {os.path.basename(file_path)}")

        if not os.path.exists(file_path):
            print(f"   ❌ File not found")
            continue

        try:
            # Analyze the file
            doc = fitz.open(file_path)

            # Check if vector
            is_vector = is_vector_pdf(doc)
            print(f"   📊 Is vector PDF: {is_vector}")

            # Get detailed info
            info = get_detailed_vector_info(doc)
            print(f"   📄 Pages: {info['pages']}")

            for page_info in info['vector_indicators']:
                print(f"   📋 Page {page_info['page_num']}:")
                print(f"      - Size: {page_info['size']}, Rotation: {page_info['rotation']}°")
                print(f"      - Text: {page_info['text_length']} chars")
                print(f"      - Images: {page_info['image_count']}")
                print(f"      - Likely vector: {page_info['likely_vector']}")
                print(f"      - Text blocks: {page_info.get('text_blocks_count', 'unknown')}")

            doc.close()

            # Test export
            print(f"   🖨️  Testing PDF export...")
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                temp_path = tmp.name

            export_success = test_pdf_export(file_path, temp_path)

            if export_success:
                # Compare file sizes
                original_size = os.path.getsize(file_path)
                exported_size = os.path.getsize(temp_path)

                print(f"   ✅ Export successful!")
                print(f"   📏 Original: {original_size:,} bytes")
                print(f"   📏 Exported: {exported_size:,} bytes")
                print(f"   📏 Ratio: {exported_size/original_size:.2f}x")

                # Check if exported file maintains rotation
                try:
                    exported_doc = fitz.open(temp_path)
                    exported_page = exported_doc[0]
                    print(f"   🔄 Exported rotation: {exported_page.rotation}°")
                    exported_doc.close()
                except Exception as e:
                    print(f"   ❌ Couldn't check exported rotation: {e}")

            else:
                print(f"   ❌ Export failed")

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

        except Exception as e:
            print(f"   ❌ Error testing file: {e}")

if __name__ == "__main__":
    test_vector_files()