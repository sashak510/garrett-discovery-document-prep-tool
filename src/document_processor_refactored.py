"""
Refactored Document Processor with extracted methods for better maintainability
This shows the recommended structure for breaking down large methods
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import tempfile
import os
import shutil
import time
from dataclasses import dataclass

# Import existing components
from pipelines.base_pipeline import BasePipeline
from pipelines.text_pipeline import TextPipeline
from pipelines.native_pdf_pipeline import NativePDFPipeline
from pipelines.scan_image_pipeline import ScanImagePipeline
from bates_numbering import BatesNumberer
from error_handling import ErrorHandler
from memory_manager import MemoryManager, MemoryConfig
from thread_safe_state import ThreadSafeProcessingState, ProcessingState


@dataclass
class ProcessingEnvironment:
    """Container for processing environment setup"""
    bates_numberer: BatesNumberer
    error_handler: ErrorHandler
    memory_manager: MemoryManager
    state_manager: ThreadSafeProcessingState
    output_folder: Path
    temp_folder: Path
    file_queue: List[Path]


class DocumentProcessorRefactored:
    """
    Refactored document processor with separated concerns
    """

    def __init__(self, log_callback: Optional[Callable] = None):
        self.log_callback = log_callback or print

        # Core components
        self.bates_numberer = BatesNumberer()
        self.error_handler = ErrorHandler(log_callback=log_callback)
        self.memory_manager = MemoryManager(log_callback=log_callback)
        self.state_manager = ThreadSafeProcessingState(log_callback=log_callback)

        # Initialize processing components
        self._initialize_pipelines()

    def log(self, message: str):
        """Thread-safe logging"""
        if self.log_callback:
            self.log_callback(message)

    def _initialize_pipelines(self):
        """Initialize all processing pipelines"""
        self.pipelines = {
            'text': TextPipeline(self.bates_numberer),
            'native_pdf': NativePDFPipeline(self.bates_numberer),
            'scan_image': ScanImagePipeline(self.bates_numberer)
        }

    def process_all_documents(
        self,
        source_folder: str,
        output_folder: str,
        bates_prefix: str,
        bates_start: int,
        file_naming_start: int
    ) -> Dict[str, Any]:
        """
        Main processing method - now much cleaner and focused on orchestration
        """
        # Setup processing environment
        env = self._setup_processing_environment(
            source_folder, output_folder, bates_prefix, bates_start, file_naming_start
        )

        # Execute processing pipeline
        results = self._execute_processing_pipeline(env)

        # Finalize and cleanup
        return self._finalize_processing_session(env, results)

    def _setup_processing_environment(
        self,
        source_folder: str,
        output_folder: str,
        bates_prefix: str,
        bates_start: int,
        file_naming_start: int
    ) -> ProcessingEnvironment:
        """
        Setup processing environment and validate inputs
        """
        self.log("🚀 Setting up processing environment...")

        # Validate inputs
        validation_errors = self._validate_processing_inputs(
            source_folder, output_folder, bates_prefix, bates_start, file_naming_start
        )

        if validation_errors:
            raise ValueError(f"Validation failed: {'; '.join(validation_errors)}")

        # Create directories
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create temporary folder
        temp_folder = Path(tempfile.mkdtemp(prefix="gdi_processing_"))

        # Discover files
        file_queue = self._discover_and_queue_files(source_folder)

        # Configure memory management
        memory_config = MemoryConfig(
            batch_size=min(len(file_queue), 5),  # Adaptive batch size
            max_file_size_mb=100,
            enable_monitoring=True
        )
        self.memory_manager.config = memory_config

        self.log(f"📁 Found {len(file_queue)} files to process")

        return ProcessingEnvironment(
            bates_numberer=self.bates_numberer,
            error_handler=self.error_handler,
            memory_manager=self.memory_manager,
            state_manager=self.state_manager,
            output_folder=output_path,
            temp_folder=temp_folder,
            file_queue=file_queue
        )

    def _validate_processing_inputs(
        self,
        source_folder: str,
        output_folder: str,
        bates_prefix: str,
        bates_start: int,
        file_naming_start: int
    ) -> List[str]:
        """
        Validate all processing inputs
        """
        source_path = Path(source_folder)

        # Use existing error handler for validation
        return self.error_handler.validate_input_parameters(
            bates_prefix, bates_start, file_naming_start, source_path
        )

    def _discover_and_queue_files(self, source_folder: str) -> List[Path]:
        """
        Discover and queue files for processing
        """
        source_path = Path(source_folder)
        file_queue = []

        # Scan for PDF files
        for pdf_file in source_path.glob("**/*.pdf"):
            if self._should_process_file(pdf_file):
                file_queue.append(pdf_file)

        # Sort files for consistent processing
        file_queue.sort(key=lambda x: x.name.lower())

        return file_queue

    def _should_process_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be processed
        """
        # Skip temporary files
        if file_path.name.startswith('~') or file_path.name.startswith('.'):
            return False

        # Skip files that are too large
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 200:  # 200MB limit
                self.log(f"⚠️  Skipping large file: {file_path.name} ({file_size_mb:.1f}MB)")
                return False
        except (OSError, PermissionError):
            return False

        return True

    def _execute_processing_pipeline(self, env: ProcessingEnvironment) -> Dict[str, Any]:
        """
        Execute the main processing pipeline
        """
        with env.state_manager.processing_context(ProcessingState.PROCESSING):
            self.log("🔄 Starting document processing pipeline...")

            total_files = len(env.file_queue)
            processed_count = 0

            for file_index, file_path in enumerate(env.file_queue):
                if not env.state_manager.should_continue:
                    break

                # Update progress
                progress = file_index / total_files if total_files > 0 else 0
                env.state_manager.update_progress(progress)
                env.state_manager.update_current_file(file_path.name)

                # Process single file
                result = self._process_single_file(
                    file_path, env, file_index, file_naming_start
                )

                if result['success']:
                    processed_count += 1
                    env.state_manager.increment_files_processed()
                    env.state_manager.add_bytes_processed(result['bytes_processed'])
                else:
                    env.state_manager.increment_files_failed()

                # Log progress periodically
                if file_index % 10 == 0 or file_index == total_files - 1:
                    self.log(f"📊 Progress: {processed_count}/{total_files} files processed")

            return {
                'total_files': total_files,
                'processed_files': processed_count,
                'failed_files': total_files - processed_count,
                'success_rate': processed_count / total_files if total_files > 0 else 0
            }

    def _process_single_file(
        self,
        file_path: Path,
        env: ProcessingEnvironment,
        file_index: int,
        file_naming_start: int
    ) -> Dict[str, Any]:
        """
        Process a single document file
        """
        start_time = time.time()

        try:
            # Validate PDF integrity
            if not env.error_handler.validate_pdf_integrity(file_path):
                return {
                    'success': False,
                    'error': 'PDF validation failed',
                    'bytes_processed': 0,
                    'processing_time': 0
                }

            # Determine pipeline type
            pipeline_type = self._determine_pipeline_type(file_path)

            # Generate output path
            clean_stem = self._clean_filename_stem(file_path.stem)
            sequential_number = file_naming_start + file_index
            output_filename = f"{sequential_number:04d}_{clean_stem}_{pipeline_type}.pdf"
            output_path = env.output_folder / output_filename

            # Get appropriate pipeline
            pipeline = self.pipelines[pipeline_type]

            # Process the document
            pipeline.process_document(
                source_path=file_path,
                output_path=output_path,
                file_sequential_number=f"{sequential_number:04d}",
                bates_prefix=bates_prefix,
                bates_start_number=bates_start + file_index
            )

            processing_time = time.time() - start_time
            file_size = file_path.stat().st_size

            return {
                'success': True,
                'pipeline_used': pipeline_type,
                'output_path': str(output_path),
                'bytes_processed': file_size,
                'processing_time': processing_time
            }

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to process {file_path.name}: {str(e)}"
            self.log(f"❌ {error_msg}")

            return {
                'success': False,
                'error': error_msg,
                'bytes_processed': 0,
                'processing_time': processing_time
            }

    def _determine_pipeline_type(self, file_path: Path) -> str:
        """
        Determine the appropriate pipeline for a file
        """
        # This would contain the logic from the original _detect_document_type method
        # For brevity, returning a default value
        return 'native_pdf'

    def _clean_filename_stem(self, stem: str) -> str:
        """
        Clean filename stem for safe output naming
        """
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            stem = stem.replace(char, '_')

        # Limit length
        if len(stem) > 50:
            stem = stem[:47] + '...'

        return stem.strip()

    def _finalize_processing_session(
        self,
        env: ProcessingEnvironment,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Finalize processing and generate final report
        """
        self.log("🏁 Finalizing processing session...")

        # Cleanup temporary folder
        try:
            shutil.rmtree(env.temp_folder)
        except Exception as e:
            self.log(f"⚠️  Failed to cleanup temp folder: {str(e)}")

        # Get final metrics
        metrics = env.state_manager.get_metrics()

        # Generate final report
        final_report = {
            **results,
            **metrics,
            'processing_complete': True,
            'output_folder': str(env.output_folder)
        }

        self.log(f"✅ Processing complete: {results['processed_files']}/{results['total_files']} files processed")

        return final_report

    def stop_processing(self):
        """Stop all processing"""
        self.state_manager.force_stop()
        self.log("🛑 Processing stop requested")

    def pause_processing(self):
        """Pause current processing"""
        self.state_manager.pause_processing()
        self.log("⏸️ Processing paused")

    def resume_processing(self):
        """Resume paused processing"""
        self.state_manager.resume_processing()
        self.log("▶️ Processing resumed")

    def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status"""
        return self.state_manager.get_metrics()