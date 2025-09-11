"""
File Scanner Module
Scans directories for supported file types (PDF, TIFF, Word, Notepad/Text files)
"""

import os
from pathlib import Path
import logging


class FileScanner:
    """Scans directories for supported document file types"""
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        '.pdf',      # PDF files
        '.tiff',     # TIFF images
        '.tif',      # TIFF images (alternative extension)
        '.docx',     # Word documents (Office Open XML)
        '.doc',      # Word documents (legacy format)
        '.txt',      # Text files (Notepad)
        '.rtf',      # Rich Text Format
    }
    
    def __init__(self, log_callback=None):
        """
        Initialize the file scanner
        
        Args:
            log_callback: Optional callback function for logging messages
        """
        self.log_callback = log_callback
        self.found_files = []
        self.scanned_count = 0
        
    def log(self, message):
        """Log a message using the callback or print"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
            
    def scan_directory(self, directory_path):
        """
        Scan a directory and all subdirectories for supported files
        
        Args:
            directory_path (str): Path to the directory to scan
            
        Returns:
            list: List of dictionaries containing file information
        """
        self.found_files = []
        self.scanned_count = 0
        
        directory = Path(directory_path)
        
        if not directory.exists():
            self.log(f"Error: Directory '{directory_path}' does not exist")
            return []
            
        if not directory.is_dir():
            self.log(f"Error: '{directory_path}' is not a directory")
            return []
            
        self.log(f"Scanning directory: {directory_path}")
        
        try:
            # Walk through all subdirectories
            for root, dirs, files in os.walk(directory_path):
                # Skip hidden directories and common system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                          d.lower() not in ['__pycache__', 'node_modules', '.git']]
                
                for file in files:
                    self.scanned_count += 1
                    file_path = Path(root) / file
                    
                    # Check if file extension is supported
                    if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        file_info = self._get_file_info(file_path)
                        self.found_files.append(file_info)
                        
        except PermissionError as e:
            self.log(f"Permission error scanning directory: {e}")
        except Exception as e:
            self.log(f"Error scanning directory: {e}")
            
        self.log(f"Scan complete. Found {len(self.found_files)} supported files out of {self.scanned_count} total files")
        
        return self.found_files
        
    def _get_file_info(self, file_path):
        """
        Get detailed information about a file
        
        Args:
            file_path (Path): Path object for the file
            
        Returns:
            dict: Dictionary containing file information
        """
        try:
            stat = file_path.stat()
            
            file_info = {
                'path': str(file_path),
                'name': file_path.name,
                'stem': file_path.stem,  # filename without extension
                'extension': file_path.suffix.lower(),
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': stat.st_mtime,
                'directory': str(file_path.parent),
                'relative_path': str(file_path.relative_to(file_path.parents[len(file_path.parents) - 1])),
                'is_readable': os.access(file_path, os.R_OK),
                'type': self._get_file_type(file_path.suffix.lower())
            }
            
            return file_info
            
        except Exception as e:
            self.log(f"Error getting file info for {file_path}: {e}")
            return {
                'path': str(file_path),
                'name': file_path.name,
                'extension': file_path.suffix.lower(),
                'error': str(e),
                'type': 'unknown'
            }
            
    def _get_file_type(self, extension):
        """
        Determine the file type category based on extension
        
        Args:
            extension (str): File extension (with dot)
            
        Returns:
            str: File type category
        """
        type_mapping = {
            '.pdf': 'pdf',
            '.tiff': 'image',
            '.tif': 'image',
            '.docx': 'word',
            '.doc': 'word',
            '.txt': 'text',
            '.rtf': 'text'
        }
        
        return type_mapping.get(extension, 'unknown')
        
    def filter_by_type(self, file_type):
        """
        Filter found files by type
        
        Args:
            file_type (str): Type to filter by ('pdf', 'image', 'word', 'text')
            
        Returns:
            list: Filtered list of files
        """
        return [f for f in self.found_files if f.get('type') == file_type]
        
    def get_file_summary(self):
        """
        Get a summary of found files by type
        
        Returns:
            dict: Summary statistics
        """
        summary = {
            'total_files': len(self.found_files),
            'total_scanned': self.scanned_count,
            'by_type': {},
            'total_size_mb': 0
        }
        
        for file_info in self.found_files:
            file_type = file_info.get('type', 'unknown')
            if file_type not in summary['by_type']:
                summary['by_type'][file_type] = 0
            summary['by_type'][file_type] += 1
            
            # Add to total size
            size_mb = file_info.get('size_mb', 0)
            if isinstance(size_mb, (int, float)):
                summary['total_size_mb'] += size_mb
                
        summary['total_size_mb'] = round(summary['total_size_mb'], 2)
        
        return summary
        
    def get_largest_files(self, count=5):
        """
        Get the largest files found
        
        Args:
            count (int): Number of files to return
            
        Returns:
            list: List of largest files
        """
        # Sort by size (descending) and return top N
        sorted_files = sorted(
            [f for f in self.found_files if 'size' in f],
            key=lambda x: x.get('size', 0),
            reverse=True
        )
        
        return sorted_files[:count]
        
    def get_unreadable_files(self):
        """
        Get list of files that are not readable
        
        Returns:
            list: List of unreadable files
        """
        return [f for f in self.found_files if not f.get('is_readable', True)]


