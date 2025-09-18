#!/usr/bin/env python3
"""
Create a transparent A4 gutter overlay with line numbering image
No background, no edge lines - just the line numbers on transparent background
"""

from PIL import Image, ImageDraw, ImageFont
import sys
import os
import requests
from io import BytesIO

# Add src to path to import config
sys.path.insert(0, 'src')
from config import *

# A4 dimensions (in inches)
A4_HEIGHT_INCHES = 11.69
A4_WIDTH_INCHES = 8.27

# Gutter configuration - A4 relative
GUTTER_WIDTH_INCHES = 0.25  # 1/4 inch wide gutter
GUTTER_LENGTH_INCHES = 10.0  # Full 10 inch length as requested
LINES_PER_PAGE = 28

# Use PDF DPI (72 points per inch) for exact PDF overlay dimensions
DPI = 600
GUTTER_WIDTH_PIXELS = int(GUTTER_WIDTH_INCHES * DPI)
GUTTER_LENGTH_PIXELS = int(GUTTER_LENGTH_INCHES * DPI)

# Line numbering image URLs (from the screenshots)
LINE_NUMBERING_IMAGE_URLS = [
    "https://maas-log-prod.cn-wlcb.ufileos.com/anthropic/f1eafc39-e79c-4f3b-9db0-5a42f943c4d6/240eff39a321e565b71b0ad425402dcb.png?UCloudPublicKey=TOKEN_e15ba47a-d098-4fbd-9afc-a0dcf0e4e621&Expires=1758227855&Signature=CaCgMomUsaxaK+HqYeNfmsCY5+A=",
    "https://maas-log-prod.cn-wlcb.ufileos.com/anthropic/f1eafc39-e79c-4f3b-9db0-5a42f943c4d6/7932e1a07274ec672d3792493cf087b4.png?UCloudPublicKey=TOKEN_e15ba47a-d098-4fbd-9afc-a0dcf0e4e621&Expires=1758227855&Signature=NHfwkmjrc2ld1Fg1AMO96jfRYe0="
]

def download_line_numbering_image():
    """Download the line numbering image from the provided URLs"""
    for url in LINE_NUMBERING_IMAGE_URLS:
        try:
            print(f"Attempting to download line numbering image from: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Load image from response
            img = Image.open(BytesIO(response.content))
            print(f"Successfully downloaded line numbering image: {img.size}")
            return img

        except Exception as e:
            print(f"Failed to download from {url}: {str(e)}")
            continue

    # If all URLs fail, create a fallback image
    print("Creating fallback line numbering image...")
    return create_fallback_line_numbering_image()

def create_fallback_line_numbering_image():
    """Create a fallback line numbering image if download fails"""
    # Create transparent background image
    img = Image.new('RGBA', (50, GUTTER_LENGTH_PIXELS), (255, 255, 255, 0))  # Transparent
    draw = ImageDraw.Draw(img)

    # Draw simple line numbers as fallback
    line_spacing = GUTTER_LENGTH_PIXELS / LINES_PER_PAGE
    font_size = 12

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    for i in range(LINES_PER_PAGE):
        line_number = str(i + 1)
        y_position = int(i * line_spacing + line_spacing / 2)

        try:
            bbox = draw.textbbox((0, 0), line_number, font=font)
            text_height = bbox[3] - bbox[1]
        except:
            text_height = font_size

        y_position_adjusted = y_position - text_height // 2

        # Draw with some opacity (semi-transparent grey)
        draw.text((5, y_position_adjusted), line_number,
                 fill=(128, 128, 128, 200), font=font)  # Semi-transparent grey

    return img

def create_transparent_a4_gutter_image():
    """Create a transparent A4 gutter overlay with line numbering image"""

    # Download the line numbering image
    line_numbering_img = download_line_numbering_image()

    # Create transparent background image (RGBA mode for transparency)
    img = Image.new('RGBA', (GUTTER_WIDTH_PIXELS, GUTTER_LENGTH_PIXELS), (255, 255, 255, 0))

    # Calculate positioning for the line numbering image
    # We want it positioned 1/4 inch from the left edge of the document
    # and evenly spaced vertically

    # Resize line numbering image to fit the gutter width while maintaining aspect ratio
    original_width, original_height = line_numbering_img.size

    # Calculate new width to fit in gutter (with some padding)
    target_width = GUTTER_WIDTH_PIXELS - 10  # 5px padding on each side
    aspect_ratio = original_height / original_width
    target_height = int(target_width * aspect_ratio)

    # Resize the line numbering image
    resized_line_img = line_numbering_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # Calculate vertical positioning to center the line numbers
    vertical_start = (GUTTER_LENGTH_PIXELS - target_height) // 2

    # If the line numbers are taller than the gutter, scale them down
    if target_height > GUTTER_LENGTH_PIXELS:
        scale_factor = GUTTER_LENGTH_PIXELS / target_height
        target_width = int(target_width * scale_factor)
        target_height = GUTTER_LENGTH_PIXELS
        vertical_start = 0
        resized_line_img = line_numbering_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # Calculate horizontal position (centered in gutter)
    horizontal_start = (GUTTER_WIDTH_PIXELS - target_width) // 2

    # If the line numbering image has transparency (RGBA), paste it directly
    if resized_line_img.mode == 'RGBA':
        # Paste with transparency handling
        img.paste(resized_line_img, (horizontal_start, vertical_start), resized_line_img)
    else:
        # Convert to RGBA and add transparency
        resized_line_img = resized_line_img.convert('RGBA')
        # Make white background transparent
        datas = resized_line_img.getdata()
        new_data = []
        for item in datas:
            # Change white (or near white) to transparent
            if item[0] > 250 and item[1] > 250 and item[2] > 250:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        resized_line_img.putdata(new_data)
        img.paste(resized_line_img, (horizontal_start, vertical_start), resized_line_img)

    return img

def main():
    """Main function to create and save the transparent A4 gutter image"""
    print("Creating transparent A4 gutter image...")
    print(f"A4 dimensions: {A4_WIDTH_INCHES} x {A4_HEIGHT_INCHES} inches")
    print(f"Gutter: {GUTTER_WIDTH_INCHES} x {GUTTER_LENGTH_INCHES} inches")
    print(f"Lines: {LINES_PER_PAGE}")
    print(f"Quality: Lossless PNG with transparency at {DPI} DPI")
    print("Features: No background, no edge lines, transparent overlay")

    # Create the image
    gutter_image = create_transparent_a4_gutter_image()

    # Save the image as lossless PNG with transparency
    output_path = "a4_gutter_overlay_transparent.png"
    gutter_image.save(output_path, "PNG", quality=100)

    print(f"Transparent A4 gutter image saved as: {output_path}")
    print(f"Pixel dimensions: {GUTTER_WIDTH_PIXELS} x {GUTTER_LENGTH_PIXELS} pixels")
    print(f"Image mode: {gutter_image.mode} (should be RGBA for transparency)")

    # Also save a copy in the src directory
    src_path = os.path.join("src", "a4_gutter_overlay_transparent.png")
    gutter_image.save(src_path, "PNG", quality=100)
    print(f"Also saved in src directory: {src_path}")

if __name__ == "__main__":
    main()