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

            # If both methods failed, try aggressive rotation correction for obvious issues
            self.log(f"⚠️  OCR detection failed, trying aggressive rotation correction")
            correction_applied = self._try_aggressive_correction(input_pdf_path, output_pdf_path)

            if correction_applied:
                self.log(f"✅ Aggressive rotation correction applied")
                return True

            # If all methods failed, just copy the original
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
        Enhanced approach - multiple text extraction methods for better compatibility

        Args:
            page: PyMuPDF page object

        Returns:
            int: Suggested rotation angle (0, 90, 180, 270)
        """
        try:
            current_rotation = page.rotation

            # ENHANCED: Try multiple text extraction methods
            text_data = self._extract_text_data_multiple_methods(page)

            if not text_data:
                # No text found, can't determine orientation - keep current
                self.log(f"      No text content found, keeping current rotation {current_rotation}°")
                return current_rotation

            # Use improved heuristics
            return self._determine_orientation_conservative(text_data, page.rect, current_rotation)

        except Exception as e:
            self.log(f"      Text analysis failed: {str(e)}")
            return page.rotation

    def _extract_text_data_multiple_methods(self, page):
        """
        Enhanced text extraction using multiple methods for better compatibility
        """
        text_data = []

        # Method 1: Dict extraction (most reliable for structured text)
        try:
            text_dict = page.get_text("dict")
            if text_dict and 'blocks' in text_dict:
                for block in text_dict['blocks']:
                    if 'lines' in block:
                        for line in block['lines']:
                            if 'spans' in line:
                                for span in line['spans']:
                                    if 'text' in span and span['text'].strip():
                                        x0, y0 = span['bbox'][0], span['bbox'][1]
                                        x1, y1 = span['bbox'][2], span['bbox'][3]
                                        text_data.append({
                                            'text': span['text'],
                                            'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                                            'width': x1 - x0,
                                            'height': y1 - y0
                                        })
        except Exception as e:
            self.log(f"      Dict extraction failed: {str(e)}")

        # Method 2: Raw text extraction with position analysis
        if not text_data:
            try:
                blocks = page.get_text("blocks")
                for block in blocks:
                    if len(block) >= 4:  # x0, y0, x1, y1, text, ...
                        x0, y0, x1, y1, text = block[:5]
                        if text.strip():
                            text_data.append({
                                'text': text,
                                'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                                'width': x1 - x0,
                                'height': y1 - y0
                            })
            except Exception as e:
                self.log(f"      Block extraction failed: {str(e)}")

        # Method 3: Simple text extraction as fallback
        if not text_data:
            try:
                text = page.get_text()
                if text.strip():
                    # For simple text, create a single block covering most of the page
                    page_rect = page.rect
                    text_data.append({
                        'text': text[:100],  # Limit text length
                        'x0': page_rect.x0 + 50,
                        'y0': page_rect.y0 + 50,
                        'x1': page_rect.x1 - 50,
                        'y1': page_rect.y1 - 50,
                        'width': page_rect.width - 100,
                        'height': page_rect.height - 100
                    })
            except Exception as e:
                self.log(f"      Simple extraction failed: {str(e)}")

        return text_data

    def _determine_orientation_conservative(self, text_data: list, page_rect, current_rotation: int) -> int:
        """
        Improved orientation determination - correct obvious rotation issues more aggressively

        Args:
            text_data: List of text block data
            page_rect: Page rectangle dimensions
            current_rotation: Current rotation setting

        Returns:
            int: Suggested rotation angle
        """
        try:
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
            if total_blocks == 0:
                return current_rotation

            horizontal_ratio = horizontal_text / total_blocks

            # Improved rotation logic based on text direction
            if current_rotation == 0:
                # If we have mostly vertical text but page is portrait, might need rotation
                if horizontal_ratio < 0.3 and page_width < page_height:
                    # Portrait page with mostly vertical text - likely needs 90° rotation
                    self.log(f"   Correction: 0° rotation with {horizontal_ratio:.1f} horizontal text - setting to 90°")
                    return 90

            elif current_rotation == 90:
                # If we have mostly horizontal text but page is portrait, likely wrong
                if horizontal_ratio > 0.7 and page_width < page_height:
                    # Portrait page with 90° rotation and mostly horizontal text - reset to 0°
                    self.log(f"   Correction: 90° rotation with {horizontal_ratio:.1f} horizontal text - setting to 0°")
                    return 0

            elif current_rotation == 180:
                # 180° rotation is rarely correct for normal documents
                # If we have reasonable text layout, reset to 0°
                if horizontal_ratio > 0.4:  # More reasonable threshold
                    self.log(f"   Correction: 180° rotation with {horizontal_ratio:.1f} horizontal text - setting to 0°")
                    return 0

            elif current_rotation == 270:
                # Similar to 90° logic but for 270° rotation
                if horizontal_ratio > 0.7 and page_width < page_height:
                    # Portrait page with 270° rotation and mostly horizontal text - reset to 0°
                    self.log(f"   Correction: 270° rotation with {horizontal_ratio:.1f} horizontal text - setting to 0°")
                    return 0

            # Default: keep current rotation if no obvious correction needed
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

            # Test other orientations if current confidence is moderate or low
            if current_confidence < 0.7:  # Moderate confidence threshold
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

                # Apply correction if we have reasonable confidence, but prefer 0° rotation for consistency
                confidence_threshold = 0.3  # Lower threshold for OCR-based correction

                # Always prefer 0° rotation if it has reasonable confidence
                if orientation_scores.get(0, 0) > confidence_threshold:
                    # 0° rotation has reasonable confidence - use it
                    if orientation_scores[0] > current_confidence * 1.1:  # Only need slight improvement
                        self.log(f"   Conservative OCR correction: 0° rotation (preferred orientation)")
                        doc.close()
                        return self._apply_rotation_correction(input_pdf_path, output_pdf_path, 0)
                    else:
                        self.log(f"   No OCR correction: 0° rotation confidence similar to current")
                elif best_confidence > confidence_threshold and best_rotation != 0:
                    # Only use non-zero rotation if 0° confidence is very low
                    if best_confidence > current_confidence * 1.5:  # Require significant improvement
                        self.log(f"   Conservative OCR correction: {best_rotation}° (0° confidence too low)")
                        doc.close()
                        return self._apply_rotation_correction(input_pdf_path, output_pdf_path, best_rotation)
                    else:
                        self.log(f"   No OCR correction: insufficient confidence for non-zero rotation")

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
                page.set_rotation(rotation)  # Set absolute rotation, don't add

                if page_num < 3:  # Log first 3 pages
                    self.log(f"   Page {page_num + 1}: rotation {current_rotation}° → {rotation}°")

            doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
            doc.close()

            self.log(f"✅ Applied {rotation}° rotation correction")
            return True

        except Exception as e:
            self.log(f"   Rotation correction failed: {str(e)}")
            return False

    def _try_aggressive_correction(self, input_pdf_path: str, output_pdf_path: str) -> bool:
        """
        Aggressive rotation correction for obvious rotation issues
        This method corrects clearly wrong rotations without needing text analysis

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

            corrections_needed = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                current_rotation = page.rotation
                page_rect = page.rect
                page_width = page_rect.width
                page_height = page_rect.height

                # Aggressive correction rules for obvious issues
                needs_correction = False
                suggested_rotation = current_rotation

                # Rule 1: 180° rotation is almost always wrong for normal documents
                if current_rotation == 180:
                    suggested_rotation = 0
                    needs_correction = True
                    self.log(f"   Page {page_num + 1}: Aggressive correction - 180° → 0° (180° is rarely correct)")

                # Rule 2: 90° or 270° rotations should generally be corrected to 0° for consistency
                elif current_rotation in [90, 270]:
                    # Calculate what the aspect ratio would be after correction to 0°
                    if page_width < page_height:
                        # Currently portrait-oriented, would become landscape after correction
                        corrected_aspect_ratio = page_height / page_width
                    else:
                        # Currently landscape-oriented, would become portrait after correction
                        corrected_aspect_ratio = page_width / page_height

                    # ENHANCED: More aggressive correction for native PDFs with obvious rotation issues
                    # Most documents should be in portrait orientation (0°) for reading
                    # If we have a reasonable aspect ratio after correction, apply it
                    if 1.0 <= corrected_aspect_ratio <= 2.0:
                        # This would create a readable document - correct to 0°
                        suggested_rotation = 0
                        needs_correction = True
                        self.log(f"   Page {page_num + 1}: Enhanced correction - {current_rotation}° → 0° (creates readable aspect ratio {corrected_aspect_ratio:.2f})")
                    else:
                        # Unusual aspect ratio - check if it's a special case
                        # For very wide or very tall documents, keep current rotation
                        needs_correction = False
                        self.log(f"   Page {page_num + 1}: Keeping {current_rotation}° rotation (unusual aspect ratio {corrected_aspect_ratio:.2f})")

                # Rule 2b: Check if current page dimensions suggest it should be landscape but isn't rotated
                elif current_rotation == 0 and page_width > page_height:
                    # Page is landscape-oriented but has 0° rotation - check if it should be portrait
                    aspect_ratio = page_width / page_height
                    if aspect_ratio > 1.5:  # Unusually wide landscape
                        # This might be a portrait document that was incorrectly saved as landscape
                        suggested_rotation = 90  # Try rotating to portrait
                        needs_correction = True
                        self.log(f"   Page {page_num + 1}: Aggressive correction - 0° → 90° (unusually wide landscape {aspect_ratio:.2f})")

                # Rule 3: Check if the rotation creates an extremely unusual aspect ratio
                elif current_rotation in [90, 270]:
                    # After 90° rotation, check if aspect ratio is reasonable
                    rotated_width = page_height  # What would be width after rotation
                    rotated_height = page_width  # What would be height after rotation

                    # If rotated aspect ratio is extreme (e.g., > 3:1), it's probably wrong
                    aspect_ratio = max(rotated_width / rotated_height, rotated_height / rotated_width)
                    if aspect_ratio > 3.0:
                        suggested_rotation = 0
                        needs_correction = True
                        self.log(f"   Page {page_num + 1}: Aggressive correction - {current_rotation}° → 0° (extreme aspect ratio {aspect_ratio:.1f}:1)")

                if needs_correction and suggested_rotation != current_rotation:
                    corrections_needed.append((page_num, suggested_rotation))

            doc.close()

            # Apply corrections if needed
            if corrections_needed:
                self.log(f"📝 Applying {len(corrections_needed)} aggressive rotation corrections")
                return self._apply_pymupdf_corrections(input_pdf_path, output_pdf_path, corrections_needed)

            return False

        except Exception as e:
            self.log(f"   Aggressive correction failed: {str(e)}")
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