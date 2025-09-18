"""
Image-based Line Numbering System
Uses PNG overlay instead of text generation for consistent appearance
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, Optional
import io
from PIL import Image
import os


class ImageLineNumberer:
    """
    Image-based line numbering system that applies line numbers as PNG overlay
    - Uses the pre-generated line numbering PNG image
    - 1/4 inch gutter width (0.25" = 18 points)
    - 10 inch total length (720 points)
    - Consistent appearance across all document types
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

        # Image path
        self.line_numbering_image_path = "a4_gutter_overlay.png"
        self.line_numbering_image = None

        # Track processing to prevent duplication
        self.processed_pages = set()
        self.processed_documents = set()

    def log(self, message: str):
        """Log message with callback"""
        if self.log_callback:
            self.log_callback(message)

    def _load_line_numbering_image(self):
        """Load the line numbering image if not already loaded"""
        if self.line_numbering_image is None:
            try:
                # Try to load from current directory
                if os.path.exists(self.line_numbering_image_path):
                    self.line_numbering_image = Image.open(self.line_numbering_image_path)
                    self.log(f"✅ Loaded line numbering image: {self.line_numbering_image.size}")
                else:
                    # Try to load from src directory
                    src_path = os.path.join("src", self.line_numbering_image_path)
                    if os.path.exists(src_path):
                        self.line_numbering_image = Image.open(src_path)
                        self.log(f"✅ Loaded line numbering image from src: {self.line_numbering_image.size}")
                    else:
                        raise FileNotFoundError(f"Line numbering image not found: {self.line_numbering_image_path}")
            except Exception as e:
                self.log(f"❌ Error loading line numbering image: {str(e)}")
                raise

    def add_image_line_numbers(self, input_pdf_path: Path, output_pdf_path: Path) -> bool:
        """
        Add image-based line numbering to all pages of a PDF

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF

        Returns:
            bool: True if successful
        """
        try:
            self.log(f"Adding image-based line numbering to {input_pdf_path.name}")

            # Load the line numbering image
            self._load_line_numbering_image()

            doc = fitz.open(str(input_pdf_path))
            total_pages = len(doc)

            for page_num in range(total_pages):
                page = doc[page_num]
                self._add_image_overlay_to_page(page, page_num + 1)

            doc.save(str(output_pdf_path), garbage=4, deflate=True, clean=True)
            doc.close()

            self.log(f"✅ Image-based line numbering completed for {input_pdf_path.name}")
            return True

        except Exception as e:
            self.log(f"❌ Error adding image-based line numbers to {input_pdf_path.name}: {str(e)}")
            return False

    def _add_image_overlay_to_page(self, page, page_number: int):
        """Add line numbering image overlay to a single page"""
        try:
            # Get page dimensions
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Calculate vertical positioning (center the 10" grid on page)
            grid_start_y = (page_height - self.total_length) / 2
            if grid_start_y < 0:
                grid_start_y = 0  # If page is shorter than 10", start at top

            # Create the overlay rectangle
            overlay_rect = fitz.Rect(
                self.gutter_margin,  # Left edge with margin
                grid_start_y,  # Top of grid
                self.gutter_margin + self.gutter_width,  # Right edge (margin + gutter width)
                grid_start_y + self.total_length  # Bottom of grid
            )

            # Convert PIL image to bytes for PyMuPDF
            img_byte_arr = io.BytesIO()
            self.line_numbering_image.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # Insert the line numbering image overlay
            page.insert_image(
                overlay_rect,
                stream=img_bytes,
                width=self.gutter_width,
                height=self.total_length
            )

            # Add vertical separator line
            separator_x = self.gutter_margin + self.gutter_width
            page.draw_line(
                fitz.Point(separator_x, grid_start_y),
                fitz.Point(separator_x, grid_start_y + self.total_length),
                color=(0.8, 0.8, 0.8),  # Light grey separator
                width=0.5
            )

            self.log(f"📄 Applied image overlay to page {page_number}")

        except Exception as e:
            self.log(f"❌ Error adding image overlay to page {page_number}: {str(e)}")
            raise

    def add_filename_to_page(self, page, filename: str, page_number: int, total_pages: int):
        """
        Add filename to bottom left of page (compatibility method)

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

    def get_specifications(self) -> Dict[str, Any]:
        """Get the current numbering specifications"""
        return {
            'gutter_width_inches': 0.25,
            'gutter_width_points': self.gutter_width,
            'total_length_inches': 10,
            'total_length_points': self.total_length,
            'lines_per_page': self.lines_per_page,
            'line_height_points': round(self.line_height, 2),
            'overlay_method': 'PNG image overlay',
            'image_path': self.line_numbering_image_path
        }

    def add_universal_line_numbers(self, input_pdf_path: Path, output_pdf_path: Path) -> bool:
        """
        Add universal line numbering (compatibility method - uses image overlay)
        This method maintains compatibility with existing pipeline code
        """
        return self.add_image_line_numbers(input_pdf_path, output_pdf_path)

    def add_bates_and_filename_to_pdf(self, input_pdf_path: Path, output_pdf_path: Path,
                                     bates_prefix: str, bates_number: int, filename: str) -> bool:
        """
        Add both Bates number (bottom right) and filename (bottom left) to PDF
        Bates number increments for each page within the document
        """
        try:
            self.log(f"Adding Bates number and filename to {input_pdf_path.name}")

            doc = fitz.open(str(input_pdf_path))
            total_pages = len(doc)

            for page_num in range(total_pages):
                page = doc[page_num]
                current_bates = bates_number + page_num

                # Add both filename and Bates number
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
        """Add both filename and Bates number"""
        try:
            # Get page dimensions
            rect = page.rect
            page_width = rect.width
            page_height = rect.height

            # Define positioning
            margin_1_4_inch = 18  # 0.25 * 72 points
            bottom_margin = 20  # Points from bottom edge

            # Text formatting
            font_size = 8
            char_width = 4.3  # Approximate character width

            # Filename text (bottom left)
            filename_text = f"{filename} (Page {page_number} of {total_pages})"
            filename_width = len(filename_text) * char_width

            # Bates number text (bottom right)
            bates_text = f"{bates_prefix}{bates_number:04d}"
            bates_width = len(bates_text) * 4.2

            # Position filename
            filename_x = margin_1_4_inch
            filename_y = page_height - bottom_margin

            # Position Bates number
            bates_x = page_width - margin_1_4_inch - bates_width
            bates_y = page_height - bottom_margin

            # Add filename text
            page.insert_text(
                fitz.Point(filename_x, filename_y),
                filename_text,
                fontsize=font_size,
                color=(0, 0, 0),
                rotate=0,
                fontname="helv"
            )

            # Add Bates number text
            page.insert_text(
                fitz.Point(bates_x, bates_y),
                bates_text,
                fontsize=font_size,
                color=(0, 0, 0),
                rotate=0,
                fontname="helv"
            )

        except Exception as e:
            self.log(f"❌ Error adding footer with background: {str(e)}")
            raise