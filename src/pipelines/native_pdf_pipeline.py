"""
Native PDF Pipeline for processing text-based PDF documents

UPDATED: Now using Universal 28-Line Grid Numbering System for all document types
This pipeline applies consistent 28-line grid numbering to all PDF documents.
"""
from pathlib import Path
import shutil
from .base_pipeline import BasePipeline

class NativePDFPipeline(BasePipeline):
    """Pipeline for processing native PDF documents with universal 28-line grid numbering"""

    def __init__(self, line_numberer, bates_numberer, logger_manager=None, universal_line_numberer=None):
        # Use universal line numbering system for consistent 28-line grid
        super().__init__(line_numberer, bates_numberer, logger_manager)
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
            self.log(f"[DEBUG] NativePDFPipeline processing: {source_path.name}")
            self.log(f"[DEBUG] Universal line numberer available: {self.universal_line_numberer is not None}")
            # Step 1: Copy source to working location
            pdf_path = output_path.with_suffix('.working.pdf')
            shutil.copy2(str(source_path), str(pdf_path))

            # Step 2: Add universal 28-line grid numbering
            temp_lined_path = pdf_path.with_suffix('.lined.pdf')
            if self.universal_line_numberer:
                self.log(f"[DEBUG] Using universal line numbering for {source_path.name}")
                line_success = self.universal_line_numberer.add_universal_line_numbers(
                    pdf_path, temp_lined_path
                )
                self.log(f"[DEBUG] Universal line numbering result: {line_success}")
            else:
                # Fallback to base pipeline method if universal line numberer not available
                self.log(f"[DEBUG] Universal line numberer not available, using fallback for {source_path.name}")
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

                bates_success = self.universal_line_numberer.add_bates_and_filename_to_pdf(
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