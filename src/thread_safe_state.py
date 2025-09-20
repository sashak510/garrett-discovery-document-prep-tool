"""
Thread-safe processing state management for Garrett Discovery Document Prep Tool
Provides safe state synchronization between GUI thread and background processing
"""

import threading
import time
from typing import Optional, Callable, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager


class ProcessingState(Enum):
    """Processing states for better state management"""
    IDLE = "idle"
    SCANNING = "scanning"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProcessingMetrics:
    """Thread-safe metrics tracking"""
    files_processed: int = 0
    files_failed: int = 0
    bytes_processed: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def get_duration(self) -> float:
        """Get processing duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0

    def get_files_per_second(self) -> float:
        """Get processing rate"""
        duration = self.get_duration()
        if duration > 0 and self.files_processed > 0:
            return self.files_processed / duration
        return 0.0


class ThreadSafeProcessingState:
    """
    Thread-safe state management for document processing
    Ensures safe access to shared state between GUI and worker threads
    """

    def __init__(self, log_callback: Optional[Callable] = None):
        self._log_callback = log_callback or print

        # State protection
        self._state_lock = threading.RLock()
        self._should_continue = True
        self._processing_state = ProcessingState.IDLE
        self._current_file = ""
        self._progress = 0.0

        # Metrics
        self._metrics = ProcessingMetrics()

        # Thread coordination
        self._processing_thread = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # Start unpaused

    def log(self, message: str):
        """Thread-safe logging"""
        if self._log_callback:
            self._log_callback(message)

    @property
    def should_continue(self) -> bool:
        """Thread-safe access to processing continuation flag"""
        with self._state_lock:
            return self._should_continue

    @should_continue.setter
    def should_continue(self, value: bool):
        """Thread-safe update of processing continuation flag"""
        with self._state_lock:
            old_value = self._should_continue
            self._should_continue = value
            if old_value and not value:
                self.log("Processing stop requested")
                self._processing_state = ProcessingState.IDLE

    @property
    def processing_state(self) -> ProcessingState:
        """Thread-safe access to processing state"""
        with self._state_lock:
            return self._processing_state

    @processing_state.setter
    def processing_state(self, value: ProcessingState):
        """Thread-safe update of processing state"""
        with self._state_lock:
            old_state = self._processing_state
            self._processing_state = value
            if old_state != value:
                self.log(f"State changed: {old_state.value} → {value.value}")

    def set_processing_thread(self, thread: Optional[threading.Thread]):
        """Set the current processing thread"""
        with self._state_lock:
            self._processing_thread = thread

    def get_processing_thread(self) -> Optional[threading.Thread]:
        """Get the current processing thread"""
        with self._state_lock:
            return self._processing_thread

    def pause_processing(self):
        """Pause the current processing"""
        with self._state_lock:
            if self._processing_state in [ProcessingState.PROCESSING, ProcessingState.SCANNING]:
                self._processing_state = ProcessingState.PAUSED
                self._pause_event.clear()
                self.log("Processing paused")

    def resume_processing(self):
        """Resume paused processing"""
        with self._state_lock:
            if self._processing_state == ProcessingState.PAUSED:
                self._processing_state = ProcessingState.PROCESSING
                self._pause_event.set()
                self.log("Processing resumed")

    def wait_if_paused(self):
        """Block processing if paused, return False if should stop"""
        while not self._pause_event.is_set():
            if not self.should_continue:
                return False
            time.sleep(0.1)  # Small sleep to prevent busy waiting
        return True

    def update_current_file(self, filename: str):
        """Update the currently processing file"""
        with self._state_lock:
            self._current_file = filename

    def get_current_file(self) -> str:
        """Get the currently processing file"""
        with self._state_lock:
            return self._current_file

    def update_progress(self, progress: float):
        """Update processing progress (0.0 to 1.0)"""
        with self._state_lock:
            self._progress = max(0.0, min(1.0, progress))

    def get_progress(self) -> float:
        """Get current processing progress"""
        with self._state_lock:
            return self._progress

    def increment_files_processed(self):
        """Increment successful file count"""
        with self._state_lock:
            self._metrics.files_processed += 1

    def increment_files_failed(self):
        """Increment failed file count"""
        with self._state_lock:
            self._metrics.files_failed += 1

    def add_bytes_processed(self, bytes_count: int):
        """Add to total bytes processed"""
        with self._state_lock:
            self._metrics.bytes_processed += bytes_count

    def start_timing(self):
        """Start processing timer"""
        with self._state_lock:
            self._metrics.start_time = time.time()
            self._metrics.end_time = None

    def stop_timing(self):
        """Stop processing timer"""
        with self._state_lock:
            self._metrics.end_time = time.time()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics"""
        with self._state_lock:
            return {
                'files_processed': self._metrics.files_processed,
                'files_failed': self._metrics.files_failed,
                'bytes_processed': self._metrics.bytes_processed,
                'duration_seconds': self._metrics.get_duration(),
                'files_per_second': self._metrics.get_files_per_second(),
                'current_file': self._current_file,
                'progress': self._progress,
                'state': self._processing_state.value
            }

    def reset_metrics(self):
        """Reset all metrics"""
        with self._state_lock:
            self._metrics = ProcessingMetrics()
            self._current_file = ""
            self._progress = 0.0

    @contextmanager
    def processing_context(self, initial_state: ProcessingState = ProcessingState.PROCESSING):
        """
        Context manager for safe processing state management

        Usage:
            with state_manager.processing_context():
                # Do processing work
                pass
        """
        try:
            self.processing_state = initial_state
            self.start_timing()
            self.should_continue = True
            yield self
        except Exception as e:
            self.processing_state = ProcessingState.ERROR
            self.log(f"Processing error: {str(e)}")
            raise
        finally:
            if self.processing_state not in [ProcessingState.PAUSED, ProcessingState.ERROR]:
                self.processing_state = ProcessingState.COMPLETED
            self.stop_timing()

    def force_stop(self):
        """Force stop all processing"""
        with self._state_lock:
            self.should_continue = False
            self._processing_state = ProcessingState.IDLE
            self._pause_event.set()

            # Signal processing thread to stop
            if self._processing_thread and self._processing_thread.is_alive():
                self.log("Force stopping processing thread...")
                # Note: Thread interruption is handled cooperatively via should_continue flag

    def is_processing_active(self) -> bool:
        """Check if processing is currently active"""
        with self._state_lock:
            return self._processing_state in [
                ProcessingState.SCANNING,
                ProcessingState.PROCESSING,
                ProcessingState.PAUSED
            ]

    def can_start_processing(self) -> bool:
        """Check if new processing can be started"""
        with self._state_lock:
            return self._processing_state in [ProcessingState.IDLE, ProcessingState.COMPLETED, ProcessingState.ERROR]