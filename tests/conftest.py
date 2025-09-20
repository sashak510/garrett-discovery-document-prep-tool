"""
Pytest configuration and fixtures for Garrett Discovery Document Prep Tool tests
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_pdf_path(temp_dir):
    """Create a sample PDF file for testing"""
    pdf_path = temp_dir / "sample.pdf"
    # Create a minimal valid PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF"
    pdf_path.write_bytes(pdf_content)
    yield pdf_path


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file for testing"""
    text_path = temp_dir / "sample.txt"
    text_path.write_text("This is a sample text file for testing.\nIt has multiple lines.\nAnd some content.")
    yield text_path


@pytest.fixture
def mock_log_callback():
    """Mock callback for logging"""
    return MagicMock()


@pytest.fixture
def mock_error_handler(mock_log_callback):
    """Mock error handler for testing"""
    from error_handling import ErrorHandler
    return ErrorHandler(log_callback=mock_log_callback)


@pytest.fixture
def sample_source_folder(temp_dir):
    """Create a sample source folder with test files"""
    source_folder = temp_dir / "source"
    source_folder.mkdir()

    # Create test files
    (source_folder / "doc1.pdf").write_text("PDF content 1")
    (source_folder / "doc2.txt").write_text("Text content")
    (source_folder / "empty.txt").write_text("")

    yield source_folder


@pytest.fixture
def document_processor_factory(temp_dir, mock_log_callback):
    """Factory to create document processor instances for testing"""
    from document_processor import GDIDocumentProcessor
    from bates_numbering import BatesNumberer

    def _create_processor(**kwargs):
        defaults = {
            'source_folder': temp_dir / "input",
            'bates_prefix': 'TEST',
            'bates_start_number': 1,
            'file_naming_start': 1,
            'output_folder': temp_dir / "output",
            'log_callback': mock_log_callback,
        }
        defaults.update(kwargs)
        return GDIDocumentProcessor(**defaults)

    return _create_processor


@pytest.fixture
def bates_numberer_factory(mock_log_callback):
    """Factory to create bates numberer instances for testing"""
    from bates_numbering import BatesNumberer

    def _create_bates_numberer(**kwargs):
        defaults = {
            'prefix': 'TEST',
            'start_number': 1,
            'log_callback': mock_log_callback,
        }
        defaults.update(kwargs)
        return BatesNumberer(**defaults)

    return _create_bates_numberer