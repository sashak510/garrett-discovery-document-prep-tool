"""
Centralized configuration for Garrett Discovery Document Prep Tool
Contains all shared constants and settings
"""

# Font configuration - MANDATORY Times New Roman for legal documents
LEGAL_FONT_NAME = "Times-Roman"
LEGAL_FONT_SIZE_NORMAL = 8
LEGAL_FONT_SIZE_SMALL = 7

# Universal Line Numbering Configuration
GUTTER_MARGIN_INCHES = 0.25
GUTTER_WIDTH_INCHES = 0.25
TOTAL_LENGTH_INCHES = 10.0
LINES_PER_PAGE = 28

# Colors
BACKGROUND_COLOR_LIGHT_GREY = (0.9, 0.9, 0.9)  # Light grey for footer backgrounds
FONT_COLOR_BLACK = (0, 0, 0)  # Black for all text (except line numbers)
LINE_NUMBER_COLOR_RED = (1.0, 0.0, 0.0)  # Red for line numbers

# Margins (in points, 1 inch = 72 points)
PRINTER_SAFE_MARGIN_INCHES = 0.5
PRINTER_SAFE_MARGIN_POINTS = 36  # 0.5 inches
BOTTOM_MARGIN_POINTS = 20  # Distance from bottom edge

# Footer configuration - consistent styling for filename and Bates number
FOOTER_FONT_NAME = "Times-Roman"
FOOTER_FONT_SIZE = 9
FOOTER_FONT_COLOR = (0, 0, 0)  # Black for both filename and Bates number