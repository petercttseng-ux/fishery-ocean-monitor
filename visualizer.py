# -*- coding: utf-8 -*-
"""
JMA Weather Desktop GUI System - Enhanced Visualizer (v2.0)
農業部水產試驗所 漁海況研究小組

Premium visualization module with enhanced color schemes and styling.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.ticker import MaxNLocator
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from typing import Optional, Tuple
import config
from data_parser import HIMSSTData, NPRSUBTData, NPRSUBCData


class JMAVisualizer:
    """Enhanced visualizer for JMA oceanographic data with light theme styling."""
    
    def __init__(self):
        # Set font for Chinese characters
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        # Light theme colors for figures
        plt.rcParams['figure.facecolor'] = '#ffffff'
        plt.rcParams['axes.facecolor'] = '#f8f9fa'
        plt.rcParams['savefig.facecolor'] = '#ffffff'
        plt.rcParams['axes.edgecolor'] = '#bdbdbd'
        plt.rcParams['axes.linewidth'] = 1.5
        plt.rcParams['text.color'] = '#212121'
        plt.rcParams['axes.labelcolor'] = '#424242'
        plt.rcParams['xtick.color'] = '#424242'
        plt.rcParams['ytick.color'] = '#424242'
        
        self.projection = ccrs.PlateCarree()
    
    def create_sst_colormap(self):
        """Create premium SST colormap with smooth ocean-inspired transitions."""
        colors = [
            '#0a0033',  # Deep navy (coldest)
            '#000066',  # Dark blue
            '#0033aa',  # Rich blue
            '#0066dd',  # Bright blue
            '#0099ff',  # Sky blue
            '#00ccee',  # Cyan
            '#00e6b8',  # Turquoise
            '#33ff77',  # Bright green
            '#66ff33',  # Lime
            '#aaff00',  # Yellow-green
            '#dddd00',  # Golden yellow
            '#ffbb00',  # Orange-yellow
            '#ff8800',  # Bright orange
            '#ff5500',  # Orange-red
            '#ee2200',  # Bright red
            '#cc0022',  # Dark red
            '#990044',  # Deep crimson (warmest)
        ]
        return LinearSegmentedColormap.from_list('sst_premium', colors, N=512)
    
    def create_depth_colormap(self):
        """Create colormap for subsurface temperature with depth-inspired gradients."""
        colors = [
            '#0d1b4c',  # Deepest indigo (cold)
            '#1a237e',  # Deep indigo
            '#283593',  # Indigo
            '#3949ab',  # Electric blue
            '#5c6bc0',  # Periwinkle
            '#7986cb',  # Light indigo
            '#42a5f5',  # Bright blue
            '#29b6f6',  # Sky blue
            '#26c6da',  # Cyan
            '#26a69a',  # Teal
            '#4caf50',  # Green
            '#8bc34a',  # Light green
            '#cddc39',  # Lime
            '#ffeb3b',  # Yellow
            '#ffc107',  # Amber
            '#ff9800',  # Orange
            '#ff5722',  # Deep orange
            '#f44336',  # Red
            '#d32f2f',  # Dark red (warm)
        ]
        return LinearSegmentedColormap.from_list('depth_temp_premium', colors, N=512)
    
    def _setup_map(self, ax, extent):
        """Setup common map features with light theme styling."""
        ax.set_extent(extent, crs=self.projection)
        
        # Add high-resolution coastline
        ax.add_feature(cfeature.COASTLINE.with_scale('50m'), 
                      linewidth=1.0, edgecolor='#424242', zorder=10)
        
        # Add land with light fill
        ax.add_feature(cfeature.LAND.with_scale('50m'), 
                      facecolor='#e8e8e8', edgecolor='none', zorder=5)
        
        # Add country borders
        ax.add_feature(cfeature.BORDERS.with_scale('50m'), 
                      linewidth=0.5, edgecolor='#757575', linestyle='--', zorder=6)
        
        # Add styled gridlines - dark text for light theme
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, 
                         color='#757575', alpha=0.6, linestyle='-')
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {'size': 11, 'color': '#424242', 'weight': 'bold', 'family': 'Microsoft JhengHei'}
        gl.ylabel_style = {'size': 11, 'color': '#424242', 'weight': 'bold', 'family': 'Microsoft JhengHei'}
    
    def _add_colorbar(self, fig, ax, mappable, label, cmap):
        """Add styled colorbar for light theme."""
        cbar = fig.colorbar(mappable, ax=ax, orientation='vertical', 
                           pad=0.025, shrink=0.82, aspect=32)
        cbar.set_label(label, fontsize=14, color='#212121', fontweight='bold', labelpad=10)
        cbar.ax.tick_params(colors='#424242', labelsize=11, width=1.5)
        cbar.outline.set_edgecolor('#bdbdbd')
        cbar.outline.set_linewidth(1.5)
        return cbar
    
    def _add_title(self, ax, title, subtitle=""):
        """Add styled title for light theme."""
        ax.set_title(title, fontsize=20, fontweight='bold', 
                    color='#01579b', pad=25, 
                    fontfamily='Microsoft JhengHei')
        if subtitle:
            ax.text(0.5, 1.03, subtitle, transform=ax.transAxes,
                   fontsize=13, color='#616161', ha='center', va='bottom',
                   fontweight='500', fontfamily='Microsoft JhengHei')
    
    def _add_watermark(self, fig):
        """Add organization watermark for light theme."""
        fig.text(0.99, 0.01, config.ORGANIZATION, 
                ha='right', va='bottom',
                fontsize=12, color='#01579b', alpha=0.95,
                fontweight='bold', style='italic',
                fontfamily='Microsoft JhengHei',
                bbox=dict(boxstyle='round,pad=0.4', 
                         facecolor='#e3f2fd', 
                         edgecolor='#0288d1',
                         linewidth=1.5,
                         alpha=0.95))
    
    def plot_himsst(self, data: HIMSSTData, fig: Figure = None,
                    extent: Tuple = None, show_isotherm: bool = True,
                    isotherm_interval: float = 2.0,
                    show_labels: bool = True) -> Figure:
        """Plot HIMSST sea surface temperature with light theme styling."""
        if fig is None:
            fig = Figure(figsize=(12, 10), dpi=100, facecolor='#ffffff')
        fig.clear()
        fig.set_facecolor('#ffffff')
        
        ax = fig.add_subplot(1, 1, 1, projection=self.projection)
        ax.set_facecolor('#f8f9fa')
        
        if extent is None:
            extent = [config.INITIAL_EXTENT['lon_min'], config.INITIAL_EXTENT['lon_max'],
                     config.INITIAL_EXTENT['lat_min'], config.INITIAL_EXTENT['lat_max']]
        
        self._setup_map(ax, extent)
        
        # Create mesh grid
        lon2d, lat2d = np.meshgrid(data.lon, data.lat)
        cmap = self.create_sst_colormap()
        
        # Plot SST with smooth shading
        cf = ax.pcolormesh(lon2d, lat2d, data.sst, cmap=cmap,
                          vmin=config.SST_VMIN, vmax=config.SST_VMAX,
                          transform=self.projection, shading='gouraud',
                          zorder=1)
        
        # Add colorbar
        self._add_colorbar(fig, ax, cf, '海表水溫 (°C)', cmap)
        
        # Add isotherms with enhanced styling
        if show_isotherm:
            levels = np.arange(config.SST_VMIN, config.SST_VMAX + 1, isotherm_interval)
            cs = ax.contour(lon2d, lat2d, data.sst, levels=levels,
                           colors='#1a1a1a', linewidths=1.0, 
                           transform=self.projection, zorder=8)
            if show_labels:
                ax.clabel(cs, inline=True, fontsize=10, fmt='%.0f°C',
                         colors='#1a1a1a', inline_spacing=6)
        
        # Add title
        date_str = data.date.strftime('%Y年%m月%d日')
        self._add_title(ax, f"🌡️ HIMSST 海表水溫分布圖", date_str)
        
        # Add watermark
        self._add_watermark(fig)
        
        fig.tight_layout(pad=1.5)
        return fig
    
    def plot_nprsubt(self, data: NPRSUBTData, depth: int, fig: Figure = None,
                     extent: Tuple = None, show_isotherm: bool = True,
                     isotherm_interval: float = 2.0,
                     show_labels: bool = True) -> Figure:
        """Plot NPRSUBT subsurface temperature with light theme styling."""
        if fig is None:
            fig = Figure(figsize=(12, 10), dpi=100, facecolor='#ffffff')
        fig.clear()
        fig.set_facecolor('#ffffff')
        
        ax = fig.add_subplot(1, 1, 1, projection=self.projection)
        ax.set_facecolor('#f8f9fa')
        
        if extent is None:
            extent = [config.INITIAL_EXTENT['lon_min'], config.INITIAL_EXTENT['lon_max'],
                     config.INITIAL_EXTENT['lat_min'], config.INITIAL_EXTENT['lat_max']]
        
        self._setup_map(ax, extent)
        
        temp_data = data.temperature.get(depth)
        if temp_data is None:
            return fig
        
        lon2d, lat2d = np.meshgrid(data.lon, data.lat)
        cmap = self.create_depth_colormap()
        
        # Calculate data range
        valid_data = temp_data[~np.ma.getmaskarray(temp_data)]
        if len(valid_data) > 0:
            vmin = np.percentile(valid_data, 2)
            vmax = np.percentile(valid_data, 98)
        else:
            vmin, vmax = 0, 30
        
        cf = ax.pcolormesh(lon2d, lat2d, temp_data, cmap=cmap,
                          vmin=vmin, vmax=vmax,
                          transform=self.projection, shading='gouraud',
                          zorder=1)
        
        self._add_colorbar(fig, ax, cf, f'{depth}m 水溫 (°C)', cmap)
        
        # Add isotherms with enhanced styling
        if show_isotherm:
            levels = np.arange(int(vmin), int(vmax) + 1, isotherm_interval)
            cs = ax.contour(lon2d, lat2d, temp_data, levels=levels,
                           colors='#1a1a1a', linewidths=1.0,
                           transform=self.projection, zorder=8)
            if show_labels:
                ax.clabel(cs, inline=True, fontsize=10, fmt='%.0f°C',
                         colors='#1a1a1a', inline_spacing=6)
        
        date_str = data.date.strftime('%Y年%m月%d日')
        self._add_title(ax, f"📊 NPRSUBT 水下{depth}m 溫度分布圖", date_str)
        
        self._add_watermark(fig)
        
        fig.tight_layout(pad=1.5)
        return fig
    
    def plot_combined(self, sst_data: HIMSSTData, current_data: NPRSUBCData,
                      fig: Figure = None, extent: Tuple = None,
                      show_isotherm: bool = True, isotherm_interval: float = 2.0,
                      show_currents: bool = True, arrow_skip: int = 10) -> Figure:
        """Plot SST with ocean currents overlay using light theme styling."""
        if fig is None:
            fig = Figure(figsize=(14, 10), dpi=100, facecolor='#ffffff')
        fig.clear()
        fig.set_facecolor('#ffffff')
        
        ax = fig.add_subplot(1, 1, 1, projection=self.projection)
        ax.set_facecolor('#f8f9fa')
        
        if extent is None:
            extent = [config.INITIAL_EXTENT['lon_min'], config.INITIAL_EXTENT['lon_max'],
                     config.INITIAL_EXTENT['lat_min'], config.INITIAL_EXTENT['lat_max']]
        
        self._setup_map(ax, extent)
        
        # Plot SST
        lon2d, lat2d = np.meshgrid(sst_data.lon, sst_data.lat)
        cmap = self.create_sst_colormap()
        
        cf = ax.pcolormesh(lon2d, lat2d, sst_data.sst, cmap=cmap,
                          vmin=config.SST_VMIN, vmax=config.SST_VMAX,
                          transform=self.projection, shading='gouraud',
                          zorder=1)
        
        self._add_colorbar(fig, ax, cf, '海表水溫 (°C)', cmap)
        
        # Add isotherms with enhanced styling
        if show_isotherm:
            levels = np.arange(config.SST_VMIN, config.SST_VMAX + 1, isotherm_interval)
            cs = ax.contour(lon2d, lat2d, sst_data.sst, levels=levels,
                           colors='#1a1a1a', linewidths=0.8,
                           transform=self.projection, zorder=8)
            ax.clabel(cs, inline=True, fontsize=9, fmt='%.0f°C',
                     colors='#1a1a1a', inline_spacing=5)
        
        # Add ocean currents with enhanced styling
        if show_currents and current_data is not None:
            curr_lon2d, curr_lat2d = np.meshgrid(current_data.lon, current_data.lat)
            skip = arrow_skip
            
            # Subsample data
            u_sub = current_data.u[::skip, ::skip]
            v_sub = current_data.v[::skip, ::skip]
            lon_sub = curr_lon2d[::skip, ::skip]
            lat_sub = curr_lat2d[::skip, ::skip]
            
            # Calculate speed for color
            speed = np.sqrt(u_sub**2 + v_sub**2)
            
            # Plot quiver with white arrows and glow effect
            Q = ax.quiver(lon_sub, lat_sub, u_sub, v_sub,
                         transform=self.projection,
                         scale=3, scale_units='inches',
                         color='white', alpha=0.9,
                         width=0.005, headwidth=4.5, headlength=5.5,
                         zorder=9)
            
            # Add quiver key with styled box
            ax.quiverkey(Q, 0.92, 0.025, 0.5, '0.5 m/s',
                        labelpos='W', color='white',
                        coordinates='axes', fontproperties={'size': 11, 'weight': 'bold'})
        
        date_str = sst_data.date.strftime('%Y年%m月%d日')
        self._add_title(ax, "🔀 海表水溫與海流分布圖", date_str)
        
        self._add_watermark(fig)
        
        fig.tight_layout(pad=1.5)
        return fig
