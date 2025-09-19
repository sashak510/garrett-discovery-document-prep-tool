"""
Scan/Image Pipeline for processing scanned documents and image-based PDFs

UPDATED: Now using Universal 28-Line Grid Numbering System for all document types
This pipeline applies consistent 28-line grid numbering to all PDF documents.
"""
from pathlib import Path
import shutil
import os
import fitz
from .base_pipeline import BasePipeline


class ScanImagePipeline(BasePipeline):
    """Pipeline for processing scanned documents and image-based PDFs with universal 28-line grid numbering"""

    def __init__(self, bates_numberer, logger_manager=None, universal_line_numberer=None):
        # Use universal line numbering system for consistent 28-line grid
        super().__init__(bates_numberer, logger_manager)
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
            # Use vector line numbering system if available
            if self.universal_line_numberer:
                success = self.universal_line_numberer.add_line_numbers_to_pdf(
                    str(input_path), str(output_path)
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
                # page.rect reflects current page dimensions (orientation already corrected)
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
            # 1) Copy source to a working location with rotation correction
            pdf_path = output_path.with_suffix(".working.pdf")

            # Apply rotation correction using line numbering system's orientation logic
            rotation_applied = self._correct_scanimage_rotation(str(source_path), str(pdf_path))

            # 1.5) Scale down large documents to improve line number visibility
            scaled_path = pdf_path.with_suffix(".scaled.pdf")
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

            # 2) Add line numbers using universal line numbering system
            if self.universal_line_numberer:
                # Use universal line numbering to add line numbers with true gutter
                temp_lined_path = pdf_path.with_suffix(".lined.pdf")
                line_success = self.universal_line_numberer.add_line_numbers_to_pdf(
                    str(pdf_path), str(temp_lined_path)
                )
                if line_success:
                    shutil.move(str(temp_lined_path), str(pdf_path))
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

            # 4) Add Bates numbers and filename using universal line numbering system
            if self.universal_line_numberer:
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

                # Step 5: Normalize PDF orientation to fix rotation issues
                # This flattens all content including annotations and applies rotation properly
                normalized_path = output_path.with_suffix('.normalized.pdf')
                if self.universal_line_numberer and hasattr(self.universal_line_numberer, 'normalize_pdf_orientation'):
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

                    # Step 5: Normalize PDF orientation to fix rotation issues
                    # This flattens all content including annotations and applies rotation properly
                    normalized_path = output_path.with_suffix('.normalized.pdf')
                    if self.universal_line_numberer and hasattr(self.universal_line_numberer, 'normalize_pdf_orientation'):
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
    def _set_rotation_to_zero(self, input_pdf_path: str, output_pdf_path: str):
        """
        Set all page rotations to 0

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF with rotation set to 0
        """
        try:
            self.log(f"🔄 Setting rotation to 0 for ScanImage PDF")
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
            self.log(f"   Saving ScanImage PDF with rotation set to 0: {output_pdf_path}")
            doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
            doc.close()

            # Verify output file was created
            if os.path.exists(output_pdf_path):
                file_size = os.path.getsize(output_pdf_path)
                self.log(f"✅ ScanImage PDF rotation set to 0 successfully ({file_size} bytes)")
            else:
                raise RuntimeError(f"Output PDF was not created: {output_pdf_path}")

        except Exception as e:
            self.log(f"❌ Failed to set ScanImage PDF rotation to 0: {e}")
            import traceback
            self.log(f"❌ Traceback: {traceback.format_exc()}")
            raise

    def _correct_scanimage_rotation(self, input_pdf_path: str, output_pdf_path: str) -> bool:
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
                shutil.copy2(input_pdf_path, output_pdf_path)
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
                self.log(f"🔄 Setting rotation to 0 for ScanImage PDF: {input_pdf_path}")
                self._set_rotation_to_zero(input_pdf_path, output_pdf_path)
                return True  # Rotation applied
            else:
                # No rotation needed
                self.log(f"✅ ScanImage PDF orientation is correct, no rotation needed")
                # Just copy the original file
                shutil.copy2(input_pdf_path, output_pdf_path)
                return False  # No rotation applied

        except Exception as e:
            self.log(f"⚠️  ScanImage rotation correction failed: {e} - using original")
            # Fallback: copy original file
            try:
                shutil.copy2(input_pdf_path, output_pdf_path)
            except:
                pass
            return False
