"""
Universal 28-Line Grid Numbering System
Implements consistent line numbering across all document types with 1/4" gutter, 10" length, 28 lines per page
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, Optional
import math


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

        # Text formatting
        self.font_size = 8
        self.font_color = (0.5, 0.5, 0.5)  # Light grey
        self.background_color = (0.95, 0.95, 0.95)  # Very light grey background

        # Positioning
        self.number_x_offset = 2  # Points from left edge of gutter
        self.number_y_offset = 3  # Points from line position

    def log(self, message: str):
        """Log message with callback"""
        if self.log_callback:
            self.log_callback(message)

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
            self.log(f"Adding universal 28-line numbering to {input_pdf_path.name}")

            doc = fitz.open(str(input_pdf_path))

            for page_num in range(len(doc)):
                page = doc[page_num]
                # Create true gutter by expanding page and shifting content
                self._create_true_gutter(page, input_pdf_path.name)
                # Add line numbers to the gutter
                self._add_grid_to_page(page, page_num + 1)

            doc.save(str(output_pdf_path), garbage=4, deflate=True, clean=True)
            doc.close()

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

    def _create_true_gutter(self, page, filename=None):
        """
        Create a true gutter by shifting existing content inward within standard 8.5x11 page dimensions.
        This creates space for line numbers on the left while maintaining printable page size.
        """
        try:
            # Check if content is already shifted (has gutter)
            # Look for existing line numbers or check if content appears shifted
            text_blocks = page.get_text("blocks")
            if text_blocks:
                # Check if text starts after margin + gutter width
                total_gutter_space = self.gutter_margin + self.gutter_width
                min_x = min(block[0] for block in text_blocks)
                if min_x >= total_gutter_space - 5:  # Allow 5pt tolerance
                    self.log(f"🚫 Skipping gutter creation - content already shifted (min_x: {min_x:.1f}pt)")
                    return True

            original_rect = page.rect
            page_rotation = page.rotation

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

            # Clear the page
            page.clean_contents()

            # Calculate content position - shift right by margin + gutter width
            total_gutter_space = self.gutter_margin + self.gutter_width
            content_width = original_rect.width - total_gutter_space
            content_height = original_rect.height

            # Insert the captured content shifted right by margin + gutter width
            content_rect = fitz.Rect(total_gutter_space, 0, original_rect.width, original_rect.height)
            page.insert_image(content_rect, pixmap=pix)

            self.log(f"✅ TRUE gutter created: content shifted right by {total_gutter_space}pt within 8.5x11 page")
            return True

        except Exception as e:
            self.log(f"❌ Error creating true gutter: {str(e)}")
            return False

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

            # Define common vertical alignment (same height for both elements)
            bottom_margin = 20  # Moved closer to bottom edge (printer-safe margin)
            text_baseline_y = page_height - bottom_margin  # Baseline for text

            # Background color (light grey)
            bg_color = (0.9, 0.9, 0.9)  # Light grey background
            padding_h = 6  # Horizontal padding
            padding_v = 3  # Even vertical padding (3px above and below)

            # Calculate text dimensions first
            filename_text = f"{filename} (Page {page_number} of {total_pages})"
            filename_width = len(filename_text) * 4.2  # Width approximation for 7pt helvetica
            font_size_filename = 7

            bates_text = f"{bates_prefix}{bates_number:04d}"
            bates_width = len(bates_text) * 4.8  # Width approximation for Times-Roman 8pt
            font_size_bates = 8

            # Calculate dynamic positioning: both elements equidistant from edges
            # and push inward when text gets longer
            base_margin = 36  # Base margin from edge (0.5 inch)
            
            # Calculate the maximum width needed for either element
            max_text_width = max(filename_width, bates_width)
            
            # Calculate dynamic margin: base margin + extra space for longer text
            # This ensures both elements are equidistant and push inward when text is longer
            dynamic_margin = base_margin + max(0, (max_text_width - min(filename_width, bates_width)) / 2)
            
            # Position filename from left edge
            left_margin = dynamic_margin
            
            # Position Bates number from right edge (same distance)
            right_margin = dynamic_margin

            # Adjust horizontal padding to be slightly less on left side
            padding_left = 5  # Slightly less padding on left
            padding_right = 6  # Standard padding on right

            # Use consistent box height for both elements to ensure uniform padding
            box_height = 12  # Fixed height for both boxes (accommodates larger font)

            # Calculate background rectangles with asymmetric padding
            filename_bg_rect = fitz.Rect(
                left_margin - padding_left,
                text_baseline_y - box_height + padding_v,  # Top edge
                left_margin + filename_width + padding_right,
                text_baseline_y + padding_v  # Bottom edge
            )

            bates_x = page_width - right_margin - bates_width
            bates_bg_rect = fitz.Rect(
                bates_x - padding_left,
                text_baseline_y - box_height + padding_v,  # Top edge
                bates_x + bates_width + padding_right,
                text_baseline_y + padding_v  # Bottom edge
            )

            # Draw light grey backgrounds first (so text appears on top)
            page.draw_rect(filename_bg_rect, color=bg_color, fill=bg_color, width=0)
            page.draw_rect(bates_bg_rect, color=bg_color, fill=bg_color, width=0)

            # Calculate consistent vertical center for both text elements
            # Position text properly within boxes without going past edges
            # Use proper centering: box_height/2 from baseline, adjusted for visual center
            text_center_y = text_baseline_y - (box_height / 2) + 5.5  # Move down by 5.5 points for visual center

            # For Bates number, use same centering logic for consistency
            bates_text_y = text_baseline_y - (box_height / 2) + 5.5  # Move down by 5.5 points for visual center

            # Add filename text - vertically centered within consistent box height
            page.insert_text(
                fitz.Point(left_margin, text_center_y),
                filename_text,
                fontsize=font_size_filename,
                color=(0.3, 0.3, 0.3),  # Dark grey
                rotate=0,
                fontname="helv"
            )

            # Add Bates number text - vertically centered within consistent box height
            page.insert_text(
                fitz.Point(bates_x, bates_text_y),
                bates_text,
                fontsize=font_size_bates,
                color=(0, 0, 0),  # Black text
                rotate=0,
                fontname="Times-Roman"  # Times New Roman font
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