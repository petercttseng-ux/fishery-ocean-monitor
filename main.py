# -*- coding: utf-8 -*-
"""
JMA Weather Desktop GUI System - Main Application (Enhanced Edition)
農業部水產試驗所 漁海況研究小組

Premium Professional Desktop GUI with Advanced Visualization
Version 2.0 - Enhanced UI/UX with Modern Design
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QTabWidget, QStatusBar, QProgressBar, QMessageBox,
    QFrame, QSizePolicy, QGraphicsDropShadowEffect, QSlider, QSplashScreen,
    QScrollArea, QToolTip, QGraphicsOpacityEffect
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QSequentialAnimationGroup, QPoint, QRect,
    QAbstractAnimation
)
from PyQt5.QtGui import (
    QFont, QColor, QLinearGradient, QPalette, QBrush, QPainter,
    QPixmap, QIcon, QPen, QRadialGradient, QFontDatabase
)

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import config
from data_downloader import JMADataDownloader, get_local_files
from data_parser import JMADataParser, HIMSSTData, NPRSUBTData, NPRSUBCData
from visualizer import JMAVisualizer


# ============================================================================
# Enhanced Color Scheme & Design Tokens
# ============================================================================

class DesignTokens:
    """Centralized design tokens for consistent styling - LIGHT THEME."""
    
    # Primary palette - Ocean inspired
    PRIMARY_GRADIENT_START = "#0288d1"
    PRIMARY_GRADIENT_END = "#01579b"
    PRIMARY = "#0288d1"
    PRIMARY_DARK = "#01579b"
    PRIMARY_LIGHT = "#03a9f4"
    
    # Secondary palette
    SECONDARY = "#e53935"
    SECONDARY_DARK = "#c62828"
    ACCENT_ORANGE = "#fb8c00"
    ACCENT_PURPLE = "#8e24aa"
    ACCENT_GREEN = "#43a047"
    
    # Background palette - Light theme
    BG_WHITE = "#ffffff"
    BG_LIGHTEST = "#fafafa"
    BG_LIGHTER = "#f5f5f5"
    BG_LIGHT = "#eeeeee"
    BG_MEDIUM = "#e0e0e0"
    BG_DARK = "#bdbdbd"
    
    # Text palette - Dark text for light backgrounds
    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#424242"
    TEXT_MUTED = "#757575"
    TEXT_DIM = "#9e9e9e"
    
    # Status colors
    SUCCESS = "#4caf50"
    WARNING = "#ff9800"
    ERROR = "#f44336"
    INFO = "#2196f3"
    
    # Effects
    SHADOW_COLOR = "rgba(0, 0, 0, 0.15)"
    BORDER_COLOR = "#e0e0e0"
    ACCENT_BORDER = "#0288d1"


# ============================================================================
# Custom Styled Widgets - Light Theme Edition
# ============================================================================

class LightButton(QPushButton):
    """Clean button for light theme with clear visibility."""
    
    def __init__(self, text, color="#0288d1", parent=None):
        super().__init__(text, parent)
        self.base_color = color
        self.setMinimumHeight(48)
        self.setMinimumWidth(140)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_style()
        self._setup_shadow()
        
    def _setup_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.base_color}, 
                    stop:1 {self._darken(self.base_color, 30)});
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                padding: 12px 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self._lighten(self.base_color, 20)}, 
                    stop:1 {self.base_color});
            }}
            QPushButton:pressed {{
                background: {self._darken(self.base_color, 40)};
            }}
            QPushButton:disabled {{
                background: #bdbdbd;
                color: #757575;
            }}
        """)
    
    def _setup_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
    
    def _darken(self, color, amount):
        c = QColor(color)
        return QColor(max(0, c.red()-amount), max(0, c.green()-amount), max(0, c.blue()-amount)).name()
    
    def _lighten(self, color, amount):
        c = QColor(color)
        return QColor(min(255, c.red()+amount), min(255, c.green()+amount), min(255, c.blue()+amount)).name()


class LightGroupBox(QGroupBox):
    """Clean group box for light theme."""
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._setup_style()
        
    def _setup_style(self):
        self.setStyleSheet("""
            QGroupBox {
                background: #ffffff;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                margin-top: 20px;
                padding: 15px;
                padding-top: 28px;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 6px 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0288d1, stop:1 #01579b);
                border-radius: 10px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)


class LightComboBox(QComboBox):
    """Clean combo box for light theme with clear visibility."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(42)
        self.setMinimumWidth(150)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_style()
        
    def _setup_style(self):
        self.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 2px solid #bdbdbd;
                border-radius: 8px;
                padding: 10px 15px;
                color: #212121;
                font-size: 14px;
                font-weight: 500;
            }
            QComboBox:hover {
                border: 2px solid #0288d1;
            }
            QComboBox:focus {
                border: 2px solid #01579b;
                background: #f5f5f5;
            }
            QComboBox::drop-down {
                border: none;
                width: 35px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid #0288d1;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 2px solid #0288d1;
                border-radius: 8px;
                selection-background-color: #0288d1;
                selection-color: white;
                color: #212121;
                padding: 5px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 10px 15px;
                border-radius: 5px;
                margin: 2px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #e3f2fd;
            }
        """)


class LightCheckBox(QCheckBox):
    """Clean checkbox for light theme."""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QCheckBox {
                color: #212121;
                font-size: 14px;
                font-weight: 500;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 24px;
                height: 24px;
                border-radius: 6px;
                border: 2px solid #bdbdbd;
                background: #ffffff;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #0288d1;
                background: #e3f2fd;
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0288d1, stop:1 #01579b);
                border: 2px solid #0288d1;
            }
            QCheckBox::indicator:checked:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #03a9f4, stop:1 #0288d1);
                border: 2px solid #03a9f4;
            }
        """)


class LightSpinBox(QDoubleSpinBox):
    """Clean spin box for light theme."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(42)
        self.setMinimumWidth(100)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_style()
        
    def _setup_style(self):
        self.setStyleSheet("""
            QDoubleSpinBox, QSpinBox {
                background: #ffffff;
                border: 2px solid #bdbdbd;
                border-radius: 8px;
                padding: 8px 10px;
                color: #212121;
                font-size: 14px;
                font-weight: bold;
            }
            QDoubleSpinBox:hover, QSpinBox:hover {
                border: 2px solid #0288d1;
            }
            QDoubleSpinBox:focus, QSpinBox:focus {
                border: 2px solid #01579b;
            }
            QDoubleSpinBox::up-button, QSpinBox::up-button {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0288d1, stop:1 #01579b);
                border-radius: 5px;
                width: 22px;
                margin: 2px;
            }
            QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #03a9f4, stop:1 #0288d1);
            }
            QDoubleSpinBox::down-button, QSpinBox::down-button {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0288d1, stop:1 #01579b);
                border-radius: 5px;
                width: 22px;
                margin: 2px;
            }
            QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #03a9f4, stop:1 #0288d1);
            }
            QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid white;
            }
            QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid white;
            }
        """)


class LightHeaderLabel(QLabel):
    """Header label for light theme."""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(70)
        self.setStyleSheet("""
            QLabel {
                color: #01579b;
                font-size: 18px;
                font-weight: bold;
                padding: 15px 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e3f2fd, stop:0.5 #bbdefb, stop:1 #e3f2fd);
                border-radius: 12px;
                border: 2px solid #0288d1;
            }
        """)


# ============================================================================
# Download Thread
# ============================================================================

class DownloadThread(QThread):
    """Background thread for downloading data."""
    progress = pyqtSignal(str, float)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, max_files: int = 10):
        super().__init__()
        self.max_files = max_files
    
    def run(self):
        try:
            downloader = JMADataDownloader(
                progress_callback=lambda msg, prog: self.progress.emit(msg, prog)
            )
            results = downloader.download_all(self.max_files)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


# ============================================================================
# Interactive Canvas
# ============================================================================

class InteractiveCanvas(FigureCanvas):
    """Interactive matplotlib canvas with hover and zoom."""
    
    coordinate_update = pyqtSignal(float, float, float)
    
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(12, 10), dpi=100, facecolor='#0a1628')
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.current_data = None
        self.data_type = None
        self.depth = None
        
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
    
    def on_mouse_move(self, event):
        if event.inaxes is None or self.current_data is None:
            return
        
        lon, lat = event.xdata, event.ydata
        if lon is None or lat is None:
            return
        
        try:
            value = self._get_value_at_point(lat, lon)
            if value is not None:
                self.coordinate_update.emit(lat, lon, value)
        except:
            pass
    
    def _get_value_at_point(self, lat: float, lon: float) -> Optional[float]:
        data = self.current_data
        if data is None:
            return None
        
        lat_idx = np.argmin(np.abs(data.lat - lat))
        lon_idx = np.argmin(np.abs(data.lon - lon))
        
        if isinstance(data, HIMSSTData):
            value = data.sst[lat_idx, lon_idx]
        elif isinstance(data, NPRSUBTData) and self.depth:
            temp = data.temperature.get(self.depth)
            value = temp[lat_idx, lon_idx] if temp is not None else None
        elif isinstance(data, NPRSUBCData):
            value = data.speed[lat_idx, lon_idx]
        else:
            return None
        
        if value is None or np.ma.is_masked(value) or np.isnan(value):
            return None
        return float(value)
    
    def set_data(self, data, data_type: str, depth: int = None):
        self.current_data = data
        self.data_type = data_type
        self.depth = depth


# ============================================================================
# Main Window
# ============================================================================

class MainWindow(QMainWindow):
    """Main application window with enhanced UI."""
    
    def __init__(self):
        super().__init__()
        self.parser = JMADataParser()
        self.visualizer = JMAVisualizer()
        
        self.himsst_data: Dict[str, HIMSSTData] = {}
        self.nprsubt_data: Dict[str, NPRSUBTData] = {}
        self.nprsubc_data: Dict[str, NPRSUBCData] = {}
        
        self.current_extent = [
            config.INITIAL_EXTENT['lon_min'],
            config.INITIAL_EXTENT['lon_max'],
            config.INITIAL_EXTENT['lat_min'],
            config.INITIAL_EXTENT['lat_max']
        ]
        
        self.init_ui()
        self.apply_theme()
        
        QTimer.singleShot(500, self.start_download)
    
    def init_ui(self):
        self.setWindowTitle(f"🌊 {config.APP_TITLE} - {config.ORGANIZATION}")
        self.setGeometry(50, 50, 1700, 950)
        self.setMinimumSize(1400, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 0)
        
        # Plot area
        plot_area = self.create_plot_area()
        main_layout.addWidget(plot_area, 1)
        
        # Status bar
        self.create_status_bar()
    
    def create_control_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(420)
        panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f5f5f5);
                border-radius: 15px;
                border: 2px solid #e0e0e0;
            }
        """)
        
        # Add shadow to panel
        panel_shadow = QGraphicsDropShadowEffect()
        panel_shadow.setBlurRadius(20)
        panel_shadow.setColor(QColor(0, 0, 0, 40))
        panel_shadow.setOffset(3, 3)
        panel.setGraphicsEffect(panel_shadow)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with logo - light theme
        header = LightHeaderLabel(f"🌊 {config.ORGANIZATION}")
        layout.addWidget(header)
        
        # Subtitle with version badge
        subtitle_container = QWidget()
        subtitle_layout = QHBoxLayout(subtitle_container)
        subtitle_layout.setContentsMargins(0, 5, 0, 5)
        subtitle_layout.setSpacing(8)
        
        subtitle = QLabel("JMA 氣象海況展示系統")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            color: #616161; 
            font-size: 14px; 
            font-weight: 500;
        """)
        subtitle_layout.addStretch()
        subtitle_layout.addWidget(subtitle)
        
        version_badge = QLabel("v2.0")
        version_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0288d1, stop:1 #01579b);
            color: white;
            font-size: 11px;
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 8px;
        """)
        subtitle_layout.addWidget(version_badge)
        subtitle_layout.addStretch()
        layout.addWidget(subtitle_container)
        
        # Tab widget - light theme
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background: #ffffff;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                padding: 12px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: #f5f5f5;
                color: #616161;
                padding: 12px 16px;
                margin-right: 3px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: bold;
                font-size: 13px;
                min-width: 90px;
                border: 1px solid #e0e0e0;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0288d1, stop:1 #01579b);
                color: white;
                border: none;
            }
            QTabBar::tab:hover:!selected {
                background: #e3f2fd;
                color: #0288d1;
            }
        """)
        
        self.tab_widget.addTab(self.create_himsst_tab(), "🌡️ HIMSST")
        self.tab_widget.addTab(self.create_nprsubt_tab(), "📊 NPRSUBT")
        self.tab_widget.addTab(self.create_combined_tab(), "🔀 合併顯示")
        layout.addWidget(self.tab_widget)
        
        # Common options group - light theme
        common_group = LightGroupBox("⚙️ 繪圖設定")
        common_layout = QVBoxLayout(common_group)
        common_layout.setSpacing(12)
        
        self.isotherm_check = LightCheckBox("📏 顯示等溫線")
        self.isotherm_check.setChecked(True)
        common_layout.addWidget(self.isotherm_check)
        
        interval_layout = QHBoxLayout()
        interval_layout.setSpacing(10)
        interval_label = QLabel("等溫線間距:")
        interval_label.setStyleSheet("""
            color: #424242; 
            font-size: 14px; 
            font-weight: 500;
        """)
        interval_layout.addWidget(interval_label)
        
        self.interval_spin = LightSpinBox()
        self.interval_spin.setRange(0.5, 10)
        self.interval_spin.setValue(2.0)
        self.interval_spin.setSingleStep(0.5)
        self.interval_spin.setSuffix(" °C")
        interval_layout.addWidget(self.interval_spin)
        common_layout.addLayout(interval_layout)
        
        self.label_check = LightCheckBox("🏷️ 顯示溫度數值標籤")
        self.label_check.setChecked(True)
        common_layout.addWidget(self.label_check)
        
        layout.addWidget(common_group)
        
        # Action buttons - light theme
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        self.refresh_btn = LightButton("🔄 重新下載資料", "#0288d1")
        self.refresh_btn.clicked.connect(self.start_download)
        btn_layout.addWidget(self.refresh_btn)
        
        self.reset_btn = LightButton("🔍 重設視圖範圍", "#8e24aa")
        self.reset_btn.clicked.connect(self.reset_view)
        btn_layout.addWidget(self.reset_btn)
        
        self.clear_btn = LightButton("🗑️ 清除繪圖畫面", "#607d8b")
        self.clear_btn.clicked.connect(self.clear_plot)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        # Footer - light theme
        footer = QLabel("© 2026 農業部水產試驗所\n漁海況研究小組")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color: #757575; 
            font-size: 12px; 
            line-height: 1.5;
            padding: 12px;
            background: #f5f5f5;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            margin-top: 10px;
        """)
        layout.addWidget(footer)
        
        return panel
    
    def create_himsst_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        
        lbl = QLabel("📅 選擇日期:")
        lbl.setStyleSheet("""
            color: #424242; 
            font-size: 14px; 
            font-weight: bold;
        """)
        layout.addWidget(lbl)
        
        self.himsst_date_combo = LightComboBox()
        layout.addWidget(self.himsst_date_combo)
        
        self.himsst_plot_btn = LightButton("🌡️ 繪製海表水溫圖", "#e53935")
        self.himsst_plot_btn.clicked.connect(self.plot_himsst)
        layout.addWidget(self.himsst_plot_btn)
        
        layout.addStretch()
        return tab
    
    def create_nprsubt_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        
        lbl1 = QLabel("📅 選擇日期:")
        lbl1.setStyleSheet("""
            color: #424242; 
            font-size: 14px; 
            font-weight: bold;
        """)
        layout.addWidget(lbl1)
        
        self.nprsubt_date_combo = LightComboBox()
        layout.addWidget(self.nprsubt_date_combo)
        
        lbl2 = QLabel("📏 選擇深度:")
        lbl2.setStyleSheet("""
            color: #424242; 
            font-size: 14px; 
            font-weight: bold;
        """)
        layout.addWidget(lbl2)
        
        self.depth_combo = LightComboBox()
        self.depth_combo.addItems(["50m", "100m", "200m", "400m"])
        layout.addWidget(self.depth_combo)
        
        self.nprsubt_plot_btn = LightButton("📊 繪製水層溫度圖", "#43a047")
        self.nprsubt_plot_btn.clicked.connect(self.plot_nprsubt)
        layout.addWidget(self.nprsubt_plot_btn)
        
        layout.addStretch()
        return tab
    
    def create_combined_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        
        lbl = QLabel("📅 SST 日期:")
        lbl.setStyleSheet("""
            color: #424242; 
            font-size: 14px; 
            font-weight: bold;
        """)
        layout.addWidget(lbl)
        
        self.combined_sst_combo = LightComboBox()
        layout.addWidget(self.combined_sst_combo)
        
        self.current_check = LightCheckBox("🌊 疊加海流向量")
        self.current_check.setChecked(True)
        layout.addWidget(self.current_check)
        
        skip_layout = QHBoxLayout()
        skip_layout.setSpacing(10)
        skip_lbl = QLabel("箭頭間距:")
        skip_lbl.setStyleSheet("""
            color: #424242; 
            font-size: 14px;
            font-weight: 500;
        """)
        skip_layout.addWidget(skip_lbl)
        
        self.arrow_skip_spin = QSpinBox()
        self.arrow_skip_spin.setRange(5, 30)
        self.arrow_skip_spin.setValue(10)
        self.arrow_skip_spin.setMinimumHeight(40)
        self.arrow_skip_spin.setCursor(Qt.PointingHandCursor)
        self.arrow_skip_spin.setStyleSheet("""
            QSpinBox {
                background: #ffffff;
                border: 2px solid #bdbdbd;
                border-radius: 8px;
                padding: 8px 10px;
                color: #212121;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }
            QSpinBox:hover {
                border: 2px solid #0288d1;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #0288d1;
                border-radius: 4px;
                width: 20px;
                margin: 2px;
            }
        """)
        skip_layout.addWidget(self.arrow_skip_spin)
        layout.addLayout(skip_layout)
        
        self.combined_plot_btn = LightButton("🔀 繪製合併圖", "#e91e63")
        self.combined_plot_btn.clicked.connect(self.plot_combined)
        layout.addWidget(self.combined_plot_btn)
        
        layout.addStretch()
        return tab
    
    def create_plot_area(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border-radius: 15px;
                border: 2px solid #e0e0e0;
            }
        """)
        
        # Add shadow to plot area
        plot_shadow = QGraphicsDropShadowEffect()
        plot_shadow.setBlurRadius(20)
        plot_shadow.setColor(QColor(0, 0, 0, 40))
        plot_shadow.setOffset(-3, 3)
        frame.setGraphicsEffect(plot_shadow)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Toolbar - light theme
        self.canvas = InteractiveCanvas(self)
        self.canvas.coordinate_update.connect(self.update_coordinates)
        
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("""
            QToolBar {
                background: #f5f5f5;
                border-radius: 10px;
                padding: 6px 10px;
                spacing: 6px;
                border: 1px solid #e0e0e0;
            }
            QToolButton {
                background: transparent;
                border-radius: 6px;
                padding: 6px;
                margin: 2px;
            }
            QToolButton:hover {
                background: #e3f2fd;
            }
            QToolButton:pressed {
                background: #bbdefb;
            }
        """)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        return frame
    
    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f5f5f5);
                color: #424242;
                font-size: 13px;
                font-weight: 500;
                padding: 8px 15px;
                border-top: 2px solid #e0e0e0;
            }
        """)
        self.setStatusBar(self.status_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(350)
        self.progress_bar.setMinimumHeight(22)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #e0e0e0;
                border: none;
                border-radius: 11px;
                text-align: center;
                color: #424242;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0288d1, stop:1 #03a9f4);
                border-radius: 10px;
            }
        """)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.coord_label = QLabel("📍 經度: -- | 緯度: -- | 數值: --")
        self.coord_label.setStyleSheet("""
            QLabel {
                background: #e3f2fd;
                border: 1px solid #0288d1;
                border-radius: 10px;
                padding: 6px 18px;
                color: #01579b;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.status_bar.addPermanentWidget(self.coord_label)
    
    def apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e8f4fc, 
                    stop:0.5 #f5f5f5, 
                    stop:1 #e8f4fc);
            }}
            QLabel {{
                color: #424242;
            }}
            QToolTip {{
                background: #ffffff;
                color: #424242;
                border: 1px solid #0288d1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QMessageBox {{
                background: #ffffff;
            }}
            QMessageBox QLabel {{
                color: #424242;
                font-size: 13px;
            }}
            QMessageBox QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0288d1, stop:1 #01579b);
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #03a9f4, stop:1 #0288d1);
            }}
        """)
    
    def start_download(self):
        self.refresh_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("🔄 正在下載資料...")
        
        self.download_thread = DownloadThread(config.MAX_FILES_TO_DOWNLOAD)
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()
    
    def on_download_progress(self, message: str, progress: float):
        self.progress_bar.setValue(int(progress * 100))
        self.status_bar.showMessage(f"🔄 {message}")
    
    def on_download_finished(self, results: dict):
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
        
        total = sum(len(v) for v in results.values())
        self.status_bar.showMessage(f"✅ 下載完成: 共 {total} 個檔案")
        
        self.load_local_data()
    
    def on_download_error(self, error: str):
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
        self.status_bar.showMessage(f"❌ 下載錯誤: {error}")
        QMessageBox.warning(self, "下載錯誤", f"資料下載失敗:\n{error}")
        self.load_local_data()
    
    def load_local_data(self):
        self.himsst_data.clear()
        for f in get_local_files('himsst'):
            data = self.parser.parse_himsst(f)
            if data:
                key = data.date.strftime('%Y-%m-%d')
                self.himsst_data[key] = data
        
        self.nprsubt_data.clear()
        for f in get_local_files('nprsubt'):
            data = self.parser.parse_nprsubt(f)
            if data:
                key = data.date.strftime('%Y-%m-%d')
                self.nprsubt_data[key] = data
        
        self.nprsubc_data.clear()
        for f in get_local_files('nprsubc'):
            data = self.parser.parse_nprsubc(f)
            if data:
                key = data.date.strftime('%Y-%m-%d')
                self.nprsubc_data[key] = data
        
        self.update_date_combos()
    
    def update_date_combos(self):
        self.himsst_date_combo.clear()
        self.himsst_date_combo.addItems(sorted(self.himsst_data.keys(), reverse=True))
        
        self.nprsubt_date_combo.clear()
        self.nprsubt_date_combo.addItems(sorted(self.nprsubt_data.keys(), reverse=True))
        
        self.combined_sst_combo.clear()
        self.combined_sst_combo.addItems(sorted(self.himsst_data.keys(), reverse=True))
    
    def plot_himsst(self):
        date = self.himsst_date_combo.currentText()
        if not date or date not in self.himsst_data:
            QMessageBox.warning(self, "錯誤", "請選擇有效的日期")
            return
        
        data = self.himsst_data[date]
        self.canvas.set_data(data, 'himsst')
        
        self.visualizer.plot_himsst(
            data, self.canvas.fig, self.current_extent,
            show_isotherm=self.isotherm_check.isChecked(),
            isotherm_interval=self.interval_spin.value(),
            show_labels=self.label_check.isChecked()
        )
        self.canvas.draw()
        self.status_bar.showMessage(f"🌡️ 已繪製 HIMSST 海表水溫圖 - {date}")
    
    def plot_nprsubt(self):
        date = self.nprsubt_date_combo.currentText()
        if not date or date not in self.nprsubt_data:
            QMessageBox.warning(self, "錯誤", "請選擇有效的日期")
            return
        
        depth = int(self.depth_combo.currentText().replace('m', ''))
        data = self.nprsubt_data[date]
        self.canvas.set_data(data, 'nprsubt', depth)
        
        self.visualizer.plot_nprsubt(
            data, depth, self.canvas.fig, self.current_extent,
            show_isotherm=self.isotherm_check.isChecked(),
            isotherm_interval=self.interval_spin.value(),
            show_labels=self.label_check.isChecked()
        )
        self.canvas.draw()
        self.status_bar.showMessage(f"📊 已繪製 NPRSUBT 水下{depth}m溫度圖 - {date}")
    
    def plot_combined(self):
        sst_date = self.combined_sst_combo.currentText()
        if not sst_date or sst_date not in self.himsst_data:
            QMessageBox.warning(self, "錯誤", "請選擇有效的SST日期")
            return
        
        sst_data = self.himsst_data[sst_date]
        
        current_data = None
        if self.current_check.isChecked() and self.nprsubc_data:
            current_date = list(self.nprsubc_data.keys())[0]
            current_data = self.nprsubc_data.get(current_date)
        
        self.canvas.set_data(sst_data, 'combined')
        
        self.visualizer.plot_combined(
            sst_data, current_data, self.canvas.fig, self.current_extent,
            show_isotherm=self.isotherm_check.isChecked(),
            isotherm_interval=self.interval_spin.value(),
            show_currents=self.current_check.isChecked(),
            arrow_skip=self.arrow_skip_spin.value()
        )
        self.canvas.draw()
        self.status_bar.showMessage(f"🔀 已繪製合併圖 (SST + 海流) - {sst_date}")
    
    def reset_view(self):
        self.current_extent = [
            config.INITIAL_EXTENT['lon_min'],
            config.INITIAL_EXTENT['lon_max'],
            config.INITIAL_EXTENT['lat_min'],
            config.INITIAL_EXTENT['lat_max']
        ]
        tab_idx = self.tab_widget.currentIndex()
        if tab_idx == 0 and self.himsst_date_combo.currentText():
            self.plot_himsst()
        elif tab_idx == 1 and self.nprsubt_date_combo.currentText():
            self.plot_nprsubt()
        elif tab_idx == 2 and self.combined_sst_combo.currentText():
            self.plot_combined()
    
    def clear_plot(self):
        self.canvas.fig.clear()
        self.canvas.draw()
        self.status_bar.showMessage("🗑️ 畫面已清除")
    
    def update_coordinates(self, lat: float, lon: float, value: float):
        self.coord_label.setText(
            f"📍 經度: {lon:.2f}°E | 緯度: {lat:.2f}°N | 🌡️ 數值: {value:.2f}°C"
        )


def main():
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application font
    font = QFont("Microsoft JhengHei", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
