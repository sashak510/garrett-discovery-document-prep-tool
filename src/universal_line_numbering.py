"""
Universal 28-Line Grid Numbering System
Implements consistent line numbering across all document types with 1/4" gutter, 10" length, 28 lines per page
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, Optional
import math
from config import FOOTER_FONT_NAME, FOOTER_FONT_SIZE, FOOTER_FONT_COLOR


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
            if doc_id in self.processed_documents:
                self.log(f"⚠️ Document {input_pdf_path.name} already processed, skipping to prevent duplication")
                return True

            self.log(f"Adding universal 28-line numbering to {input_pdf_path.name}")

            doc = fitz.open(str(input_pdf_path))
            total_pages = len(doc)

            # Clear processed pages tracking for this document
            self.processed_pages.clear()

            for page_num in range(total_pages):
                page = doc[page_num]

                # Check if this page has already been processed
                page_id = f"{input_pdf_path.name}_page_{page_num}"
                if page_id in self.processed_pages:
                    self.log(f"⚠️ Page {page_num + 1} already processed, skipping to prevent duplication")
                    continue

                # Mark page as processed
                self.processed_pages.add(page_id)

                # Use vector-based processing for native PDFs to avoid overlay issues
                if page_num == 0 and self._is_native_pdf(input_pdf_path):
                    self.log(f"📄 Using vector-based line numbering for native PDF {input_pdf_path.name}")
                    self._add_vector_grid_to_page(page, page_num + 1)
                else:
                    # Use original image-based method for non-native PDFs or subsequent pages
                    self._create_true_gutter(page, input_pdf_path.name)
                    self._add_grid_to_page(page, page_num + 1)

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

    def _add_vector_grid_to_page(self, page, page_number: int):
        """Add 28-line grid numbers to a single page using vector operations (no image capture)"""
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

            # Save original page content as text blocks
            text_blocks = page.get_text("blocks")
            images = page.get_images()

            # Clear and resize page
            page.clean_contents()
            page.set_cropbox(fitz.Rect(0, 0, new_page_width, page_height))
            page.set_mediabox(fitz.Rect(0, 0, new_page_width, page_height))

            # Re-insert text content shifted right
            for block in text_blocks:
                if len(block) >= 4:  # Valid text block
                    x0, y0, x1, y1, text, block_no, block_type = block[:7]
                    if text.strip():  # Only insert non-empty text
                        new_x0 = x0 + total_gutter_space
                        page.insert_text(
                            fitz.Point(new_x0, y1),
                            text,
                            fontsize=8,  # Default font size
                            color=(0, 0, 0),
                            rotate=0,
                            fontname="Times-Roman"
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

            # Create the gutter (background rectangle)
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

            # Add line numbers
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
            self.log(f"❌ Error adding vector grid to page {page_number}: {str(e)}")
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

            # Clear the page contents properly
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
            # Check for double processing
            doc_id = f"{input_pdf_path}_{input_pdf_path.stat().st_mtime}_footer"
            if doc_id in self.processed_documents:
                self.log(f"⚠️ Document {input_pdf_path.name} footer already processed, skipping to prevent duplication")
                return True

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

            # Mark document footer as processed
            self.processed_documents.add(doc_id)

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

            # Background color and padding
            bg_color = (0.9, 0.9, 0.9)  # Light grey background
            horizontal_padding = 6  # Horizontal padding for readability
            vertical_padding = 2  # Vertical padding as requested

            # Calculate text dimensions - more accurate width calculation
            filename_text = f"{filename} (Page {page_number} of {total_pages})"
            filename_width = len(filename_text) * 4.2  # More accurate width for Times-Roman 8pt
            font_size = FOOTER_FONT_SIZE

            bates_text = f"{bates_prefix}{bates_number:04d}"
            bates_width = len(bates_text) * 4.2  # More accurate width for Times-Roman 8pt

            # Calculate text height (approximate for centering)
            text_height = font_size * 1.2  # Approximate text height with line spacing

            # Calculate rectangle dimensions
            filename_rect_width = filename_width + (2 * horizontal_padding)
            filename_rect_height = text_height + (2 * vertical_padding)

            bates_rect_width = bates_width + (2 * horizontal_padding)
            bates_rect_height = text_height + (2 * vertical_padding)

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

            # Draw background rectangles (no white gap between them)
            page.draw_rect(filename_bg_rect, color=bg_color, fill=bg_color, width=0)
            page.draw_rect(bates_bg_rect, color=bg_color, fill=bg_color, width=0)

            # Calculate text positions (perfectly centered within rectangles)
            filename_text_x = filename_rect_x + (filename_rect_width - filename_width) / 2  # Center horizontally
            filename_text_y = filename_rect_y + (filename_rect_height / 2) + (font_size / 3)  # Center vertically with baseline adjustment

            bates_text_x = bates_rect_x + (bates_rect_width - bates_width) / 2  # Center horizontally
            bates_text_y = bates_rect_y + (bates_rect_height / 2) + (font_size / 3)  # Center vertically with baseline adjustment

            # Add filename text (perfectly centered)
            page.insert_text(
                fitz.Point(filename_text_x, filename_text_y),
                filename_text,
                fontsize=font_size,
                color=FOOTER_FONT_COLOR,
                rotate=0,
                fontname=FOOTER_FONT_NAME
            )

            # Add Bates number text (perfectly centered)
            page.insert_text(
                fitz.Point(bates_text_x, bates_text_y),
                bates_text,
                fontsize=font_size,
                color=FOOTER_FONT_COLOR,
                rotate=0,
                fontname=FOOTER_FONT_NAME
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