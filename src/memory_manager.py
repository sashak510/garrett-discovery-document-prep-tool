"""
Memory Management System for Garrett Discovery Document Prep Tool
Handles memory monitoring, resource pooling, and batch processing to prevent crashes
"""

import os
import gc
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import logging

# Optional psutil import for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available - memory monitoring will be limited")


class MemoryState(Enum):
    """Memory usage states"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OUT_OF_MEMORY = "out_of_memory"


@dataclass
class MemoryConfig:
    """Configuration for memory management"""
    max_memory_percent: float = 80.0  # Maximum memory usage percentage
    warning_percent: float = 70.0    # Warning threshold
    batch_size: int = 5              # Files to process in each batch
    max_file_size_mb: int = 100      # Maximum file size in MB
    enable_monitoring: bool = True   # Enable memory monitoring
    cleanup_interval: int = 10       # Clean up every N files processed


class MemoryManager:
    """Advanced memory management system for document processing"""

    def __init__(self, config: MemoryConfig = None, log_callback: Callable = None):
        self.config = config or MemoryConfig()
        self.log_callback = log_callback or print
        self.logger = logging.getLogger(__name__)

        # Memory tracking
        self.processed_files_count = 0
        self.current_batch = []
        self.memory_history = []
        self.is_monitoring = False

        # Resource pools
        self.pdf_pool = {}
        self.temp_files = []

        # Threading
        self.monitoring_thread = None
        self.monitoring_lock = threading.Lock()

        # Initialize
        self._log_memory_info("Memory Manager initialized")

    def _log_memory_info(self, message: str, level: str = "INFO"):
        """Log memory information with current usage"""
        try:
            memory_info = self.get_memory_info()
            log_message = f"[MEMORY] {message} | Usage: {memory_info['percent_used']:.1f}% | " \
                         f"Available: {memory_info['available_mb']:.1f}MB | " \
                         f"Processed: {self.processed_files_count}"

            if level == "ERROR":
                self.logger.error(log_message)
            elif level == "WARNING":
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)

            if self.log_callback:
                self.log_callback(log_message)
        except Exception as e:
            self.logger.error(f"Error logging memory info: {e}")

    def get_memory_info(self) -> Dict[str, Any]:
        """Get current memory usage information"""
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    'error': 'psutil not available',
                    'processed_files': self.processed_files_count,
                    'note': 'Memory monitoring disabled'
                }

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            # System memory
            system_memory = psutil.virtual_memory()

            return {
                'process_rss_mb': memory_info.rss / 1024 / 1024,
                'process_vms_mb': memory_info.vms / 1024 / 1024,
                'system_total_mb': system_memory.total / 1024 / 1024,
                'system_available_mb': system_memory.available / 1024 / 1024,
                'system_used_mb': system_memory.used / 1024 / 1024,
                'percent_used': system_memory.percent,
                'processed_files': self.processed_files_count
            }
        except Exception as e:
            self.logger.error(f"Error getting memory info: {e}")
            return {'error': str(e), 'processed_files': self.processed_files_count}

    def get_memory_state(self) -> MemoryState:
        """Get current memory state"""
        try:
            if not PSUTIL_AVAILABLE:
                return MemoryState.HEALTHY  # Assume healthy if can't monitor

            memory_info = self.get_memory_info()
            if 'error' in memory_info:
                return MemoryState.CRITICAL

            percent_used = memory_info['percent_used']

            if percent_used >= 95:
                return MemoryState.OUT_OF_MEMORY
            elif percent_used >= self.config.max_memory_percent:
                return MemoryState.CRITICAL
            elif percent_used >= self.config.warning_percent:
                return MemoryState.WARNING
            else:
                return MemoryState.HEALTHY
        except Exception as e:
            self.logger.error(f"Error getting memory state: {e}")
            return MemoryState.CRITICAL

    def check_memory_before_operation(self, file_size_mb: float = 0) -> bool:
        """Check if there's enough memory for an operation"""
        try:
            memory_state = self.get_memory_state()
            memory_info = self.get_memory_info()

            if memory_state == MemoryState.OUT_OF_MEMORY:
                self._log_memory_info("❌ OUT OF MEMORY - Cannot proceed", "ERROR")
                return False

            if memory_state == MemoryState.CRITICAL:
                # Check if we can free up memory
                self.force_cleanup()
                memory_state = self.get_memory_state()

                if memory_state == MemoryState.CRITICAL:
                    self._log_memory_info("❌ CRITICAL MEMORY - Cannot proceed even after cleanup", "ERROR")
                    return False

            # Check if file size is reasonable
            if file_size_mb > self.config.max_file_size_mb:
                self._log_memory_info(f"⚠️ File too large: {file_size_mb:.1f}MB (max: {self.config.max_file_size_mb}MB)", "WARNING")
                return False

            # Estimate if we have enough memory for this file
            estimated_needed = file_size_mb * 3  # PDF processing can use 3x file size
            available_mb = memory_info['system_available_mb']

            if available_mb < estimated_needed:
                self._log_memory_info(f"⚠️ Insufficient memory for file: Need {estimated_needed:.1f}MB, Have {available_mb:.1f}MB", "WARNING")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking memory before operation: {e}")
            return False

    def force_cleanup(self):
        """Force cleanup of resources and garbage collection"""
        try:
            self._log_memory_info("🧹 Starting force cleanup")

            # Clear PDF pool
            if self.pdf_pool:
                for doc_id, doc in self.pdf_pool.items():
                    try:
                        if hasattr(doc, 'close'):
                            doc.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing PDF {doc_id}: {e}")
                self.pdf_pool.clear()

            # Clean up temporary files
            self.cleanup_temp_files()

            # Force garbage collection
            collected = gc.collect()
            self._log_memory_info(f"🧹 Cleanup completed. Garbage collected: {collected} objects")

            # Update memory state
            memory_state = self.get_memory_state()
            if memory_state == MemoryState.HEALTHY:
                self._log_memory_info("✅ Memory state restored to healthy")
            else:
                self._log_memory_info(f"⚠️ Memory state after cleanup: {memory_state.value}", "WARNING")

        except Exception as e:
            self.logger.error(f"Error during force cleanup: {e}")

    def cleanup_temp_files(self):
        """Clean up all temporary files"""
        try:
            removed_count = 0
            for temp_file in self.temp_files[:]:  # Copy list to avoid modification during iteration
                try:
                    if temp_file and temp_file.exists():
                        temp_file.unlink()
                        removed_count += 1
                        self.temp_files.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"Error removing temp file {temp_file}: {e}")

            if removed_count > 0:
                self._log_memory_info(f"🧹 Cleaned up {removed_count} temporary files")

        except Exception as e:
            self.logger.error(f"Error cleaning up temporary files: {e}")

    @contextmanager
    def memory_monitoring(self):
        """Context manager for memory monitoring during operations"""
        try:
            if self.config.enable_monitoring:
                self.is_monitoring = True
                self._log_memory_info("🔍 Started memory monitoring")

            yield self

        except Exception as e:
            self.logger.error(f"Error in memory monitoring: {e}")
        finally:
            if self.config.enable_monitoring:
                self.is_monitoring = False
                self._log_memory_info("🔍 Stopped memory monitoring")

    def process_in_batches(self, files: List[Any], process_func: Callable) -> Iterator[Any]:
        """
        Process files in batches with memory management between batches

        Args:
            files: List of files to process
            process_func: Function to call for each file

        Yields:
            Results from processing each file
        """
        total_files = len(files)
        self._log_memory_info(f"📊 Starting batch processing of {total_files} files (batch size: {self.config.batch_size})")

        for batch_start in range(0, total_files, self.config.batch_size):
            batch_end = min(batch_start + self.config.batch_size, total_files)
            batch_files = files[batch_start:batch_end]

            self._log_memory_info(f"📦 Processing batch {batch_start//self.config.batch_size + 1}: "
                                 f"files {batch_start + 1}-{batch_end}")

            # Check memory before batch
            if not self.check_memory_before_operation():
                self._log_memory_info("❌ Insufficient memory for batch - stopping", "ERROR")
                break

            # Process batch
            try:
                for file_info in batch_files:
                    if not self.check_memory_before_operation():
                        self._log_memory_info("❌ Memory check failed during batch - stopping", "ERROR")
                        break

                    # Process file with error handling
                    try:
                        result = process_func(file_info)
                        yield result
                        self.processed_files_count += 1

                        # Periodic cleanup
                        if self.processed_files_count % self.config.cleanup_interval == 0:
                            self.perform_periodic_cleanup()

                    except Exception as e:
                        self.logger.error(f"Error processing file {file_info}: {e}")
                        # Continue with next file

                # Batch cleanup
                self._log_memory_info(f"✅ Completed batch {batch_start//self.config.batch_size + 1}")
                self.force_cleanup()

            except Exception as e:
                self.logger.error(f"Error in batch processing: {e}")
                self.force_cleanup()
                continue

        self._log_memory_info(f"🎉 Batch processing completed. Total processed: {self.processed_files_count}")

    def perform_periodic_cleanup(self):
        """Perform periodic cleanup operations"""
        try:
            if self.processed_files_count % self.config.cleanup_interval == 0:
                self._log_memory_info(f"🧹 Periodic cleanup (every {self.config.cleanup_interval} files)")
                self.force_cleanup()

        except Exception as e:
            self.logger.error(f"Error during periodic cleanup: {e}")

    @contextmanager
    def pdf_resource(self, file_path: Path, file_id: str = None):
        """
        Context manager for PDF resources with pooling

        Args:
            file_path: Path to PDF file
            file_id: Optional identifier for resource pooling
        """
        doc = None
        doc_id = file_id or str(file_path)

        try:
            import fitz  # PyMuPDF

            # Check if PDF is already in pool
            if doc_id in self.pdf_pool:
                doc = self.pdf_pool[doc_id]
                self._log_memory_info(f"♻️ Reusing PDF resource: {doc_id}")
            else:
                # Create new PDF resource
                doc = fitz.open(str(file_path))
                self.pdf_pool[doc_id] = doc
                self._log_memory_info(f"📄 Created PDF resource: {doc_id}")

            yield doc

        except ImportError:
            raise Exception("PyMuPDF not available")
        except Exception as e:
            self.logger.error(f"Error with PDF resource {doc_id}: {e}")
            raise
        finally:
            # Note: Don't close PDF here - managed by pool and force_cleanup
            pass

    def register_temp_file(self, temp_path: Path):
        """Register a temporary file for cleanup"""
        if temp_path and temp_path not in self.temp_files:
            self.temp_files.append(temp_path)
            self._log_memory_info(f"📄 Registered temp file: {temp_path.name}")

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get memory management statistics"""
        return {
            'processed_files': self.processed_files_count,
            'memory_state': self.get_memory_state().value,
            'pdf_pool_size': len(self.pdf_pool),
            'temp_files_count': len(self.temp_files),
            'config': {
                'batch_size': self.config.batch_size,
                'max_memory_percent': self.config.max_memory_percent,
                'max_file_size_mb': self.config.max_file_size_mb
            },
            'current_memory': self.get_memory_info()
        }

    def start_background_monitoring(self, interval_seconds: int = 30):
        """Start background memory monitoring"""
        def monitor_memory():
            while self.is_monitoring:
                try:
                    memory_state = self.get_memory_state()
                    if memory_state in [MemoryState.CRITICAL, MemoryState.OUT_OF_MEMORY]:
                        self._log_memory_info(f"⚠️ Background monitoring detected {memory_state.value} memory", "WARNING")
                        self.force_cleanup()

                    time.sleep(interval_seconds)
                except Exception as e:
                    self.logger.error(f"Error in background monitoring: {e}")
                    time.sleep(interval_seconds)

        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=monitor_memory, daemon=True)
            self.monitoring_thread.start()
            self._log_memory_info(f"🔍 Started background monitoring (interval: {interval_seconds}s)")

    def stop_background_monitoring(self):
        """Stop background memory monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            self._log_memory_info("🔍 Stopped background monitoring")

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_background_monitoring()
            self.force_cleanup()
        except Exception:
            pass  # Ignore errors during cleanup


# Decorator for memory-managed operations
def memory_managed(operation_name: str = None):
    """Decorator for automatic memory management"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            memory_manager = getattr(self, 'memory_manager', None)
            op_name = operation_name or func.__name__

            try:
                if memory_manager:
                    memory_manager._log_memory_info(f"🚀 Starting {op_name}")

                    # Check memory before operation
                    if not memory_manager.check_memory_before_operation():
                        raise MemoryError(f"Insufficient memory for {op_name}")

                    result = func(self, *args, **kwargs)

                    # Update processed count
                    memory_manager.processed_files_count += 1

                    # Periodic cleanup
                    if memory_manager.processed_files_count % memory_manager.config.cleanup_interval == 0:
                        memory_manager.perform_periodic_cleanup()

                    memory_manager._log_memory_info(f"✅ Completed {op_name}")
                    return result

                else:
                    # No memory manager available
                    return func(self, *args, **kwargs)

            except MemoryError as e:
                if memory_manager:
                    memory_manager._log_memory_info(f"❌ Memory error in {op_name}: {str(e)}", "ERROR")
                raise
            except Exception as e:
                if memory_manager:
                    memory_manager._log_memory_info(f"❌ Error in {op_name}: {str(e)}", "ERROR")
                raise

        return wrapper
    return decorator