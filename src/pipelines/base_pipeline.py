"""
Base Pipeline class for document processing

🔒 LOCKED COMPONENT - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
This file contains line numbering logic that is RINGFENCED and LOCKED.
All line numbering, gutter settings, and positioning calculations are FINAL.
Modifying this file will break the carefully calibrated text line numbering system.

LAST MODIFIED: Line numbering positioning and centering completed
STATUS: LOCKED BY USER - Requires explicit authorization for any changes
"""
from abc import ABC, abstractmethod
from pathlib import Path
import logging

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

class BasePipeline(ABC):
    """Base class for all document processing pipelines"""
    
    def __init__(self, bates_numberer, logger_manager=None):
        self.bates_numberer = bates_numberer
        self.logger_manager = logger_manager
        self.log = self._get_logger()
        self._apply_common_settings()
        
        # 🔒 LOCKED SETTINGS - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
        # Text-specific line numbering settings available to all pipelines
        # These values are carefully calibrated and FINAL
        self.text_line_settings = {
            'gutter_width': 18,         # Standard gutter width for text (0.3") - LOCKED
            'number_font_size': 7,       # Font size for line numbers - LOCKED
            'line_height': 12,            # Line height for text documents - LOCKED
            'left_margin': 50,            # Left margin for text - LOCKED
            'top_margin': 72,             # Top margin (1 inch) - LOCKED
            'number_color': (1, 0, 0),    # Red color for line numbers (RGB) - LOCKED
            'number_x_position': 8,       # X position for line numbers - LOCKED
            'font_family': 'Times-Roman'   # Font family for line numbers - LOCKED
        }
        
    def _get_logger(self):
        """Get logger instance"""
        if self.logger_manager and hasattr(self.logger_manager, 'log'):
            return self.logger_manager.log
        else:
            return print
    
    def _apply_common_settings(self):
        """Apply common settings that all pipelines share"""
        # Common settings are now handled by individual line numbering classes
        pass
    
    @abstractmethod
    def get_pipeline_type(self):
        """Return the pipeline type identifier"""
        pass
    
    @abstractmethod
    def get_pipeline_name(self):
        """Return the human-readable pipeline name"""
        pass
    
    @abstractmethod
    def configure_line_numberer(self):
        """Configure line numberer settings for this pipeline"""
        pass
    
    @abstractmethod
    def process_document(self, source_path, output_path, file_sequential_number, bates_prefix, bates_start_number):
        """
        Process a document through this pipeline
        
        Args:
            source_path (Path): Input file path
            output_path (Path): Output file path
            file_sequential_number (str): Sequential file number
            bates_prefix (str): Bates number prefix
            bates_start_number (int): Bates starting number
            
        Returns:
            dict: Processing results including success status, line count, etc.
        """
        pass
    
    def generate_filename(self, file_sequential_number, clean_stem):
        """Generate output filename with pipeline type"""
        pipeline_type = self.get_pipeline_type()
        return f"{file_sequential_number}_{clean_stem}_{pipeline_type}.pdf"
    
    def add_text_line_numbers(self, input_pdf_path, output_pdf_path, start_line=1):
        """
        Add line numbers to PDF specifically for text documents using text-specific settings
        Available to all pipelines that need text-based line numbering
        
        Args:
            input_pdf_path (str): Path to input PDF
            output_pdf_path (str): Path to output PDF with line numbers
            start_line (int): Starting line number
            
        Returns:
            tuple: (success: bool, final_line_number: int)
        """
        try:
            # Import fitz locally to avoid scope issues
            import fitz
            
            self.log(f"Attempting to open PDF: {input_pdf_path}")
            doc = fitz.open(input_pdf_path)
            self.log(f"Successfully opened PDF with {doc.page_count} pages")
            current_line = start_line
            settings = self.text_line_settings
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Create gutter for line numbers
                self._create_text_gutter(page, settings['gutter_width'])
                
                # Add line numbers based on text content
                lines_added = self._add_text_numbers_to_page(page, current_line, settings)
                current_line += lines_added
                
            doc.save(output_pdf_path)
            doc.close()
            
            self.log(f"Added text line numbers: {Path(input_pdf_path).name} ({current_line - start_line} lines)")
            return True, current_line
            
        except Exception as e:
            self.log(f"Error adding text line numbers: {e}")
            return False, start_line
    
    def _create_text_gutter(self, page, gutter_width):
        """🔒 LOCKED METHOD - Create gutter on the page for text documents
        DO NOT MODIFY - Gutter creation logic is FINAL and calibrated"""
        try:
            # Import fitz locally to avoid scope issues
            import fitz
            
            page_rect = page.rect
            
            # Create a white rectangle for the gutter
            gutter_rect = fitz.Rect(0, 0, gutter_width, page_rect.height)
            page.draw_rect(gutter_rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Add a vertical line to separate gutter from content
            line_start = fitz.Point(gutter_width, 0)
            line_end = fitz.Point(gutter_width, page_rect.height)
            page.draw_line(line_start, line_end, color=(0, 0, 0), width=1)
            
        except Exception as e:
            self.log(f"Error creating text gutter: {e}")
    
    def _calculate_centered_x_position(self, line_number, settings):
        """🔒 LOCKED METHOD - Calculate centered x-position for line number based on digit count
        DO NOT MODIFY - Centering algorithm is FINAL and carefully calibrated"""
        try:
            # Import fitz locally to avoid scope issues
            import fitz
            
            line_str = str(line_number)
            num_digits = len(line_str)
            font_size = settings['number_font_size']
            gutter_width = settings['gutter_width']
            
            # Use consistent character width calculation (matching Bates numbering)
            # Line numbers are typically just digits, so use the number width
            char_width = font_size * 0.6  # Match Bates numbering for consistency
            total_width = num_digits * char_width
            
            # Calculate center position (middle of the gutter area on the page)
            # The gutter is positioned at the left edge of the page, so center is at gutter_width/2
            gutter_center = gutter_width / 2
            
            # Calculate x position to center the text in the gutter
            # Position text so its center aligns with the gutter center
            x_pos = gutter_center - (total_width / 2)
            
            # Ensure we don't go too close to the edges
            min_margin = 2
            x_pos = max(min_margin, min(x_pos, gutter_width - total_width - min_margin))
            
            return x_pos
            
        except Exception as e:
            self.log(f"Error calculating centered x position: {e}")
            return settings['number_x_position']  # Fallback to default
    
    
    def _add_text_numbers_to_page(self, page, start_line, settings):
        """🔒 LOCKED METHOD - Add line numbers to a page based on text content
        DO NOT MODIFY - Line positioning and baseline calculation are FINAL"""
        try:
            # Import fitz locally to avoid scope issues
            import fitz
            
            # Extract text blocks from the page
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            current_line = start_line
            line_positions = []
            
            # Extract line positions and font sizes from text blocks
            line_info_list = []
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        # Get the bounding box of the line
                        bbox = line["bbox"]
                        y_position = bbox[1]  # Top Y coordinate
                        
                        # Calculate actual text height from the bounding box
                        text_height = bbox[3] - bbox[1]  # bottom - top
                        
                        # Get average font size from spans
                        font_sizes = []
                        for span in line.get("spans", []):
                            if "size" in span and span["size"] > 0:
                                font_sizes.append(span["size"])
                        
                        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else settings['number_font_size']
                        
                        # Only add line number if there's actual text content
                        if any(span["text"].strip() for span in line.get("spans", [])):
                            line_info_list.append({
                                'y_position': y_position,
                                'text_height': text_height,
                                'font_size': avg_font_size
                            })
            
            # Sort line info by Y coordinate (top to bottom)
            line_info_list.sort(key=lambda x: x['y_position'])
            
            # Remove duplicate positions (lines very close together)
            filtered_line_info = []
            for line_info in line_info_list:
                if not filtered_line_info or abs(line_info['y_position'] - filtered_line_info[-1]['y_position']) > settings['line_height'] * 0.5:
                    filtered_line_info.append(line_info)
            
            # Add line numbers using the filtered line information
            for line_info in filtered_line_info:
                # Calculate centered x-position based on line number digits
                x_pos = self._calculate_centered_x_position(current_line, settings)
                y_position = line_info['y_position']
                text_height = line_info['text_height']
                font_size = line_info['font_size']
                
                # Calculate baseline offset based on actual text characteristics
                # Use a combination of font size and text height for better alignment
                baseline_offset = text_height * 0.75  # 75% down the text height for baseline
                adjusted_y_position = y_position + baseline_offset
                
                # Add line number with red color
                page.insert_text(
                    fitz.Point(x_pos, adjusted_y_position),
                    str(current_line),
                    fontsize=settings['number_font_size'],
                    color=settings['number_color'],
                    fontname=settings['font_family']
                )
                
                current_line += 1
            
            lines_added = current_line - start_line
            return max(lines_added, 0)  # Ensure we don't return negative numbers
            
        except Exception as e:
            self.log(f"Error adding text numbers to page: {e}")
            return 0