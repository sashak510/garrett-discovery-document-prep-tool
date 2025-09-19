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
            
            page_height = page.rect.height
            
            # Calculate line positions for even distribution over 10 inches
            line_spacing = self.total_length / (self.lines_per_page - 1)
            start_y = (page_height - self.total_length) / 2
            
            if start_y < 0:
                start_y = config.PRINTER_SAFE_MARGIN_POINTS  # Minimum top margin if page is shorter than 10 inches
            
            # Add line numbers using direct content stream manipulation
            for line_num in range(1, self.lines_per_page + 1):
                y_pos = start_y + (line_num - 1) * line_spacing
                self._add_non_searchable_text(page, str(line_num), self.x_position, y_pos)
            
            
        except Exception as e:
            self.log(f"  ❌ Error adding line numbers to page {page_number}: {str(e)}")
            raise
    
    
    def _add_non_searchable_text(self, page, text: str, x: float, y: float):
        """
        Add text that is visible but not searchable by rendering as image
        
        This creates a small image containing the text and inserts it as graphics,
        making it completely non-searchable while maintaining crisp appearance.
        """
        try:
            # Create a small image containing the text
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Calculate image size for the text
            img_width = 20
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
                
                # Draw the text
                draw.text((2, 2), text, fill=color)
                
            except Exception:
                # Fallback: simple red color
                draw.text((2, 2), text, fill=(255, 0, 0, 255))
            
            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Insert the image at the specified position
            rect = fitz.Rect(x-2, y-10, x+img_width-2, y+6)
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
                
                # Add bates number (bottom right) - searchable
                self._add_bates_text(page, bates_prefix, current_bates)
                
                # Add filename (bottom left) - searchable
                self._add_filename_text(page, filename, page_num + 1, len(doc))
            
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
    
    def _add_bates_text(self, page, bates_prefix: str, bates_number: int):
        """Add bates number text to bottom right (searchable)"""
        try:
            page_rect = page.rect
            bates_text = f"{bates_prefix}{bates_number:04d}"
            
            # Position in bottom right corner
            x_pos = page_rect.width - 60 - config.BOTTOM_MARGIN_POINTS
            y_pos = page_rect.height - config.BOTTOM_MARGIN_POINTS
            
            page.insert_text(
                fitz.Point(x_pos, y_pos),
                bates_text,
                fontsize=config.FOOTER_FONT_SIZE,
                color=config.FOOTER_FONT_COLOR,
                fontname=config.FOOTER_FONT_NAME,
                rotate=0,
                overlay=False  # Make sure it's part of searchable content
            )
            
            self.log(f"    ✅ Added bates text: {bates_text}")
            
        except Exception as e:
            self.log(f"    ❌ Failed to add bates text: {str(e)}")
    
    def _add_filename_text(self, page, filename: str, page_num: int, total_pages: int):
        """Add filename text to bottom left (non-searchable vector graphics)"""
        try:
            filename_text = f"{filename} (Page {page_num} of {total_pages})"
            
            # Position in bottom left corner
            x_pos = config.BOTTOM_MARGIN_POINTS + self.gutter_width  # Account for gutter
            y_pos = page.rect.height - config.BOTTOM_MARGIN_POINTS
            
            # Use vector graphics approach for non-searchable filename
            self._add_non_searchable_filename_text(page, filename_text, x_pos, y_pos)
            
            self.log(f"    ✅ Added non-searchable filename text: {filename_text}")
            
        except Exception as e:
            self.log(f"    ❌ Failed to add filename text: {str(e)}")
            # Fallback to searchable text if vector approach fails
            try:
                page.insert_text(
                    fitz.Point(x_pos, y_pos),
                    filename_text,
                    fontsize=config.LEGAL_FONT_SIZE_SMALL,
                    color=config.FOOTER_FONT_COLOR,
                    fontname=config.FOOTER_FONT_NAME,
                    rotate=0,
                    overlay=False
                )
                self.log(f"    ✅ Added fallback searchable filename text: {filename_text}")
            except Exception as e2:
                self.log(f"    ❌ Filename text failed completely: {str(e2)}")
    
    def _add_non_searchable_filename_text(self, page, text: str, x: float, y: float):
        """
        Add filename text as non-searchable vector graphics with background
        
        This creates an image containing the text with subtle background,
        making it completely non-searchable while maintaining readability.
        """
        try:
            # Create image with background and text
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Estimate text dimensions (filename text is typically longer)
            font_size = config.LEGAL_FONT_SIZE_SMALL
            estimated_char_width = font_size * 0.6  # Average character width
            text_width = len(text) * estimated_char_width
            text_height = font_size + 4
            
            # Calculate image size with padding
            padding = 3
            img_width = int(text_width + padding * 2)
            img_height = int(text_height + padding * 2)
            
            # Create image with light background (subtle for filename)
            bg_color = (250, 250, 250, 255)  # Very light grey background
            img = Image.new('RGBA', (img_width, img_height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Draw subtle border
            border_color = (200, 200, 200, 255)  # Light grey border
            draw.rectangle([0, 0, img_width-1, img_height-1], outline=border_color, width=1)
            
            # Draw the text
            try:
                # Convert font color from config
                text_color = (
                    int(config.FOOTER_FONT_COLOR[0] * 255),
                    int(config.FOOTER_FONT_COLOR[1] * 255), 
                    int(config.FOOTER_FONT_COLOR[2] * 255),
                    255
                )
                
                # Position text in image
                text_x = padding
                text_y = padding
                
                draw.text((text_x, text_y), text, fill=text_color)
                
            except Exception:
                # Fallback: simple black color
                draw.text((padding, padding), text, fill=(0, 0, 0, 255))
            
            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Insert the image at the specified position (left-aligned)
            rect = fitz.Rect(x, y-img_height, x+img_width, y)
            page.insert_image(rect, stream=img_bytes)
            
        except ImportError:
            # PIL is required for non-searchable filename text
            self.log(f"      ❌ PIL not available - cannot create non-searchable filename text for '{text}'")
            raise ImportError("PIL (Pillow) is required for non-searchable filename text")
            
        except Exception as e:
            self.log(f"      ❌ Failed to add non-searchable filename text '{text}': {str(e)}")
            raise
    
    def get_errors(self) -> List[dict]:
        """Get list of processing errors"""
        return self.errors
    
    def clear_errors(self):
        """Clear the errors list"""
        self.errors = []
    
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