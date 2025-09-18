"""
Scan/Image Pipeline for processing scanned documents and image-based PDFs

UPDATED: Now using Universal 28-Line Grid Numbering System for all document types
This pipeline applies consistent 28-line grid numbering to all PDF documents.
"""
from pathlib import Path
import shutil
import fitz
from .base_pipeline import BasePipeline


class ScanImagePipeline(BasePipeline):
    """Pipeline for processing scanned documents and image-based PDFs with universal 28-line grid numbering"""

    def __init__(self, line_numberer, bates_numberer, logger_manager=None, universal_line_numberer=None):
        # Use universal line numbering system for consistent 28-line grid
        super().__init__(line_numberer, bates_numberer, logger_manager)
        self.universal_line_numberer = universal_line_numberer

    def get_pipeline_type(self):
        return "ScanImage"

    def get_pipeline_name(self):
        return "Scan/Image"

    def configure_line_numberer(self):
        """Configure line numberer for scanned/image documents"""
        # Using universal 28-line grid numbering system
        pass

    # =========================
    # PUBLIC: Line numbering
    # =========================
    def add_scan_image_line_numbers(self, input_path, output_path, start_line=1):
        """
        Add universal 28-line grid numbers to a PDF that is already rotation-normalized.
        Uses the universal line numbering system for consistency across all document types.

        Args:
            input_path (str): Path to input PDF (rotation already cleared)
            output_path (str): Path to output PDF
            start_line (int): Starting line number (ignored in universal system)

        Returns:
            tuple: (success, final_line_number)
        """
        try:
            # Use universal line numbering system if available
            if self.universal_line_numberer:
                success = self.universal_line_numberer.add_universal_line_numbers(
                    Path(input_path), Path(output_path)
                )
                return success, 28  # Universal system always uses 28 lines per page
            else:
                # Fallback to original method if universal line numberer not available
                return self._add_scan_image_line_numbers_fallback(input_path, output_path, start_line)

        except Exception as e:
            if self.logger_manager:
                self.logger_manager.log(f"Scan/Image line numbering failed: {e}")
            return False, start_line

    def _add_scan_image_line_numbers_fallback(self, input_path, output_path, start_line=1):
        """Fallback method using original scan/image line numbering logic"""
        try:
            src = fitz.open(input_path)
            dst = fitz.open()
            current_line = start_line

            gutter_width = 18  # ~0.25" at 72 dpi PDF space
            target_lines = 28  # Standard line count for legal docs

            for pno, page in enumerate(src):
                # page.rect reflects page rotation; our normalized input has rotation=0
                rect = page.rect  # width & height in points

                # Create a new page with extra gutter on the left
                new_w = rect.width + gutter_width
                new_h = rect.height
                new_page = dst.new_page(width=new_w, height=new_h)

                # Place original page content shifted to the right
                shifted_rect = fitz.Rect(gutter_width, 0, new_w, new_h)
                # Copy page content without rasterizing:
                new_page.show_pdf_page(shifted_rect, src, pno)  # keeps appearance & quality

                # Draw gutter AFTER placing content (so it doesn't get overwritten)
                # Create a white rectangle for the gutter
                gutter_rect = fitz.Rect(0, 0, gutter_width, new_h)
                new_page.draw_rect(gutter_rect, color=(1, 1, 1), fill=(1, 1, 1))

                # Add a vertical line to separate gutter from content
                line_start = fitz.Point(gutter_width, 0)
                line_end = fitz.Point(gutter_width, new_h)
                new_page.draw_line(line_start, line_end, color=(0, 0, 0), width=1)

                # Add line numbers down the gutter
                page_height = new_h
                line_spacing = page_height / (target_lines + 1)
                settings = self.text_line_settings

                lines_added = 0
                for i in range(target_lines):
                    line_number = current_line + i
                    y = (i + 1) * line_spacing
                    # Center x-position within the gutter using your helper
                    x = self._calculate_centered_x_position(line_number, settings)
                    try:
                        new_page.insert_text(
                            (x, y),
                            str(line_number),
                            fontsize=settings["number_font_size"],
                            color=settings["number_color"],
                            fontname=settings["font_family"],
                            rotate=0,  # Always upright in gutter
                        )
                        lines_added += 1
                    except Exception:
                        # Keep going even if one draw fails
                        pass

                current_line += lines_added

            dst.save(output_path, garbage=4, deflate=True)
            src.close()
            dst.close()
            return True, current_line

        except Exception as e:
            if self.logger_manager:
                self.logger_manager.log(f"Scan/Image line numbering fallback failed: {e}")
            return False, start_line

    # =========================
    # PUBLIC: Main processing
    # =========================
    def process_document(
        self,
        source_path,
        output_path,
        file_sequential_number,
        bates_prefix,
        bates_start_number,
    ):
        """
        Process scanned/image-based document

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
            # 1) Copy source to a working location
            pdf_path = output_path.with_suffix(".working.pdf")
            shutil.copy2(str(source_path), str(pdf_path))

            # 2) Normalize rotation *losslessly* (no rasterization)
            temp_cleared_path = pdf_path.with_suffix(".cleared.pdf")
            rotation_cleared = self._clear_rotation_and_assess_orientation(
                str(pdf_path), str(temp_cleared_path)
            )
            if not rotation_cleared:
                if temp_cleared_path.exists():
                    temp_cleared_path.unlink()
                if pdf_path.exists():
                    pdf_path.unlink()
                return {
                    "success": False,
                    "error": "Failed to clear rotation metadata",
                    "lines_added": 0,
                    "pipeline_type": self.get_pipeline_name(),
                }

            # 3) Move normalized file into place
            shutil.move(str(temp_cleared_path), str(pdf_path))
            # Cleared rotation metadata

            # 4) Add line numbers using universal line numbering system
            if self.universal_line_numberer:
                # Use universal line numbering to add line numbers with true gutter
                line_success = self.universal_line_numberer.add_universal_line_numbers(
                    pdf_path, pdf_path
                )
                lines_added = 28  # Universal system always adds 28 lines per page
            else:
                # Fallback to old line numbering method
                temp_lined_path = pdf_path.with_suffix(".lined.pdf")
                start_line = 1
                line_success, final_line = self.add_scan_image_line_numbers(
                    str(pdf_path), str(temp_lined_path), start_line
                )
                if line_success:
                    lines_added = final_line - start_line
                    shutil.move(str(temp_lined_path), str(pdf_path))
                else:
                    lines_added = 0
                    if temp_lined_path.exists():
                        temp_lined_path.unlink()

            # 5) Add Bates numbers and filename using universal line numbering system
            if self.universal_line_numberer:
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
                # Fallback to old bates numbering if universal line numberer not available
                temp_bates_path = pdf_path.with_suffix(".bates.pdf")
                bates_success, next_bates = self.bates_numberer.add_bates_number(
                    str(pdf_path), str(temp_bates_path), bates_prefix, bates_start_number
                )

                if bates_success:
                    # Move to final location
                    if Path(str(output_path)) != Path(str(temp_bates_path)):
                        shutil.move(str(temp_bates_path), str(output_path))

                    return {
                        'success': True,
                        'lines_added': lines_added,
                        'bates_number': f"{bates_prefix}{bates_start_number:04d}",
                        'next_bates': next_bates,
                        'pipeline_type': self.get_pipeline_name()
                    }
                else:
                    if temp_bates_path.exists():
                        temp_bates_path.unlink()
                    if pdf_path.exists():
                        pdf_path.unlink()
                    return {
                        "success": False,
                        "error": "Bates numbering failed",
                        "lines_added": lines_added,
                        "pipeline_type": self.get_pipeline_name(),
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "lines_added": 0,
                "pipeline_type": self.get_pipeline_name(),
            }

    # =========================
    # INTERNAL: Rotation helper
    # =========================
    def _clear_rotation_and_assess_orientation(self, input_path, output_path):
        """
        Print PDF to PDF to strip all metadata and normalize content
        This is the most reliable way to handle rotation issues
        """
        try:
            src = fitz.open(input_path)
            dst = fitz.open()

            for pno, page in enumerate(src):
                # Get the page as it appears (with rotation applied)
                pix = page.get_pixmap()
                
                # Create new page with the pixmap dimensions
                new_page = dst.new_page(width=pix.width, height=pix.height)
                
                # Insert the pixmap as an image - this strips all metadata
                new_page.insert_image(new_page.rect, pixmap=pix)

            dst.save(output_path, garbage=4, deflate=True)
            src.close()
            dst.close()
            return True

        except Exception as e:
            if self.logger_manager:
                pass
                # PDF printing failed
            return False


    # (Optional legacy helpers kept for compatibility / reference)
    def _physically_rotate_document(self, input_path, output_path, rotation_angle):
        """Deprecated in favor of _clear_rotation_and_assess_orientation (lossless)."""
        try:
            if rotation_angle not in (0, 90, 180, 270):
                rotation_angle = 0
            src = fitz.open(input_path)
            dst = fitz.open()
            for pno, page in enumerate(src):
                rect = page.rect
                # Swap width/height for 90/270
                if rotation_angle in (90, 270):
                    rect = fitz.Rect(0, 0, rect.height, rect.width)
                new_page = dst.new_page(width=rect.width, height=rect.height)
                new_page.show_pdf_page(new_page.rect, src, pno, rotate=rotation_angle)
            dst.save(output_path, garbage=4, deflate=True)
            src.close()
            dst.close()
            return True
        except Exception as e:
            if self.logger_manager:
                self.logger_manager.log(f"Physical rotation failed: {e}")
            return False
