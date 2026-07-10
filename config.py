# -*- coding: utf-8 -*-
"""
JMA Weather Desktop GUI System - Configuration
農業部水產試驗所 漁海況研究小組

Global configuration settings for the application.
"""

import os
from pathlib import Path

# =============================================================================
# Application Information
# =============================================================================
APP_TITLE = "JMA 氣象海況展示系統"
APP_VERSION = "1.0.0"
ORGANIZATION = "農業部水產試驗所 漁海況研究小組"

# =============================================================================
# Data Source URLs
# =============================================================================
HIMSST_BASE_URL = "https://www.data.jma.go.jp/goos/data/pub/JMA-product/him_sst_pac_D/"
NPRSUBT_BASE_URL = "https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subt_jpn_D/"
NPRSUBC_BASE_URL = "https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subc_jpn_D/"

# =============================================================================
# Data Directories
# =============================================================================
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = BASE_DIR / "data"
HIMSST_DATA_DIR = DATA_DIR / "himsst"
NPRSUBT_DATA_DIR = DATA_DIR / "nprsubt"
NPRSUBC_DATA_DIR = DATA_DIR / "nprsubc"

# Create directories if they don't exist
for directory in [DATA_DIR, HIMSST_DATA_DIR, NPRSUBT_DATA_DIR, NPRSUBC_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Data Format Specifications
# =============================================================================

# HIMSST Data Format
HIMSST_CONFIG = {
    "lat_start": 60.0,      # North boundary
    "lat_end": 0.0,         # South boundary
    "lon_start": 100.0,     # West boundary  
    "lon_end": 180.0,       # East boundary
    "lat_resolution": 0.1,  # degrees
    "lon_resolution": 0.1,  # degrees
    "n_rows": 600,          # Number of data records
    "n_cols": 800,          # Grid points per record
    "value_scale": 0.1,     # Convert to Celsius
    "missing_value": 999,   # Land/undefined
    "ice_value": 888,       # Sea ice
}

# NPRSUBT Data Format
NPRSUBT_CONFIG = {
    "lat_start": 56.2,      # North boundary
    "lat_end": 16.8,        # South boundary
    "lon_start": 113.545455,  # West boundary
    "lon_end": 163.454545,    # East boundary
    "lat_resolution": 0.1,    # degrees
    "lon_resolution": 1/11,   # degrees (~0.0909)
    "n_rows": 395,            # Number of data records per depth
    "n_cols": 550,            # Grid points per record
    "value_scale": 0.01,      # Convert to Celsius
    "missing_value": 9999,    # Undefined/bottom
    "depths": [50, 100, 200, 400],  # Available depths in meters
}

# NPRSUBC Data Format (Surface Currents)
NPRSUBC_CONFIG = {
    "lat_start": 56.25,       # North boundary
    "lat_end": 16.75,         # South boundary
    "lon_start": 113.5,       # West boundary
    "lon_end": 163.5,         # East boundary
    "lat_resolution": 0.1,    # degrees
    "lon_resolution": 1/11,   # degrees (~0.0909)
    "n_rows": 396,            # Number of data records per component
    "n_cols": 551,            # Grid points per record
    "value_scale": 0.01,      # Convert to m/s (from cm/s)
    "missing_value": 9999,    # Undefined/bottom
}

# =============================================================================
# Visualization Settings
# =============================================================================

# Initial map extent (N, S, E, W)
INITIAL_EXTENT = {
    "lat_min": 17,
    "lat_max": 56,
    "lon_min": 114,
    "lon_max": 162,
}

# Color map settings
SST_COLORMAP = "jet"
SST_VMIN = 0     # Minimum temperature for colorbar
SST_VMAX = 32    # Maximum temperature for colorbar

CURRENT_COLORMAP = "viridis"
CURRENT_SCALE = 25  # Arrow scale factor

# Isotherm settings
ISOTHERM_LEVELS_DEFAULT = [5, 10, 15, 20, 25, 30]
ISOTHERM_COLOR = "black"
ISOTHERM_LINEWIDTH = 0.8

# =============================================================================
# Download Settings
# =============================================================================
MAX_FILES_TO_DOWNLOAD = 10
REQUEST_TIMEOUT = 60  # seconds
RETRY_COUNT = 3
RETRY_DELAY = 2  # seconds

# =============================================================================
# GUI Theme Settings
# =============================================================================
THEME_COLORS = {
    "primary": "#1a237e",       # Deep blue
    "secondary": "#0d47a1",     # Blue
    "accent": "#00bcd4",        # Cyan
    "background": "#0a1628",    # Dark navy
    "surface": "#1e2d4a",       # Dark blue-gray
    "text": "#ffffff",          # White
    "text_secondary": "#b0bec5",  # Light gray
    "success": "#4caf50",       # Green
    "warning": "#ff9800",       # Orange
    "error": "#f44336",         # Red
}

FONT_FAMILY = "Microsoft JhengHei"  # 微軟正黑體
FONT_SIZE_TITLE = 18
FONT_SIZE_HEADER = 14
FONT_SIZE_NORMAL = 11
FONT_SIZE_SMALL = 9
