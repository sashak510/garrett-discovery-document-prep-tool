"""
Native PDF Pipeline for processing text-based PDF documents

UPDATED: Now using Universal 28-Line Grid Numbering System for all document types
This pipeline applies consistent 28-line grid numbering to all PDF documents.
"""
from pathlib import Path
import shutil
import os
import fitz
from .base_pipeline import BasePipeline

class NativePDFPipeline(BasePipeline):
    """Pipeline for processing native PDF documents with universal 28-line grid numbering"""

    def __init__(self, bates_numberer, logger_manager=None, universal_line_numberer=None):
        # Use universal line numbering system for consistent 28-line grid
        super().__init__(bates_numberer, logger_manager)
        self.universal_line_numberer = universal_line_numberer
    
    def get_pipeline_type(self):
        return "NativePDF"
    
    def get_pipeline_name(self):
        return "Native PDF"
    
    def configure_line_numberer(self):
        """Configure line numberer for native PDF documents"""
        # Using universal 28-line grid numbering system
        pass
    
    def process_document(self, source_path, output_path, file_sequential_number, bates_prefix, bates_start_number):
        """
        Process native PDF document using universal 28-line grid numbering system

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
            # self.log(f"[DEBUG] NativePDFPipeline processing: {source_path.name}")
            # self.log(f"[DEBUG] Universal line numberer available: {self.universal_line_numberer is not None}")
            # Step 1: Copy source to working location and check orientation
            pdf_path = output_path.with_suffix('.working.pdf')
            
            # First, check if PDF needs orientation correction
            rotation_applied = self._correct_pdf_orientation(str(source_path), str(pdf_path))
            if rotation_applied:
                # Orientation was corrected and saved to pdf_path
                self.log(f"✅ Orientation corrected for {source_path.name}")
            else:
                # No correction needed, just copy original to working location
                shutil.copy2(str(source_path), str(pdf_path))

            # Step 2: Add universal 28-line grid numbering
            temp_lined_path = pdf_path.with_suffix('.lined.pdf')
            if self.universal_line_numberer:
                # self.log(f"[DEBUG] Using universal line numbering for {source_path.name}")
                line_success = self.universal_line_numberer.add_line_numbers_to_pdf(
                    str(pdf_path), str(temp_lined_path)
                )
                # self.log(f"[DEBUG] Universal line numbering result: {line_success}")
            else:
                # Fallback to base pipeline method if universal line numberer not available
                # self.log(f"[DEBUG] Universal line numberer not available, using fallback for {source_path.name}")
                line_success, _ = self.add_text_line_numbers(
                    str(pdf_path), str(temp_lined_path), 1
                )

            if line_success:
                lines_added = 28  # Universal system always adds 28 lines per page
                # Replace original with lined version
                shutil.move(str(temp_lined_path), str(pdf_path))
            else:
                lines_added = 0
                if temp_lined_path.exists():
                    temp_lined_path.unlink()

            # Step 3: Add bates numbers and filename
            temp_bates_path = pdf_path.with_suffix('.bates.pdf')

            if self.universal_line_numberer:
                # Use universal line numberer to add both bates numbers and filename
                filename = source_path.stem
                # Get the total number of pages to calculate next Bates number
                import fitz
                doc = fitz.open(str(pdf_path))
                total_pages = len(doc)
                doc.close()

                bates_success = self.universal_line_numberer.add_bates_and_filename(
                    pdf_path, output_path, bates_prefix, bates_start_number, filename
                )
                next_bates = bates_start_number + total_pages  # Increment by number of pages

                # Clean up working files
                if pdf_path.exists():
                    pdf_path.unlink()

                # Create bates range for multi-page documents
                if total_pages > 1:
                    bates_range = f"{bates_prefix}{bates_start_number:04d}-{bates_prefix}{next_bates-1:04d}"
                else:
                    bates_range = f"{bates_prefix}{bates_start_number:04d}"

                return {
                    'success': True,
                    'lines_added': lines_added,
                    'bates_number': f"{bates_prefix}{bates_start_number:04d}",
                    'bates_range': bates_range,
                    'next_bates': next_bates,
                    'pipeline_type': self.get_pipeline_name()
                }
            else:
                # Use old bates numbering system
                bates_success, next_bates = self.bates_numberer.add_bates_number(
                    str(pdf_path), str(temp_bates_path), bates_prefix, bates_start_number
                )
                if bates_success:
                    # Copy to final location
                    shutil.copy2(str(temp_bates_path), str(output_path))
                    if temp_bates_path.exists():
                        temp_bates_path.unlink()

                    # Clean up working files
                    if pdf_path.exists():
                        pdf_path.unlink()

                    # Create bates range for multi-page documents
                    if next_bates > bates_start_number + 1:
                        bates_range = f"{bates_prefix}{bates_start_number:04d}-{bates_prefix}{next_bates-1:04d}"
                    else:
                        bates_range = f"{bates_prefix}{bates_start_number:04d}"

                    return {
                        'success': True,
                        'lines_added': lines_added,
                        'bates_number': f"{bates_prefix}{bates_start_number:04d}",
                        'bates_range': bates_range,
                        'next_bates': next_bates,
                        'pipeline_type': self.get_pipeline_name()
                    }
                else:
                    # Clean up on failure
                    if temp_bates_path.exists():
                        temp_bates_path.unlink()
                    if pdf_path.exists():
                        pdf_path.unlink()

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
    
    def _correct_pdf_orientation(self, input_pdf_path: str, output_pdf_path: str) -> str:
        """
        Check PDF orientation by converting first page to image and using Tesseract,
        then apply rotation to entire PDF if needed.
        
        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF
            
        Returns:
            bool: True if rotation was applied, False if no rotation needed
        """
        try:
            import tempfile
            from pdf_converter import PDFConverter
            
            # Create a PDF converter instance to use its orientation detection
            pdf_converter = PDFConverter(log_callback=getattr(self, 'log_callback', None))
            
            # Open the PDF and get first page as image for orientation detection
            doc = fitz.open(input_pdf_path)
            if len(doc) == 0:
                doc.close()
                return input_pdf_path
                
            first_page = doc[0]
            
            # Convert first page to image for Tesseract orientation detection
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                pix = first_page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better OCR
                pix.save(tmp_img.name)
                tmp_img_path = tmp_img.name
            
            doc.close()
            
            try:
                # Use the PDF converter's orientation detection on the image
                _, rotation_needed = pdf_converter._detect_and_correct_orientation(tmp_img_path)
                
                self.log(f"🔍 Orientation detection result: {rotation_needed}° rotation needed")
                
                if rotation_needed != 0:
                    # Apply rotation to entire PDF
                    self.log(f"🔄 Applying {rotation_needed}° rotation to PDF: {input_pdf_path} -> {output_pdf_path}")
                    self._rotate_pdf(input_pdf_path, output_pdf_path, rotation_needed)
                    
                    # Verify the rotated file was created
                    if os.path.exists(output_pdf_path):
                        self.log(f"✅ Rotated PDF created successfully: {output_pdf_path}")
                        return True  # Rotation applied
                    else:
                        self.log(f"❌ Failed to create rotated PDF: {output_pdf_path}")
                        return False
                else:
                    # No rotation needed
                    self.log(f"✅ PDF orientation is correct, no rotation needed")
                    return False  # No rotation applied
                    
            finally:
                # Clean up temp image
                try:
                    os.unlink(tmp_img_path)
                except:
                    pass
                    
        except Exception as e:
            self.log(f"⚠️  PDF orientation detection failed: {e} - using original")
            return False  # No rotation applied
    
    def _rotate_pdf(self, input_pdf_path: str, output_pdf_path: str, rotation_degrees: int):
        """
        Rotate entire PDF by specified degrees
        
        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for rotated PDF  
            rotation_degrees: Degrees to rotate (90, 180, 270)
        """
        try:
            self.log(f"🔄 Starting PDF rotation: {rotation_degrees}°")
            self.log(f"   Input: {input_pdf_path}")
            self.log(f"   Output: {output_pdf_path}")
            
            # Verify input file exists
            if not os.path.exists(input_pdf_path):
                raise FileNotFoundError(f"Input PDF not found: {input_pdf_path}")
            
            src_doc = fitz.open(input_pdf_path)
            dst_doc = fitz.open()
            
            self.log(f"   Processing {len(src_doc)} pages...")
            
            for page_num in range(len(src_doc)):
                src_page = src_doc[page_num]
                original_rect = src_page.rect
                
                # Create new page with rotated dimensions
                if rotation_degrees in (90, 270):
                    # Swap width and height for 90/270 degree rotations
                    new_width = original_rect.height
                    new_height = original_rect.width
                    self.log(f"   Page {page_num+1}: {original_rect.width}x{original_rect.height} -> {new_width}x{new_height}")
                else:
                    new_width = original_rect.width
                    new_height = original_rect.height
                    self.log(f"   Page {page_num+1}: keeping dimensions {new_width}x{new_height}")
                
                new_page = dst_doc.new_page(width=new_width, height=new_height)
                
                # Insert the rotated page content
                new_page.show_pdf_page(new_page.rect, src_doc, page_num, rotate=rotation_degrees)
                self.log(f"   Page {page_num+1}: rotated {rotation_degrees}° and added")
            
            # Save the rotated PDF
            self.log(f"   Saving rotated PDF to: {output_pdf_path}")
            dst_doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
            dst_doc.close()
            src_doc.close()
            
            # Verify output file was created
            if os.path.exists(output_pdf_path):
                file_size = os.path.getsize(output_pdf_path)
                self.log(f"✅ PDF rotated {rotation_degrees}° successfully ({file_size} bytes)")
            else:
                raise RuntimeError(f"Output PDF was not created: {output_pdf_path}")
            
        except Exception as e:
            self.log(f"❌ Failed to rotate PDF: {e}")
            import traceback
            self.log(f"❌ Traceback: {traceback.format_exc()}")
            raise
    
    def _detect_rotation_from_filename_and_metadata(self, pdf_path: str) -> int:
        """
        Fallback method to detect rotation from filename patterns and PDF metadata
        when Tesseract is not available
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            int: Rotation degrees (0, 90, 180, 270)
        """
        try:
            filename = os.path.basename(pdf_path).lower()
            
            # Check filename for rotation indicators
            if '180' in filename and ('rotat' in filename or 'landscape' in filename):
                self.log(f"   Filename suggests 180° rotation: {filename}")
                return 180
            elif '270' in filename and ('rotat' in filename or 'landscape' in filename):
                self.log(f"   Filename suggests 270° rotation: {filename}")
                return 270
            elif '90' in filename and ('rotat' in filename or 'landscape' in filename):
                self.log(f"   Filename suggests 90° rotation: {filename}")
                return 90
            
            # Check PDF metadata for rotation
            try:
                doc = fitz.open(pdf_path)
                if len(doc) > 0:
                    first_page = doc[0]
                    
                    # Check if page has rotation metadata
                    if hasattr(first_page, 'rotation') and first_page.rotation != 0:
                        rotation = first_page.rotation
                        self.log(f"   PDF metadata indicates {rotation}° rotation")
                        doc.close()
                        return rotation
                    
                    # Check page dimensions for obvious landscape orientation
                    rect = first_page.rect
                    if rect.width > rect.height * 1.3:  # Significantly wider than tall
                        self.log(f"   Page dimensions suggest landscape: {rect.width}x{rect.height}")
                        # Could be 90° or 270°, default to 270° for upside-down landscape
                        if 'landscape' in filename:
                            doc.close()
                            return 270
                
                doc.close()
            except Exception as e:
                self.log(f"   Could not check PDF metadata: {e}")
            
            return 0  # No rotation detected
            
        except Exception as e:
            self.log(f"   Fallback rotation detection failed: {e}")
            return 0