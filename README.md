# Garrett Discovery Document Prep Tool

tive'Professional document processing tool for legal discovery with intelligent pipeline routing, line numbering, and bates stamping.

## Requirements

- **Python 3.9+** (Enterprise Compatible)
- Windows OS
- Tesseract OCR (automatically installed)

## Installation

1. **Install Python 3.9+**
   - Download from [python.org](https://python.org)
   - ✅ Check "Add Python to PATH" during installation

2. **Run Installer**
   ```
   cd installation
   python install_demo.py
   ```

3. **Launch Application**
   - Double-click: `Launch Garrett Discovery Document Prep Tool.vbs`

## Features

- **Smart Pipeline Detection**: Automatically routes documents to optimal processing pipeline
- **Line Numbering**: Sequential numbering with legal formatting (Times New Roman, red text)
- **Bates Numbering**: Legal document stamps with custom prefix and sequential numbering
- **Multi-Format Support**: PDF, Word, Text, TIFF files
- **Rotation Correction**: Automatic detection and correction of rotated documents
- **Professional Output**: Clean, court-ready documents with proper legal formatting

## Processing Pipelines

The tool uses **intelligent pipeline detection** to automatically route documents to the most appropriate processing method:

### 🔍 **Smart Detection Process**
1. **Content Analysis**: Analyzes each page for text, images, forms, and layout
2. **Document Classification**: Determines document type (Native PDF, Scanned, Hybrid, Text-based)
3. **Pipeline Selection**: Routes to optimal processing pipeline
4. **Quality Optimization**: Applies best practices for each document type

### 📄 **Text Pipeline** (`TextPipeline`)
**Used for**: Word documents (.docx), Text files (.txt)
- **Processing**: Direct text extraction and conversion to PDF
- **Line Numbering**: Content-aware positioning based on actual text lines
- **Quality**: 100% accuracy, preserves original formatting
- **Gutter**: Vector-based gutter creation for crisp lines

### 🖼️ **Scan Image Pipeline** (`ScanImagePipeline`)
**Used for**: Scanned PDFs, TIFF files, image-based documents
- **Processing**: OCR text extraction with rotation correction
- **Line Numbering**: Grid-based numbering (28 lines per page)
- **Rotation**: Automatic detection and correction using OCR analysis
- **Quality**: Optimized for scanned documents and images
- **Special Features**: 
  - PDF "printing" to strip metadata and normalize content
  - Smart rotation detection using text readability analysis

### 📋 **Native PDF Pipeline** (`NativePDFPipeline`)
**Used for**: Native PDFs with extractable text, forms, and mixed content
- **Processing**: Direct PDF manipulation preserving vector quality
- **Line Numbering**: Text-based positioning using actual content
- **Quality**: Maintains original PDF quality and formatting
- **Forms**: Preserves fillable forms and annotations

### 🔄 **Hybrid Document Handling**
**Smart routing for mixed content**:
- **Text + Images**: Routed to ScanImage pipeline for best OCR results
- **Forms + Text**: Routed to NativePDF pipeline to preserve form functionality
- **Substantial Text**: Documents with >200 characters prioritized as NativePDF
- **TIFF Files**: Automatically assigned to ScanImage pipeline

## File Numbering System

### **Sequential File Numbering**
- **Only successful files** receive sequential numbers (0001, 0002, 0003...)
- **Failed files** keep original names and go to Failures folder
- **No gaps** in numbering sequence
- **Legal compliance** for discovery document tracking

### **Bates Numbering**
- **Custom prefix** support (e.g., "GAR")
- **Sequential numbering** (0001, 0002, 0003...)
- **Legal positioning** (bottom-right corner)
- **Professional formatting** (Times New Roman, black text)

## Output Structure

```
Input_Folder_Processed/
├── 0001_document1.pdf
├── 0002_document2.pdf
├── 0003_document3.pdf
├── Failures/
│   ├── corrupted_file.pdf
│   └── protected_document.pdf
│   └── landscape.pdf
├── processing_log_YYYYMMDD_HHMMSS.json
└── processing_summary_YYYYMMDD_HHMMSS.txt
```

## Technical Architecture

### **Core Components**
- **`GDIDocumentProcessor`**: Main orchestrator with smart detection
- **`FileScanner`**: Intelligent file discovery and classification
- **`PDFConverter`**: Multi-format conversion with OCR
- **`LineNumberer`**: Content-aware line numbering
- **`BatesNumberer`**: Legal-compliant bates stamping

### **Pipeline Classes**
- **`BasePipeline`**: Abstract base with common functionality
- **`TextPipeline`**: Word/Text document processing
- **`ScanImagePipeline`**: Scanned document and image processing
- **`NativePDFPipeline`**: Native PDF document processing

## Quality Features

### **Rotation Handling**
- **Metadata Analysis**: Detects rotation metadata in PDFs
- **OCR-Based Detection**: Uses text readability to determine correct orientation
- **Physical Rotation**: Applies actual rotation to page content
- **Metadata Stripping**: "Print to PDF" technique removes problematic metadata

### **Content Preservation**
- **Vector Quality**: Maintains original PDF vector graphics
- **Form Functionality**: Preserves fillable forms and annotations
- **Text Quality**: High-quality OCR with fallback options
- **Layout Integrity**: Preserves original document layout and formatting

## Support

For technical issues:
1. Check the processing logs in the output folder
2. Review the `processing_summary_*.txt` file for detailed results
3. Failed files + Landscape (for now) are moved to the `Failures/` folder with error details

## Legal Compliance

- **Sequential numbering** ensures no gaps in document tracking
- **Professional formatting** meets court requirements
- **Audit trail** with comprehensive logging
- **Quality assurance** with multiple processing options
