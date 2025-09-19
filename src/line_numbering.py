"""
Line Numbering Module
Adds line numbers to PDF documents for document review purposes
"""

import os
from pathlib import Path
import tempfile

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import black, red
except ImportError:
    canvas = None
    red = None

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class LineNumberer:
    """Adds line numbers to PDF documents"""
    
    def __init__(self, log_callback=None):
        """
        Initialize the line numberer
        
        Args:
            log_callback: Optional callback function for logging messages
        """
        self.log_callback = log_callback
        self.numbering_errors = []
        self.gutter_created_pages = set()  # Track which pages already have gutters
        self.gutter_created_docs = set()  # Track which documents already have gutters
        
        # Line numbering settings (CONTENT-AWARE MODE)
        self.line_height = 12  # For fallback only - now we use actual content positions
        self.lines_per_page = 50  # For fallback only
        self.left_margin = 50  # Standard margin  
        self.top_margin = 72  # Standard top margin (1 inch)
        self.number_font_size = 10  # Smaller font size for 0.25" gutter
        self.max_font_size = 14  # Maximum line number font size (never exceed text)
        self.min_font_size = 6   # Minimum for readability
        
        # Hardcoded colors and fonts
        self.number_color = (1.0, 0.0, 0.0)  # Bright red color for line numbers like v1
        self.number_font = "Times-Roman"  # Times New Roman font
        self.gutter_border_color = (0.8, 0.8, 0.8)    # Light grey border
        self.gutter_fill_color = (0.95, 0.95, 0.95)   # Very light grey fill
        
        # Print size constraints (8.5 x 11 inches = 612 x 792 points)
        self.max_print_width = 612  # 8.5 inches in points
        self.max_print_height = 792  # 11 inches in points
        
        # Legal industry settings for TIFF and PDF scans
        self.legal_lines_per_page = 28  # Legal industry standard
        self.legal_gutter_width = 18  # 0.25 inch = 18 points left gutter for all PDFs
        self.legal_line_height = 20  # Slightly larger spacing for legal documents
        self.legal_x_position = 8  # Fixed left position, never rotate
        
        # Landscape-specific settings
        self.landscape_lines_per_page = 28  # Same as legal standard for consistency
        
    def _validate_and_scale_page_for_printing(self, page):
        """
        Ensure page + gutter fits within printable 8.5 x 11 inch portrait format
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            bool: True if page was modified, False if already valid
        """
        try:
            page_rect = page.rect
            current_width = page_rect.width
            current_height = page_rect.height
            
            # Account for gutter width when checking if scaling is needed
            # Gutter width is 18 points = 0.25 inches
            gutter_width_pt = self.legal_gutter_width  # 18 points
            total_width_with_gutter = current_width + gutter_width_pt
            
            # Check if page + gutter exceeds print size limits
            needs_scaling = (total_width_with_gutter > self.max_print_width or 
                           current_height > self.max_print_height)
            
            if needs_scaling:
                # Calculate scale factors to fit within print limits
                # For width: account for gutter width (page + gutter must fit in max width)
                available_width = self.max_print_width - gutter_width_pt
                width_scale = available_width / current_width
                height_scale = self.max_print_height / current_height
                
                # Use the smaller scale to ensure both dimensions fit
                scale_factor = min(width_scale, height_scale)
                
                new_width = current_width * scale_factor
                new_height = current_height * scale_factor
                
                self.log(f"📏 Scaling oversized page from {current_width:.1f}x{current_height:.1f}pt "
                        f"to {new_width:.1f}x{new_height:.1f}pt (scale: {scale_factor:.3f})")
                self.log(f"📏 Total width with gutter: {total_width_with_gutter:.1f}pt → {(new_width + gutter_width_pt):.1f}pt")
                
                # Create a new page with the scaled content
                # Get page content as pixmap at scale factor
                mat = fitz.Matrix(scale_factor, scale_factor)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Set new page size
                new_mediabox = fitz.Rect(0, 0, new_width, new_height)
                page.set_mediabox(new_mediabox)
                page.set_cropbox(new_mediabox)
                
                # Clear page and insert scaled content
                page.clean_contents()
                page.insert_image(new_mediabox, pixmap=pix)
                
                self.log(f"✅ Page scaled successfully to fit print format")
                return True
            else:
                # Page is already within print limits
                self.log(f"📏 Page size {current_width:.1f}x{current_height:.1f}pt is within print limits")
                return False
                
        except Exception as e:
            self.log(f"⚠️ Error scaling page for printing: {str(e)}")
            return False
        
    def log(self, message):
        """Log a message using the callback or print"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def debug_log(self, message, filename=None):
        """Debug logging to file - logs EVERYTHING with filename context"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Add filename context if provided
        if filename:
            debug_msg = f"[{timestamp}] DEBUG [{filename}]: {message}"
        else:
            debug_msg = f"[{timestamp}] DEBUG: {message}"
        
        # Log to console
        self.log(debug_msg)
        
        # Also log to debug file
        try:
            with open("debug_output.txt", "a", encoding="utf-8") as f:
                f.write(debug_msg + "\n")
        except Exception as e:
            print(f"Failed to write debug log: {e}")
    
    def _is_landscape_page(self, page):
        """
        Detect if a page is in landscape orientation
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            bool: True if page is landscape (width > height)
        """
        page_rect = page.rect
        return page_rect.width > page_rect.height
    
    def _detect_ocr_rotation(self, page):
        """
        Use OCR to detect the correct orientation of a scanned page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            int: Correct rotation angle (0, 90, 180, or 270 degrees)
        """
        if not OCR_AVAILABLE:
            self.log("OCR not available - using page metadata rotation")
            return page.rotation
        
        try:
            import io
            # Convert page to image at high resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Create PIL image
            img = Image.open(io.BytesIO(img_data))
            
            # Test OCR at different rotations
            rotations = [0, 90, 180, 270]
            best_rotation = 0
            best_confidence = 0
            
            for rotation in rotations:
                # Rotate image
                if rotation != 0:
                    rotated_img = img.rotate(-rotation, expand=True)  # PIL rotates counter-clockwise
                else:
                    rotated_img = img
                
                # Perform OCR
                try:
                    ocr_data = pytesseract.image_to_data(rotated_img, output_type=pytesseract.Output.DICT)
                    
                    # Calculate confidence score based on:
                    # 1. Number of words detected
                    # 2. Average confidence of detected text
                    # 3. Presence of common English words
                    
                    confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                    word_count = len([word for word in ocr_data['text'] if word.strip()])
                    
                    if confidences and word_count > 0:
                        avg_confidence = sum(confidences) / len(confidences)
                        # Bonus for more words detected
                        confidence_score = avg_confidence * (1 + word_count / 100)
                        
                        if confidence_score > best_confidence:
                            best_confidence = confidence_score
                            best_rotation = rotation
                            
                except Exception as e:
                    self.log(f"OCR error at rotation {rotation}°: {e}")
                    continue
            
            self.log(f"OCR detected best rotation: {best_rotation}° (confidence: {best_confidence:.1f})")
            return best_rotation
            
        except Exception as e:
            self.log(f"OCR rotation detection failed: {e}")
            return page.rotation
    
    def _is_scanned_or_image_document(self, doc_path, doc=None):
        """
        Detect if document is image-based/scanned (TIFF or PDF with primarily images)
        
        Args:
            doc_path (str): Path to document
            doc: Optional already opened PyMuPDF document
            
        Returns:
            bool: True if document is scanned/image-based
        """
        try:
            # Check file extension first
            if doc_path.lower().endswith(('.tiff', '.tif')):
                self.log("Processing TIFF document")
                return True
            
            # For PDFs, analyze content
            if doc is None:
                doc = fitz.open(doc_path)
                should_close = True
            else:
                should_close = False
            
            # Check for rotation metadata first - this is a strong indicator of scanned documents
            pages_to_check = min(3, doc.page_count)
            rotated_pages = 0
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                if page.rotation != 0:
                    rotated_pages += 1
            
            # If any pages have rotation metadata, it's likely a scanned document
            if rotated_pages > 0:
                self.log(f"Scanned document detected - {rotated_pages}/{pages_to_check} pages have rotation metadata")
                if should_close:
                    doc.close()
                return True
            
            # Analyze first few pages to determine if primarily image-based
            image_based_pages = 0
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                
                # Get text content
                text_blocks = page.get_text("dict")
                text_length = len(page.get_text().strip())
                
                # Get image content
                image_list = page.get_images()
                
                # Criteria for image-based page:
                # 1. Very little text content (< 50 characters) AND has images
                # 2. Contains images that cover significant page area
                # 3. High image-to-text ratio
                
                # More restrictive: only consider scanned if BOTH low text AND images present
                # Also check if this is a landscape page with extractable text
                is_landscape = self._is_landscape_page(page)
                if text_length < 50 and len(image_list) > 0 and not is_landscape:
                    # Additional check: if images cover more than 30% of page
                    page_area = page.rect.width * page.rect.height
                    image_coverage = 0
                    
                    for img_index, img in enumerate(image_list):
                        if img_index < 5:  # Check first 5 images only
                            try:
                                img_rect = page.get_image_bbox(img)
                                if img_rect:
                                    img_area = (img_rect.x1 - img_rect.x0) * (img_rect.y1 - img_rect.y0)
                                    image_coverage += img_area
                            except:
                                pass
                    
                    coverage_ratio = image_coverage / page_area if page_area > 0 else 0
                    
                    if coverage_ratio > 0.3 or (text_length < 50 and len(image_list) > 0):
                        image_based_pages += 1
            
            if should_close:
                doc.close()
            
            # If majority of checked pages are image-based
            is_scanned = image_based_pages > (pages_to_check / 2)
            
            # Special case: If this is a landscape document with any extractable text,
            # always use text-aligned numbering instead of grid
            if is_scanned and doc:
                has_any_text = False
                for page_num in range(min(3, doc.page_count)):
                    page = doc[page_num]
                    if self._is_landscape_page(page):
                        text_length = len(page.get_text().strip())
                        if text_length > 10:  # Any meaningful text
                            has_any_text = True
                            break
                
                if has_any_text:
                    self.log(f"Landscape document with extractable text detected - using text-aligned numbering")
                    return False  # Force text-based numbering
            
            if is_scanned:
                self.log(f"Scanned document detected - using grid numbering")
            else:
                self.log(f"Text-based document detected - using content-aware numbering")
            
            return is_scanned
            
        except Exception as e:
            self.log(f"Error detecting document type: {e} - defaulting to content-aware numbering")
            return False
            
    def add_line_numbers(self, input_pdf_path, output_pdf_path, start_line=1):
        """
        Add line numbers to a PDF document using enhanced metadata when available
        
        Args:
            input_pdf_path (str): Path to input PDF file
            output_pdf_path (str): Path for output PDF file with line numbers
            start_line (int): Starting line number (default: 1)
            
        Returns:
            tuple: (success: bool, final_line_number: int)
        """
        if not fitz:
            self.log("PyMuPDF not available for line numbering")
            return False, start_line
            
        input_file = Path(input_pdf_path)
        output_file = Path(output_pdf_path)
        
        if not input_file.exists():
            self.log(f"Error: Input PDF does not exist: {input_pdf_path}")
            return False, start_line
            
        # Check for enhanced conversion metadata
        line_mapping = self._load_line_mapping(input_pdf_path)
            
        try:
            # Initialize debug file only if it doesn't exist (append mode for all files)
            import os
            import datetime
            if not os.path.exists("debug_output.txt"):
                with open("debug_output.txt", "w", encoding="utf-8") as f:
                    f.write("=== COMPREHENSIVE DEBUG LOG - ALL FILES ===\n")
                    f.write(f"Processing started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("Files will be processed in numerical order: 0001, 0002, 0003, etc.\n\n")
            
            # Open the PDF
            doc = fitz.open(input_pdf_path)
            current_line = start_line
            
            filename = input_file.name
            # Essential logging only
            self.log(f"Processing: {Path(input_pdf_path).name}")
            
            # STEP 1: Fix rotation issues FIRST, then validate and scale pages
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Validate and scale page for printing compatibility
                self._validate_and_scale_page_for_printing(page)
            
            # STEP 2: Create unified gutter for ALL pages AFTER scaling
            for page_num in range(doc.page_count):
                page = doc[page_num]
                self._create_true_gutter(page, self.legal_gutter_width, input_pdf_path)
            
            # STEP 3: Add line numbers (gutter already exists for all pages)
            # Check if this is a scanned/image document
            is_scanned = self._is_scanned_or_image_document(input_pdf_path, doc)
            
            if is_scanned:
                # For scanned documents, use 28-line grid for consistent spacing
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    lines_added = self._add_legal_grid_line_numbers(page, current_line, input_pdf_path)
                    current_line += lines_added
            elif line_mapping:
                # Use enhanced line mapping for 100% accuracy on native text documents
                current_line = self._add_line_numbers_with_mapping(doc, line_mapping, start_line, input_pdf_path)
            else:
                # Fall back to content-aware detection for native text documents
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    lines_added = self._add_line_numbers_to_page(page, current_line, None, input_pdf_path)
                    current_line += lines_added
                
            # Save the modified PDF
            output_file.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_pdf_path))
            doc.close()
            
            # Clean up metadata file if it exists
            self._cleanup_line_mapping(input_pdf_path)
            
            self.log(f"Done: {Path(input_pdf_path).name}")
            return True, current_line
            
        except Exception as e:
            self.log(f"Error adding line numbers to {input_pdf_path}: {str(e)}")
            self.numbering_errors.append({
                'file': input_pdf_path,
                'error': str(e),
                'type': 'line_numbering_error'
            })
            return False, start_line
            
    def _calculate_lines_on_page(self, page, start_line):
        """
        Calculate how many lines should be on this page
        
        Args:
            page: PyMuPDF page object
            start_line: Starting line number for this page
            
        Returns:
            int: Number of lines on this page
        """
        # Get page dimensions
        page_rect = page.rect
        page_height = page_rect.height
        
        # Calculate usable height (minus margins)
        usable_height = page_height - (self.top_margin * 2)
        
        # Calculate number of lines that fit
        lines_on_page = int(usable_height / self.line_height)
        
        # Ensure we don't exceed our standard lines per page
        return min(lines_on_page, self.lines_per_page)
        
    def _add_line_numbers_to_page(self, page, start_line, num_lines=None, doc_path=None):
        """
        Add line numbers aligned with actual text content
        
        Args:
            page: PyMuPDF page object
            start_line: Starting line number for this page
            num_lines: Ignored - we determine lines based on actual content
            
        Returns:
            int: Number of lines actually numbered
        """
        try:
            # Analyze actual text content to find line positions
            text_dict = page.get_text("dict")
            
            # Check if PDF has highlightable text (better positioning available)
            has_selectable_text = self._has_highlightable_text(page, text_dict)
            
            # SAFEGUARDED SEQUENTIAL NUMBERING - BULLETPROOF APPROACH
            
            # Try the reliable method first
            lines_added = self._add_guaranteed_sequential_numbers(page, start_line, doc_path)
            
            if lines_added > 0:
                return lines_added
            else:
                # Final fallback if everything fails
                return self._add_simple_grid_numbers(page, start_line, doc_path)
            
        except Exception as e:
            self.log(f"Content analysis failed, using fallback: {e}")
            # Fallback to simple regular spacing
            return self._add_fallback_line_numbers(page, start_line, doc_path)
    
    def _has_highlightable_text(self, page, text_dict):
        """
        Check if PDF has highlightable/selectable text (not just images)
        
        Args:
            page: PyMuPDF page object
            text_dict: Text dictionary from page.get_text("dict")
            
        Returns:
            bool: True if PDF has selectable text with good positioning data
        """
        try:
            # Check if we have text blocks with font information
            text_blocks_found = 0
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text_content = span.get("text", "").strip()
                            if text_content and len(text_content) > 2:  # Meaningful text
                                # Check if we have font and positioning data
                                if span.get("bbox") and span.get("size") and span.get("font"):
                                    text_blocks_found += 1
            
            # If we found any meaningful text blocks with good data, text is highlightable
            return text_blocks_found >= 1  # Much more lenient - even 1 good text block is enough
            
        except Exception as e:
            self.log(f"Error checking text selectability: {e}")
            return False
    
    def _add_guaranteed_sequential_numbers(self, page, start_line, doc_path=None):
        """
        REFINED method that guarantees sequential numbering (1,2,3,4,5...)
        Uses improved text detection and positioning for better accuracy
        """
        try:
            # Detect and ignore form fields and annotations
            form_fields = self._get_form_fields_and_annotations(page)
            if form_fields:
                self.log(f"🔍 Detected {len(form_fields)} form fields/annotations - will ignore during text extraction")
            
            text_dict = page.get_text("dict")
            
            # Extract and group text lines more accurately
            text_lines = self._extract_text_lines_with_metadata(text_dict, form_fields)
            
            if not text_lines:
                return 0  # No text found
            
            # Group text fragments that belong to the same visual line
            grouped_lines = self._group_text_lines_by_proximity(text_lines)
            
            # Sort lines by reading order (top to bottom, left to right)
            # Use the simple version that doesn't require columns parameter
            sorted_lines = self._sort_lines_by_reading_order_simple(grouped_lines)
            
            # Create gutter for all documents (content-aware method)
            gutter_created = self._create_true_gutter(page, self.legal_gutter_width, doc_path)
            
            # Add line numbers with optimized gutter positioning
            x_position = self._calculate_optimal_gutter_position()
            lines_added = 0
            
            # self.log(f"DEBUG: Found {len(text_lines)} text fragments, grouped to {len(sorted_lines)} lines")
            # self.log(f"DEBUG: Placing {len(sorted_lines)} line numbers from top to bottom")
            
            for i, line_data in enumerate(sorted_lines):
                line_number = start_line + i
                y_pos = line_data['baseline_y']
                
                try:
                    page.insert_text(
                        (x_position, y_pos),
                        str(line_number),
                        fontsize=self.number_font_size,
                        color=self.number_color,
                        fontname=self.number_font,
                        rotate=0  # Ensure upright text
                    )
                    lines_added += 1
                    
                    # Debug first few placements
                    if i < 5:
                        self.log(f"✅ Line {line_number:2d} at y={y_pos:6.1f} (text: '{line_data['text'][:30]}...')")
                        
                except Exception as e:
                    self.log(f"Failed to place line {line_number:2d}: {e}")
            
            self.log(f"✅ Added {lines_added} line numbers with improved positioning")
            return lines_added
                
        except Exception as e:
            self.log(f"Refined positioning method failed: {e}")
            return 0
    
    def _add_simple_grid_numbers(self, page, start_line, doc_path=None):
        """
        FINAL FALLBACK: Simple grid-based numbering when all else fails
        Guarantees professional appearance with regular spacing
        """
        try:
            page_height = page.rect.height
            
            # Create gutter for grid fallback method
            gutter_created = self._create_true_gutter(page, self.legal_gutter_width, doc_path)
            
            # Use landscape-aware line count for grid fallback
            is_landscape = self._is_landscape_page(page)
            if is_landscape:
                target_lines = self.landscape_lines_per_page  # 28 for landscape
            else:
                target_lines = 25  # Default for portrait
            
            # Grid with target lines, evenly spaced
            line_spacing = (page_height - 144) / target_lines  # Leave margins top/bottom
            x_position = int(self.legal_gutter_width * 0.2)  # 20% of gutter width for better visual balance
            lines_added = 0
            
            
            for i in range(target_lines):
                y_pos = 72 + (i * line_spacing)  # Start 72pt from top
                line_number = start_line + i
                
                try:
                    page.insert_text(
                        (x_position, y_pos),
                        str(line_number),
                        fontsize=10,
                        color=self.number_color,
                        fontname=self.number_font,
                        rotate=0  # Ensure upright text
                    )
                    lines_added += 1
                    
                except Exception as e:
                    self.log(f"Grid fallback failed for line {line_number}: {e}")
            
            return lines_added
            
        except Exception as e:
            self.log(f"Grid fallback failed: {e}")
            return 0
    
    def _add_line_numbers_next_to_lines(self, page, text_dict, start_line):
        """
        DISABLED: This method was causing backwards numbering chaos
        Always use the bulletproof safeguard method instead
        """
        self.log("WARNING: Complex positioning method disabled - using safeguard")
        return self._add_guaranteed_sequential_numbers(page, start_line)
    
    def _extract_text_lines_with_metadata(self, text_dict, form_fields):
        """
        Extract text lines with enhanced metadata for better positioning
        
        Args:
            text_dict: Text dictionary from page.get_text("dict")
            form_fields: List of form fields to exclude
            
        Returns:
            List of text line dictionaries with enhanced metadata
        """
        text_lines = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    if line.get("spans"):
                        # Get line text first
                        line_text = ""
                        line_font_sizes = []
                        line_colors = []
                        
                        for span in line["spans"]:
                            span_text = span.get("text", "")
                            line_text += span_text
                            
                            if "size" in span and span["size"] > 0:
                                line_font_sizes.append(span["size"])
                            if "color" in span:
                                line_colors.append(span["color"])
                        
                        # Check if this line overlaps with form fields or annotations
                        line_bbox = line.get("bbox", [0, 0, 0, 0])
                        if self._is_text_from_form_field(line_bbox, form_fields):
                            continue  # Skip this line - it's from a form field or annotation
                        
                        # Only include meaningful text lines
                        if line_text.strip() and len(line_text.strip()) > 2:
                            bbox = line.get("bbox", [0, 0, 0, 0])
                            
                            # Calculate enhanced positioning data
                            font_size = self._calculate_representative_font_size(line_font_sizes)
                            text_height = bbox[3] - bbox[1]
                            
                            # Improved baseline calculation
                            # Use the bottom of the text line as baseline, adjusted for font size
                            baseline_y = bbox[3] - (text_height * 0.15)  # 15% up from bottom for better alignment
                            
                            # Calculate text center for better grouping
                            center_x = (bbox[0] + bbox[2]) / 2
                            center_y = (bbox[1] + bbox[3]) / 2
                            
                            text_lines.append({
                                'text': line_text.strip(),
                                'bbox': bbox,
                                'x': bbox[0],  # Left edge
                                'y': center_y,  # Center Y for grouping
                                'baseline_y': baseline_y,  # Actual positioning Y
                                'font_size': font_size,
                                'text_height': text_height,
                                'center_x': center_x,
                                'center_y': center_y,
                                'width': bbox[2] - bbox[0],
                                'height': text_height
                            })
        
        return text_lines
    
    def _calculate_representative_font_size(self, font_sizes):
        """Calculate a representative font size from a list of font sizes"""
        if not font_sizes:
            return 12  # Default
        
        # Remove outliers and use median for stability
        font_sizes = [fs for fs in font_sizes if 6 <= fs <= 24]  # Reasonable range
        if not font_sizes:
            return 12
        
        font_sizes.sort()
        return font_sizes[len(font_sizes) // 2]  # Median
    
    def _group_text_lines_by_proximity(self, text_lines):
        """
        Group text fragments that are on the same visual line with improved logic
        
        Args:
            text_lines: List of text line dictionaries with metadata
            
        Returns:
            List of grouped line dictionaries (one per visual line)
        """
        if not text_lines:
            return []
        
        # Sort by Y position (center Y for grouping)
        sorted_lines = sorted(text_lines, key=lambda x: x['center_y'])
        
        grouped = []
        current_group = []
        
        for line in sorted_lines:
            if not current_group:
                current_group = [line]
            else:
                # Calculate distance to the last line in current group
                last_line = current_group[-1]
                y_distance = abs(line['center_y'] - last_line['center_y'])
                
                # Use adaptive spacing based on font size
                avg_font_size = (line['font_size'] + last_line['font_size']) / 2
                max_spacing = max(8.0, avg_font_size * 0.8)  # Adaptive spacing
                
                # Check if lines are close enough to be on the same visual line
                if y_distance <= max_spacing:
                    current_group.append(line)
                else:
                    # Start a new group - finalize the current one
                    if current_group:
                        representative = self._create_line_representative(current_group)
                        grouped.append(representative)
                    current_group = [line]
        
        # Don't forget the last group
        if current_group:
            representative = self._create_line_representative(current_group)
            grouped.append(representative)
        
        return grouped
    
    def _create_line_representative(self, line_group):
        """
        Create a representative line from a group of text fragments
        
        Args:
            line_group: List of text line dictionaries on the same visual line
            
        Returns:
            Single line dictionary representing the group
        """
        if len(line_group) == 1:
            return line_group[0]
        
        # Combine text from all fragments
        combined_text = " ".join([line['text'] for line in line_group])
        
        # Use the leftmost fragment's positioning as the base
        leftmost_line = min(line_group, key=lambda x: x['x'])
        
        # Calculate average font size and height
        avg_font_size = sum(line['font_size'] for line in line_group) / len(line_group)
        avg_height = sum(line['text_height'] for line in line_group) / len(line_group)
        
        # Use the leftmost line's baseline Y for consistent positioning
        baseline_y = leftmost_line['baseline_y']
        
        return {
            'text': combined_text,
            'bbox': leftmost_line['bbox'],  # Use leftmost bbox as reference
            'x': leftmost_line['x'],
            'y': leftmost_line['center_y'],
            'baseline_y': baseline_y,
            'font_size': avg_font_size,
            'text_height': avg_height,
            'center_x': leftmost_line['center_x'],
            'center_y': leftmost_line['center_y'],
            'width': leftmost_line['width'],
            'height': avg_height
        }
    
    def _sort_lines_by_reading_order_simple(self, grouped_lines):
        """
        Sort lines by proper reading order (top to bottom, left to right)
        
        Args:
            grouped_lines: List of grouped line dictionaries
            
        Returns:
            List of lines sorted in reading order
        """
        if not grouped_lines:
            return []
        
        # Sort by Y position (top to bottom), then by X position (left to right)
        return sorted(grouped_lines, key=lambda line: (line['center_y'], line['x']))
    
    def _calculate_optimal_gutter_position(self):
        """
        Calculate the optimal X position for line numbers within the gutter
        
        Returns:
            int: X position for line numbers within the gutter
        """
        # Use a more precise positioning within the gutter
        # Position line numbers at 25% of gutter width for better visual balance
        # This provides good spacing from the gutter edge while maintaining readability
        optimal_position = int(self.legal_gutter_width * 0.25)
        
        # Ensure minimum spacing from gutter edge
        min_position = 3
        max_position = self.legal_gutter_width - 3
        
        # Clamp to reasonable bounds
        return max(min_position, min(optimal_position, max_position))
    
    def _group_lines_by_proximity(self, text_lines):
        """
        Legacy method - now redirects to the improved version
        """
        return self._group_text_lines_by_proximity(text_lines)
    
    def _group_lines_by_proximity_column_aware(self, text_lines, columns):
        """
        Group text fragments that are on the same visual line, but keep columns separate
        This prevents mixing left/right column content which causes backwards numbering
        
        Args:
            text_lines: List of text line dictionaries
            columns: List of column dictionaries from _detect_columns
            
        Returns:
            List of grouped line dictionaries (one per visual line per column)
        """
        if not text_lines:
            return []
        
        # Group lines by column first
        column_lines = {i: [] for i in range(len(columns))}
        
        for line in text_lines:
            # Find which column this line belongs to
            line_column_info = self._get_column_for_position(line['x'], columns)
            
            # Find the column index
            column_index = 0
            for i, col in enumerate(columns):
                if col == line_column_info:
                    column_index = i
                    break
                
            column_lines[column_index].append(line)
        
        # Group within each column separately, then merge by Y position for proper reading order
        column_grouped_results = {}
        
        for column_index in sorted(column_lines.keys()):
            lines_in_column = column_lines[column_index]
            
            if not lines_in_column:
                column_grouped_results[column_index] = []
                continue
                
            # Group lines within this column by proximity
            column_grouped = self._group_lines_by_proximity(lines_in_column)
            column_grouped_results[column_index] = column_grouped
        
        # Now merge all columns by Y position to get proper reading order
        all_grouped = []
        
        # Collect all lines with their column info
        all_lines_with_column = []
        for column_index, lines in column_grouped_results.items():
            for line in lines:
                line_with_column = line.copy()
                line_with_column['column_index'] = column_index
                all_lines_with_column.append(line_with_column)
        
        # Sort by Y position (top to bottom) across all columns
        all_lines_with_column.sort(key=lambda x: x['y'])
        
        # Remove the temporary column_index field
        for line in all_lines_with_column:
            del line['column_index']
            all_grouped.append(line)
        
        return all_grouped
    
    def _detect_columns(self, grouped_lines, page_width):
        """
        Detect column layout by analyzing text X positions
        
        Args:
            grouped_lines: List of line dictionaries with x, y positions
            page_width: Width of the page
            
        Returns:
            List of column dictionaries with start, end, and side information
        """
        if not grouped_lines:
            return [{'start': 0, 'end': page_width, 'side': 'left'}]
        
        # Collect all X positions
        x_positions = [line['x'] for line in grouped_lines]
        
        # If all text is in the left half, likely single column
        max_x = max(x_positions)
        min_x = min(x_positions)
        text_width = max_x - min_x
        
        # Much more conservative multi-column detection
        if max_x < page_width * 0.7 or text_width < page_width * 0.4:
            return [{'start': 0, 'end': page_width, 'side': 'left'}]
        
        # Find natural column breaks by analyzing X position clusters
        x_positions_sorted = sorted(set(x_positions))
        
        # Look for significant gaps in X positions that indicate column boundaries
        gaps = []
        for i in range(len(x_positions_sorted) - 1):
            gap_size = x_positions_sorted[i + 1] - x_positions_sorted[i]
            if gap_size > 50:  # Significant gap indicates column break
                gaps.append({
                    'position': (x_positions_sorted[i] + x_positions_sorted[i + 1]) / 2,
                    'size': gap_size
                })
        
        # If we found significant gaps, we have multiple columns
        if gaps:
            # Find the largest gap - this is likely the main column separator
            main_gap = max(gaps, key=lambda g: g['size'])
            column_break = main_gap['position']
            
            return [
                {'start': 0, 'end': column_break, 'side': 'left'},
                {'start': column_break, 'end': page_width, 'side': 'right'}
            ]
        else:
            # Single column
            return [{'start': 0, 'end': page_width, 'side': 'left'}]
    
    def _get_column_for_position(self, x_position, columns):
        """
        Determine which column a given X position belongs to
        
        Args:
            x_position: X coordinate of the text
            columns: List of column dictionaries from _detect_columns
            
        Returns:
            Column dictionary that contains this position
        """
        for column in columns:
            if column['start'] <= x_position < column['end']:
                return column
        
        # If not found, return the last column (rightmost)
        return columns[-1]
    
    def _sort_lines_by_reading_order(self, grouped_lines, columns):
        """
        Sort lines using proper reading order for multi-column layouts
        
        For single column: top to bottom, then left to right
        For multi-column: within each column top to bottom, then columns left to right
        
        Args:
            grouped_lines: List of line dictionaries
            columns: List of column dictionaries from _detect_columns
            
        Returns:
            List of lines sorted in proper reading order
        """
        if len(columns) <= 1:
            # Single column - simple top to bottom, left to right sort
            grouped_lines.sort(key=lambda line: (line['y'], line['x']))
            return grouped_lines
        
        # Multi-column layout - sort each column separately then combine
        
        # Group lines by column
        column_lines = {i: [] for i in range(len(columns))}
        
        for line in grouped_lines:
            # Find which column this line belongs to
            line_column_info = self._get_column_for_position(line['x'], columns)
            
            # Find the column index
            column_index = 0
            for i, col in enumerate(columns):
                if col == line_column_info:
                    column_index = i
                    break
            
            column_lines[column_index].append(line)
        
        # Sort lines within each column by Y position (top to bottom)
        for column_index in column_lines:
            column_lines[column_index].sort(key=lambda line: line['y'])
        
        # Combine columns in left-to-right order
        sorted_lines = []
        for column_index in sorted(column_lines.keys()):
            lines_in_column = column_lines[column_index]
            sorted_lines.extend(lines_in_column)
            
            if lines_in_column:  # Only log if column has content
                first_line_y = lines_in_column[0]['y']
                last_line_y = lines_in_column[-1]['y']
        
        return sorted_lines
            
    def _adjust_overlapping_positions_with_fonts(self, position_font_pairs):
        """
        Adjust overlapping line number positions by spacing them out vertically
        Now handles font sizes and adjusts spacing based on font size
        
        Args:
            position_font_pairs (list): List of (Y position, font_size) tuples
            
        Returns:
            list: Adjusted (Y position, font_size) tuples with minimum spacing
        """
        if not position_font_pairs or len(position_font_pairs) <= 1:
            return position_font_pairs
        
        adjusted = [position_font_pairs[0]]  # First position stays the same
        
        for i in range(1, len(position_font_pairs)):
            current_pos, current_font = position_font_pairs[i]
            previous_pos, previous_font = adjusted[-1]
            
            # Calculate minimum spacing based on the larger font size - VERY CONSERVATIVE
            larger_font = max(current_font, previous_font)
            min_spacing = max(8.0, larger_font * 0.8)  # Much smaller threshold - only fix severe overlaps
            
            # Check if current position would overlap with previous
            if abs(current_pos - previous_pos) < min_spacing:
                # ALWAYS move conflicting positions downward to maintain visual order
                # In PDF coordinates, downward = higher Y value
                new_pos = previous_pos + min_spacing
                adjusted.append((new_pos, current_font))
                
                # Log adjustment for debugging
                if abs(current_pos - previous_pos) < 6.0:  # Only log very close overlaps
                    pass
            else:
                # No overlap - keep original position
                adjusted.append((current_pos, current_font))
        
        # Count adjustments made
        adjustments = sum(1 for i in range(len(position_font_pairs)) if abs(position_font_pairs[i][0] - adjusted[i][0]) > 1.0)
        if adjustments > 0:
            pass
        
        return adjusted

    def _detect_layout_type(self, page, text_dict, text_line_positions):
        """
        Detect the type of document layout for optimal line numbering strategy
        
        Args:
            page: PyMuPDF page object
            text_dict: Text dictionary from page.get_text("dict")
            text_line_positions: List of detected line positions
            
        Returns:
            str: Layout type ('table_invoice', 'form', 'regular')
        """
        try:
            # Analyze content patterns
            total_text = ""
            number_count = 0
            currency_count = 0
            date_count = 0
            
            # Look for table/invoice indicators
            table_keywords = ['total', 'amount', 'invoice', 'bill', 'tax', 'vat', 'subtotal', 
                             'balance', 'due', 'payment', 'account', 'reference']
            form_keywords = ['name', 'address', 'date', 'application', 'form', 'details',
                            'contact', 'phone', 'email']
            
            table_indicators = 0
            form_indicators = 0
            
            # Analyze text content
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            span_text = span.get("text", "").lower()
                            line_text += span_text
                            total_text += span_text + " "
                        
                        # Count numeric patterns (amounts, dates, references)
                        import re
                        if re.search(r'\d+\.\d{2}', line_text):  # Currency amounts
                            currency_count += 1
                        if re.search(r'\b\d{1,2}/\d{1,2}/\d{4}\b', line_text):  # Dates
                            date_count += 1
                        if re.search(r'\b\d{3,}\b', line_text):  # Numbers/references
                            number_count += 1
                        
                        # Check for keywords
                        for keyword in table_keywords:
                            if keyword in line_text:
                                table_indicators += 1
                        for keyword in form_keywords:
                            if keyword in line_text:
                                form_indicators += 1
            
            # Classification logic
            total_chars = len(total_text.strip())
            
            # Table/Invoice detection (like your examples)
            if (currency_count >= 3 or  # Multiple currency amounts
                table_indicators >= 2 or  # Table-related keywords
                (number_count >= 5 and total_chars > 200)):  # Lots of numbers and data
                return "table_invoice"
            
            # Form detection
            elif (form_indicators >= 2 or  # Form-related keywords
                  (date_count >= 1 and total_chars < 500)):  # Dates but not too much text
                return "form"
            
            # Regular document
            else:
                return "regular"
            
        except Exception as e:
            self.log(f"Error detecting layout type: {e}")
            return "regular"
            
    def _detect_narrow_margins(self, page, text_dict):
        """
        Detect if this page has narrow margins (typical for invoices, forms)
        
        Args:
            page: PyMuPDF page object
            text_dict: Text dictionary from page.get_text("dict")
            
        Returns:
            bool: True if narrow margins detected
        """
        try:
            page_width = page.rect.width
            leftmost_text = page_width
            rightmost_text = 0
            
            # Analyze text block positions to determine content width
            for block in text_dict["blocks"]:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        if line["spans"]:
                            bbox = line["bbox"]
                            leftmost_text = min(leftmost_text, bbox[0])
                            rightmost_text = max(rightmost_text, bbox[2])
            
            # Calculate margins
            if leftmost_text < page_width and rightmost_text > 0:
                left_margin = leftmost_text
                right_margin = page_width - rightmost_text
                content_width = rightmost_text - leftmost_text
                content_percentage = (content_width / page_width) * 100
                
                # Detect narrow margins:
                # 1. Left margin < 40 points (about 0.55 inches)
                # 2. Content uses > 85% of page width
                narrow_left_margin = left_margin < 40
                wide_content = content_percentage > 85
                
                # Log margin analysis for debugging
                
                return narrow_left_margin or wide_content
                
        except Exception as e:
            self.log(f"Error detecting narrow margins: {e}")
            
        return False
        
    def _load_line_mapping(self, pdf_path):
        """Load enhanced line mapping metadata if available"""
        try:
            import json
            
            pdf_path_obj = Path(pdf_path)
            metadata_path = pdf_path_obj.with_suffix('.linemap.json')
            
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                return mapping_data
            else:
                return None
                
        except Exception as e:
            self.log(f"Warning: Could not load line mapping metadata: {e}")
            return None
    
    def _add_line_numbers_with_mapping(self, doc, line_mapping, start_line, input_pdf_path=None):
        """Add line numbers using enhanced conversion metadata for 100% accuracy"""
        try:
            line_positions = line_mapping.get('line_positions', [])
            total_lines = line_mapping.get('total_lines', 0)
            
            if not line_positions:
                self.log("No line positions in mapping data, falling back to content analysis")
                current_line = start_line
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    lines_added = self._add_line_numbers_to_page(page, current_line, None, input_pdf_path)
                    current_line += lines_added
                return current_line
            
            # Calculate line numbers distribution across pages
            current_line = start_line
            lines_per_page = len(line_positions) // doc.page_count if doc.page_count > 0 else len(line_positions)
            
            # Create gutter for enhanced mapping method
            
            # Enhanced positioning for narrow margins inside the gutter
            x_position = int(self.legal_gutter_width * 0.2)  # 20% of gutter width for better visual balance
            
            line_index = 0
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Create gutter for this page
                gutter_created = self._create_true_gutter(page, self.legal_gutter_width, input_pdf_path)
                
                # Calculate how many lines belong to this page
                if page_num == doc.page_count - 1:
                    # Last page gets remaining lines
                    page_lines = len(line_positions) - line_index
                else:
                    # Distribute lines evenly, with slight variation allowed
                    page_lines = min(lines_per_page, len(line_positions) - line_index)
                
                # Extract page positions and apply spacing adjustment
                page_positions = []
                for i in range(page_lines):
                    if line_index + i >= len(line_positions):
                        break
                    page_positions.append(line_positions[line_index + i])
                
                # Convert to (y_position, font_size) tuples for spacing adjustment
                position_font_pairs = [(pos, 10.0) for pos in page_positions]  # Default font size
                
                # Sort positions by Y coordinate to get proper document reading order
                sorted_positions = sorted(position_font_pairs, key=lambda x: x[0])
                
                # SAFEGUARD: Apply bulletproof sequential numbering (no overlap adjustment!)
                
                # Add line numbers sequentially without any complex adjustments
                for i, (y_pos, font_size) in enumerate(sorted_positions):
                    if line_index >= len(line_positions):
                        break
                        
                    line_number = current_line + i  # GUARANTEED sequential numbering
                    
                    try:
                        page.insert_text(
                            (x_position, y_pos),  # Use original Y position, no adjustment
                            str(line_number),
                            fontsize=self.number_font_size,
                            color=self.number_color,
                            fontname=self.number_font,
                            rotate=0  # Ensure upright text
                        )
                        line_index += 1
                        
                        # Log progress occasionally
                        if line_number % 25 == 1:
                            pass
                            
                    except Exception as e:
                        self.log(f"Failed to place enhanced line number {line_number}: {e}")
                        line_index += 1  # Skip this position
                
                current_line += page_lines
            
            return current_line
            
        except Exception as e:
            self.log(f"Error in enhanced line numbering: {e}")
            # Fall back to content analysis
            current_line = start_line
            for page_num in range(doc.page_count):
                page = doc[page_num]
                lines_added = self._add_line_numbers_to_page(page, current_line, None, input_pdf_path)
                current_line += lines_added
            return current_line
    


    def _cleanup_line_mapping(self, pdf_path):
        """Clean up line mapping metadata file after processing"""
        try:
            pdf_path_obj = Path(pdf_path)
            metadata_path = pdf_path_obj.with_suffix('.linemap.json')
            
            if metadata_path.exists():
                metadata_path.unlink()
                self.log(f"Cleaned up metadata file: {metadata_path.name}")
                
        except Exception as e:
            self.log(f"Warning: Could not clean up metadata file: {e}")
            # Not critical - continue processing
        
    def _add_legal_grid_line_numbers(self, page, start_line, doc_path=None):
        """
        Legal industry grid numbering for TIFF and PDF scans
        - 28 lines per page (legal standard)
        - 0.25" left gutter overlaying margin (industry standard approach)
        - Fixed orientation (no rotation)
        """
        lines_added = 0
        
        
        # Use the configured legal gutter width
        gutter_width = self.legal_gutter_width
        
        # CREATE THE TRUE GUTTER - actual additional space
        gutter_created = self._create_true_gutter(page, gutter_width, doc_path)
        # self.log(f"DEBUG: Legal grid gutter creation result: {gutter_created}")
        
        # Get updated page dimensions AFTER gutter creation and rotation fix
        page_rect = page.rect
        
        # Determine if this is a landscape page after gutter creation
        is_landscape = self._is_landscape_page(page)
        
        # Use landscape-specific line count for landscape pages
        if is_landscape:
            target_lines_per_page = self.landscape_lines_per_page  # 28 for landscape
        else:
            target_lines_per_page = self.legal_lines_per_page  # 28 for portrait (same value but clear intent)
        
        # Calculate vertical spacing for target lines - ensure even distribution
        # We want exactly 28 lines evenly spaced from top margin to bottom margin
        usable_height = page_rect.height - (2 * self.top_margin)  # Top and bottom margins
        # For 28 lines, we need 27 equal spaces between them to cover the full usable height
        line_spacing = usable_height / (target_lines_per_page - 1)
        
        # Ensure minimum spacing for readability
        if line_spacing < self.legal_line_height:
            line_spacing = self.legal_line_height
            max_lines = int(usable_height / line_spacing) + 1  # +1 because we count start and end
            lines_to_add = min(target_lines_per_page, max_lines)
        else:
            lines_to_add = target_lines_per_page
        
        # Page is now always upright (0 degrees) after gutter creation
        page_rotation = page.rotation
        
        # Add legal grid line numbers - no coordinate transformation needed since page is upright
        # Debug grid spacing calculation
        # self.log(f"DEBUG: Grid spacing - page_height: {page_rect.height}, top_margin: {self.top_margin}")
        # self.log(f"DEBUG: Grid spacing - usable_height: {usable_height}, line_spacing: {line_spacing:.2f}")
        # self.log(f"DEBUG: Grid spacing - target_lines: {target_lines_per_page}, lines_to_add: {lines_to_add}")
        # self.log(f"DEBUG: Grid spacing - gutter_created: {gutter_created}, gutter_width: {gutter_width}")
        
        for i in range(lines_to_add):
            y_position = self.top_margin + (i * line_spacing)
            
            if y_position > (page_rect.height - self.top_margin):  # Stop if too close to bottom
                # self.log(f"DEBUG: Stopping at line {i+1}, y_position {y_position:.2f} > bottom margin {page_rect.height - self.top_margin}")
                break
            
            line_number = start_line + i
            
            # Simple coordinates - page is always upright now
            if gutter_created:
                actual_x = self.legal_x_position  # Use configured position (8 points from left)
            else:
                actual_x = 5  # Fallback position if gutter creation failed
            actual_y = y_position
            text_rotation = 0  # Always upright
            
            # Debug first few and last few positions
            if i < 3 or i >= lines_to_add - 3:
                # self.log(f"DEBUG: Line {i+1}: position ({actual_x}, {y_position:.2f}), number {line_number}")
                pass

            try:
                # Insert line number with transformed coordinates
                page.insert_text(
                    (actual_x, actual_y),
                    str(line_number),
                    fontsize=self.number_font_size,
                    color=self.number_color,
                    fontname=self.number_font,
                    rotate=text_rotation  # Keep text upright
                )
                lines_added += 1
                
            except Exception as e:
                self.log(f"Legal grid line numbering failed at line {line_number}: {e}")
                break
        
        self.log(f"Legal grid numbering completed: {lines_added} lines added with {gutter_width}pt gutter")
        return lines_added
    
    def _create_true_gutter(self, page, gutter_width, doc_path=None):
        """
        Create a TRUE gutter by expanding page dimensions and shifting existing content.
        This creates actual additional space on the left for line numbers.
        ALSO handles document rotation to ensure upright orientation.
        Based on v1 approach that was most successful.
        """
        try:
            # Page-level gutter tracking instead of document-level
            page_id = f"{doc_path}_page_{page.number}" if doc_path else f"page_{page.number}"
            if hasattr(self, 'gutter_created_pages') and page_id in self.gutter_created_pages:
                return True
            
            # Initialize page-level tracking if not exists
            if not hasattr(self, 'gutter_created_pages'):
                self.gutter_created_pages = set()
                
            original_rect = page.rect
            page_rotation = page.rotation
            
            # ULTRA-AGGRESSIVE duplicate prevention: Skip if page already has gutter
            # Check if CropBox is wider than standard letter width (612pt = 8.5 inches)
            # This indicates a gutter may already exist
            cropbox_width = page.cropbox.width
            if cropbox_width > 620:  # Allow some margin for standard pages
                self.log(f"🚫 Skipping gutter creation - CropBox width {cropbox_width:.0f}pt > 620pt (likely already has gutter)")
                self.gutter_created_pages.add(page_id)
                return True
                
            # Get the page content with proper rotation to ensure upright capture
            # Apply rotation matrix to capture content upright, preventing overlay issues
            if page_rotation == 90:
                # For 90° rotation, apply 270° rotation to get upright content
                rotation_matrix = fitz.Matrix(1, 1).prerotate(270)
                pix = page.get_pixmap(matrix=rotation_matrix)
                content_width = pix.width
                content_height = pix.height
                self.log(f"🔄 Page {page.number+1}: Applied 270° rotation correction for 90° page, now upright {content_width}x{content_height}")
            elif page_rotation == 270:
                # For 270° rotation, apply 90° rotation to get upright content
                rotation_matrix = fitz.Matrix(1, 1).prerotate(90)
                pix = page.get_pixmap(matrix=rotation_matrix)
                content_width = pix.width
                content_height = pix.height
                self.log(f"🔄 Page {page.number+1}: Applied 90° rotation correction for 270° page, now upright {content_width}x{content_height}")
            else:
                # No rotation needed, get content as-is
                rotation_matrix = fitz.Matrix(1, 1)
                pix = page.get_pixmap(matrix=rotation_matrix)
                content_width = pix.width
                content_height = pix.height
                self.log(f"📄 Page {page.number+1}: {page_rotation}° rotation, using original dimensions {content_width}x{content_height}")
            
            # Calculate new page dimensions with gutter
            new_width = content_width + gutter_width
            new_height = content_height
            
            # Clear the current page content
            page.clean_contents()
            
            # Set the page to be upright (0 degrees rotation)
            page.set_rotation(0)
            
            # Set new page dimensions
            new_mediabox = fitz.Rect(0, 0, new_width, new_height)
            page.set_mediabox(new_mediabox)
            page.set_cropbox(new_mediabox)
            
            # Draw the gutter background
            gutter_rect = fitz.Rect(0, 0, gutter_width, new_height)
            
            # Use the configured colors
            border_color = self.gutter_border_color
            fill_color = self.gutter_fill_color
            
            page.draw_rect(gutter_rect, color=border_color, fill=fill_color, width=0)
            
            # Insert the rotated (now upright) content shifted to the right by gutter_width
            shifted_rect = fitz.Rect(gutter_width, 0, new_width, new_height)
            page.insert_image(shifted_rect, pixmap=pix)
            
            # Mark this page as having a gutter to prevent double creation
            page._gdi_gutter_created = True
            self.gutter_created_pages.add(page_id)
            
            # DEBUG: Check final rotation and dimensions
            final_rotation = page.rotation
            final_rect = page.rect
            self.log(f"✅ TRUE gutter created: expanded page to {new_width}x{new_height}")
            self.log(f"✅ Content shifted right by {gutter_width}pt")
            self.log(f"✅ Final page rotation: {final_rotation}°")
            self.log(f"✅ Final page dimensions: {final_rect.width}x{final_rect.height}")
            return True
                
        except Exception as e:
            self.log(f"Warning: Could not create true gutter: {e}")
            import traceback
            # self.log(f"DEBUG: Gutter creation traceback: {traceback.format_exc()}")
            return False

    def _add_fallback_line_numbers(self, page, start_line, doc_path=None):
        """Fallback method if content analysis fails"""
        page_rect = page.rect
        
        # Create gutter for fallback method
        gutter_created = self._create_true_gutter(page, self.legal_gutter_width, doc_path)
        
        # Use tight positioning for fallback inside the gutter
        x_position = self.legal_gutter_width // 2  # Always center of gutter (half the gutter width)
        lines_added = 0
        
        # Use landscape-aware line count for fallback
        is_landscape = self._is_landscape_page(page)
        if is_landscape:
            target_lines = self.landscape_lines_per_page  # 28 for landscape
        else:
            target_lines = self.lines_per_page  # 50 for portrait fallback
        
        # Calculate proper spacing for the target lines
        usable_height = page_rect.height - (2 * self.top_margin)
        if target_lines > 0:
            line_spacing = usable_height / target_lines
        else:
            line_spacing = self.line_height
            
        # Add lines at calculated intervals for proper spacing
        for i in range(target_lines):
            y_position = self.top_margin + (i * line_spacing)
            if y_position > (page_rect.height - self.top_margin):
                break
                
            line_number = start_line + i
            try:
                page.insert_text(
                    (x_position, y_position),
                    str(line_number),
                    fontsize=self.number_font_size,
                    color=self.number_color,
                    fontname=self.number_font,
                    rotate=0  # Ensure upright text
                )
                lines_added += 1
            except Exception as e:
                self.log(f"Fallback line numbering failed: {e}")
                break
                
        return lines_added
    
    def add_line_numbers_to_tiff(self, input_tiff_path, output_pdf_path, start_line=1):
        """
        Convert TIFF to PDF and add legal industry grid line numbering
        
        Args:
            input_tiff_path (str): Path to input TIFF file
            output_pdf_path (str): Path for output PDF file with line numbers
            start_line (int): Starting line number (default: 1)
            
        Returns:
            tuple: (success: bool, final_line_number: int)
        """
        try:
            from PIL import Image
            from reportlab.pdfgen import canvas as pdf_canvas
            from reportlab.lib.pagesizes import letter
            
            self.log(f"Converting TIFF to PDF with legal grid numbering: {input_tiff_path}")
            
            # Open TIFF file
            with Image.open(input_tiff_path) as img:
                # Handle multi-page TIFF
                pages = []
                try:
                    while True:
                        pages.append(img.copy())
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                
                # Create PDF with line numbers
                current_line = start_line
                c = pdf_canvas.Canvas(output_pdf_path, pagesize=letter)
                page_width, page_height = letter
                
                for page_idx, page_img in enumerate(pages):
                    self.log(f"Processing TIFF page {page_idx + 1}/{len(pages)}")
                    
                    # Convert page to RGB if needed
                    if page_img.mode != 'RGB':
                        page_img = page_img.convert('RGB')
                    
                    # Calculate image size to fit page with margins
                    img_width, img_height = page_img.size
                    margin = 72  # 1 inch margin
                    max_width = page_width - (2 * margin) - self.legal_gutter_width
                    max_height = page_height - (2 * margin)
                    
                    # Scale image to fit
                    scale = min(max_width / img_width, max_height / img_height)
                    new_width = img_width * scale
                    new_height = img_height * scale
                    
                    # Position image with gutter
                    x_offset = margin + self.legal_gutter_width
                    y_offset = margin
                    
                    # Save image temporarily
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
                        page_img.save(tmp_img.name, "JPEG", quality=85)
                        
                        # Draw image on PDF
                        c.drawImage(tmp_img.name, x_offset, y_offset, 
                                  width=new_width, height=new_height)
                        
                        # Clean up temp file
                        os.unlink(tmp_img.name)
                    
                    # Add legal grid line numbers
                    c.setFont("Helvetica", self.number_font_size)
                    c.setFillColorRGB(1, 0, 0)  # Red color
                    
                    # Use landscape-aware line count for TIFF processing
                    is_landscape = page_width > page_height  # Simple landscape detection for TIFF
                    if is_landscape:
                        target_lines = self.landscape_lines_per_page  # 28 for landscape
                    else:
                        target_lines = self.legal_lines_per_page  # 28 for portrait
                    
                    # Calculate line positions
                    usable_height = page_height - (2 * self.top_margin)
                    line_spacing = usable_height / target_lines
                    
                    x_position = int(self.legal_gutter_width * 0.2)  # 20% of gutter width for better visual balance
                    
                    for i in range(target_lines):
                        y_position = page_height - self.top_margin - (i * line_spacing)
                        line_number = current_line + i
                        
                        c.drawString(x_position, y_position, str(line_number))
                    
                    current_line += target_lines
                    c.showPage()
                
                c.save()
                self.log(f"TIFF to PDF conversion completed: {len(pages)} pages, {current_line - start_line} lines")
                return True, current_line
                
        except ImportError:
            self.log("PIL (Pillow) or ReportLab not available for TIFF processing")
            return False, start_line
        except Exception as e:
            self.log(f"Error processing TIFF file: {e}")
            return False, start_line
            
        
        
    def _get_form_fields_and_annotations(self, page):
        """
        Detect form fields and annotations on a PDF page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            list: List of form field and annotation bounding boxes
        """
        form_fields = []
        
        try:
            # Get form fields (widgets)
            widgets = page.widgets()
            for widget in widgets:
                if widget.rect:
                    form_fields.append({
                        'type': 'widget',
                        'rect': widget.rect,
                        'field_type': widget.field_type,
                        'field_name': widget.field_name
                    })
            
            # Get annotations
            annotations = page.annots()
            for annot in annotations:
                if annot.rect:
                    form_fields.append({
                        'type': 'annotation',
                        'rect': annot.rect,
                        'annot_type': annot.type[0] if annot.type else 'unknown'
                    })
            
            # Also check for specific form field indicators in text content (more conservative)
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            text = span.get("text", "").lower()
                            bbox = span.get("bbox", None)
                            font = span.get("font", "")
                            color = span.get("color", (0, 0, 0))
                            
                            # More specific form field patterns (less aggressive)
                            # Only match very specific form field indicators
                            form_patterns = [
                                'please sign here', 'signature:', 'initial here:',
                                'check if applicable', 'mark one', 'select one'
                            ]
                            
                            # Enhanced Adobe Fill & Sign detection
                            # Check if text appears to be manually added (not part of original document)
                            is_manually_added = False
                            
                            # 1. Check for specific form field patterns
                            if bbox and any(pattern in text for pattern in form_patterns):
                                is_manually_added = True
                            
                            # 2. Enhanced Adobe Fill & Sign detection based on common patterns
                            if bbox and font:
                                x0, y0, x1, y1 = bbox
                                
                                # Monetary values - strong indicator of Fill & Sign
                                monetary_patterns = [
                                    r'£\d+\.?\d*', r'\$\d+\.?\d*', r'€\d+\.?\d*',  # Currency amounts
                                    r'\d+\.\d{2}',  # Decimal numbers (likely money)
                                ]
                                import re
                                if any(re.search(pattern, text, re.IGNORECASE) for pattern in monetary_patterns):
                                    # Additional check: must be in right side or unusual location
                                    if x0 > 350 or y0 > 500:  # Right side or bottom area
                                        is_manually_added = True
                                
                                # Contact information patterns
                                contact_patterns = [
                                    r'\d{5}\s?\d{6}',  # UK phone pattern
                                    r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # US phone pattern
                                    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email
                                    r'vat\s+no\.?\s*\d+',  # VAT numbers
                                    r'company\s+no\.?\s*\d+',  # Company numbers
                                ]
                                if any(re.search(pattern, text, re.IGNORECASE) for pattern in contact_patterns):
                                    is_manually_added = True
                                
                                # Addresses (postcodes, street addresses)
                                if re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s+\d[A-Z]{2}\b', text):  # UK postcode
                                    is_manually_added = True
                                
                                # Text in typical Fill & Sign locations
                                if x0 > 400:  # Right side of page (common for Fill & Sign additions)
                                    # Check if it's short text (likely form field entries)
                                    if len(text) < 30 and not text.isupper():
                                        is_manually_added = True
                                
                                # Text in left margin (but not our line numbering)
                                if x0 < 50 and x1 < 100:  # Left margin text
                                    # Check if it's not our line numbering (red color)
                                    if color != (16711680, 0, 0) and color != 16711680:
                                        is_manually_added = True
                                
                                # Text in signature areas (bottom of page)
                                if y0 > 600:  # Bottom area of page
                                    signature_keywords = ['signed', 'date', 'name', 'title', 'signature']
                                    if any(keyword in text for keyword in signature_keywords):
                                        is_manually_added = True
                            
                            if bbox and is_manually_added:
                                # Create exclusion zone around manually added text
                                expanded_rect = fitz.Rect(
                                    bbox[0] - 3, bbox[1] - 2,
                                    bbox[2] + 3, bbox[3] + 2
                                )
                                form_fields.append({
                                    'type': 'adobe_fill_sign',
                                    'rect': expanded_rect,
                                    'text': text.strip(),
                                    'font': font
                                })
            
            return form_fields
            
        except Exception as e:
            self.log(f"Error detecting form fields: {e}")
            return []
    
    def _is_text_from_form_field(self, text_bbox, form_fields):
        """
        Check if text overlaps with form fields or annotations
        
        Args:
            text_bbox: Bounding box of the text line [x0, y0, x1, y1]
            form_fields: List of form field dictionaries with 'rect' keys
            
        Returns:
            bool: True if text overlaps with form fields
        """
        if not form_fields:
            return False
        
        try:
            text_rect = fitz.Rect(text_bbox)
            
            for field in form_fields:
                field_rect = field['rect']
                
                # Check if text bbox overlaps with form field bbox
                # Use a smaller tolerance for more precise detection
                tolerance = 2  # Reduced from 5 to 2 points tolerance
                expanded_field_rect = fitz.Rect(
                    field_rect[0] - tolerance,
                    field_rect[1] - tolerance,
                    field_rect[2] + tolerance,
                    field_rect[3] + tolerance
                )
                
                if text_rect.intersects(expanded_field_rect):
                    return True
            
            return False
            
        except Exception as e:
            self.log(f"Error checking form field overlap: {e}")
            return False
        
    def get_numbering_errors(self):
        """Get list of line numbering errors"""
        return self.numbering_errors
        
    def clear_errors(self):
        """Clear the numbering errors list"""
        self.numbering_errors = []
        
    def set_numbering_options(self, line_height=None, lines_per_page=None, 
                            left_margin=None, top_margin=None, font_size=None):
        """
        Set line numbering options
        
        Args:
            line_height (int): Points between lines
            lines_per_page (int): Maximum lines per page
            left_margin (int): Points from left edge
            top_margin (int): Points from top edge
            font_size (int): Font size for line numbers
        """
        if line_height is not None:
            self.line_height = line_height
        if lines_per_page is not None:
            self.lines_per_page = lines_per_page
        if left_margin is not None:
            self.left_margin = left_margin
        if top_margin is not None:
            self.top_margin = top_margin
        if font_size is not None:
            self.number_font_size = font_size


