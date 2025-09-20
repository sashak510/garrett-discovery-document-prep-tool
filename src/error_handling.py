"""
Enhanced error handling utilities for the Garrett Discovery Document Prep Tool.
Provides comprehensive validation, error handling, and resource management.
"""

import os
import re
import shutil
import tempfile
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
from contextlib import contextmanager


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


class ResourceError(Exception):
    """Raised when resource management fails"""
    pass


class ProcessingError(Exception):
    """Raised when document processing fails"""
    pass


class ErrorHandler:
    """Comprehensive error handling and validation utilities"""

    def __init__(self, logger=None, log_callback=None):
        self.logger = logger or logging.getLogger(__name__)
        self.log_callback = log_callback

    def validate_input_parameters(self, bates_prefix: str, bates_start: int,
                                 file_naming_start: int, source_folder: Path) -> List[str]:
        """Validate all input parameters and return list of errors"""
        errors = []

        # Validate Bates prefix
        if bates_prefix and not re.match(r'^[A-Za-z0-9_-]+$', bates_prefix):
            errors.append("Bates prefix contains invalid characters (only letters, numbers, hyphens, underscores)")
        if len(bates_prefix or "") > 20:
            errors.append("Bates prefix too long (max 20 characters)")

        # Validate Bates start number
        if not isinstance(bates_start, int) or bates_start < 1:
            errors.append("Bates start number must be a positive integer")
        if bates_start > 999999:
            errors.append("Bates start number too large (max 999999)")

        # Validate file naming start
        if not isinstance(file_naming_start, int) or file_naming_start < 1:
            errors.append("File naming start must be a positive integer")

        # Validate source folder
        if not source_folder.exists():
            errors.append(f"Source folder does not exist: {source_folder}")
        elif not source_folder.is_dir():
            errors.append(f"Source path is not a directory: {source_folder}")

        # Check disk space
        try:
            required_space = 1024 * 1024 * 100  # 100MB minimum
            if not self._check_disk_space(source_folder, required_space):
                errors.append("Insufficient disk space for processing (minimum 100MB required)")
        except Exception as e:
            errors.append(f"Could not check disk space: {str(e)}")

        return errors

    def validate_pdf_integrity(self, pdf_path: Path) -> bool:
        """Validate PDF file integrity before processing"""
        try:
            import fitz  # PyMuPDF

            # Check file existence and size
            if not pdf_path.exists():
                raise ValidationError(f"PDF file does not exist: {pdf_path}")

            # Validate file size limits
            file_size = pdf_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            if file_size == 0:
                raise ValidationError(f"PDF file is empty: {pdf_path}")

            if file_size_mb > 200:  # 200MB limit
                raise ValidationError(f"PDF file too large ({file_size_mb:.1f}MB - limit 200MB): {pdf_path}")

            if file_size_mb < 0.001:  # 1KB minimum
                raise ValidationError(f"PDF file too small ({file_size_mb:.3f}MB - minimum 1KB): {pdf_path}")

            # Check file accessibility
            try:
                with open(pdf_path, 'rb') as test_file:
                    test_file.read(1)  # Try to read first byte
            except (PermissionError, IOError) as e:
                raise ValidationError(f"PDF file is locked or inaccessible: {str(e)}")

            # Check system resources before processing
            self._check_system_resources(file_size_mb)

            # Validate PDF structure
            doc = fitz.open(str(pdf_path))

            # Check if PDF is encrypted
            if doc.is_encrypted:
                doc.close()
                raise ValidationError("PDF is password-protected")

            # Check page count and basic structure
            if doc.page_count == 0:
                doc.close()
                raise ValidationError("PDF has no pages")

            # Try to access first page to validate structure
            try:
                first_page = doc[0]
                _ = first_page.rect  # Basic page structure check
            except Exception as e:
                doc.close()
                raise ValidationError(f"PDF structure error: {str(e)}")

            doc.close()
            return True

        except ImportError:
            raise ValidationError("PyMuPDF not available for PDF validation")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"PDF validation failed: {str(e)}")

    def _check_system_resources(self, file_size_mb: float):
        """Check if system has sufficient resources for processing"""
        try:
            # Check available memory
            import psutil
            memory = psutil.virtual_memory()
            available_memory_mb = memory.available / (1024 * 1024)

            # Require at least 3x file size in available memory
            required_memory_mb = file_size_mb * 3
            if available_memory_mb < required_memory_mb:
                raise ValidationError(
                    f"Insufficient memory: {available_memory_mb:.0f}MB available, "
                    f"{required_memory_mb:.0f}MB required for {file_size_mb:.1f}MB file"
                )

            # Check memory usage percentage
            if memory.percent > 85:
                raise ValidationError(
                    f"System memory usage too high: {memory.percent:.1f}% (limit 85%)"
                )

            # Check available disk space (require at least 2x file size)
            import shutil
            disk_usage = shutil.disk_usage('/')
            free_space_mb = disk_usage.free / (1024 * 1024)
            required_disk_mb = file_size_mb * 2

            if free_space_mb < required_disk_mb:
                raise ValidationError(
                    f"Insufficient disk space: {free_space_mb:.0f}MB available, "
                    f"{required_disk_mb:.0f}MB required for {file_size_mb:.1f}MB file"
                )

        except ImportError:
            # psutil not available, skip resource checks
            pass
        except Exception as e:
            # Don't fail processing due to resource check failures
            if self.log_callback:
                self.log_callback(f"Resource check warning: {str(e)}")

    def validate_processing_environment(self, source_folder: Path, output_folder: Path) -> List[str]:
        """Validate the entire processing environment"""
        errors = []

        # Validate source folder
        if not source_folder.exists():
            errors.append(f"Source folder does not exist: {source_folder}")
        elif not source_folder.is_dir():
            errors.append(f"Source path is not a directory: {source_folder}")

        # Validate output folder
        if output_folder.exists() and not output_folder.is_dir():
            errors.append(f"Output path exists but is not a directory: {output_folder}")

        # Check write permissions for output folder
        try:
            if not output_folder.exists():
                output_folder.mkdir(parents=True, exist_ok=True)
            test_file = output_folder / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            errors.append(f"Cannot write to output folder: {str(e)}")

        # Check for required dependencies
        required_modules = ['fitz', 'PIL', 'pytesseract']
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                errors.append(f"Required module not available: {module}")

        return errors

    def validate_file_accessibility(self, file_path: Path) -> Dict[str, Any]:
        """Check if file is accessible and return file info"""
        try:
            if not file_path.exists():
                return {'accessible': False, 'error': 'File does not exist'}

            if not file_path.is_file():
                return {'accessible': False, 'error': 'Path is not a file'}

            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                return {'accessible': False, 'error': 'File is empty'}

            if file_size > 500 * 1024 * 1024:  # 500MB limit
                return {'accessible': False, 'error': 'File too large (max 500MB)'}

            # Check if file is accessible (not locked)
            try:
                with open(file_path, 'rb') as test_file:
                    test_file.read(1)  # Try to read first byte
            except (PermissionError, IOError) as e:
                return {'accessible': False, 'error': f'File locked or inaccessible: {str(e)}'}

            return {
                'accessible': True,
                'size': file_size,
                'extension': file_path.suffix.lower(),
                'name': file_path.name
            }

        except Exception as e:
            return {'accessible': False, 'error': f'Error checking file: {str(e)}'}

    def _check_disk_space(self, folder: Path, required_bytes: int) -> bool:
        """Check if sufficient disk space is available"""
        try:
            stat = shutil.disk_usage(str(folder))
            return stat.free >= required_bytes
        except Exception:
            return True  # Assume sufficient space if we can't check

    @contextmanager
    def safe_pdf_operation(self, pdf_path: Path):
        """Context manager for safe PDF operations with guaranteed cleanup"""
        doc = None
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            yield doc
        except ImportError:
            raise ResourceError("PyMuPDF not available")
        except Exception as e:
            raise ResourceError(f"PDF operation failed: {str(e)}")
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception as close_error:
                    self.logger.warning(f"Error closing PDF document: {close_error}")

    def safe_file_operation(self, operation_func: Callable, operation_name: str,
                           *args, **kwargs) -> Any:
        """Wrapper for safe file operations with proper error handling"""
        try:
            return operation_func(*args, **kwargs)
        except FileNotFoundError as e:
            self.logger.error(f"File not found in {operation_name}: {str(e)}")
            raise ProcessingError(f"File not found: {str(e)}")
        except PermissionError as e:
            self.logger.error(f"Permission denied in {operation_name}: {str(e)}")
            raise ProcessingError(f"Permission denied: {str(e)}")
        except OSError as e:
            self.logger.error(f"OS error in {operation_name}: {str(e)}")
            raise ProcessingError(f"OS error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error in {operation_name}: {str(e)}")
            raise ProcessingError(f"Unexpected error: {str(e)}")

    def cleanup_temporary_files(self, temp_paths: List[Path]) -> None:
        """Guaranteed cleanup of temporary files"""
        for temp_path in temp_paths:
            try:
                if temp_path and temp_path.exists():
                    temp_path.unlink()
                    self.logger.debug(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                self.logger.warning(f"Could not clean up temporary file {temp_path}: {e}")

    def process_with_retry(self, operation_func: Callable, operation_name: str,
                          max_retries: int = 3, backoff_factor: int = 2) -> Any:
        """Process operation with retry logic for transient failures"""
        last_error = None

        for attempt in range(max_retries):
            try:
                return operation_func()

            except (MemoryError, RuntimeError, ValidationError) as e:
                # Critical errors - don't retry
                self.logger.error(f"Critical error in {operation_name}: {str(e)}")
                raise ProcessingError(f"Critical error: {str(e)}")

            except (PermissionError, IOError, OSError) as e:
                # Transient errors - retry with delay
                last_error = e
                if attempt < max_retries - 1:
                    delay = backoff_factor ** attempt
                    self.logger.warning(f"Retry {attempt + 1}/{max_retries} for {operation_name} in {delay}s")
                    time.sleep(delay)
                    continue
                else:
                    self.logger.error(f"All retries failed for {operation_name}: {str(e)}")
                    raise ProcessingError(f"Operation failed after {max_retries} retries: {str(e)}")

            except Exception as e:
                # Unexpected errors - log and fail
                self.logger.error(f"Unexpected error in {operation_name}: {str(e)}")
                raise ProcessingError(f"Unexpected error: {str(e)}")

        # Should never reach here
        raise ProcessingError(f"Unknown error in {operation_name} after {max_retries} retries")

    def create_temp_file(self, suffix: str = '.tmp', prefix: str = 'gdi_') -> Path:
        """Create a temporary file with proper cleanup tracking"""
        try:
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(fd)  # Close file descriptor, we'll manage the file ourselves
            return Path(temp_path)
        except Exception as e:
            raise ResourceError(f"Failed to create temporary file: {str(e)}")

    def safe_copy_file(self, source: Path, destination: Path) -> None:
        """Safely copy a file with proper error handling"""
        self.safe_file_operation(
            shutil.copy2, "file copy", str(source), str(destination)
        )

    def safe_move_file(self, source: Path, destination: Path) -> None:
        """Safely move a file with proper error handling"""
        self.safe_file_operation(
            shutil.move, "file move", str(source), str(destination)
        )

    def safe_create_directory(self, path: Path) -> None:
        """Safely create a directory with proper error handling"""
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ProcessingError(f"Failed to create directory {path}: {str(e)}")

    def validate_filename_safety(self, filename: str) -> bool:
        """Validate that filename is safe for filesystem operations"""
        if not filename or len(filename) > 255:
            return False

        # Check for invalid characters
        invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
        if re.search(invalid_chars, filename):
            return False

        # Check for reserved names
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}
        if filename.upper() in reserved_names:
            return False

        return True

    def sanitize_path(self, path_str: str) -> Path:
        """Sanitize user input paths to prevent directory traversal"""
        try:
            path = Path(path_str).resolve()
            if not path.is_absolute():
                path = Path.cwd() / path

            # Additional safety check - ensure path doesn't contain suspicious components
            if '..' in str(path) or any(char in str(path) for char in ['<', '>', ':', '"', '|', '?', '*']):
                raise ValidationError("Path contains invalid characters")

            return path
        except Exception as e:
            raise ValidationError(f"Invalid path provided: {str(e)}")

    def validate_folder_access(self, folder_path: Path, require_write: bool = False) -> bool:
        """Validate folder accessibility and permissions"""
        try:
            if not folder_path.exists():
                return False

            if not folder_path.is_dir():
                return False

            # Check read access
            if not os.access(folder_path, os.R_OK):
                return False

            # Check write access if required
            if require_write and not os.access(folder_path, os.W_OK):
                return False

            return True
        except Exception:
            return False

    def get_file_hash(self, file_path: Path) -> str:
        """Get hash of file for duplicate detection"""
        import hashlib
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not compute hash for {file_path}: {e}")
            return ""


# Decorator for automatic error handling
def handle_errors(operation_name: str = None, retry_count: int = 3):
    """Decorator for automatic error handling and retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            error_handler = getattr(self, 'error_handler', ErrorHandler())
            op_name = operation_name or func.__name__

            def operation():
                return func(self, *args, **kwargs)

            return error_handler.process_with_retry(operation, op_name, retry_count)

        return wrapper
    return decorator


# Decorator for resource management
def manage_resources(resource_cleanup_func: Callable = None):
    """Decorator for automatic resource cleanup"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            temp_files = []
            try:
                result = func(self, *args, **kwargs)
                return result
            finally:
                error_handler = getattr(self, 'error_handler', ErrorHandler())
                if resource_cleanup_func:
                    resource_cleanup_func(self, temp_files)
                else:
                    error_handler.cleanup_temporary_files(temp_files)

        return wrapper
    return decorator