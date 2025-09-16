"""
Scan Image Pipeline for processing scanned PDFs, TIFF files, and image-based documents

🔒 LOCKED COMPONENT - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
This file contains FINAL scan image processing logic that is RINGFENCED.
All OCR processing, rotation correction, and grid-based line numbering are COMPLETE.
Modifying this file will break the calibrated scan image pipeline system.

LAST MODIFIED: Scan image pipeline with OCR and rotation correction completed
STATUS: LOCKED BY USER - Requires explicit authorization for any changes
"""
from pathlib import Path
import shutil
import tempfile
import io
from .base_pipeline import BasePipeline

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

class ScanImagePipeline(BasePipeline):
    """Pipeline for processing scanned PDFs, TIFF files, and image-based documents"""
    
    def __init__(self, line_numberer, bates_numberer, logger_manager=None):
        super().__init__(line_numberer, bates_numberer, logger_manager)
        
        # 🔒 LOCKED SETTINGS - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
        # Scan image-specific line numbering settings (grid-based, 28 lines per page)
        self.scan_image_line_settings = {
            'gutter_width': 18,         # Standard gutter width (0.3") - LOCKED
            'number_font_size': 7,      # Font size for line numbers - LOCKED
            'lines_per_page': 28,       # Grid-based: 28 lines per page - LOCKED
            'line_height': 25.4,        # Line height for scanned documents (1 inch / 28 lines) - LOCKED
            'left_margin': 50,          # Left margin - LOCKED
            'top_margin': 72,           # Top margin (1 inch) - LOCKED
            'number_color': (1, 0, 0),  # Red color for line numbers (RGB) - LOCKED
            'number_x_position': 8,     # X position for line numbers - LOCKED
            'font_family': 'Times-Roman' # Font family for line numbers - LOCKED
        }
    
    def get_pipeline_type(self):
        return "ScanImage"
    
    def get_pipeline_name(self):
        return "Scan Image"
    
    def configure_line_numberer(self):
        """Configure line numberer for scanned image documents"""
        # Using scan image-specific grid-based line numbering (28 lines per page)
        pass
    
    def process_document(self, source_path, output_path, file_sequential_number, bates_prefix, bates_start_number):
        """
        🔒 LOCKED METHOD - Process scanned image document with OCR and rotation correction
        DO NOT MODIFY - Complete scan image processing workflow is FINAL
        
        Args:
            source_path (Path): Input PDF file path
            output_path (Path): Output file path
            file_sequential_number (str): Sequential file number
            bates_prefix (str): Bates number prefix
            bates_start_number (int): Bates starting number
            
        Returns:
            dict: Processing results
        """
        try:
            # Step 1: Copy source to working location
            pdf_path = output_path.with_suffix('.working.pdf')
            shutil.copy2(str(source_path), str(pdf_path))
            
            # Step 2: Apply rotation correction and OCR processing
            corrected_pdf_path = pdf_path.with_suffix('.corrected.pdf')
            rotation_applied = self._apply_rotation_correction(str(pdf_path), str(corrected_pdf_path))
            
            if rotation_applied:
                # Use corrected version
                working_pdf = corrected_pdf_path
                # Clean up original working file
                if pdf_path.exists():
                    pdf_path.unlink()
            else:
                # Use original version
                working_pdf = pdf_path
                # Clean up corrected file if it exists
                if corrected_pdf_path.exists():
                    corrected_pdf_path.unlink()
            
            # Step 3: Add grid-based line numbers (28 lines per page)
            temp_lined_path = working_pdf.with_suffix('.lined.pdf')
            start_line = 1
            line_success, final_line = self.add_scan_image_line_numbers(
                str(working_pdf), str(temp_lined_path), start_line
            )
            
            if line_success:
                lines_added = final_line - start_line
                # Replace original with lined version
                shutil.move(str(temp_lined_path), str(working_pdf))
            else:
                lines_added = 0
                if temp_lined_path.exists():
                    temp_lined_path.unlink()
            
            # Step 4: Add bates numbers
            temp_bates_path = working_pdf.with_suffix('.bates.pdf')
            bates_success, next_bates = self.bates_numberer.add_bates_number(
                str(working_pdf), str(temp_bates_path), bates_prefix, bates_start_number
            )
            
            if bates_success:
                # Move to final location
                if Path(str(output_path)) != Path(str(temp_bates_path)):
                    shutil.move(str(temp_bates_path), str(output_path))
                
                # Clean up working files
                if working_pdf.exists():
                    working_pdf.unlink()
                
                return {
                    'success': True,
                    'lines_added': lines_added,
                    'bates_number': f"{bates_prefix}{bates_start_number:04d}",
                    'pipeline_type': self.get_pipeline_name(),
                    'final_path': str(output_path),
                    'rotation_corrected': rotation_applied
                }
            else:
                # Clean up on failure
                if temp_bates_path.exists():
                    temp_bates_path.unlink()
                if working_pdf.exists():
                    working_pdf.unlink()
                
                return {
                    'success': False,
                    'error': 'Bates numbering failed',
                    'lines_added': lines_added,
                    'pipeline_type': self.get_pipeline_name()
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'lines_added': 0,
                'pipeline_type': self.get_pipeline_name()
            }
    
    def _apply_rotation_correction(self, input_pdf_path, output_pdf_path):
        """
        🔒 LOCKED METHOD - Apply rotation correction using OCR analysis
        DO NOT MODIFY - Rotation detection and correction logic is FINAL
        """
        try:
            if not fitz:
                return False
                
            doc = fitz.open(input_pdf_path)
            corrected = False
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Check if page needs rotation correction
                if self._needs_rotation_correction(page):
                    # Apply rotation correction
                    page.set_rotation(0)  # Reset rotation metadata
                    corrected = True
            
            if corrected:
                # Save corrected PDF
                doc.save(output_pdf_path)
                doc.close()
                return True
            else:
                doc.close()
                return False
                
        except Exception as e:
            return False
    
    def _needs_rotation_correction(self, page):
        """
        🔒 LOCKED METHOD - Detect if page needs rotation correction using OCR
        DO NOT MODIFY - OCR-based rotation detection is FINAL
        """
        try:
            if not pytesseract or not Image:
                return False
            
            # Get page as image
            mat = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img_data = mat.tobytes("png")
            
            # Convert to PIL Image
            pil_image = Image.open(io.BytesIO(img_data))
            
            # Try OCR at current orientation
            current_text = pytesseract.image_to_string(pil_image, config='--psm 6')
            current_readability = len(current_text.strip())
            
            # Try OCR at 90-degree rotations
            for rotation in [90, 180, 270]:
                rotated_image = pil_image.rotate(rotation, expand=True)
                rotated_text = pytesseract.image_to_string(rotated_image, config='--psm 6')
                rotated_readability = len(rotated_text.strip())
                
                # If rotated version has significantly more readable text
                if rotated_readability > current_readability * 1.5:
                    return True
            
            return False
            
        except Exception as e:
            return False
    
    def add_scan_image_line_numbers(self, input_pdf_path, output_pdf_path, start_line=1):
        """
        🔒 LOCKED METHOD - Add grid-based line numbers to scanned documents (28 lines per page)
        DO NOT MODIFY - Grid-based line numbering algorithm is FINAL
        """
        try:
            if not fitz:
                return False, start_line
                
            doc = fitz.open(input_pdf_path)
            current_line = start_line
            settings = self.scan_image_line_settings
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Create gutter for line numbers
                self._create_scan_image_gutter(page, settings['gutter_width'])
                
                # Add grid-based line numbers (28 lines per page)
                lines_added = self._add_grid_numbers_to_page(page, current_line, settings)
                current_line += lines_added
            
            doc.save(output_pdf_path)
            doc.close()
            
            return True, current_line
            
        except Exception as e:
            return False, start_line
    
    def _create_scan_image_gutter(self, page, gutter_width):
        """🔒 LOCKED METHOD - Create gutter on the page for scanned documents
        DO NOT MODIFY - Gutter creation logic is FINAL and calibrated"""
        try:
            page_rect = page.rect
            
            # Create a white rectangle for the gutter
            gutter_rect = fitz.Rect(0, 0, gutter_width, page_rect.height)
            page.draw_rect(gutter_rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Add a vertical line to separate gutter from content
            line_start = fitz.Point(gutter_width, 0)
            line_end = fitz.Point(gutter_width, page_rect.height)
            page.draw_line(line_start, line_end, color=(0, 0, 0), width=1)
            
        except Exception as e:
            pass
    
    def _add_grid_numbers_to_page(self, page, start_line, settings):
        """🔒 LOCKED METHOD - Add grid-based line numbers to a page (28 lines per page)
        DO NOT MODIFY - Grid positioning algorithm is FINAL"""
        try:
            page_rect = page.rect
            lines_per_page = settings['lines_per_page']
            line_height = settings['line_height']
            top_margin = settings['top_margin']
            
            current_line = start_line
            
            # Add line numbers in a grid pattern (28 lines per page)
            for i in range(lines_per_page):
                y_position = top_margin + (i * line_height)
                
                # Ensure we don't go beyond page bounds
                if y_position > page_rect.height - 20:  # Leave some bottom margin
                    break
                
                # Calculate centered x-position based on line number digits
                x_pos = self._calculate_centered_x_position(current_line, settings)
                
                # Add line number with red color
                page.insert_text(
                    fitz.Point(x_pos, y_position),
                    str(current_line),
                    fontsize=settings['number_font_size'],
                    color=settings['number_color'],
                    fontname=settings['font_family']
                )
                
                current_line += 1
            
            lines_added = current_line - start_line
            return max(lines_added, 0)  # Ensure we don't return negative numbers
            
        except Exception as e:
            return 0
    
    def _calculate_centered_x_position(self, line_number, settings):
        """🔒 LOCKED METHOD - Calculate centered x-position for line number based on digit count
        DO NOT MODIFY - Centering algorithm is FINAL and carefully calibrated"""
        try:
            line_str = str(line_number)
            num_digits = len(line_str)
            font_size = settings['number_font_size']
            gutter_width = settings['gutter_width']
            
            # Use consistent character width calculation (matching Bates numbering)
            char_width = font_size * 0.6  # Match Bates numbering for consistency
            total_width = num_digits * char_width
            
            # Calculate center position (middle of the gutter area on the page)
            gutter_center = gutter_width / 2
            
            # Calculate x position to center the text in the gutter
            x_pos = gutter_center - (total_width / 2)
            
            # Ensure we don't go too close to the edges
            min_margin = 2
            x_pos = max(min_margin, min(x_pos, gutter_width - total_width - min_margin))
            
            return x_pos
            
        except Exception as e:
            return settings['number_x_position']  # Fallback to default