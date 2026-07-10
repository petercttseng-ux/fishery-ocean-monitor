# -*- coding: utf-8 -*-
"""
JMA Weather Desktop GUI System - Data Parser
農業部水產試驗所 漁海況研究小組
"""

import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import config


@dataclass
class HIMSSTData:
    """Container for HIMSST (Sea Surface Temperature) data."""
    date: datetime
    lat: np.ndarray
    lon: np.ndarray
    sst: np.ndarray
    filepath: Path


@dataclass
class NPRSUBTData:
    """Container for NPRSUBT (Subsurface Temperature) data."""
    date: datetime
    lat: np.ndarray
    lon: np.ndarray
    temperature: Dict[int, np.ndarray]
    filepath: Path
    
    @property
    def depths(self) -> List[int]:
        return list(self.temperature.keys())


@dataclass
class NPRSUBCData:
    """Container for NPRSUBC (Surface Currents) data."""
    date: datetime
    lat: np.ndarray
    lon: np.ndarray
    u: np.ndarray
    v: np.ndarray
    filepath: Path
    
    @property
    def speed(self) -> np.ndarray:
        return np.sqrt(self.u**2 + self.v**2)


class JMADataParser:
    """Parser for JMA oceanographic data files."""
    
    def parse_himsst(self, filepath: Path) -> Optional[HIMSSTData]:
        """Parse HIMSST data file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if len(lines) < 601:
                return None
            
            header = lines[0].strip()
            year, month, day = int(header[0:4]), int(header[4:8]), int(header[8:12])
            date = datetime(year, month, day)
            
            cfg = config.HIMSST_CONFIG
            lat = np.linspace(cfg['lat_start'] - 0.05, cfg['lat_end'] + 0.05, cfg['n_rows'])
            lon = np.linspace(cfg['lon_start'] + 0.05, cfg['lon_end'] - 0.05, cfg['n_cols'])
            
            sst = np.zeros((cfg['n_rows'], cfg['n_cols']), dtype=np.float32)
            for i in range(cfg['n_rows']):
                # 注意：不可 strip() 行首空白，否則固定寬度欄位會錯位
                line = lines[i + 1].rstrip('\r\n')
                for j in range(cfg['n_cols']):
                    try:
                        value = int(line[j*3:(j+1)*3])
                        if value in (cfg['missing_value'], cfg['ice_value']):
                            sst[i, j] = np.nan
                        else:
                            sst[i, j] = value * cfg['value_scale']
                    except:
                        sst[i, j] = np.nan
            
            return HIMSSTData(date=date, lat=lat, lon=lon, 
                            sst=np.ma.masked_invalid(sst), filepath=filepath)
        except Exception as e:
            print(f"Error parsing HIMSST: {e}")
            return None
    
    def parse_nprsubt(self, filepath: Path) -> Optional[NPRSUBTData]:
        """Parse NPRSUBT data file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if len(lines) < 1585:
                return None
            
            header = lines[0].strip()
            year, month, day = int(header[0:4]), int(header[4:8]), int(header[8:12])
            date = datetime(year, month, day)
            
            cfg = config.NPRSUBT_CONFIG
            lat = np.linspace(cfg['lat_start'], cfg['lat_end'], cfg['n_rows'])
            lon = np.linspace(cfg['lon_start'], cfg['lon_end'], cfg['n_cols'])
            
            temperature = {}
            for depth_idx, depth in enumerate(cfg['depths']):
                block_start = 1 + depth_idx * 396
                data_start = block_start + 1
                temp = np.zeros((cfg['n_rows'], cfg['n_cols']), dtype=np.float32)
                
                for i in range(cfg['n_rows']):
                    # 注意：不可 strip() 行首空白，否則固定寬度欄位會錯位
                    line = lines[data_start + i].rstrip('\r\n')
                    for j in range(cfg['n_cols']):
                        try:
                            value = int(line[j*4:(j+1)*4])
                            temp[i, j] = np.nan if value == cfg['missing_value'] else value * cfg['value_scale']
                        except:
                            temp[i, j] = np.nan
                
                temperature[depth] = np.ma.masked_invalid(temp)
            
            return NPRSUBTData(date=date, lat=lat, lon=lon, 
                              temperature=temperature, filepath=filepath)
        except Exception as e:
            print(f"Error parsing NPRSUBT: {e}")
            return None
    
    def parse_nprsubc(self, filepath: Path) -> Optional[NPRSUBCData]:
        """Parse NPRSUBC data file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if len(lines) < 795:
                return None
            
            header = lines[0].strip()
            year, month, day = int(header[0:4]), int(header[4:8]), int(header[8:12])
            date = datetime(year, month, day)
            
            cfg = config.NPRSUBC_CONFIG
            lat = np.linspace(cfg['lat_start'], cfg['lat_end'], cfg['n_rows'])
            lon = np.linspace(cfg['lon_start'], cfg['lon_end'], cfg['n_cols'])
            
            def parse_component(start_line):
                arr = np.zeros((cfg['n_rows'], cfg['n_cols']), dtype=np.float32)
                for i in range(cfg['n_rows']):
                    # 注意：不可 strip() 行首空白，否則固定寬度欄位會錯位
                    line = lines[start_line + i].rstrip('\r\n')
                    for j in range(cfg['n_cols']):
                        try:
                            value = int(line[j*4:(j+1)*4])
                            arr[i, j] = np.nan if value == cfg['missing_value'] else value * cfg['value_scale']
                        except:
                            arr[i, j] = np.nan
                return np.ma.masked_invalid(arr)
            
            u = parse_component(2)
            v = parse_component(399)
            
            return NPRSUBCData(date=date, lat=lat, lon=lon, u=u, v=v, filepath=filepath)
        except Exception as e:
            print(f"Error parsing NPRSUBC: {e}")
            return None
