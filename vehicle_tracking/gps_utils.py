"""
GPS Utilities for Vehicle Tracking
Handles NMEA parsing and location updates
"""

import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GPSParser:
    """Parse NMEA GPS data from Raspberry Pi"""
    
    @staticmethod
    def parse_gga(sentence):
        """Parse GGA sentence for location data"""
        parts = sentence.split(',')
        
        if len(parts) >= 10 and parts[6] in ['1', '2']:  # 1=GPS fix, 2=DGPS fix
            try:
                # Parse latitude (DDMM.MMMMM)
                lat_raw = parts[2]
                lat_dir = parts[3]
                if lat_raw and lat_dir:
                    lat_deg = int(float(lat_raw) / 100)
                    lat_min = float(lat_raw) - (lat_deg * 100)
                    latitude = lat_deg + (lat_min / 60)
                    if lat_dir == 'S':
                        latitude = -latitude
                
                # Parse longitude (DDDMM.MMMMM)
                lon_raw = parts[4]
                lon_dir = parts[5]
                if lon_raw and lon_dir:
                    lon_deg = int(float(lon_raw) / 100)
                    lon_min = float(lon_raw) - (lon_deg * 100)
                    longitude = lon_deg + (lon_min / 60)
                    if lon_dir == 'W':
                        longitude = -longitude
                
                # Altitude
                altitude = float(parts[9]) if parts[9] else 0
                
                # Satellites
                satellites = int(parts[7]) if parts[7] else 0
                
                return {
                    'latitude': latitude,
                    'longitude': longitude,
                    'altitude': altitude,
                    'satellites': satellites,
                    'fix_quality': int(parts[6])
                }
            except Exception as e:
                logger.error(f"Parse error: {e}")
        
        return None
    
    @staticmethod
    def parse_rmc(sentence):
        """Parse RMC sentence for speed and heading"""
        parts = sentence.split(',')
        
        if len(parts) >= 8 and parts[2] == 'A':  # A = Active fix
            try:
                # Speed in knots
                speed_knots = float(parts[7]) if parts[7] else 0
                speed_kmh = speed_knots * 1.852
                
                # Heading
                heading = float(parts[8]) if parts[8] else 0
                
                return {
                    'speed': speed_kmh,
                    'heading': heading
                }
            except Exception as e:
                logger.error(f"Parse error: {e}")
        
        return None
