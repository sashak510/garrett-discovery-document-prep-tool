"""
Logger Manager Module
Manages comprehensive logging for the document processing application
"""

import os
import logging
from pathlib import Path
from datetime import datetime
import json


class LoggerManager:
    """Manages logging for document processing operations"""
    
    def __init__(self, log_directory=None, log_callback=None):
        """
        Initialize the logger manager
        
        Args:
            log_directory (str): Directory for log files (optional)
            log_callback: Optional callback function for real-time logging
        """
        self.log_callback = log_callback
        self.log_directory = log_directory
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize log data structures
        self.processing_log = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'source_folder': None,
            'bates_prefix': None,
            'bates_start_number': None,
            'files_scanned': [],
            'files_not_copied': [],
            'files_converted': [],
            'conversion_failures': [],
            'files_processed': [],
            'processing_errors': [],
            'statistics': {}
        }
        
        # Set up file logging if directory provided
        if self.log_directory:
            self.setup_file_logging()
            
    def log(self, message, level='INFO'):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        
        # Send to callback if available
        if self.log_callback:
            self.log_callback(formatted_message)
            
        # Log to file if configured
        if hasattr(self, 'file_logger'):
            if level == 'ERROR':
                self.file_logger.error(message)
            elif level == 'WARNING':
                self.file_logger.warning(message)
            elif level == 'DEBUG':
                self.file_logger.debug(message)
            else:
                self.file_logger.info(message)
                
    def setup_file_logging(self):
        """Set up file-based logging"""
        log_dir = Path(self.log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log filename with timestamp
        log_filename = f"document_processor_{self.session_id}.log"
        log_path = log_dir / log_filename
        
        # Configure file logger
        self.file_logger = logging.getLogger(f'DocumentProcessor_{self.session_id}')
        self.file_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.file_logger.handlers[:]:
            self.file_logger.removeHandler(handler)
            
        # Create file handler
        file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.file_logger.addHandler(file_handler)
        
        self.log(f"File logging initialized: {log_path}")
        
    def start_processing_session(self, source_folder, bates_prefix, bates_start_number):
        """Start a new processing session"""
        self.processing_log['source_folder'] = source_folder
        self.processing_log['bates_prefix'] = bates_prefix
        self.processing_log['bates_start_number'] = bates_start_number
        self.processing_log['start_time'] = datetime.now().isoformat()
        
        self.log(f"Starting processing session: {self.session_id}")
        self.log(f"Source folder: {source_folder}")
        self.log(f"Bates prefix: {bates_prefix}")
        self.log(f"Starting bates number: {bates_start_number}")
        
    def log_files_scanned(self, files_found):
        """Log the results of file scanning"""
        self.processing_log['files_scanned'] = files_found
        
        # Create summary
        file_types = {}
        total_size = 0
        
        for file_info in files_found:
            file_type = file_info.get('type', 'unknown')
            if file_type not in file_types:
                file_types[file_type] = 0
            file_types[file_type] += 1
            
            size_mb = file_info.get('size_mb', 0)
            if isinstance(size_mb, (int, float)):
                total_size += size_mb
                
        self.log(f"Files scanned: {len(files_found)} files found")
        self.log(f"Total size: {total_size:.2f} MB")
        
        for file_type, count in file_types.items():
            self.log(f"  {file_type}: {count} files")
            
    def log_file_not_copied(self, file_path, reason):
        """Log a file that was not copied to RR folder"""
        entry = {
            'file': file_path,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self.processing_log['files_not_copied'].append(entry)
        self.log(f"File not copied: {file_path} - {reason}", 'WARNING')
        
    def log_file_converted(self, original_path, converted_path, file_type):
        """Log a successful file conversion"""
        entry = {
            'original': original_path,
            'converted': converted_path,
            'type': file_type,
            'timestamp': datetime.now().isoformat()
        }
        self.processing_log['files_converted'].append(entry)
        self.log(f"Converted {file_type}: {Path(original_path).name}")
        
    def log_conversion_failure(self, file_path, error, file_type):
        """Log a file conversion failure"""
        entry = {
            'file': file_path,
            'error': str(error),
            'type': file_type,
            'timestamp': datetime.now().isoformat()
        }
        self.processing_log['conversion_failures'].append(entry)
        self.log(f"Conversion failed: {Path(file_path).name} - {error}", 'ERROR')
        
    def log_file_processed(self, file_path, bates_number, line_range=None, bates_range=None):
        """Log a successfully processed file"""
        entry = {
            'file': file_path,
            'bates_number': bates_number,
            'line_range': line_range,
            'bates_range': bates_range,
            'timestamp': datetime.now().isoformat()
        }
        self.processing_log['files_processed'].append(entry)

        # Display bates range if available, otherwise use single bates number
        display_bates = bates_range if bates_range else bates_number

        if line_range and line_range != "no lines":
            self.log(f"Processed: {Path(file_path).name} - {display_bates} (lines {line_range})")
        elif line_range == "no lines":
            self.log(f"Processed: {Path(file_path).name} - {display_bates} (N/A)")
        else:
            self.log(f"Processed: {Path(file_path).name} - {display_bates}")
            
    def log_processing_error(self, file_path, error, operation):
        """Log a processing error"""
        entry = {
            'file': file_path,
            'error': str(error),
            'operation': operation,
            'timestamp': datetime.now().isoformat()
        }
        self.processing_log['processing_errors'].append(entry)
        self.log(f"Processing error in {operation}: {Path(file_path).name} - {error}", 'ERROR')
        
    def finalize_session(self):
        """Finalize the processing session and generate final statistics"""
        self.processing_log['end_time'] = datetime.now().isoformat()
        
        # Calculate statistics
        stats = {
            'total_files_scanned': len(self.processing_log['files_scanned']),
            'total_files_not_copied': len(self.processing_log['files_not_copied']),
            'total_files_converted': len(self.processing_log['files_converted']),
            'total_conversion_failures': len(self.processing_log['conversion_failures']),
            'total_files_processed': len(self.processing_log['files_processed']),
            'total_processing_errors': len(self.processing_log['processing_errors']),
            'success_rate': 0
        }
        
        # Calculate success rate
        total_attempted = stats['total_files_scanned'] - stats['total_files_not_copied']
        if total_attempted > 0:
            stats['success_rate'] = (stats['total_files_processed'] / total_attempted) * 100
            
        self.processing_log['statistics'] = stats
        
        # Log final statistics
        self.log("=== PROCESSING COMPLETE ===")
        self.log(f"Files scanned: {stats['total_files_scanned']}")
        self.log(f"Files not copied: {stats['total_files_not_copied']}")
        self.log(f"Files converted: {stats['total_files_converted']}")
        self.log(f"Conversion failures: {stats['total_conversion_failures']}")
        self.log(f"Files processed: {stats['total_files_processed']}")
        self.log(f"Processing errors: {stats['total_processing_errors']}")
        self.log(f"Success rate: {stats['success_rate']:.1f}%")
        
        return stats
        
    def save_log_file(self, output_directory):
        """Save comprehensive log file in JSON format"""
        if not output_directory:
            return None
            
        log_dir = Path(output_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log filename
        log_filename = f"processing_log_{self.session_id}.json"
        log_path = log_dir / log_filename
        
        try:
            # Save log as JSON
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.processing_log, f, indent=2, ensure_ascii=False)
                
            self.log(f"Log file saved: {log_path}")
            return str(log_path)
            
        except Exception as e:
            self.log(f"Error saving log file: {e}", 'ERROR')
            return None
            
    def create_summary_report(self, output_directory):
        """Create a human-readable summary report"""
        if not output_directory:
            return None
            
        log_dir = Path(output_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create report filename
        report_filename = f"processing_summary_{self.session_id}.txt"
        report_path = log_dir / report_filename
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("LEGAL DOCUMENT PROCESSING REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                # Session information
                f.write("PROCESSING SESSION DETAILS\n")
                f.write("-" * 30 + "\n")
                f.write(f"Date/Time: {self.processing_log['start_time'][:19].replace('T', ' ')}\n")
                f.write(f"Source Folder: {self.processing_log['source_folder']}\n")
                f.write(f"Bates Prefix: {self.processing_log['bates_prefix']}\n")
                f.write(f"Starting Bates Number: {self.processing_log['bates_start_number']}\n\n")
                
                # Statistics
                stats = self.processing_log.get('statistics', {})
                f.write("PROCESSING SUMMARY\n")
                f.write("-" * 25 + "\n")
                f.write(f"Total Documents Found: {stats.get('total_files_scanned', 0)}\n")
                f.write(f"Documents Successfully Processed: {stats.get('total_files_processed', 0)}\n")
                f.write(f"Documents with Errors: {stats.get('total_processing_errors', 0)}\n")
                f.write(f"Success Rate: {stats.get('success_rate', 0):.1f}%\n\n")
                
                # Files not copied
                if self.processing_log['files_not_copied']:
                    f.write("FILES NOT COPIED\n")
                    f.write("-" * 20 + "\n")
                    for entry in self.processing_log['files_not_copied']:
                        f.write(f"  {entry['file']} - {entry['reason']}\n")
                    f.write("\n")
                    
                # Conversion failures
                if self.processing_log['conversion_failures']:
                    f.write("CONVERSION FAILURES\n")
                    f.write("-" * 20 + "\n")
                    for entry in self.processing_log['conversion_failures']:
                        f.write(f"  {entry['file']} ({entry['type']}) - {entry['error']}\n")
                    f.write("\n")
                    
                # Processing errors
                if self.processing_log['processing_errors']:
                    f.write("PROCESSING ERRORS\n")
                    f.write("-" * 18 + "\n")
                    for entry in self.processing_log['processing_errors']:
                        f.write(f"  {entry['file']} ({entry['operation']}) - {entry['error']}\n")
                    f.write("\n")
                    
                # Successfully processed files
                if self.processing_log['files_processed']:
                    f.write("BATES NUMBERED DOCUMENTS\n")
                    f.write("-" * 30 + "\n")
                    f.write("The following documents have been processed with Bates numbering and line numbers:\n\n")
                    
                    for entry in self.processing_log['files_processed']:
                        file_name = Path(entry['file']).name
                        bates = entry['bates_number']
                        line_range = entry.get('line_range', '')
                        if line_range and line_range != "no lines":
                            f.write(f"  {file_name}\n")
                            f.write(f"    Bates Number: {bates}\n")
                            f.write(f"    Line Numbers: {line_range}\n\n")
                        elif line_range == "no lines":
                            f.write(f"  {file_name}\n")
                            f.write(f"    Bates Number: {bates}\n")
                            f.write(f"    Line Numbers: N/A (empty document)\n\n")
                        else:
                            f.write(f"  {file_name} - Bates Number: {bates}\n\n")
                            
            self.log(f"Summary report saved: {report_path}")
            return str(report_path)
            
        except Exception as e:
            self.log(f"Error creating summary report: {e}", 'ERROR')
            return None
            
    def get_processing_statistics(self):
        """Get current processing statistics"""
        return self.processing_log.get('statistics', {})
        
    def get_session_info(self):
        """Get session information"""
        return {
            'session_id': self.processing_log['session_id'],
            'start_time': self.processing_log['start_time'],
            'source_folder': self.processing_log['source_folder'],
            'bates_prefix': self.processing_log['bates_prefix'],
            'bates_start_number': self.processing_log['bates_start_number']
        }


if __name__ == "__main__":
    # Test the logger manager
    def test_callback(message):
        print(f"[CALLBACK] {message}")
        
    # Test with callback
    logger = LoggerManager(log_callback=test_callback)
    
    logger.start_processing_session("/test/folder", "TEST", 1)
    logger.log_files_scanned([
        {'path': '/test/file1.pdf', 'type': 'pdf', 'size_mb': 1.5},
        {'path': '/test/file2.docx', 'type': 'word', 'size_mb': 0.8}
    ])
    logger.log_file_converted('/test/file2.docx', '/test/file2.pdf', 'word')
    logger.log_file_processed('/test/file1.pdf', 'TEST0001', '1-25')
    
    stats = logger.finalize_session()
    print("\nFinal statistics:", stats)
