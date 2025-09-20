#!/usr/bin/env python3
"""
Comprehensive PDF analysis script to examine every possible attribute
and identify patterns that differentiate problematic files
"""

import sys
import os
import json
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import fitz  # PyMuPDF

def analyze_pdf_comprehensive(pdf_path):
    """Analyze every possible attribute of a PDF file"""

    result = {
        'filename': Path(pdf_path).name,
        'file_size_bytes': os.path.getsize(pdf_path),
        'pages': []
    }

    try:
        doc = fitz.open(pdf_path)

        # Document-level metadata
        result['metadata'] = doc.metadata
        result['page_count'] = len(doc)
        result['is_encrypted'] = doc.is_encrypted
        result['is_pdf'] = doc.is_pdf
        result['needs_pass'] = doc.needs_pass

        # Page-level analysis
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_data = {
                'page_number': page_num + 1,
                'rect': {
                    'width': page.rect.width,
                    'height': page.rect.height,
                    'x0': page.rect.x0,
                    'y0': page.rect.y0,
                    'x1': page.rect.x1,
                    'y1': page.rect.y1
                },
                'rotation': page.rotation,
                'is_landscape': page.rect.width > page.rect.height,
                'aspect_ratio': round(page.rect.width / page.rect.height, 3)
            }

            # Text analysis
            try:
                text = page.get_text()
                page_data['text'] = {
                    'length': len(text),
                    'has_content': len(text.strip()) > 0,
                    'char_count': len(text.strip()),
                    'line_count': len(text.split('\n')),
                    'sample': text[:100] + '...' if len(text) > 100 else text
                }
            except Exception as e:
                page_data['text'] = {'error': str(e)}

            # Text blocks analysis (dict format)
            try:
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])
                page_data['text_blocks'] = {
                    'count': len(blocks),
                    'blocks': []
                }

                for i, block in enumerate(blocks[:5]):  # Limit to first 5 blocks
                    block_info = {
                        'block_num': i,
                        'type': block.get('type', 'unknown'),
                        'bbox': block.get('bbox', []),
                        'lines': len(block.get('lines', []))
                    }

                    if 'lines' in block:
                        # Analyze text direction in lines
                        horizontal_lines = 0
                        vertical_lines = 0

                        for line in block['lines']:
                            bbox = line.get('bbox', [0, 0, 0, 0])
                            width = bbox[2] - bbox[0] if len(bbox) >= 4 else 0
                            height = bbox[3] - bbox[1] if len(bbox) >= 4 else 0

                            if width > height:
                                horizontal_lines += 1
                            else:
                                vertical_lines += 1

                        block_info['text_direction'] = {
                            'horizontal_lines': horizontal_lines,
                            'vertical_lines': vertical_lines,
                            'total_lines': horizontal_lines + vertical_lines
                        }

                    page_data['text_blocks']['blocks'].append(block_info)

            except Exception as e:
                page_data['text_blocks'] = {'error': str(e)}

            # Images analysis
            try:
                images = page.get_images()
                page_data['images'] = {
                    'count': len(images),
                    'details': []
                }

                for i, img in enumerate(images[:3]):  # Limit to first 3 images
                    page_data['images']['details'].append({
                        'image_num': i,
                        'xref': img[0],
                        'width': img[2] if len(img) > 2 else 'unknown',
                        'height': img[3] if len(img) > 3 else 'unknown'
                    })

            except Exception as e:
                page_data['images'] = {'error': str(e)}

            # Fonts analysis
            try:
                fonts = page.get_fonts()
                page_data['fonts'] = {
                    'count': len(fonts),
                    'font_names': [font[1] for font in fonts[:5]]  # First 5 font names
                }
            except Exception as e:
                page_data['fonts'] = {'error': str(e)}

            # Widgets (form fields)
            try:
                widgets = list(page.widgets())
                page_data['widgets'] = {
                    'count': len(widgets),
                    'types': [widget.type for widget in widgets[:3]]
                }
            except Exception as e:
                page_data['widgets'] = {'error': str(e)}

            # Links
            try:
                links = page.get_links()
                page_data['links'] = {
                    'count': len(links),
                    'types': [link.get('kind', 'unknown') for link in links[:3]]
                }
            except Exception as e:
                page_data['links'] = {'error': str(e)}

            # Content streams
            try:
                page_data['has_content_stream'] = page.get_contents() is not None
            except Exception as e:
                page_data['has_content_stream'] = {'error': str(e)}

            # Transparency and blending
            try:
                page_data['transparency'] = page.transparency
                page_data['blend_mode'] = page.blend_mode
            except Exception as e:
                page_data['transparency'] = {'error': str(e)}

            # Colorspace information
            try:
                page_data['colorspace'] = page.colorspace
            except Exception as e:
                page_data['colorspace'] = {'error': str(e)}

            result['pages'].append(page_data)

        doc.close()

    except Exception as e:
        result['error'] = str(e)

    return result

def main():
    """Analyze all PDFs in the Rotations folder"""
    print("🔍 Comprehensive PDF Analysis")
    print("=" * 60)

    rotations_folder = "Test Files 2/Rotations"

    if not os.path.exists(rotations_folder):
        print(f"❌ Folder not found: {rotations_folder}")
        return

    # Get all PDF files
    pdf_files = []
    for file in os.listdir(rotations_folder):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(rotations_folder, file))

    pdf_files.sort()

    print(f"📄 Found {len(pdf_files)} PDF files to analyze")
    print()

    all_results = []

    for pdf_path in pdf_files:
        print(f"🔍 Analyzing: {Path(pdf_path).name}")
        result = analyze_pdf_comprehensive(pdf_path)
        all_results.append(result)
        print(f"   - Pages: {result.get('page_count', 'unknown')}")
        print(f"   - Size: {result.get('file_size_bytes', 0)} bytes")

        if 'pages' in result and result['pages']:
            first_page = result['pages'][0]
            print(f"   - Page 1: {first_page['rect']['width']}x{first_page['rect']['height']}, rotation: {first_page['rotation']}°")
            print(f"   - Text: {first_page.get('text', {}).get('char_count', 0)} chars")
            print(f"   - Images: {first_page.get('images', {}).get('count', 0)}")
            print(f"   - Text blocks: {first_page.get('text_blocks', {}).get('count', 0)}")

        print()

    # Save detailed results to JSON file
    output_file = "pdf_analysis_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"📊 Detailed results saved to: {output_file}")
    print()

    # Look for patterns
    print("🔍 Pattern Analysis")
    print("=" * 40)

    # Group files by type
    native_rotated = [r for r in all_results if 'native rotated' in r['filename']]
    landscape_rotated = [r for r in all_results if 'landscape rotated' in r['filename'] and 'content' not in r['filename']]
    landscape_content_rotated = [r for r in all_results if 'landscape_content_rotated' in r['filename']]
    scanned = [r for r in all_results if 'Scanned' in r['filename']]

    print(f"📋 File Groups:")
    print(f"   - Native rotated: {len(native_rotated)} files")
    print(f"   - Landscape rotated: {len(landscape_rotated)} files")
    print(f"   - Landscape content rotated: {len(landscape_content_rotated)} files")
    print(f"   - Scanned: {len(scanned)} files")
    print()

    # Compare characteristics
    if native_rotated:
        print("🔍 Native Rotated Files Characteristics:")
        nr = native_rotated[0]
        if 'pages' in nr and nr['pages']:
            p = nr['pages'][0]
            print(f"   - Size: {p['rect']['width']}x{p['rect']['height']}")
            print(f"   - Rotation: {p['rotation']}°")
            print(f"   - Text chars: {p.get('text', {}).get('char_count', 0)}")
            print(f"   - Images: {p.get('images', {}).get('count', 0)}")
            print(f"   - File size: {nr.get('file_size_bytes', 0)} bytes")
        print()

    if landscape_rotated:
        print("🔍 Landscape Rotated Files Characteristics:")
        lr = landscape_rotated[0]
        if 'pages' in lr and lr['pages']:
            p = lr['pages'][0]
            print(f"   - Size: {p['rect']['width']}x{p['rect']['height']}")
            print(f"   - Rotation: {p['rotation']}°")
            print(f"   - Text chars: {p.get('text', {}).get('char_count', 0)}")
            print(f"   - Images: {p.get('images', {}).get('count', 0)}")
            print(f"   - File size: {lr.get('file_size_bytes', 0)} bytes")
        print()

    if scanned:
        print("🔍 Scanned Files Characteristics:")
        s = scanned[0]
        if 'pages' in s and s['pages']:
            p = s['pages'][0]
            print(f"   - Size: {p['rect']['width']}x{p['rect']['height']}")
            print(f"   - Rotation: {p['rotation']}°")
            print(f"   - Text chars: {p.get('text', {}).get('char_count', 0)}")
            print(f"   - Images: {p.get('images', {}).get('count', 0)}")
            print(f"   - File size: {s.get('file_size_bytes', 0)} bytes")
        print()

if __name__ == "__main__":
    main()