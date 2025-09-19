"""
Native PDF Pipeline for processing text-based PDF documents

UPDATED: Now using Universal 28-Line Grid Numbering System for all document types
This pipeline applies consistent 28-line grid numbering to all PDF documents.

ENHANCED: Advanced orientation detection using PyMuPDF and OCR fallback
"""
from pathlib import Path
import shutil
import os
import fitz
from .base_pipeline import BasePipeline
from pdf_orientation_detector import PDFOrientationDetector

class NativePDFPipeline(BasePipeline):
    """Pipeline for processing native PDF documents with universal 28-line grid numbering and advanced orientation detection"""

    def __init__(self, bates_numberer, logger_manager=None, universal_line_numberer=None):
        # Use universal line numbering system for consistent 28-line grid
        super().__init__(bates_numberer, logger_manager)
        self.universal_line_numberer = universal_line_numberer
        # Initialize advanced orientation detector
        self.orientation_detector = PDFOrientationDetector(log_callback=self.log)
    
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
            # Step 1: Copy source to working location and apply advanced orientation detection
            pdf_path = output_path.with_suffix('.working.pdf')

            # Use advanced orientation detection with PyMuPDF and OCR fallback
            self.log(f"🔍 Using advanced orientation detection for {source_path.name}")
            rotation_applied = self.orientation_detector.detect_and_correct_orientation(
                str(source_path), str(pdf_path)
            )

            if rotation_applied:
                self.log(f"✅ Advanced orientation correction applied for {source_path.name}")
            else:
                self.log(f"ℹ️  No orientation correction needed for {source_path.name}")

            # Step 1.5: Scale down large documents to improve line number visibility
            scaled_path = pdf_path.with_suffix('.scaled.pdf')
            if self.universal_line_numberer and hasattr(self.universal_line_numberer, 'scale_large_document'):
                scaling_applied = self.universal_line_numberer.scale_large_document(
                    str(pdf_path), str(scaled_path)
                )
                if scaling_applied:
                    # Scaling was applied, use the scaled version
                    shutil.move(str(scaled_path), str(pdf_path))
                    self.log(f"✅ Document scaled for better line number visibility: {source_path.name}")
                else:
                    # No scaling needed or failed, clean up temp file
                    if scaled_path.exists():
                        scaled_path.unlink()
            else:
                # Scaling not available, continue with original
                if scaled_path.exists():
                    scaled_path.unlink()

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

            # Step 3: Add bates numbers and filename using universal line numberer
            if not self.universal_line_numberer:
                return {
                    'success': False,
                    'error': 'Universal line numberer not available',
                    'lines_added': lines_added,
                    'pipeline_type': self.get_pipeline_name()
                }

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

            if not bates_success:
                # Clean up working files
                if pdf_path.exists():
                    pdf_path.unlink()
                return {
                    'success': False,
                    'error': 'Failed to add Bates numbers and filename',
                    'lines_added': lines_added,
                    'pipeline_type': self.get_pipeline_name()
                }

            # Step 4: Normalize PDF orientation to fix rotation issues
            # This flattens all content including annotations and applies rotation properly
            normalized_path = output_path.with_suffix('.normalized.pdf')
            if hasattr(self.universal_line_numberer, 'normalize_pdf_orientation'):
                normalization_success = self.universal_line_numberer.normalize_pdf_orientation(
                    output_path, normalized_path
                )

                if normalization_success:
                    # Replace the output file with the normalized version
                    shutil.move(str(normalized_path), str(output_path))
                    self.log(f"✅ PDF orientation normalized for {source_path.name}")
                else:
                    # If normalization fails, continue with the original file
                    if normalized_path.exists():
                        normalized_path.unlink()
                    self.log(f"⚠️  Orientation normalization failed for {source_path.name}, continuing with original")
            else:
                self.log(f"⚠️  Orientation normalization not available for {source_path.name}")

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

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'lines_added': 0,
                'pipeline_type': self.get_pipeline_name()
            }
    
    def _correct_pdf_orientation(self, input_pdf_path: str, output_pdf_path: str) -> str:
        """
        Simple PDF orientation correction by setting all page rotations to 0.

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF

        Returns:
            bool: True if rotation was applied, False if no rotation needed
        """
        try:
            # Open the PDF to check for rotation
            doc = fitz.open(input_pdf_path)
            if len(doc) == 0:
                doc.close()
                return False

            # Check if any pages have rotation
            has_rotation = False
            for page in doc:
                if page.rotation != 0:
                    has_rotation = True
                    break

            doc.close()

            if has_rotation:
                # Apply simple rotation correction by setting rotation to 0
                self.log(f"🔄 Setting rotation to 0 for PDF: {input_pdf_path}")
                self._set_rotation_to_zero(input_pdf_path, output_pdf_path)
                return True  # Rotation applied
            else:
                # No rotation needed
                self.log(f"✅ PDF orientation is correct, no rotation needed")
                # Just copy the original file
                shutil.copy2(input_pdf_path, output_pdf_path)
                return False  # No rotation applied

        except Exception as e:
            self.log(f"⚠️  PDF orientation correction failed: {e} - using original")
            # Fallback: copy original file
            try:
                shutil.copy2(input_pdf_path, output_pdf_path)
            except:
                pass
            return False  # No rotation applied
    
    def _set_rotation_to_zero(self, input_pdf_path: str, output_pdf_path: str):
        """
        Set all page rotations to 0

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF with rotation set to 0
        """
        try:
            self.log(f"🔄 Setting rotation to 0 for PDF")
            self.log(f"   Input: {input_pdf_path}")
            self.log(f"   Output: {output_pdf_path}")

            # Verify input file exists
            if not os.path.exists(input_pdf_path):
                raise FileNotFoundError(f"Input PDF not found: {input_pdf_path}")

            doc = fitz.open(input_pdf_path)

            self.log(f"   Processing {len(doc)} pages...")

            # Set all page rotations to 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                if page.rotation != 0:
                    page.set_rotation(0)
                    self.log(f"   Page {page_num+1}: set rotation to 0")

            # Save the PDF with rotation set to 0
            self.log(f"   Saving PDF with rotation set to 0: {output_pdf_path}")
            doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
            doc.close()

            # Verify output file was created
            if os.path.exists(output_pdf_path):
                file_size = os.path.getsize(output_pdf_path)
                self.log(f"✅ PDF rotation set to 0 successfully ({file_size} bytes)")
            else:
                raise RuntimeError(f"Output PDF was not created: {output_pdf_path}")

        except Exception as e:
            self.log(f"❌ Failed to set rotation to 0: {e}")
            import traceback
            self.log(f"❌ Traceback: {traceback.format_exc()}")
            raise
    
