"""
Bates Numbering Module - 🔒 LOCKED COMPONENT
Adds bates numbering to PDF documents for legal document management

🚫 WARNING: This component is LOCKED and ringfenced. 
All modifications require explicit authorization per COMPONENT_LOCK_STATUS.md

LOCKED SETTINGS:
- Background fill system with centered text positioning
- Compact box design with precise margins and padding
- Light gray background (0.98, 0.98, 0.98) with black border
- Font rendering with baseline adjustment and perfect centering
- Safe margin system to avoid content overlap
"""

import os
from pathlib import Path
import tempfile
import config

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import black, blue
except ImportError:
    canvas = None
    blue = None


class BatesNumberer:
    """
    🔒 LOCKED COMPONENT - Bates Numbering System
    Adds bates numbering to PDF documents with background fill and precise positioning
    
    🚫 WARNING: All methods and settings in this class are LOCKED.
    Modifications require explicit authorization per COMPONENT_LOCK_STATUS.md
    """
    
    def __init__(self, log_callback=None):
        """
        Initialize the bates numberer
        
        Args:
            log_callback: Optional callback function for logging messages
        """
        self.log_callback = log_callback
        self.bates_errors = []
        
        # Bates numbering settings - from config.py
        self.font_size = config.FOOTER_FONT_SIZE
        self.font_color = config.FOOTER_FONT_COLOR
        self.font_name = config.FOOTER_FONT_NAME
        self.position = 'bottom_right'  # bottom_right, bottom_left, top_right, top_left, bottom_center
        self.margin = config.BOTTOM_MARGIN_POINTS  # Margin from config
        self.format_template = "{prefix}{number:04d}"  # Default format
        self.background_fill = True  # Add background fill for visibility
        self.fill_color = config.BACKGROUND_COLOR_LIGHT_GREY  # Light grey from config
        self.border_color = config.FONT_COLOR_BLACK  # Black border from config
        self.min_margin = config.PRINTER_SAFE_MARGIN_POINTS  # Minimum margin to avoid content overlap
        
    def log(self, message):
        """Log a message using the callback or print"""
        if self.log_callback:
            self.log_callback(message)
            
    def add_bates_number(self, input_pdf_path, output_pdf_path, prefix, number):
        """
        Add bates number to a single PDF document
        
        Args:
            input_pdf_path (str): Path to input PDF file
            output_pdf_path (str): Path for output PDF file with bates number
            prefix (str): Bates number prefix (e.g., "GAR")
            number (int): Starting bates number for first page
            
        Returns:
            tuple: (success: bool, final_bates_number: int) - final number after all pages
        """
        if not fitz:
            self.log("PyMuPDF not available for bates numbering")
            return False, number
            
        input_file = Path(input_pdf_path)
        output_file = Path(output_pdf_path)
        
        if not input_file.exists():
            self.log(f"Error: Input PDF does not exist: {input_pdf_path}")
            return False, number
            
        try:
            # Open the PDF
            doc = fitz.open(input_pdf_path)
            
            current_bates = number
            self.log(f"Adding bates numbers starting from '{prefix}{current_bates:04d}' to {input_file.name}")
            
            # Add incremental bates number to each page
            for page_num in range(doc.page_count):
                page = doc[page_num]
                # Generate bates number string for this page
                bates_number = self.format_template.format(prefix=prefix, number=current_bates)
                self.log(f"Adding Bates number '{bates_number}' to page {page_num + 1}")
                self._add_bates_to_page(page, bates_number)
                current_bates += 1  # Increment for next page
                
            # Save the modified PDF
            output_file.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_pdf_path))
            doc.close()
            
            self.log(f"✓ Bates numbering completed for {input_file.name} (pages {number}-{current_bates-1})")
            return True, current_bates  # Return success and next available number
            
        except Exception as e:
            self.log(f"Error adding bates number to {input_pdf_path}: {str(e)}")
            self.bates_errors.append({
                'file': input_pdf_path,
                'bates_number': f"{prefix}{number:04d}",
                'error': str(e),
                'type': 'bates_numbering_error'
            })
            return False, number  # Return original number on failure
            
    def _add_bates_to_page(self, page, bates_number):
        """
        Add bates number to a single page
        
        Args:
            page: PyMuPDF page object
            bates_number (str): The bates number string to add
        """
        page_rect = page.rect
        
        # Calculate position based on settings
        x_pos, y_pos = self._calculate_bates_position(page_rect, bates_number)
        
        # Calculate text dimensions for a more compact box
        # Use actual text measurement for accurate width (handles letters vs numbers differently)
        text_width = self._measure_text_width(bates_number, self.font_size, self.font_name)
            
        text_height = self.font_size + 2
        padding = 2  # Minimal padding for a very tight box
        
        # Insert non-searchable Bates number using vector graphics approach (includes background)
        try:
            self._add_non_searchable_bates_text(page, bates_number, x_pos, y_pos, text_width, text_height, padding)
            self.log(f"Successfully added non-searchable Bates number '{bates_number}' at position ({x_pos:.1f}, {y_pos:.1f})")
        except Exception as e:
            self.log(f"Error placing non-searchable Bates number '{bates_number}': {str(e)}")
            # Fallback to simple searchable text if vector approach fails
            try:
                self.log(f"Attempting fallback text insertion for '{bates_number}'")
                page.insert_text(
                    (x_pos, y_pos), 
                    bates_number,
                    fontsize=self.font_size,
                    color=self.font_color,
                    fontname=self.font_name,
                    rotate=0
                )
                self.log(f"Fallback text insertion successful for '{bates_number}'")
            except Exception as e2:
                self.log(f"Bates numbering failed completely for '{bates_number}': {str(e2)}")
                import traceback
                self.log(f"Full traceback: {traceback.format_exc()}")
        
    def _measure_text_width(self, text, font_size, font_name):
        """
        Measure text width with character-specific approach:
        - Numbers: 0.4 × font_size (narrower)
        - Letters: 0.7 × font_size (wider)
        - Mixed: Sum of individual character widths
        
        Args:
            text (str): Text to measure
            font_size (int): Font size
            font_name (str): Font name
            
        Returns:
            float: Actual text width in points
        """
        total_width = 0
        
        for char in text:
            if char.isdigit():
                # Numbers are narrower
                total_width += font_size * 0.5
            elif char.isalpha():
                # Letters are wider
                total_width += font_size * 0.65
            else:
                # Other characters (spaces, symbols)
                total_width += font_size * 0.6
                
        return total_width

    def _calculate_bates_position(self, page_rect, bates_number):
        """
        Calculate the position for the bates number based on settings
        
        Args:
            page_rect: PyMuPDF page rectangle
            bates_number (str): The bates number string
            
        Returns:
            tuple: (x_position, y_position)
        """
        width = page_rect.width
        height = page_rect.height
        
        # Calculate text width to ensure it fits on page
        estimated_text_width = self._measure_text_width(bates_number, self.font_size, self.font_name)
        padding = 2  # Account for rectangle padding (match the minimal padding)
        rectangle_width = estimated_text_width + (padding * 2)
        rectangle_height = self.font_size + (padding * 2)
        
        # Use margins to mirror filename positioning from left edge
        # Filename positioning: BOTTOM_MARGIN_POINTS (20) + gutter_width (18) + padding (18) = 56 points
        filename_distance_from_left = config.BOTTOM_MARGIN_POINTS + (config.GUTTER_WIDTH_INCHES * 72) + (0.25 * 72)
        safe_margin = max(self.margin, self.min_margin, filename_distance_from_left)  # Mirror filename distance
        
        if self.position == 'bottom_right':
            x_pos = width - safe_margin - rectangle_width/2  # Position rectangle center
            y_pos = height - safe_margin - rectangle_height/2  # Bottom of page, centered vertically
        elif self.position == 'bottom_left':
            x_pos = safe_margin + rectangle_width/2  # Position rectangle center
            y_pos = height - safe_margin - rectangle_height/2  # Bottom of page, centered vertically
        elif self.position == 'bottom_center':
            x_pos = width / 2  # Center horizontally
            y_pos = height - safe_margin - rectangle_height/2  # Bottom of page, centered vertically
        elif self.position == 'top_right':
            x_pos = width - safe_margin - rectangle_width/2  # Position rectangle center
            y_pos = safe_margin + rectangle_height/2  # Top of page, centered vertically
        elif self.position == 'top_left':
            x_pos = safe_margin + rectangle_width/2  # Position rectangle center
            y_pos = safe_margin + rectangle_height/2  # Top of page, centered vertically
        else:  # default to bottom_right
            x_pos = width - safe_margin - rectangle_width/2  # Position rectangle center
            y_pos = height - safe_margin - rectangle_height/2  # Bottom of page, centered vertically
            
        return x_pos, y_pos
    
    def _add_non_searchable_bates_text(self, page, text: str, x: float, y: float, text_width: float, text_height: float, padding: float):
        """
        Add Bates number as non-searchable vector graphics with background
        
        This creates an image containing the text with background fill and border,
        making it completely non-searchable while maintaining professional appearance.
        """
        try:
            # Create image with background and text
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Calculate image size including padding
            img_width = int(text_width + padding * 2 + 4)  # Extra padding for border
            img_height = int(text_height + padding * 2 + 4)
            
            # Create image with background fill color
            bg_color = (
                int(self.fill_color[0] * 255),
                int(self.fill_color[1] * 255), 
                int(self.fill_color[2] * 255),
                255
            )
            
            img = Image.new('RGBA', (img_width, img_height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Draw border
            border_color = (
                int(self.border_color[0] * 255),
                int(self.border_color[1] * 255),
                int(self.border_color[2] * 255),
                255
            )
            draw.rectangle([0, 0, img_width-1, img_height-1], outline=border_color, width=1)
            
            # Draw the text centered
            try:
                # Convert font color from 0-1 range to 0-255 range
                text_color = (
                    int(self.font_color[0] * 255),
                    int(self.font_color[1] * 255), 
                    int(self.font_color[2] * 255),
                    255
                )
                
                # Center text in image
                text_x = (img_width - text_width) / 2
                text_y = (img_height - text_height) / 2 + 2  # Slight adjustment for baseline
                
                draw.text((text_x, text_y), text, fill=text_color)
                
            except Exception:
                # Fallback: simple black color
                draw.text((padding + 2, padding + 2), text, fill=(0, 0, 0, 255))
            
            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Calculate image position (center the image at x,y coordinates)
            rect_left = x - img_width/2
            rect_top = y - img_height/2
            rect_right = x + img_width/2
            rect_bottom = y + img_height/2
            
            # Insert the image at the specified position
            rect = fitz.Rect(rect_left, rect_top, rect_right, rect_bottom)
            page.insert_image(rect, stream=img_bytes)
            
        except ImportError:
            # PIL is required for non-searchable bates numbers
            self.log(f"      ❌ PIL not available - cannot create non-searchable bates number for '{text}'")
            raise ImportError("PIL (Pillow) is required for non-searchable bates numbers")
            
        except Exception as e:
            self.log(f"      ❌ Failed to add non-searchable bates number '{text}': {str(e)}")
            raise
        
        
    def get_bates_errors(self):
        """Get list of bates numbering errors"""
        return self.bates_errors
        
    def clear_errors(self):
        """Clear the bates numbering errors list"""
        self.bates_errors = []
        
    def set_bates_options(self, font_size=None, position=None, margin=None, 
                         format_template=None, min_margin=None, fill_color=None, 
                         border_color=None, background_fill=None):
        """
        Set bates numbering options
        
        Args:
            font_size (int): Font size for bates numbers
            position (str): Position on page (bottom_right, bottom_left, etc.)
            margin (int): Points from edge
            format_template (str): Format template for bates numbers
            min_margin (int): Minimum margin to avoid content overlap
            fill_color (tuple): Background fill color (R, G, B)
            border_color (tuple): Border color (R, G, B)
            background_fill (bool): Whether to add background fill
        """
        if font_size is not None:
            self.font_size = font_size
        if position is not None:
            self.position = position
        if margin is not None:
            self.margin = margin
        if format_template is not None:
            self.format_template = format_template
        if min_margin is not None:
            self.min_margin = min_margin
        if fill_color is not None:
            self.fill_color = fill_color
        if border_color is not None:
            self.border_color = border_color
        if background_fill is not None:
            self.background_fill = background_fill


