"""
Text Pipeline for processing Word and Text documents using complete v1 approach
All v1 text processing components integrated directly into this pipeline
SELF-CONTAINED: All text/word processing logic is contained within this pipeline

🔒 LOCKED COMPONENT - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
This file contains FINAL text and word processing logic that is RINGFENCED.
All text extraction, PDF conversion, and document processing workflows are COMPLETE.
Modifying this file will break the self-contained text pipeline architecture.

LAST MODIFIED: Text pipeline consolidation and line numbering integration completed
STATUS: LOCKED BY USER - Requires explicit authorization for any changes
"""
from pathlib import Path
import shutil
import tempfile
from datetime import datetime

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
except ImportError:
    canvas = None
    SimpleDocTemplate = None
    Paragraph = None

from .base_pipeline import BasePipeline

class TextPipeline(BasePipeline):
    """Complete v1-derived text processing pipeline using base pipeline line numbering"""
    
    def __init__(self, line_numberer, bates_numberer, logger_manager=None):
        super().__init__(line_numberer, bates_numberer, logger_manager)
        self.conversion_errors = []
    
    def get_pipeline_type(self):
        return "Text"
    
    def get_pipeline_name(self):
        return "Text-based (Word/Text) - Complete v1"
    
    def configure_line_numberer(self):
        """Configure text-specific line numbering settings"""
        # Settings are already configured in __init__
        pass
    
    def log(self, message):
        """Log a message using the logger manager or print"""
        if hasattr(self.logger_manager, 'log'):
            self.logger_manager.log(message)
        else:
            print(f"[TextPipeline] {message}")
    
    def process_document(self, source_path, output_path, file_sequential_number, bates_prefix, bates_start_number):
        """
        🔒 LOCKED METHOD - Process text-based document (Word/Text) using complete v1 approach
        DO NOT MODIFY - Complete text/word processing workflow is FINAL
        
        Args:
            source_path (Path): Input file path
            output_path (Path): Output file path  
            file_sequential_number (str): Sequential file number
            bates_prefix (str): Bates number prefix
            bates_start_number (int): Bates starting number
            
        Returns:
            dict: Processing results
        """
        try:
            # Generate bates number for filename
            bates_str = f"{bates_prefix}{bates_start_number:04d}"
            
            # Clean filename for output
            original_stem = source_path.stem
            if '-' in original_stem:
                parts = original_stem.split('-', 1)
                if parts[0].isdigit():
                    clean_stem = parts[1]
                else:
                    clean_stem = original_stem
            else:
                clean_stem = original_stem
            
            # Use v1 approach: extract content → convert to PDF → add bates numbers (no line numbers)
            temp_pdf_path = output_path.with_suffix('.temp.pdf')
            
            if source_path.suffix.lower() in ['.docx', '.doc']:
                # V1 Word processing
                success, content = self._extract_word_text(source_path)
                if not success:
                    return {
                        'success': False,
                        'error': f'Word extraction failed: {content}',
                        'lines_added': 0,
                        'pipeline_type': self.get_pipeline_name()
                    }
                
                # Convert formatted Word content to PDF
                success = self._convert_formatted_content_to_pdf(content, temp_pdf_path)
                conversion_type = "Word (v1 formatted)"
                
            elif source_path.suffix.lower() == '.txt':
                # V1 text processing
                success, content = self._extract_text_content(source_path)
                if not success:
                    return {
                        'success': False,
                        'error': f'Text extraction failed: {content}',
                        'lines_added': 0,
                        'pipeline_type': self.get_pipeline_name()
                    }
                
                # Convert text content to PDF
                success = self._convert_clean_text_to_pdf(content, temp_pdf_path)
                conversion_type = "Text (v1 clean)"
                
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {source_path.suffix}',
                    'lines_added': 0,
                    'pipeline_type': self.get_pipeline_name()
                }
            
            if not success:
                return {
                    'success': False,
                    'error': f'{conversion_type} conversion failed',
                    'lines_added': 0,
                    'pipeline_type': self.get_pipeline_name()
                }
            
            # Add line numbers using base pipeline's text line numbering method
            lined_pdf_path = output_path.with_suffix('.lined.pdf')
            start_line = 1
            line_success, final_line = self.add_text_line_numbers(
                str(temp_pdf_path), str(lined_pdf_path), start_line
            )
            
            if line_success:
                lines_added = final_line - start_line
                # Replace original with lined version
                shutil.move(str(lined_pdf_path), str(temp_pdf_path))
            else:
                lines_added = 0
                if lined_pdf_path.exists():
                    lined_pdf_path.unlink()
            
            # Add bates numbers
            bates_success, next_bates = self.bates_numberer.add_bates_number(
                str(temp_pdf_path), str(output_path), bates_prefix, bates_start_number
            )
            
            # Clean up temporary files
            if temp_pdf_path.exists():
                temp_pdf_path.unlink()
            
            if bates_success:
                return {
                    'success': True,
                    'lines_added': lines_added,  # Line numbers added by text line numberer
                    'bates_number': bates_str,
                    'pipeline_type': self.get_pipeline_name(),
                    'final_path': str(output_path),
                    'conversion_type': conversion_type
                }
            else:
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
    
    # ========== V1 TEXT PROCESSING METHODS (Copied directly from v1) ==========
    
    def _extract_word_text(self, word_path):
        """Extract text content with formatting from Word document (V1 method)"""
        try:
            if not Document:
                return False, "python-docx not available"
                
            doc = Document(word_path)
            formatted_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    # Extract paragraph with formatting metadata
                    para_info = {
                        'text': paragraph.text,
                        'style': paragraph.style.name if paragraph.style else 'Normal',
                        'runs': []
                    }
                    
                    # Extract run-level formatting (bold, italic, underline)
                    for run in paragraph.runs:
                        if run.text.strip():
                            run_info = {
                                'text': run.text,
                                'bold': run.bold if run.bold is not None else False,
                                'italic': run.italic if run.italic is not None else False,
                                'underline': run.underline if run.underline is not None else False,
                                'font_size': run.font.size.pt if run.font.size else None
                            }
                            para_info['runs'].append(run_info)
                    
                    formatted_content.append(para_info)
                else:
                    # Preserve empty paragraphs
                    formatted_content.append({'text': '', 'style': 'Normal', 'runs': []})
            
            return True, formatted_content
            
        except Exception as e:
            return False, f"Word extraction error: {str(e)}"
    
    def _extract_text_content(self, text_path):
        """Extract text content from text file (V1 method)"""
        try:
            with open(text_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return True, content
            
        except Exception as e:
            return False, f"Text extraction error: {str(e)}"
    
    def _convert_formatted_content_to_pdf(self, formatted_content, pdf_path):
        """Convert Word content with formatting to PDF preserving styles (Enhanced V1 method)"""
        try:
            if not SimpleDocTemplate or not Paragraph:
                self.log("ReportLab not available for formatted conversion")
                return False
                
            # Handle empty content
            if not formatted_content:
                doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
                styles = getSampleStyleSheet()
                story = [Paragraph("[Empty Document]", styles['Normal'])]
                doc.build(story)
                return True
                
            # Create PDF with formatting preservation
            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                                    topMargin=inch, bottomMargin=inch,
                                    leftMargin=inch, rightMargin=inch)
            styles = getSampleStyleSheet()
            story = []
            
            for para_info in formatted_content:
                style_name = para_info['style']
                
                # Map Word styles to ReportLab styles
                if 'Heading 1' in style_name:
                    style = styles['Heading1']
                elif 'Heading 2' in style_name:
                    style = styles['Heading2']
                elif 'Heading 3' in style_name:
                    style = styles['Heading3']
                elif 'Title' in style_name:
                    style = styles['Title']
                else:
                    style = styles['Normal']
                
                # Build formatted text with runs
                if para_info['runs']:
                    # Construct paragraph with inline formatting
                    formatted_text = ""
                    for run in para_info['runs']:
                        run_text = run['text']
                        
                        # Apply formatting tags
                        if run['bold']:
                            run_text = f"<b>{run_text}</b>"
                        if run['italic']:
                            run_text = f"<i>{run_text}</i>"
                        if run['underline']:
                            run_text = f"<u>{run_text}</u>"
                            
                        formatted_text += run_text
                        
                    para = Paragraph(formatted_text, style)
                else:
                    # Fallback to plain text
                    para = Paragraph(para_info['text'], style)
                    
                story.append(para)
                story.append(Spacer(1, 6))  # Small space between paragraphs
                    
            doc.build(story)
            return True
            
        except Exception as e:
            self.log(f"Formatted content to PDF conversion error: {str(e)}")
            return False
    
    def _convert_clean_text_to_pdf(self, content, pdf_path):
        """Convert clean text to PDF preserving formatting (Enhanced V1 method)"""
        try:
            if not SimpleDocTemplate or not Paragraph:
                self.log("ReportLab not available for text conversion")
                return False
                
            # Handle empty or whitespace-only content
            if not content or not content.strip():
                # Create a minimal PDF with just one line for empty documents
                doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
                styles = getSampleStyleSheet()
                story = [Paragraph("[Empty Document]", styles['Normal'])]
                doc.build(story)
                return True
                
            # Create PDF with better formatting preservation
            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                                    topMargin=inch, bottomMargin=inch,
                                    leftMargin=inch, rightMargin=inch)
            styles = getSampleStyleSheet()
            
            # Create a monospace style for better formatting preservation
            mono_style = ParagraphStyle(
                'MonoNormal',
                parent=styles['Normal'],
                fontName='Courier',  # Monospace font
                fontSize=10,
                leading=12,
                alignment=TA_LEFT,
                spaceAfter=0,
                spaceBefore=0
            )
            
            story = []
            lines = content.split('\n')
            
            for line in lines:
                if line.strip():
                    # Escape HTML characters and preserve spaces
                    escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    escaped_line = escaped_line.replace(' ', '&nbsp;')  # Preserve spaces
                    para = Paragraph(escaped_line, mono_style)
                    story.append(para)
                else:
                    # Add small spacer for empty lines
                    story.append(Spacer(1, 6))
                    
            doc.build(story)
            return True
            
        except Exception as e:
            self.log(f"Clean text to PDF conversion error: {str(e)}")
            return False
    
    # Text line numbering methods are now inherited from BasePipeline
    # This removes code duplication and keeps the pipeline clean