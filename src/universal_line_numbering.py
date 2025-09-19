"""
Universal 28-Line Grid Numbering System
Implements consistent line numbering across all document types with 1/4" gutter, 10" length, 28 lines per page
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, Optional
import math
import os
import io
from PIL import Image, ImageDraw, ImageFont
from config import (
    FOOTER_FONT_NAME, FOOTER_FONT_SIZE, FOOTER_FONT_COLOR,
    LEGAL_FONT_NAME, LEGAL_FONT_SIZE_NORMAL, LINE_NUMBER_COLOR_RED
)


class UniversalLineNumberer:
    """
    Universal line numbering system that applies consistent 28-line grid to all PDF types
    - 1/4 inch gutter width (0.25" = 18 points)
    - 10 inch total length (720 points)
    - 28 lines per page, evenly spaced
    - Numbers reset to 1 on each page
    """

    def __init__(self, log_callback=None):
        self.log_callback = log_callback

        # Layout specifications (in points, 1 inch = 72 points)
        self.gutter_margin = 18  # 0.25 inches from left edge to gutter
        self.gutter_width = 18  # 0.25 inches wide gutter for line numbers
        self.legal_gutter_width = 18  # Duplicate for compatibility with reporting
        self.total_length = 720  # 10 inches
        self.lines_per_page = 28
        self.line_height = self.total_length / self.lines_per_page  # ~25.7 points per line

        # Text formatting - use config values for legal documents
        self.font_size = LEGAL_FONT_SIZE_NORMAL  # Use config: 8 points
        self.font_color = LINE_NUMBER_COLOR_RED  # Use config: Red for line numbers
        self.font_name = LEGAL_FONT_NAME  # Use config: Times-Roman
        self.background_color = (0.95, 0.95, 0.95)  # Very light grey background

        # Positioning
        self.number_x_offset = 2  # Points from left edge of gutter
        self.number_y_offset = 3  # Points from line position

        # Track processing to prevent duplication
        self.processed_pages = set()
        self.processed_documents = set()

    def log(self, message: str):
        """Log message with callback"""
        if self.log_callback:
            self.log_callback(message)

    def _is_native_pdf(self, pdf_path: Path) -> bool:
        """
        Check if PDF is native (text-based) vs image-based
        Returns True if PDF has extractable text content
        """
        try:
            doc = fitz.open(str(pdf_path))
            total_text = ""

            # Check first few pages for text content
            pages_to_check = min(3, len(doc))
            for page_num in range(pages_to_check):
                page = doc[page_num]
                text = page.get_text()
                total_text += text

            doc.close()

            # Consider it native if we found substantial text
            return len(total_text.strip()) > 100

        except Exception as e:
            self.log(f"Error checking if PDF is native: {str(e)}")
            return False  # Default to image-based processing if error

    def _map_font_name(self, original_font: str) -> str:
        """
        Map various font names to PyMuPDF compatible font names
        """
        # Convert to lowercase for case-insensitive matching
        font_lower = original_font.lower()

        # Mapping dictionary
        font_mapping = {
            'times': 'times-roman',
            'timesnewroman': 'times-roman',
            'times new roman': 'times-roman',
            'arial': 'helv',
            'helvetica': 'helv',
            'courier': 'cour',
            'courier new': 'cour',
            'dejavu': 'helv',  # Map DejaVu fonts to Helvetica
            'dejavusans': 'helv',
            'dejavusanscondensed': 'helv',
            'symbol': 'symb',
            'zapfdingbats': 'zapfd'
        }

        # Check for exact matches
        if font_lower in font_mapping:
            return font_mapping[font_lower]

        # Check for partial matches
        for key, value in font_mapping.items():
            if key in font_lower:
                return value

        # Default fallback
        return 'times-roman'

    def add_universal_line_numbers(self, input_pdf_path: Path, output_pdf_path: Path) -> bool:
        """
        Add universal 28-line grid numbering to all pages of a PDF

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF

        Returns:
            bool: True if successful
        """
        try:
            # Check for double processing
            doc_id = f"{input_pdf_path}_{input_pdf_path.stat().st_mtime}"
            if hasattr(self, 'processed_documents') and doc_id in self.processed_documents:
                self.log(f"⚠️ Document {input_pdf_path.name} already processed, skipping to prevent duplication")
                return True

            self.log(f"Adding universal 28-line numbering to {input_pdf_path.name}")

            doc = fitz.open(str(input_pdf_path))
            total_pages = len(doc)

            # Initialize processed pages tracking for this document
            if not hasattr(self, 'processed_pages'):
                self.processed_pages = set()
            if not hasattr(self, 'processed_documents'):
                self.processed_documents = set()

            for page_num in range(total_pages):
                page = doc[page_num]

                # Check if this page has already been processed
                page_id = f"{input_pdf_path.name}_page_{page_num}"
                if page_id in self.processed_pages:
                    self.log(f"⚠️ Page {page_num + 1} already processed, skipping to prevent duplication")
                    continue

                # Mark page as processed
                self.processed_pages.add(page_id)

                # Use PNG overlay for all document types to ensure consistent appearance
                # Disable white masks when using PNG overlay to prevent white rectangles
                if self._create_true_gutter(page, input_pdf_path.name, apply_white_masks=False):
                    # Add PNG overlay for line numbering (consistent across all document types)
                    self._add_line_numbers_as_image(page, self._get_line_strip_rect(page))

            doc.save(str(output_pdf_path), garbage=4, deflate=True, clean=True)
            doc.close()

            # Mark document as processed
            self.processed_documents.add(doc_id)

            self.log(f"✅ Universal line numbering completed for {input_pdf_path.name}")
            return True

        except Exception as e:
            self.log(f"❌ Error adding universal line numbers to {input_pdf_path.name}: {str(e)}")
            return False

    def _add_grid_to_page(self, page, page_number: int):
        """Add 28-line grid to a single page"""
        try:
            # Get page dimensions
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Calculate vertical positioning (center the 10" grid on page)
            grid_start_y = (page_height - self.total_length) / 2
            if grid_start_y < 0:
                grid_start_y = 0  # If page is shorter than 10", start at top

            # Create the gutter (background rectangle)
            gutter_rect = fitz.Rect(
                self.gutter_margin,  # Left edge with margin
                grid_start_y,  # Top of grid
                self.gutter_margin + self.gutter_width,  # Right edge (margin + gutter width)
                grid_start_y + self.total_length  # Bottom of grid
            )

            # Draw background
            page.draw_rect(
                gutter_rect,
                color=self.background_color,
                fill=self.background_color,
                width=0
            )

            # Add line numbers
            for line_num in range(1, self.lines_per_page + 1):
                self._add_line_number(page, line_num, grid_start_y)

            # Add vertical separator line
            separator_x = self.gutter_margin + self.gutter_width
            page.draw_line(
                fitz.Point(separator_x, grid_start_y),
                fitz.Point(separator_x, grid_start_y + self.total_length),
                color=(0.8, 0.8, 0.8),  # Light grey separator
                width=0.5
            )

        except Exception as e:
            self.log(f"❌ Error adding grid to page {page_number}: {str(e)}")
            raise

    def _add_line_number(self, page, line_number: int, grid_start_y: float):
        """Add a single line number to the page with dynamic centering based on digit count"""
        try:
            # Calculate Y position for this line
            y_position = grid_start_y + (line_number - 0.5) * self.line_height

            # Format the number
            number_text = str(line_number)
            digit_count = len(number_text)

            # Calculate X position for centering based on digit count
            # Character width approximation for Times New Roman at 8pt
            char_width = 4.8  # Approximate width of each character in points
            text_width = digit_count * char_width

            # Center the text within the gutter width (starting from margin)
            # For single digits (1-9): center = margin + (18 - 4.8) / 2 = 18 + 6.6 = 24.6
            # For double digits (10-28): center = margin + (18 - 9.6) / 2 = 18 + 4.2 = 22.2
            x_position = self.gutter_margin + (self.gutter_width - text_width) / 2

            # Add the number
            page.insert_text(
                fitz.Point(x_position, y_position),
                number_text,
                fontsize=self.font_size,
                color=self.font_color,
                rotate=0,
                fontname="Times-Roman"  # Times New Roman font
            )

        except Exception as e:
            self.log(f"❌ Error adding line number {line_number}: {str(e)}")
            raise

    def _add_hybrid_grid_to_page(self, page, page_number: int):
        """Add 28-line grid numbers using hybrid approach: vector content + image-based line numbers"""
        try:
            # Get page dimensions
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Calculate line positions
            start_y = (page_height - self.total_length) / 2  # Center the 10" length
            if start_y < 0:
                start_y = 0  # If page is shorter than 10", start at top

            # Shift existing content right to make room for gutter
            total_gutter_space = self.gutter_margin + self.gutter_width
            new_page_width = page_width + total_gutter_space

            # Save original page content with detailed text information
            text_dict = page.get_text("dict")
            images = page.get_images()

            # Clear and resize page
            page.clean_contents()
            # Set both MediaBox and CropBox to the new expanded size
            new_rect = fitz.Rect(0, 0, new_page_width, page_height)
            page.set_mediabox(new_rect)
            page.set_cropbox(new_rect)

            # Re-insert text content shifted right with proper formatting
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            if text.strip():  # Only insert non-empty text
                                # Get original text properties
                                orig_bbox = span["bbox"]
                                font_size = span["size"]
                                font_name = span.get("font", "Times-Roman")
                                color = span.get("color", (0, 0, 0))

                                # Calculate new position (shifted right)
                                new_x = orig_bbox[0] + total_gutter_space
                                # Use bottom of bbox for baseline positioning (more accurate)
                                new_y = orig_bbox[3]

                                # Re-insert text with original formatting
                                # Map font names to PyMuPDF compatible names
                                mapped_font = self._map_font_name(font_name)

                                # Convert color to proper RGB format (0-1 range)
                                if isinstance(color, (int, float)):
                                    # Convert integer color to RGB
                                    if color == 0:
                                        text_color = (0, 0, 0)  # Black
                                    else:
                                        # Convert from integer format (like 3355443) to RGB
                                        r = ((color >> 16) & 255) / 255.0
                                        g = ((color >> 8) & 255) / 255.0
                                        b = (color & 255) / 255.0
                                        text_color = (r, g, b)
                                elif isinstance(color, (list, tuple)):
                                    if len(color) >= 3:
                                        # Convert to 0-1 range if needed
                                        if color[0] > 1 or color[1] > 1 or color[2] > 1:
                                            text_color = (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
                                        else:
                                            text_color = (color[0], color[1], color[2])
                                    else:
                                        text_color = (0, 0, 0)
                                else:
                                    text_color = (0, 0, 0)  # Default black

                                page.insert_text(
                                    fitz.Point(new_x, new_y),
                                    text,
                                    fontsize=font_size,
                                    color=text_color,
                                    rotate=0,
                                    fontname=mapped_font
                                )

            # Re-insert images shifted right
            for img in images:
                try:
                    # Get image rectangle
                    img_rect = page.get_image_bbox(img)
                    if img_rect.width > 0 and img_rect.height > 0:
                        # Shift image right
                        new_img_rect = fitz.Rect(
                            img_rect.x0 + total_gutter_space,
                            img_rect.y0,
                            img_rect.x1 + total_gutter_space,
                            img_rect.y1
                        )
                        # Re-insert image
                        page.insert_image(new_img_rect, filename=img)
                except Exception as e:
                    self.log(f"Warning: Could not re-insert image: {str(e)}")

            # Create the gutter background
            gutter_rect = fitz.Rect(
                self.gutter_margin,  # Left edge with margin
                start_y,  # Top of grid
                self.gutter_margin + self.gutter_width,  # Right edge (margin + gutter width)
                start_y + self.total_length  # Bottom of grid
            )

            # Draw background
            page.draw_rect(
                gutter_rect,
                color=self.background_color,
                fill=self.background_color,
                width=0
            )

            # Create line numbers as an image and overlay them
            try:
                self._add_line_numbers_as_image(page, start_y)
            except Exception as e:
                self.log(f"Warning: Could not create line numbers as image, falling back to vector: {str(e)}")
                # Fallback to vector line numbers
                for line_num in range(1, self.lines_per_page + 1):
                    self._add_line_number(page, line_num, start_y)

            # Add vertical separator line
            separator_x = self.gutter_margin + self.gutter_width
            page.draw_line(
                fitz.Point(separator_x, start_y),
                fitz.Point(separator_x, start_y + self.total_length),
                color=(0.8, 0.8, 0.8),  # Light grey separator
                width=0.5
            )

        except Exception as e:
            self.log(f"❌ Error adding hybrid grid to page {page_number}: {str(e)}")
            raise

    def _add_line_numbers_as_image(self, page, start_y: float):
        """Use pre-made PNG overlay for line numbers instead of generating text"""
        try:
            import tempfile
            from PIL import Image

            # Path to the pre-made line numbering PNG overlay
            # Use the A4 gutter overlay that was already created
            png_paths = [
                "src/a4_gutter_overlay_transparent.png",  # Transparent version
                "src/a4_gutter_overlay.png",              # Regular version
                "a4_gutter_overlay_transparent.png",      # Root level transparent
                "a4_gutter_overlay.png"                   # Root level regular
            ]

            line_numbers_img = None
            png_path_used = None

            # Try to load the pre-made PNG overlay
            for png_path in png_paths:
                try:
                    if os.path.exists(png_path):
                        line_numbers_img = Image.open(png_path)
                        png_path_used = png_path
                        self.log(f"🎯 LOADED PRE-MADE PNG OVERLAY: {png_path}")
                        self.log(f"🎯 Image size: {line_numbers_img.size}")
                        self.log(f"🎯 Image mode: {line_numbers_img.mode}")
                        self.log(f"🎯 Image is transparent: {'transparency' in line_numbers_img.info or line_numbers_img.mode == 'RGBA'}")

                        # Check if image has transparency
                        if line_numbers_img.mode == 'RGBA':
                            # Check if there are any transparent pixels
                            extrema = line_numbers_img.getextrema()
                            self.log(f"🎯 Alpha channel extrema: {extrema}")

                            # Sample some pixels to check transparency
                            pixels = list(line_numbers_img.getdata())
                            transparent_pixels = sum(1 for p in pixels if len(p) == 4 and p[3] < 255)
                            total_pixels = len(pixels)
                            self.log(f"🎯 Transparent pixels: {transparent_pixels}/{total_pixels} ({transparent_pixels/total_pixels*100:.1f}%)")

                        break
                except Exception as e:
                    continue

            if line_numbers_img is None:
                # Fallback: create text-based image if PNG not available
                self.log("⚠️ Pre-made PNG not found, using fallback text generation")
                return self._add_line_numbers_as_image_fallback(page, start_y)
            else:
                self.log(f"🎯 Successfully using PNG overlay, not text generation")

            # Convert PIL image to bytes for PyMuPDF
            import io
            img_byte_arr = io.BytesIO()
            line_numbers_img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # Calculate position for line numbers image
            line_numbers_rect = fitz.Rect(
                self.gutter_margin,  # Left edge with margin
                start_y,  # Top of grid
                self.gutter_margin + self.gutter_width,  # Right edge
                start_y + self.total_length  # Bottom of grid
            )

            # Insert the line numbers image directly from bytes
            page.insert_image(line_numbers_rect, stream=img_byte_arr.getvalue())

            self.log(f"🎯 APPLIED PRE-MADE PNG OVERLAY: rect={line_numbers_rect}, file={png_path_used}")

        except Exception as e:
            self.log(f"❌ Error creating line numbers as image: {str(e)}")
            # Fallback to text-based image generation
            return self._add_line_numbers_as_image_fallback(page, start_y)

    def _add_line_numbers_as_image_fallback(self, page, start_y: float):
        """Fallback method: Create line numbers as text-based image (original method)"""
        try:
            import tempfile
            from PIL import Image, ImageDraw, ImageFont

            # Create a temporary image for the line numbers
            img_width = self.gutter_width
            img_height = self.total_length

            # Create transparent background image
            line_numbers_img = Image.new('RGBA', (int(img_width), int(img_height)), (255, 255, 255, 0))
            draw = ImageDraw.Draw(line_numbers_img)

            # Load font using config settings
            font = self._load_font_for_line_numbers()
            if font is None:
                raise Exception("Could not load any font")

            # Draw line numbers
            for line_num in range(1, self.lines_per_page + 1):
                y_position = (line_num - 0.5) * self.line_height

                # Format the number
                number_text = str(line_num)
                digit_count = len(number_text)

                # Calculate X position for centering
                char_width = 4.8  # Approximate width of each character in points
                text_width = digit_count * char_width
                x_position = (self.gutter_width - text_width) / 2

                # Convert to pixels
                x_pixel = int(x_position)
                y_pixel = int(y_position)

                # Draw the number using config color
                color_int = tuple(int(c * 255) for c in self.font_color) + (255,)
                draw.text((x_pixel, y_pixel), number_text, font=font, fill=color_int)

            # Convert to bytes for PyMuPDF
            import io
            img_byte_arr = io.BytesIO()
            line_numbers_img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # Calculate position and insert
            line_numbers_rect = fitz.Rect(
                self.gutter_margin,  # Left edge with margin
                start_y,  # Top of grid
                self.gutter_margin + self.gutter_width,  # Right edge
                start_y + self.total_length  # Bottom of grid
            )

            page.insert_image(line_numbers_rect, stream=img_byte_arr)

            self.log(f"📄 Applied fallback text-based line numbers: {line_numbers_rect}")

        except Exception as e:
            self.log(f"❌ Error in fallback line numbering: {str(e)}")
            raise

    def _create_true_gutter(self, page, filename=None, apply_white_masks: bool = True):
        """
        Create a true gutter by shifting existing content inward within standard 8.5x11 page dimensions.
        This creates space for line numbers on the left while maintaining printable page size.
        Implements robust guard and white masking to prevent duplication.
        """
        try:
            # Robust Guard: Check if gutter already created
            if getattr(page, "_gd_true_gutter_done", False):
                self.log(f"🚫 Skipping gutter creation - already done for this page")
                return True

            original_rect = page.rect
            page_rotation = page.rotation

            # CRITICAL: First, mask the gutter area with white rectangle to prevent ghosting
            gutter_mask_rect = fitz.Rect(
                0,  # Left edge
                0,  # Top edge
                self.gutter_margin + self.gutter_width,  # Right edge (margin + gutter width)
                original_rect.height  # Full height
            )

            # Draw white rectangle to mask any existing content in gutter area
            if apply_white_masks:
                page.draw_rect(gutter_mask_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
                self.log(f"🎨 Applied white mask to gutter area: {gutter_mask_rect}")
            else:
                self.log(f"🎨 SKIPPED white mask to gutter area (PNG overlay mode)")

            # Compute target content area with uniform scaling (Option A)
            page_w = original_rect.width
            page_h = original_rect.height
            left_padding = self.gutter_margin + self.gutter_width

            # Calculate uniform scale to make room for gutter
            target_w = page_w - left_padding
            scale = min(target_w / page_w, 1.0)  # Never scale up

            new_w = page_w * scale
            new_h = page_h * scale

            # Position scaled content
            dst_left = left_padding
            dst_top = (page_h - new_h) / 2  # Center vertically
            dst_rect = fitz.Rect(dst_left, dst_top, dst_left + new_w, dst_top + new_h)

            # Get the page content with proper rotation to ensure upright capture
            if page_rotation == 90:
                # For 90° rotation, apply 270° rotation to get upright content
                rotation_matrix = fitz.Matrix(1, 1).prerotate(270)
                pix = page.get_pixmap(matrix=rotation_matrix)
            elif page_rotation == 270:
                # For 270° rotation, apply 90° rotation to get upright content
                rotation_matrix = fitz.Matrix(1, 1).prerotate(90)
                pix = page.get_pixmap(matrix=rotation_matrix)
            else:
                # No rotation needed, get content as-is
                rotation_matrix = fitz.Matrix(1, 1)
                pix = page.get_pixmap(matrix=rotation_matrix)

            # Clear the page contents completely
            page.clean_contents()

            # Insert the captured content using the calculated destination rect
            page.insert_image(dst_rect, pixmap=pix)

            # CRITICAL: Apply white mask again after content insertion to ensure no bleed-through
            if apply_white_masks:
                page.draw_rect(gutter_mask_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
                self.log(f"🎨 Applied second white mask after content insertion")
            else:
                self.log(f"🎨 SKIPPED second white mask after content insertion (PNG overlay mode)")

            # CRITICAL FIX: Set page rotation to 0 to fix sideways documents
            if page_rotation != 0:
                page.set_rotation(0)
                self.log(f"🔄 Page rotation corrected: {page_rotation}° → 0°")

            # Mark page as having gutter created (CRITICAL GUARD)
            page._gd_true_gutter_done = True

            self.log(f"✅ TRUE gutter created: scale={scale:.3f}, dst_rect={dst_rect}, white masking applied")
            return True

        except Exception as e:
            self.log(f"❌ Error creating true gutter: {str(e)}")
            return False

    def _get_line_strip_rect(self, page) -> fitz.Rect:
        """Calculate the line strip rectangle for the given page"""
        page_rect = page.rect
        page_height = page_rect.height

        # Geometry constants
        left = self.gutter_margin
        right = left + self.gutter_width
        strip_top = (page_height - self.total_length) / 2
        strip_bottom = strip_top + self.total_length

        return fitz.Rect(left, strip_top, right, strip_bottom)

    def _add_line_numbers_as_image(self, page, line_rect: fitz.Rect):
        """Use pre-made PNG overlay for line numbers instead of generating text"""
        try:
            # Path to the pre-made line numbering PNG overlay
            png_paths = [
                "src/a4_gutter_overlay_transparent.png",  # Transparent version
                "src/a4_gutter_overlay.png",              # Regular version
                "a4_gutter_overlay_transparent.png",      # Root level transparent
                "a4_gutter_overlay.png"                   # Root level regular
            ]

            line_numbers_img = None
            png_path_used = None

            # Try to load the pre-made PNG overlay
            for png_path in png_paths:
                try:
                    if os.path.exists(png_path):
                        line_numbers_img = Image.open(png_path)
                        png_path_used = png_path
                        self.log(f"🎯 LOADED PRE-MADE PNG OVERLAY: {png_path}")
                        self.log(f"🎯 Image size: {line_numbers_img.size}")
                        self.log(f"🎯 Image mode: {line_numbers_img.mode}")
                        self.log(f"🎯 Image is transparent: {line_numbers_img.mode == 'RGBA'}")

                        # Check if image has transparency
                        if line_numbers_img.mode == 'RGBA':
                            # Check if there are any transparent pixels
                            extrema = line_numbers_img.getextrema()
                            self.log(f"🎯 Alpha channel extrema: {extrema}")

                            # Sample some pixels to check transparency
                            pixels = list(line_numbers_img.getdata())
                            transparent_pixels = sum(1 for p in pixels if len(p) == 4 and p[3] < 255)
                            total_pixels = len(pixels)
                            self.log(f"🎯 Transparent pixels: {transparent_pixels}/{total_pixels} ({transparent_pixels/total_pixels*100:.1f}%)")

                        break
                except Exception as e:
                    self.log(f"⚠️ Failed to load {png_path}: {e}")
                    continue

            if line_numbers_img is None:
                # Fallback: create text-based image if PNG not available
                self.log("⚠️ Pre-made PNG not found, using fallback text generation")
                return self._add_line_numbers_as_image_fallback_text(page, line_rect)

            # Convert PIL image to bytes for PyMuPDF
            img_byte_arr = io.BytesIO()
            line_numbers_img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # Insert the pre-made PNG image into PDF
            page.insert_image(line_rect, stream=img_bytes, keep_proportion=False)

            self.log(f"🎯 APPLIED PRE-MADE PNG OVERLAY: rect={line_rect}, file={png_path_used}")

        except Exception as e:
            self.log(f"❌ Error creating line numbers as image: {str(e)}")
            # Fallback to text-based image generation
            return self._add_line_numbers_as_image_fallback_text(page, line_rect)

    def _add_line_numbers_as_image_fallback_text(self, page, line_rect: fitz.Rect):
        """Fallback method: Create line numbers as text-based image with correct config settings"""
        try:
            # Create PNG at 72 dpi with pixel size matching line_rect points
            width_px = int(round(line_rect.width))
            height_px = int(round(line_rect.height))

            # Create transparent background image
            img = Image.new("RGBA", (width_px, height_px), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # Load font with config settings
            font = self._load_font_for_line_numbers()

            # Draw centered numbers for each line using config color
            for i in range(self.lines_per_page):
                y_center_px = round((i + 0.5) * (height_px / self.lines_per_page))
                txt = str(i + 1)

                # Measure text dimensions
                bbox = draw.textbbox((0, 0), txt, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Center the text
                x = max(0, (width_px - text_width) // 2)
                y = y_center_px - text_height // 2

                # Draw number using config color (red) - CONVERTED TO INT!
                color_int = tuple(int(c * 255) for c in self.font_color)
                draw.text((x, y), txt, font=font, fill=color_int)

            # Convert to PNG bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # Insert image into PDF
            page.insert_image(line_rect, stream=img_bytes, keep_proportion=False)

            self.log(f"🎨 APPLIED FALLBACK TEXT OVERLAY WITH CONFIG COLOR: rect={line_rect}")

        except Exception as e:
            self.log(f"❌ Error in fallback text generation: {str(e)}")
            raise

    def _load_font_for_line_numbers(self):
        """Load font with robust TTF fallback using config settings"""
        # Use config font name and size
        font_size = self.font_size

        # Try to load the config font first
        font_paths = []

        # Add Times New Roman paths based on config font name
        if "Times" in self.font_name:
            font_paths.extend([
                "C:/Windows/Fonts/times.ttf",
                "C:/Windows/Fonts/timesnewroman.ttf",
                "/Library/Fonts/Times New Roman.ttf",
                "/System/Library/Fonts/Times.ttc",
                "/System/Library/Fonts/Times New Roman.ttf",
                "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
            ])

        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, font_size)
            except:
                continue

        # Fallback to default font
        self.log("⚠️ Using fallback font - consider installing TTF fonts")
        return ImageFont.load_default()

    def add_filename_to_page(self, page, filename: str, page_number: int, total_pages: int):
        """
        Add filename to bottom left of page

        Args:
            page: PDF page object
            filename: Original filename to display
            page_number: Current page number
            total_pages: Total pages in document
        """
        try:
            # Get page dimensions
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Position filename in bottom left, avoiding line numbers
            margin = 30  # Points from left edge (clear of 0.25" gutter)
            bottom_margin = 20  # Points from bottom edge

            # Format filename display
            display_text = f"{filename} (Page {page_number} of {total_pages})"

            # Add filename text
            page.insert_text(
                fitz.Point(margin, page_height - bottom_margin),
                display_text,
                fontsize=7,
                color=(0.3, 0.3, 0.3),  # Dark grey
                rotate=0,
                fontname="helv"
            )

        except Exception as e:
            self.log(f"❌ Error adding filename to page: {str(e)}")
            # Don't raise - filename display is not critical

    def add_bates_and_filename_to_pdf(self, input_pdf_path: Path, output_pdf_path: Path,
                                     bates_prefix: str, bates_number: int, filename: str) -> bool:
        """
        Add both Bates number (bottom right) and filename (bottom left) to PDF
        with horizontal alignment and light grey background
        Bates number increments for each page within the document

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF
            bates_prefix: Bates number prefix
            bates_number: Starting Bates number
            filename: Original filename

        Returns:
            bool: True if successful
        """
        try:
            self.log(f"Adding Bates number and filename to {input_pdf_path.name}")

            doc = fitz.open(str(input_pdf_path))
            total_pages = len(doc)

            for page_num in range(total_pages):
                page = doc[page_num]  # PyMuPDF uses 0-based indexing
                current_bates = bates_number + page_num  # Increment Bates number for each page

                # Add both filename and Bates number with horizontal alignment and background
                self._add_footer_with_background(page, filename, bates_prefix, current_bates,
                                               page_num + 1, total_pages)

            doc.save(str(output_pdf_path), garbage=4, deflate=True, clean=True)
            doc.close()

            self.log(f"✅ Bates numbering and filename display completed for {input_pdf_path.name}")
            return True

        except Exception as e:
            self.log(f"❌ Error adding Bates number and filename to {input_pdf_path.name}: {str(e)}")
            return False

    def _add_footer_with_background(self, page, filename: str, bates_prefix: str, bates_number: int,
                                   page_number: int, total_pages: int):
        """Add both filename and Bates number with horizontal alignment and light grey background"""
        try:
            # Get page dimensions
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Define 1/4 inch margins (18 points) - outside edge of rectangles
            margin_1_4_inch = 18  # 0.25 * 72 points

            # Define vertical positioning - bottom edge of boxes 1/4 inch above document bottom
            bottom_box_margin = 18  # 0.25 inch from bottom edge

            # Background color
            bg_color = (0.9, 0.9, 0.9)  # Light grey background

            # Calculate text dimensions - simple and reliable approach
            filename_text = f"{filename} (Page {page_number} of {total_pages})"
            font_size = FOOTER_FONT_SIZE

            # Use a conservative but accurate character width for Times-Roman 8pt
            # This avoids temporary page creation issues while being reasonably accurate
            char_width = 4.3  # Slightly reduced from previous attempts
            filename_width = len(filename_text) * char_width

            bates_text = f"{bates_prefix}{bates_number:04d}"
            # Keep Bates number calculation locked (it's perfect)
            bates_width = len(bates_text) * 4.2  # Width for Times-Roman 8pt (locked - don't change)

            # Separate padding for filename and Bates number
            filename_horizontal_padding = 6  # Horizontal padding for filename
            filename_vertical_padding = 2  # Vertical padding for filename

            # BATES NUMBER - LOCKED (DO NOT CHANGE)
            # Current Bates number positioning is perfect - DO NOT MODIFY THESE VALUES
            bates_horizontal_padding = 4  # Locked: Perfect horizontal padding for Bates
            bates_vertical_padding = 2   # Locked: Perfect vertical padding for Bates

            # Calculate text height (approximate for centering)
            text_height = font_size * 1.2  # Approximate text height with line spacing

            # Calculate rectangle dimensions - separate for each element
            filename_rect_width = filename_width + (2 * filename_horizontal_padding)
            filename_rect_height = text_height + (2 * filename_vertical_padding)

            bates_rect_width = bates_width + (2 * bates_horizontal_padding)
            bates_rect_height = text_height + (2 * bates_vertical_padding)

            # Position filename rectangle: left edge at 1/4 inch margin, extending right
            # Bottom edge 1/4 inch above document bottom
            filename_rect_x = margin_1_4_inch
            filename_rect_y = page_height - bottom_box_margin - filename_rect_height

            # Position Bates rectangle: right edge at 1/4 inch margin from right, extending left
            # Bottom edge 1/4 inch above document bottom
            bates_rect_x = page_width - margin_1_4_inch - bates_rect_width
            bates_rect_y = page_height - bottom_box_margin - bates_rect_height

            # Create rectangle objects
            filename_bg_rect = fitz.Rect(
                filename_rect_x,
                filename_rect_y,
                filename_rect_x + filename_rect_width,
                filename_rect_y + filename_rect_height
            )

            bates_bg_rect = fitz.Rect(
                bates_rect_x,
                bates_rect_y,
                bates_rect_x + bates_rect_width,
                bates_rect_y + bates_rect_height
            )

            # DISABLED: Background rectangles (commented out but preserved for future use)
            # page.draw_rect(filename_bg_rect, color=bg_color, fill=bg_color, width=0)
            # page.draw_rect(bates_bg_rect, color=bg_color, fill=bg_color, width=0)

            # Calculate text positions (perfectly centered within rectangles)
            filename_text_x = filename_rect_x + (filename_rect_width - filename_width) / 2  # Center horizontally
            filename_text_y = filename_rect_y + (filename_rect_height / 2) + (font_size / 3)  # Center vertically with baseline adjustment

            # BATES NUMBER TEXT POSITIONING - LOCKED (DO NOT CHANGE)
            # Current Bates number text positioning is perfect - DO NOT MODIFY THESE CALCULATIONS
            bates_text_x = bates_rect_x + (bates_rect_width - bates_width) / 2  # Locked: Perfect horizontal centering
            bates_text_y = bates_rect_y + (bates_rect_height / 2) + (font_size / 3)  # Locked: Perfect vertical centering

            # Add filename text (perfectly centered) - BOLD
            page.insert_text(
                fitz.Point(filename_text_x, filename_text_y),
                filename_text,
                fontsize=font_size,
                color=FOOTER_FONT_COLOR,
                rotate=0,
                fontname="Times-Bold"  # Changed to bold font
            )

            # Add Bates number text (perfectly centered) - BOLD
            page.insert_text(
                fitz.Point(bates_text_x, bates_text_y),
                bates_text,
                fontsize=font_size,
                color=FOOTER_FONT_COLOR,
                rotate=0,
                fontname="Times-Bold"  # Changed to bold font
            )

        except Exception as e:
            self.log(f"❌ Error adding footer with background: {str(e)}")
            raise

    def _add_bates_number_to_page(self, page, bates_prefix: str, bates_number: int,
                                 page_number: int, total_pages: int):
        """Add Bates number to bottom right of page (legacy method - kept for compatibility)"""
        try:
            # Get page dimensions
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Position Bates number in bottom right
            right_margin = 60  # Points from right edge (positioned away from edge but not too far)
            bottom_margin = 30  # Points from bottom edge (positioned away from edge but not too far)

            # Format Bates number
            bates_text = f"{bates_prefix}{bates_number:04d}"

            # Add Bates number text without background box
            page.insert_text(
                fitz.Point(page_width - right_margin, page_height - bottom_margin),
                bates_text,
                fontsize=8,
                color=(0, 0, 0),  # Black text
                rotate=0,
                fontname="Times-Roman"  # Times New Roman font
            )

        except Exception as e:
            self.log(f"❌ Error adding Bates number to page: {str(e)}")
            # Don't raise - Bates numbering is critical but we'll let the main method handle the error

    def _add_vector_grid_to_page(self, page, page_number: int):
        """Add line numbers using vector-based processing for native PDFs to prevent duplication"""
        try:
            original_rect = page.rect
            page_width = original_rect.width
            page_height = original_rect.height

            # Calculate line positions
            line_spacing = self.total_length / (self.lines_per_page - 1)
            start_y = (page_height - self.total_length) / 2

            # CRITICAL: Create white gutter background using vector operations
            gutter_rect = fitz.Rect(
                0,  # Left edge
                0,  # Top edge
                self.gutter_margin + self.gutter_width,  # Right edge
                page_height  # Full height
            )

            # Draw white rectangle to mask existing content - prevents ghosting
            page.draw_rect(gutter_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            self.log(f"🎨 Applied vector white mask to gutter area")

            # Add line numbers directly as vector text
            for i in range(1, self.lines_per_page + 1):
                y_pos = start_y + (i - 1) * line_spacing

                # Center align text in gutter
                text_x = self.gutter_margin + (self.gutter_width / 2)

                # Use red color for line numbers
                page.insert_text(
                    fitz.Point(text_x, y_pos),
                    str(i),
                    fontname="helv",  # Use helvetica for better vector rendering
                    fontsize=self.font_size,
                    color=self.line_number_color,
                    rotate=0,
                    align=fitz.TEXT_ALIGN_CENTER
                )

            # Add vertical separator line
            separator_x = self.gutter_margin + self.gutter_width
            page.draw_line(
                fitz.Point(separator_x, start_y),
                fitz.Point(separator_x, start_y + self.total_length),
                color=(0.8, 0.8, 0.8),  # Light grey separator
                width=0.5
            )

            self.log(f"✅ Added vector grid to page {page_number}")

        except Exception as e:
            self.log(f"❌ Error adding vector grid to page {page_number}: {str(e)}")
            raise

    def get_specifications(self) -> Dict[str, Any]:
        """Get the current numbering specifications"""
        return {
            'gutter_width_inches': 0.25,
            'gutter_width_points': self.gutter_width,
            'total_length_inches': 10,
            'total_length_points': self.total_length,
            'lines_per_page': self.lines_per_page,
            'line_height_points': round(self.line_height, 2),
            'font_size': self.font_size,
            'font_color': self.font_color,
            'background_color': self.background_color
        }