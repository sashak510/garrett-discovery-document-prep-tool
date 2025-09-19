"""
PDF Orientation Detection and Correction Module

Handles intelligent orientation detection for PDF documents using:
1. PyMuPDF metadata analysis for native PDFs
2. OCR-based fallback for scanned/metadata-less PDFs
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import tempfile
import os
import shutil
import config
from PIL import Image
import pytesseract
import io


class PDFOrientationDetector:
    """
    Advanced PDF orientation detection and correction system.

    Uses multiple strategies to determine correct document orientation:
    1. PyMuPDF page analysis for native PDFs
    2. OCR text analysis as fallback for scanned documents
    """

    def __init__(self, log_callback=None):
        """
        Initialize the orientation detector

        Args:
            log_callback: Optional callback function for logging messages
        """
        self.log_callback = log_callback

    def log(self, message: str):
        """Log a message using the callback or print"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def detect_and_correct_orientation(self, input_pdf_path: str, output_pdf_path: str) -> bool:
        """
        Detect and correct PDF orientation using advanced methods

        Args:
            input_pdf_path: Path to input PDF file
            output_pdf_path: Path for output PDF file with corrected orientation

        Returns:
            bool: True if orientation correction was applied, False if no correction needed
        """
        try:
            self.log(f"🔍 Starting advanced orientation detection for: {Path(input_pdf_path).name}")

            # First, try PyMuPDF-based detection for native PDFs
            correction_applied = self._try_pymupdf_detection(input_pdf_path, output_pdf_path)

            if correction_applied:
                self.log(f"✅ PyMuPDF orientation correction applied")
                return True

            # If PyMuPDF detection failed, try OCR-based detection
            self.log(f"⚠️  PyMuPDF detection failed, trying OCR-based detection")
            correction_applied = self._try_ocr_detection(input_pdf_path, output_pdf_path)

            if correction_applied:
                self.log(f"✅ OCR-based orientation correction applied")
                return True

            # If both methods failed, just copy the original
            self.log(f"ℹ️  No orientation correction needed, using original")
            shutil.copy2(input_pdf_path, output_pdf_path)
            return False

        except Exception as e:
            self.log(f"❌ Orientation detection failed: {str(e)}")
            # Fallback: copy original file
            try:
                shutil.copy2(input_pdf_path, output_pdf_path)
            except:
                pass
            return False

    def _try_pymupdf_detection(self, input_pdf_path: str, output_pdf_path: str) -> bool:
        """
        Try to detect orientation using PyMuPDF page analysis

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF

        Returns:
            bool: True if correction was applied, False otherwise
        """
        try:
            doc = fitz.open(input_pdf_path)
            if len(doc) == 0:
                doc.close()
                return False

            # Analyze each page to determine if rotation is needed
            corrections_needed = []

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get page dimensions
                page_rect = page.rect
                width = page_rect.width
                height = page_rect.height

                # Check if page is likely landscape (wider than tall)
                is_landscape = width > height

                # Get current rotation
                current_rotation = page.rotation

                self.log(f"   Page {page_num + 1}: {width:.0f}x{height:.0f}, rotation: {current_rotation}°, landscape: {is_landscape}")

                # For native PDFs, we need to analyze text content to determine correct orientation
                suggested_rotation = self._analyze_page_text_orientation(page)

                if suggested_rotation != current_rotation:
                    corrections_needed.append((page_num, suggested_rotation))
                    self.log(f"   → Page {page_num + 1}: needs rotation from {current_rotation}° to {suggested_rotation}°")

            doc.close()

            # Apply corrections if needed
            if corrections_needed:
                self.log(f"📝 Applying {len(corrections_needed)} orientation corrections using PyMuPDF")
                return self._apply_pymupdf_corrections(input_pdf_path, output_pdf_path, corrections_needed)

            return False

        except Exception as e:
            self.log(f"   PyMuPDF detection failed: {str(e)}")
            return False

    def _analyze_page_text_orientation(self, page) -> int:
        """
        Analyze text content to determine correct orientation
        More conservative approach - only correct obvious issues

        Args:
            page: PyMuPDF page object

        Returns:
            int: Suggested rotation angle (0, 90, 180, 270)
        """
        try:
            # First, check if there's already a rotation set
            current_rotation = page.rotation
            if current_rotation == 0:
                # If no rotation is set, assume it's correct
                return 0

            # Only analyze if there's a non-zero rotation
            # Extract text blocks from the page
            text_blocks = page.get_text("blocks")

            if not text_blocks:
                # No text found, can't determine orientation - keep current
                return current_rotation

            # Analyze text block positions and orientations
            text_data = []
            for block in text_blocks:
                if len(block) >= 6:  # Ensure block has enough data
                    x0, y0, x1, y1, text, block_no, block_type = block[:7]
                    if text.strip():  # Only consider non-empty text
                        text_data.append({
                            'text': text,
                            'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                            'width': x1 - x0,
                            'height': y1 - y0
                        })

            if not text_data:
                return current_rotation

            # Use more conservative heuristics
            return self._determine_orientation_conservative(text_data, page.rect, current_rotation)

        except Exception as e:
            self.log(f"      Text analysis failed: {str(e)}")
            return page.rotation

    def _determine_orientation_conservative(self, text_data: list, page_rect, current_rotation: int) -> int:
        """
        More conservative orientation determination - only correct obvious issues

        Args:
            text_data: List of text block data
            page_rect: Page rectangle dimensions
            current_rotation: Current rotation setting

        Returns:
            int: Suggested rotation angle
        """
        try:
            # If current rotation is 0, keep it
            if current_rotation == 0:
                return 0

            page_width = page_rect.width
            page_height = page_rect.height

            # Count text directions
            horizontal_text = 0
            vertical_text = 0

            for block in text_data:
                # If text block is wider than tall, it's likely horizontal
                if block['width'] > block['height']:
                    horizontal_text += 1
                else:
                    vertical_text += 1

            total_blocks = len(text_data)
            horizontal_ratio = horizontal_text / total_blocks if total_blocks > 0 else 0

            # Only correct if we have high confidence
            # Most text should be horizontal for normal documents
            if horizontal_ratio < 0.7:  # Less than 70% horizontal text
                # This might indicate a rotation issue
                # But only correct if we're very confident

                # Check if current rotation is causing issues
                if current_rotation in [90, 270]:
                    # For 90° or 270° rotation, most text should be vertical
                    # If we have mostly horizontal text, it's probably wrong
                    if horizontal_ratio > 0.7:
                        self.log(f"   Conservative correction: 90° rotation with {horizontal_ratio:.1f} horizontal text - setting to 0°")
                        return 0

                elif current_rotation == 180:
                    # 180° rotation is rarely needed for normal documents
                    # Only correct if we have very high confidence
                    if horizontal_ratio > 0.9:
                        self.log(f"   Conservative correction: 180° rotation with {horizontal_ratio:.1f} horizontal text - setting to 0°")
                        return 0

            # Default: keep current rotation
            return current_rotation

        except Exception as e:
            self.log(f"      Conservative orientation determination failed: {str(e)}")
            return current_rotation

    def _determine_orientation_from_text_layout(self, text_data: list, page_rect) -> int:
        """
        Legacy orientation determination (less conservative)
        """
        try:
            page_width = page_rect.width
            page_height = page_rect.height

            # Calculate text distribution metrics
            total_text_width = sum(block['width'] for block in text_data)
            total_text_height = sum(block['height'] for block in text_data)

            # Calculate average text line direction
            horizontal_text = 0
            vertical_text = 0

            for block in text_data:
                # If text block is wider than tall, it's likely horizontal
                if block['width'] > block['height']:
                    horizontal_text += 1
                else:
                    vertical_text += 1

            # Determine if document should be portrait or landscape
            # Most documents should be portrait-oriented
            should_be_landscape = False

            # Heuristic: if most text is vertical and page is landscape, might need rotation
            if vertical_text > horizontal_text and page_width > page_height:
                # Landscape page with mostly vertical text - likely needs 90° rotation
                return 90

            # Heuristic: if text spans suggest landscape document
            max_text_width = max(block['width'] for block in text_data)
            if max_text_width > page_width * 0.8:  # Text spans most of width
                if page_height > page_width:  # But page is portrait
                    return 90  # Rotate to landscape

            # Default: no rotation needed
            return 0

        except Exception as e:
            self.log(f"      Orientation determination failed: {str(e)}")
            return 0

    def _apply_pymupdf_corrections(self, input_pdf_path: str, output_pdf_path: str, corrections: list) -> bool:
        """
        Apply rotation corrections using PyMuPDF

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF
            corrections: List of (page_num, rotation) tuples

        Returns:
            bool: True if successful
        """
        try:
            doc = fitz.open(input_pdf_path)

            for page_num, rotation in corrections:
                page = doc[page_num]
                page.set_rotation(rotation)
                self.log(f"   Page {page_num + 1}: set rotation to {rotation}°")

            doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
            doc.close()

            self.log(f"✅ PyMuPDF corrections applied successfully")
            return True

        except Exception as e:
            self.log(f"   PyMuPDF correction failed: {str(e)}")
            return False

    def _try_ocr_detection(self, input_pdf_path: str, output_pdf_path: str) -> bool:
        """
        Try to detect orientation using OCR analysis (conservative approach)

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF

        Returns:
            bool: True if correction was applied, False otherwise
        """
        try:
            # Only use OCR as a last resort, and be very conservative
            doc = fitz.open(input_pdf_path)

            # Check if there's already a rotation set
            has_rotation = any(page.rotation != 0 for page in doc)
            doc.close()

            if not has_rotation:
                # If no rotation is set, assume it's correct
                self.log(f"   No rotation metadata found, assuming document is correctly oriented")
                return False

            # Only proceed with OCR if there's a rotation that might be wrong
            self.log(f"   Rotation metadata found, using conservative OCR analysis")

            # Analyze first page only for speed
            doc = fitz.open(input_pdf_path)
            page = doc[0]

            # Render page at lower resolution for faster processing
            pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Test current orientation (0°) first
            current_confidence = 0
            try:
                current_text = pytesseract.image_to_string(img)
                current_confidence = self._calculate_text_confidence(current_text)
                self.log(f"   Current orientation (0°): confidence {current_confidence:.2f}")
            except Exception as e:
                self.log(f"   OCR failed for current orientation: {str(e)}")

            # Only test other orientations if current confidence is low
            if current_confidence < 0.3:  # Low confidence threshold
                orientation_scores = {0: current_confidence}

                # Test other orientations
                for rotation in [90, 180, 270]:
                    try:
                        rotated_img = img.rotate(rotation, expand=True)
                        text = pytesseract.image_to_string(rotated_img)
                        confidence_score = self._calculate_text_confidence(text)
                        orientation_scores[rotation] = confidence_score
                        self.log(f"   Orientation {rotation}°: confidence {confidence_score:.2f}")
                    except Exception as e:
                        self.log(f"      OCR failed for {rotation}° rotation: {str(e)}")
                        continue

                # Find the best orientation
                best_rotation = max(orientation_scores, key=orientation_scores.get)
                best_confidence = orientation_scores[best_rotation]

                # Only apply correction if we're very confident and it's different from current
                confidence_threshold = 0.5  # High threshold
                if best_confidence > confidence_threshold and best_rotation != 0:
                    if best_confidence > current_confidence * 1.5:  # Significant improvement
                        self.log(f"   Conservative OCR correction: {best_rotation}° (confidence: {best_confidence:.2f} vs current {current_confidence:.2f})")
                        doc.close()
                        return self._apply_rotation_correction(input_pdf_path, output_pdf_path, best_rotation)

            doc.close()
            self.log(f"   OCR analysis: no correction needed (current confidence: {current_confidence:.2f})")
            return False

        except Exception as e:
            self.log(f"   OCR detection failed: {str(e)}")
            return False

    def _calculate_text_confidence(self, text: str) -> float:
        """
        Calculate confidence score for extracted text

        Args:
            text: Extracted text from OCR

        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        try:
            if not text or len(text.strip()) == 0:
                return 0.0

            # Calculate various confidence metrics
            confidence = 0.0

            # 1. Text length (more text = higher confidence)
            text_length = len(text.strip())
            confidence += min(text_length / 1000, 0.3)  # Max 0.3 for length

            # 2. Word count
            words = text.split()
            word_count = len(words)
            confidence += min(word_count / 200, 0.3)  # Max 0.3 for word count

            # 3. Character distribution (ratio of alphanumeric to total)
            alnum_chars = sum(c.isalnum() or c.isspace() for c in text)
            if len(text) > 0:
                char_ratio = alnum_chars / len(text)
                confidence += char_ratio * 0.2  # Max 0.2 for character quality

            # 4. Line structure (presence of line breaks suggests structure)
            line_count = text.count('\n') + 1
            if line_count > 1:
                confidence += min(line_count / 50, 0.2)  # Max 0.2 for line structure

            return min(confidence, 1.0)

        except Exception:
            return 0.0

    def _apply_rotation_correction(self, input_pdf_path: str, output_pdf_path: str, rotation: int) -> bool:
        """
        Apply rotation correction to PDF

        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path for output PDF
            rotation: Rotation angle to apply

        Returns:
            bool: True if successful
        """
        try:
            doc = fitz.open(input_pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                current_rotation = page.rotation
                new_rotation = (current_rotation + rotation) % 360
                page.set_rotation(new_rotation)

                if page_num < 3:  # Log first 3 pages
                    self.log(f"   Page {page_num + 1}: rotation {current_rotation}° → {new_rotation}°")

            doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
            doc.close()

            self.log(f"✅ Applied {rotation}° rotation correction")
            return True

        except Exception as e:
            self.log(f"   Rotation correction failed: {str(e)}")
            return False

    def get_orientation_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get orientation information for a PDF file

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict: Orientation information
        """
        try:
            doc = fitz.open(pdf_path)
            info = {
                'total_pages': len(doc),
                'pages': []
            }

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_rect = page.rect
                info['pages'].append({
                    'page_number': page_num + 1,
                    'width': page_rect.width,
                    'height': page_rect.height,
                    'rotation': page.rotation,
                    'is_landscape': page_rect.width > page_rect.height
                })

            doc.close()
            return info

        except Exception as e:
            self.log(f"❌ Failed to get orientation info: {str(e)}")
            return {'error': str(e)}