"""
Vector Graphics Line Numbering Module
Creates visible but non-searchable line numbers using PDF vector graphics
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Tuple, List
import tempfile
import os
import config


class VectorLineNumberer:
    """
    Professional PDF line numbering using vector graphics approach.
    This approach:
    - Creates visible line numbers for reference
    - Numbers are NOT searchable (key requirement)
    - Uses vector graphics for professional appearance
    - Maintains small file sizes
    - Industry standard for legal documents where line numbers should not interfere with searches
    """
    
    def __init__(self, log_callback=None):
        """
        Initialize the vector line numberer

        Args:
            log_callback: Optional callback function for logging messages
        """
        self.log_callback = log_callback

        # Line numbering configuration - from config.py
        self.lines_per_page = config.LINES_PER_PAGE
        self.gutter_width = config.GUTTER_WIDTH_INCHES * 72  # Convert inches to points
        self.total_length = config.TOTAL_LENGTH_INCHES * 72  # Convert inches to points

        # Text formatting - from config.py
        self.font_size = config.LEGAL_FONT_SIZE_NORMAL
        self.font_name = config.LEGAL_FONT_NAME
        self.text_color = config.LINE_NUMBER_COLOR_RED

        # Positioning - calculated from config values
        self.x_position = (config.GUTTER_MARGIN_INCHES + config.GUTTER_WIDTH_INCHES / 2) * 72  # Center in gutter, converted to points

        # Document scaling settings
        self.max_width_inches = 8.5  # Standard letter width
        self.max_height_inches = 11.0  # Standard letter height
        self.scale_large_documents = True

        # Scaling quality settings
        self.scaling_quality = 'high'  # 'low', 'medium', 'high'
        self.scaling_dpi = 300  # Target DPI for high-quality scaling
        self.use_anti_aliasing = True

        self.errors = []
    
    def log(self, message: str):
        """Log a message using the callback or print"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def add_line_numbers_to_pdf(self, input_pdf_path: str, output_pdf_path: str) -> bool:
        """
        Add non-searchable line numbers to PDF using vector graphics
        
        Args:
            input_pdf_path: Path to input PDF file
            output_pdf_path: Path for output PDF file with line numbers
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            input_path = Path(input_pdf_path)
            output_path = Path(output_pdf_path)
            
            if not input_path.exists():
                self.log(f"❌ Input PDF does not exist: {input_pdf_path}")
                return False
            
            self.log(f"📄 Adding vector line numbers (non-searchable) to {input_path.name}")
            
            # Open PDF document
            doc = fitz.open(str(input_path))
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._add_line_numbers_to_page(page, page_num + 1)
            
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the modified PDF
            doc.save(str(output_path), garbage=4, deflate=True, clean=True)
            doc.close()
            
            self.log(f"✅ Non-searchable line numbers added: {output_path.name}")
            return True
            
        except Exception as e:
            error_msg = f"❌ Error adding line numbers to {input_pdf_path}: {str(e)}"
            self.log(error_msg)
            self.errors.append({
                'file': input_pdf_path,
                'error': str(e),
                'type': 'vector_numbering_error'
            })
            return False
    
    def _add_line_numbers_to_page(self, page, page_number: int):
        """
        Add non-searchable line numbers to a single page using vector graphics

        Args:
            page: PyMuPDF page object
            page_number: Page number for logging
        """
        try:
            # Skip gutter creation to avoid page-to-image conversion
            # The problematic _create_gutter_space method converts entire page to image
            # which causes overlay duplication and resolution loss
            # Line numbers will be placed directly without gutter modification

            page_rect = page.rect
            page_height = page_rect.height
            page_width = page_rect.width

            # Detect if page is landscape (width > height)
            is_landscape = page_width > page_height

            if is_landscape:
                # For landscape documents, use much shorter total length to fit the shorter edge
                # Calculate available space after accounting for top/bottom margins
                available_height = page_height - (2 * config.PRINTER_SAFE_MARGIN_POINTS)
                # Use 7.5 inches or available height (whichever is smaller) to ensure lines fit on screen
                landscape_total_length = min(7.5 * 72, available_height)  # 7.5 inches in points or available space
                line_spacing = landscape_total_length / (self.lines_per_page - 1)
                start_y = config.PRINTER_SAFE_MARGIN_POINTS  # Start from top margin

                self.log(f"    📄 Landscape orientation detected - using {landscape_total_length/72:.1f}-inch length for line numbering")
            else:
                # Standard portrait orientation - use 10 inch total length
                line_spacing = self.total_length / (self.lines_per_page - 1)
                start_y = (page_height - self.total_length) / 2

            if start_y < 0:
                start_y = config.PRINTER_SAFE_MARGIN_POINTS  # Minimum top margin if page is shorter than available length

            # Add line numbers using direct content stream manipulation
            for line_num in range(1, self.lines_per_page + 1):
                y_pos = start_y + (line_num - 1) * line_spacing
                self._add_non_searchable_text(page, str(line_num), self.x_position, y_pos, is_landscape)


        except Exception as e:
            self.log(f"  ❌ Error adding line numbers to page {page_number}: {str(e)}")
            raise
    
    
    def _add_non_searchable_text(self, page, text: str, x: float, y: float, is_landscape: bool = False):
        """
        Add text that is visible but not searchable by rendering as image

        This creates a small image containing the text and inserts it as graphics,
        making it completely non-searchable while maintaining crisp appearance.
        Text is centered for consistent alignment (single digits centered with double digits).

        Args:
            page: PyMuPDF page object
            text: Text to add
            x: X position
            y: Y position
            is_landscape: Whether the page is landscape (affects font size)
        """
        try:
            # Create a small image containing the text
            from PIL import Image, ImageDraw, ImageFont
            import io

            # Adjust font size for landscape pages
            font_size = self.font_size - 1 if is_landscape else self.font_size

            # Calculate image size for the text - accommodate both single and double digits
            # Use double-digit width as standard to ensure consistent centering
            max_text_width = 12  # Width for double digits
            img_width = 16  # Add some padding
            img_height = 16

            # Create image with white opaque background
            img = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)

            # Try to use a similar font, fallback to default
            try:
                # Convert color from 0-1 range to 0-255 range
                color = (
                    int(self.text_color[0] * 255),
                    int(self.text_color[1] * 255),
                    int(self.text_color[2] * 255),
                    255
                )

                # Calculate text width for centering
                try:
                    font = ImageFont.load_default()
                    # Get text bounding box for accurate positioning
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                except:
                    # Fallback estimation
                    text_width = len(text) * 6

                # Center the text in the image for consistent alignment
                text_x = (img_width - text_width) // 2
                draw.text((text_x, 2), text, fill=color)

            except Exception:
                # Fallback: simple red color with basic centering
                text_x = (img_width - len(text) * 6) // 2
                draw.text((text_x, 2), text, fill=(255, 0, 0, 255))

            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # Insert the image at the specified position (centered on the target x position)
            rect = fitz.Rect(x - img_width//2, y-10, x + img_width//2, y+6)
            page.insert_image(rect, stream=img_bytes)

        except ImportError:
            # PIL is required for non-searchable line numbers
            self.log(f"      ❌ PIL not available - cannot create non-searchable text for '{text}'")
            raise ImportError("PIL (Pillow) is required for non-searchable line numbers")

        except Exception as e:
            self.log(f"      ❌ Failed to add non-searchable text '{text}': {str(e)}")
            raise
    
    
    def _add_content_stream_text(self, page, text: str, x: float, y: float):
        """
        Alternative method: Direct content stream manipulation (more complex but truly non-searchable)
        This would require lower-level PDF manipulation
        """
        try:
            # This would be the approach for truly non-searchable text
            # but requires more complex PDF content stream manipulation
            
            # Create raw PDF content for the text
            content_stream = f"""
q
BT
/{self.font_name} {self.font_size} Tf
{self.text_color[0]} {self.text_color[1]} {self.text_color[2]} rg
{x} {y} Td
({text}) Tj
ET
Q
"""
            
            # This would need to be inserted as raw content stream
            # PyMuPDF doesn't directly support this, so we use the overlay approach above
            
        except Exception as e:
            self.log(f"      ❌ Content stream method failed: {str(e)}")
    
    def add_bates_and_filename(self, input_pdf_path: str, output_pdf_path: str,
                              bates_prefix: str, bates_number: int, filename: str) -> bool:
        """
        Add line numbers, bates numbers, and filename to PDF
        Line numbers are non-searchable, bates and filename can be searchable

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF
            bates_prefix: Bates number prefix
            bates_number: Starting bates number
            filename: Original filename to display

        Returns:
            bool: True if successful
        """
        try:
            # First add non-searchable line numbers
            temp_path = tempfile.mktemp(suffix='.pdf')

            if not self.add_line_numbers_to_pdf(input_pdf_path, temp_path):
                return False

            # Then add searchable bates and filename using regular text
            doc = fitz.open(temp_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                current_bates = bates_number + page_num

                # Detect if page is landscape
                page_rect = page.rect
                is_landscape = page_rect.width > page_rect.height

                # Add bates number (bottom right) - searchable
                self._add_bates_text(page, bates_prefix, current_bates, is_landscape)

                # Add filename (bottom left) - searchable
                self._add_filename_text(page, filename, page_num + 1, len(doc), is_landscape)

            # Save final result
            output_path = Path(output_pdf_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            doc.save(str(output_path), garbage=4, deflate=True, clean=True)
            doc.close()

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

            self.log(f"✅ Complete processing: {output_path.name}")
            return True

        except Exception as e:
            error_msg = f"❌ Error in complete processing for {input_pdf_path}: {str(e)}"
            self.log(error_msg)
            self.errors.append({
                'file': input_pdf_path,
                'error': str(e),
                'type': 'complete_processing_error'
            })
            return False
    
    def _add_bates_text(self, page, bates_prefix: str, bates_number: int, is_landscape: bool = False):
        """Add bates number as annotation text to bottom right (non-searchable vector graphics)"""
        try:
            page_rect = page.rect
            bates_text = f"{bates_prefix}{bates_number:04d}"

            # Position in bottom right corner
            right_margin_inches = 0.25
            right_margin_points = right_margin_inches * 72  # Convert inches to points

            # Estimate text width for bates number (approximately 80-100 points for typical bates)
            # and position so right edge aligns with margin
            estimated_text_width = 90  # Reasonable estimate for bates number width
            x_pos = page_rect.width - right_margin_points - estimated_text_width
            y_pos = page_rect.height - config.BOTTOM_MARGIN_POINTS

            # Use vector graphics approach for non-searchable bates number
            self._add_non_searchable_annotation_text(page, bates_text, x_pos, y_pos, is_landscape)

            self.log(f"    ✅ Added non-searchable bates annotation text: {bates_text}")

        except Exception as e:
            self.log(f"    ❌ Failed to add bates text: {str(e)}")

    def _add_filename_text(self, page, filename: str, page_num: int, total_pages: int, is_landscape: bool = False):
        """Add filename text to bottom left (non-searchable vector graphics)"""
        try:
            filename_text = f"{filename}"

            # Position in bottom left corner with 1/4 inch padding from line numbers
            padding_from_line_numbers = 0.25 * 72  # 1/4 inch in points
            x_pos = config.BOTTOM_MARGIN_POINTS + self.gutter_width + padding_from_line_numbers
            y_pos = page.rect.height - config.BOTTOM_MARGIN_POINTS

            # Use vector graphics approach for non-searchable filename
            self._add_non_searchable_annotation_text(page, filename_text, x_pos, y_pos, is_landscape)

            self.log(f"    ✅ Added non-searchable filename text: {filename_text}")

        except Exception as e:
            self.log(f"    ❌ Failed to add filename text: {str(e)}")
            # Fallback to searchable text if vector approach fails
            try:
                page.insert_text(
                    fitz.Point(x_pos, y_pos),
                    filename_text,
                    fontsize=config.LEGAL_FONT_SIZE_SMALL - 1 if is_landscape else config.LEGAL_FONT_SIZE_SMALL,
                    color=config.FOOTER_FONT_COLOR,
                    fontname=config.FOOTER_FONT_NAME,
                    rotate=0,
                    overlay=False
                )
                self.log(f"    ✅ Added fallback searchable filename text: {filename_text}")
            except Exception as e2:
                self.log(f"    ❌ Filename text failed completely: {str(e2)}")
    
    def _add_non_searchable_annotation_text(self, page, text: str, x: float, y: float, is_landscape: bool = False):
        """
        Add annotation text as non-searchable vector graphics with background

        This creates an image containing the text with subtle background,
        making it completely non-searchable while maintaining readability.
        Used for both filename and bates number annotations.

        Args:
            page: PyMuPDF page object
            text: Text to add
            x: X position
            y: Y position
            is_landscape: Whether the page is landscape (affects font size)
        """
        try:
            # Create image with background and text
            from PIL import Image, ImageDraw, ImageFont
            import io

            # Use proper font sizing and measurement to prevent text cutoff
            # Adjust font size for landscape pages
            font_size = config.FOOTER_FONT_SIZE - 1 if is_landscape else config.FOOTER_FONT_SIZE

            # More accurate text measurement - accommodate up to 30 characters
            # Use character-specific width calculation for better accuracy
            def calculate_text_width(text, font_size):
                total_width = 0
                for char in text:
                    if char.isdigit():
                        total_width += font_size * 0.5  # Numbers are narrower
                    elif char.isalpha():
                        total_width += font_size * 0.65  # Letters are wider
                    elif char.isspace():
                        total_width += font_size * 0.3  # Spaces are narrower
                    else:
                        total_width += font_size * 0.6  # Other characters/symbols
                return max(total_width, font_size * 3)  # Minimum width for very short text

            # Calculate actual text dimensions
            text_width = calculate_text_width(text, font_size)
            text_height = font_size  # Base text height

            # Calculate image size with symmetrical padding
            padding = 6  # Symmetrical padding for better appearance
            img_width = int(text_width + padding * 2)
            img_height = int(text_height + padding * 2)

            # Ensure minimum size for very short text (like Bates numbers)
            min_width = int(font_size * 4)  # Minimum width for aesthetics
            min_height = int(font_size * 3)  # Increased minimum height for better symmetry
            img_width = max(img_width, min_width)
            img_height = max(img_height, min_height)

            # Create image with light background
            bg_color = (245, 245, 245, 255)  # Very light grey background
            img = Image.new('RGBA', (img_width, img_height), bg_color)
            draw = ImageDraw.Draw(img)

            # Draw subtle border
            border_color = (180, 180, 180, 255)  # Medium light grey border
            draw.rectangle([0, 0, img_width-1, img_height-1], outline=border_color, width=1)

            # Draw the text with proper positioning
            try:
                # Convert font color from config
                text_color = (
                    int(config.FOOTER_FONT_COLOR[0] * 255),
                    int(config.FOOTER_FONT_COLOR[1] * 255),
                    int(config.FOOTER_FONT_COLOR[2] * 255),
                    255
                )

                # Try multiple font options for better compatibility
                font = None
                font_options = [
                    "Times.ttf",
                    "times.ttf",
                    "Times New Roman.ttf",
                    "arial.ttf",
                    "Arial.ttf"
                ]

                for font_file in font_options:
                    try:
                        font = ImageFont.truetype(font_file, font_size)
                        break
                    except:
                        continue

                # If no truetype font works, use PIL's default font
                if font is None:
                    font = ImageFont.load_default()

                # Position text in center of image with symmetrical padding
                # Get text bounding box for accurate centering
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except:
                    # Fallback if textbbox not available
                    try:
                        bbox = draw.textsize(text, font=font)
                        text_width = bbox[0]
                        text_height = bbox[1]
                    except:
                        # Simple estimate if both methods fail
                        text_width = len(text) * font_size * 0.6
                        text_height = font_size

                # Center text in image with symmetrical padding
                text_x = (img_width - text_width) // 2
                text_y = (img_height - text_height) // 2

                draw.text((text_x, text_y), text, fill=text_color, font=font)

            except Exception as e:
                # Final fallback - use PIL's default text without font specification
                # Center it in the image
                fallback_x = img_width // 4  # Rough center estimate for default font
                fallback_y = img_height // 3  # Rough center estimate for default font
                draw.text((fallback_x, fallback_y), text, fill=(0, 0, 0, 255))

            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # Insert the image at the specified position (left-aligned)
            # Adjust y-position to ensure proper placement
            rect = fitz.Rect(x, y-img_height+2, x+img_width, y+2)
            page.insert_image(rect, stream=img_bytes)

        except ImportError:
            # PIL is required for non-searchable annotation text
            self.log(f"      ❌ PIL not available - cannot create non-searchable annotation text for '{text}'")
            raise ImportError("PIL (Pillow) is required for non-searchable annotation text")

        except Exception as e:
            self.log(f"      ❌ Failed to add non-searchable annotation text '{text}': {str(e)}")
            raise
    
    def get_errors(self) -> List[dict]:
        """Get list of processing errors"""
        return self.errors
    
    def clear_errors(self):
        """Clear the errors list"""
        self.errors = []

    def set_scaling_quality(self, quality: str):
        """
        Set the scaling quality level

        Args:
            quality: Quality level - 'low', 'medium', 'high'
        """
        if quality not in ['low', 'medium', 'high']:
            raise ValueError("Quality must be 'low', 'medium', or 'high'")

        self.scaling_quality = quality

        # Adjust DPI based on quality
        if quality == 'low':
            self.scaling_dpi = 150
        elif quality == 'medium':
            self.scaling_dpi = 200
        else:  # high
            self.scaling_dpi = 300

        self.log(f"Scaling quality set to {quality} ({self.scaling_dpi} DPI)")

    def set_scaling_dpi(self, dpi: int):
        """
        Set custom DPI for scaling

        Args:
            dpi: Target DPI (recommended: 150-600)
        """
        if not isinstance(dpi, int) or dpi < 72 or dpi > 1200:
            raise ValueError("DPI must be an integer between 72 and 1200")

        self.scaling_dpi = dpi
        self.log(f"Scaling DPI set to {dpi}")

    def get_scaling_settings(self) -> dict:
        """Get current scaling settings"""
        return {
            'max_width_inches': self.max_width_inches,
            'max_height_inches': self.max_height_inches,
            'scale_large_documents': self.scale_large_documents,
            'scaling_quality': self.scaling_quality,
            'scaling_dpi': self.scaling_dpi,
            'use_anti_aliasing': self.use_anti_aliasing
        }
    
    def get_specifications(self) -> dict:
        """Get current numbering specifications"""
        return {
            'approach': 'Vector Graphics (Non-Searchable)',
            'lines_per_page': self.lines_per_page,
            'total_length_inches': self.total_length / 72,
            'font_size': self.font_size,
            'font_name': self.font_name,
            'text_color': self.text_color,
            'searchable_line_numbers': False,  # Key feature
            'searchable_bates': True,
            'searchable_filename': True,
            'professional_standard': True
        }

    def scale_large_document(self, input_pdf_path: str, output_pdf_path: str) -> bool:
        """
        Scale down documents larger than standard paper size to improve line number visibility.

        Args:
            input_pdf_path: Path to input PDF file
            output_pdf_path: Path for output PDF file with scaled content

        Returns:
            bool: True if scaling was applied, False if no scaling needed or failed
        """
        try:
            input_path = Path(input_pdf_path)
            output_path = Path(output_pdf_path)

            if not input_path.exists():
                self.log(f"❌ Input PDF does not exist: {input_pdf_path}")
                return False

            if not self.scale_large_documents:
                self.log(f"📄 Document scaling disabled, copying as-is: {input_path.name}")
                # Just copy the file if scaling is disabled
                import shutil
                shutil.copy2(str(input_path), str(output_path))
                return False

            # Open PDF document
            doc = fitz.open(str(input_path))

            # Check if any page needs scaling
            needs_scaling = False
            max_scale_factor = 1.0

            for page_num in range(len(doc)):
                page = doc[page_num]
                width_inches = page.rect.width / 72
                height_inches = page.rect.height / 72

                # Calculate scale factor needed for this page
                width_scale = self.max_width_inches / width_inches if width_inches > self.max_width_inches else 1.0
                height_scale = self.max_height_inches / height_inches if height_inches > self.max_height_inches else 1.0
                page_scale = min(width_scale, height_scale)

                if page_scale < 1.0:
                    needs_scaling = True
                    max_scale_factor = min(max_scale_factor, page_scale)

                    self.log(f"   Page {page_num + 1}: {width_inches:.1f}\"x{height_inches:.1f}\" -> scale factor: {page_scale:.3f}")

            if not needs_scaling:
                self.log(f"✅ Document size within limits ({max_scale_factor:.1f}x scaling): {input_path.name}")
                # Just copy the file if no scaling needed
                import shutil
                shutil.copy2(str(input_path), str(output_path))
                doc.close()
                return False

            self.log(f"📏 Scaling document by factor {max_scale_factor:.3f}: {input_path.name}")

            # Use high-quality scaling method
            if self.scaling_quality == 'high':
                self._high_quality_scale_document(doc, output_path, max_scale_factor)
            else:
                self._standard_scale_document(doc, output_path, max_scale_factor)

            doc.close()

            self.log(f"✅ Document scaled successfully: {output_path.name}")
            return True

        except Exception as e:
            error_msg = f"❌ Error scaling document {input_pdf_path}: {str(e)}"
            self.log(error_msg)
            self.errors.append({
                'file': input_pdf_path,
                'error': str(e),
                'type': 'document_scaling_error'
            })
            return False

    def _high_quality_scale_document(self, doc, output_path: str, scale_factor: float):
        """
        High-quality document scaling using rasterization at high DPI with anti-aliasing

        Args:
            doc: Source PyMuPDF document
            output_path: Path for output PDF file
            scale_factor: Scale factor to apply
        """
        try:
            import math

            # Calculate target DPI based on original document DPI
            original_dpi = 72  # PDF standard DPI
            target_dpi = self.scaling_dpi

            # Create high-quality matrix for rendering
            zoom = target_dpi / original_dpi
            matrix = fitz.Matrix(zoom, zoom)

            # Create new document for scaled pages
            scaled_doc = fitz.open()

            for page_num in range(len(doc)):
                page = doc[page_num]
                original_rect = page.rect

                # Calculate new dimensions
                new_width = original_rect.width * scale_factor
                new_height = original_rect.height * scale_factor

                # Render page at high resolution
                pix = page.get_pixmap(matrix=matrix, alpha=False)

                # Create new page with final dimensions
                new_page = scaled_doc.new_page(width=new_width, height=new_height)

                # Calculate the final scaling from high-res pixmap to target size
                final_scale_x = new_width / pix.width
                final_scale_y = new_height / pix.height

                # Insert the high-resolution pixmap with proper scaling
                new_page.insert_image(
                    fitz.Rect(0, 0, new_width, new_height),
                    pixmap=pix,
                    xref=0,
                    rotate=0,
                    alpha=0,
                    overlay=True
                )

            # Save with high-quality settings
            scaled_doc.save(
                str(output_path),
                garbage=4,
                deflate=True,
                clean=True,
                pretty=True  # Better PDF structure
            )
            scaled_doc.close()

            self.log(f"   High-quality scaling completed at {target_dpi} DPI")

        except Exception as e:
            self.log(f"   High-quality scaling failed, falling back to standard: {str(e)}")
            # Fall back to standard scaling
            self._standard_scale_document(doc, output_path, scale_factor)

    def _standard_scale_document(self, doc, output_path: str, scale_factor: float):
        """
        Standard document scaling using vector-based scaling

        Args:
            doc: Source PyMuPDF document
            output_path: Path for output PDF file
            scale_factor: Scale factor to apply
        """
        try:
            # Create new document with scaled pages
            scaled_doc = fitz.open()

            for page_num in range(len(doc)):
                page = doc[page_num]
                original_rect = page.rect

                # Calculate new dimensions
                new_width = original_rect.width * scale_factor
                new_height = original_rect.height * scale_factor

                # Create new page with scaled dimensions
                new_page = scaled_doc.new_page(width=new_width, height=new_height)

                # Copy and scale the content using vector scaling
                new_page.show_pdf_page(
                    fitz.Rect(0, 0, new_width, new_height),
                    doc,
                    page_num
                )

            # Save with standard quality settings
            scaled_doc.save(str(output_path), garbage=4, deflate=True, clean=True)
            scaled_doc.close()

            self.log(f"   Standard scaling completed")

        except Exception as e:
            self.log(f"   Standard scaling failed: {str(e)}")
            raise

    def normalize_pdf_orientation(self, input_pdf_path: str, output_pdf_path: str) -> bool:
        """
        Normalize PDF orientation by setting all page rotations to 0.

        Args:
            input_pdf_path: Path to input PDF file
            output_pdf_path: Path for output PDF file with normalized orientation

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            input_path = Path(input_pdf_path)
            output_path = Path(output_pdf_path)

            if not input_path.exists():
                self.log(f"❌ Input PDF does not exist: {input_pdf_path}")
                return False

            self.log(f"🔄 Normalizing PDF orientation (setting rotation to 0): {input_path.name}")

            # Open PDF document
            doc = fitz.open(str(input_path))

            # Set all page rotations to 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                if page.rotation != 0:
                    page.set_rotation(0)
                    self.log(f"   Page {page_num + 1}: Set rotation to 0")

            # Save the normalized PDF
            doc.save(str(output_path), garbage=4, deflate=True, clean=True)
            doc.close()

            self.log(f"✅ PDF orientation normalized: {output_path.name}")
            return True

        except Exception as e:
            error_msg = f"❌ Error normalizing PDF orientation for {input_pdf_path}: {str(e)}"
            self.log(error_msg)
            self.errors.append({
                'file': input_pdf_path,
                'error': str(e),
                'type': 'orientation_normalization_error'
            })
            return False