"""
Native PDF Pipeline for processing text-based PDF documents

🔒 LOCKED COMPONENT - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
This file contains FINAL native PDF processing logic that is RINGFENCED.
All native PDF processing, line numbering integration, and gutter creation are COMPLETE.
Modifying this file will break the calibrated native PDF pipeline system.

LAST MODIFIED: Native PDF pipeline integration with base pipeline completed
STATUS: LOCKED BY USER - Requires explicit authorization for any changes
"""
from pathlib import Path
import shutil
from .base_pipeline import BasePipeline

class NativePDFPipeline(BasePipeline):
    """Pipeline for processing native PDF documents with extractable text"""
    
    def __init__(self, line_numberer, bates_numberer, logger_manager=None):
        # Use base pipeline text line numbering (already has 0.3" gutter settings)
        super().__init__(line_numberer, bates_numberer, logger_manager)
    
    def get_pipeline_type(self):
        return "NativePDF"
    
    def get_pipeline_name(self):
        return "Native PDF"
    
    def configure_line_numberer(self):
        """Configure line numberer for native PDF documents"""
        # Using base pipeline text line numbering with 0.3" gutter settings
        pass
    
    def process_document(self, source_path, output_path, file_sequential_number, bates_prefix, bates_start_number):
        """
        🔒 LOCKED METHOD - Process native PDF document using base pipeline integration
        DO NOT MODIFY - Complete native PDF processing workflow is FINAL
        
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
            
            # Step 2: Add line numbers using base pipeline text line numbering (0.3" gutter)
            temp_lined_path = pdf_path.with_suffix('.lined.pdf')
            start_line = 1
            line_success, final_line = self.add_text_line_numbers(
                str(pdf_path), str(temp_lined_path), start_line
            )
            
            if line_success:
                lines_added = final_line - start_line
                # Replace original with lined version
                shutil.move(str(temp_lined_path), str(pdf_path))
            else:
                lines_added = 0
                if temp_lined_path.exists():
                    temp_lined_path.unlink()
            
            # Step 3: Add bates numbers
            temp_bates_path = pdf_path.with_suffix('.bates.pdf')
            bates_success, next_bates = self.bates_numberer.add_bates_number(
                str(pdf_path), str(temp_bates_path), bates_prefix, bates_start_number
            )
            
            if bates_success:
                # Move to final location
                if Path(str(output_path)) != Path(str(temp_bates_path)):
                    shutil.move(str(temp_bates_path), str(output_path))
                
                # Clean up working files
                if pdf_path.exists():
                    pdf_path.unlink()
                
                return {
                    'success': True,
                    'lines_added': lines_added,
                    'bates_number': f"{bates_prefix}{bates_start_number:04d}",
                    'pipeline_type': self.get_pipeline_name(),
                    'final_path': str(output_path)
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