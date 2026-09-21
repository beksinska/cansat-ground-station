#!/usr/bin/env python3
"""
Download OpenStreetMap tiles for offline use around any specified location
Automatically creates a 2km x 2km area around the center point
"""

import os
import math
import requests
import time
from urllib.parse import urlparse

# Configuration
ZOOM_LEVELS = [13, 14, 15, 16]  # Good range for rocket tracking
TILE_SERVER = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILES_DIR = "offline_tiles"

def get_user_coordinates():
    """Get center coordinates from user input with validation"""
    print("Enter the center coordinates for your launch site:")
    print("(You can find these using Google Maps, GPS coordinates, etc.)")
    print()
    
    while True:
        try:
            lat_input = input("Enter latitude (e.g., 52.476010): ").strip()
            lon_input = input("Enter longitude (e.g., 13.457556): ").strip()
            
            lat = float(lat_input)
            lon = float(lon_input)
            
            # Basic validation
            if not (-90 <= lat <= 90):
                print("❌ Latitude must be between -90 and 90 degrees")
                continue
            if not (-180 <= lon <= 180):
                print("❌ Longitude must be between -180 and 180 degrees")
                continue
                
            return lat, lon
            
        except ValueError:
            print("❌ Please enter valid numbers for latitude and longitude")
            continue

def calculate_bounding_box(center_lat, center_lon, distance_km=1.0):
    """
    Calculate bounding box for a square area around center point
    distance_km is the distance from center to edge (so 1km = 2km square)
    """
    # Approximate degrees per kilometer (varies by latitude)
    # At equator: 1 degree ≈ 111 km
    # Latitude degrees per km is constant
    lat_deg_per_km = 1.0 / 111.0
    
    # Longitude degrees per km varies by latitude
    lon_deg_per_km = 1.0 / (111.0 * math.cos(math.radians(center_lat)))
    
    # Calculate offsets
    lat_offset = distance_km * lat_deg_per_km
    lon_offset = distance_km * lon_deg_per_km
    
    bbox = {
        'north': center_lat + lat_offset,
        'south': center_lat - lat_offset,
        'east': center_lon + lon_offset,
        'west': center_lon - lon_offset
    }
    
    return bbox

def deg2num(lat_deg, lon_deg, zoom):
    """Convert lat/lon to tile numbers"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
    """Convert tile numbers to lat/lon"""
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def download_tile(x, y, z, output_dir):
    """Download a single tile"""
    url = TILE_SERVER.format(z=z, x=x, y=y)
    
    # Create directory structure
    tile_dir = os.path.join(output_dir, str(z), str(x))
    os.makedirs(tile_dir, exist_ok=True)
    
    # File path
    file_path = os.path.join(tile_dir, f"{y}.png")
    
    # Skip if file already exists
    if os.path.exists(file_path):
        print(f"  Tile {z}/{x}/{y} already exists, skipping...")
        return True
    
    try:
        # Add delay to be respectful to OSM servers
        time.sleep(0.1)
        
        headers = {
            'User-Agent': 'RocketTrackingApp/1.0 (Educational use)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"  Downloaded tile {z}/{x}/{y}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error downloading tile {z}/{x}/{y}: {e}")
        return False

def download_tiles_for_bbox(bbox, zoom_levels, output_dir):
    """Download all tiles within bounding box for specified zoom levels"""
    
    total_tiles = 0
    successful_downloads = 0
    
    for zoom in zoom_levels:
        print(f"\n📥 Downloading tiles for zoom level {zoom}...")
        
        # Get tile bounds for this zoom level
        # Note: Y coordinates are inverted - north has smaller Y values than south
        x_nw, y_nw = deg2num(bbox['north'], bbox['west'], zoom)
        x_se, y_se = deg2num(bbox['south'], bbox['east'], zoom)
        
        # Ensure we have the correct min/max values
        x_min = min(x_nw, x_se)
        x_max = max(x_nw, x_se)
        y_min = min(y_nw, y_se) 
        y_max = max(y_nw, y_se)
        
        tiles_this_zoom = (x_max - x_min + 1) * (y_max - y_min + 1)
        total_tiles += tiles_this_zoom
        
        print(f"  Zoom {zoom}: {tiles_this_zoom} tiles needed")
        print(f"  X range: {x_min} to {x_max}")
        print(f"  Y range: {y_min} to {y_max}")
        
        # Download each tile
        zoom_successful = 0
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if download_tile(x, y, zoom, output_dir):
                    successful_downloads += 1
                    zoom_successful += 1
        
        print(f"  ✅ Downloaded {zoom_successful}/{tiles_this_zoom} tiles for zoom {zoom}")
    
    print(f"\n🎉 Download complete!")
    print(f"Total tiles needed: {total_tiles}")
    print(f"Successfully downloaded: {successful_downloads}")
    
    return successful_downloads == total_tiles

def create_tile_info_file(center_lat, center_lon, bbox, zoom_levels, output_dir):
    """Create an info file with download details"""
    info_file = os.path.join(output_dir, "tile_info.txt")
    
    with open(info_file, 'w') as f:
        f.write("Offline Tiles for Rocket Tracking\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Center: {center_lat}, {center_lon}\n")
        f.write(f"Area: 2km x 2km square\n\n")
        f.write(f"Bounding Box:\n")
        f.write(f"  North: {bbox['north']:.6f}\n")
        f.write(f"  South: {bbox['south']:.6f}\n")
        f.write(f"  East: {bbox['east']:.6f}\n")
        f.write(f"  West: {bbox['west']:.6f}\n\n")
        f.write(f"Zoom Levels: {zoom_levels}\n")
        f.write(f"Tile Server: {TILE_SERVER}\n")
        f.write(f"Download Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("To use these tiles:\n")
        f.write("1. Update CENTER_LAT and CENTER_LON in app.py\n")
        f.write("2. Update OFFLINE_BBOX coordinates in app.py\n")
        f.write("3. Start tile server: python tile_server.py\n")
        f.write("4. Start dashboard: python app.py\n")

def print_coordinates_summary(center_lat, center_lon, bbox):
    """Print a nice summary of coordinates for the user"""
    print("\n" + "="*60)
    print("📍 COORDINATE SUMMARY")
    print("="*60)
    print(f"Launch Site Center: {center_lat:.6f}, {center_lon:.6f}")
    print(f"Coverage Area: 2km x 2km square")
    print()
    print("Bounding Box Coordinates:")
    print(f"  🔼 North: {bbox['north']:.6f}")
    print(f"  🔽 South: {bbox['south']:.6f}")
    print(f"  ➡️  East:  {bbox['east']:.6f}")
    print(f"  ⬅️  West:  {bbox['west']:.6f}")
    print()
    print("📋 Copy these coordinates to your app.py:")
    print(f"CENTER_LAT = {center_lat}")
    print(f"CENTER_LON = {center_lon}")
    print("OFFLINE_BBOX = {")
    print(f"    'north': {bbox['north']:.6f},")
    print(f"    'south': {bbox['south']:.6f},")
    print(f"    'east': {bbox['east']:.6f},")
    print(f"    'west': {bbox['west']:.6f}")
    print("}")
    print("="*60)

if __name__ == "__main__":
    print("🚀 OpenStreetMap Tile Downloader for Rocket Tracking")
    print("=" * 55)
    print()
    print("This tool will download map tiles for a 2km x 2km area")
    print("around your launch site for offline use.")
    print()
    
    # Get coordinates from user
    center_lat, center_lon = get_user_coordinates()
    
    # Calculate 2km square bounding box
    bbox = calculate_bounding_box(center_lat, center_lon, distance_km=1.0)
    
    # Show summary
    print_coordinates_summary(center_lat, center_lon, bbox)
    
    # Estimate total tiles
    total_estimate = 0
    for zoom in ZOOM_LEVELS:
        x_nw, y_nw = deg2num(bbox['north'], bbox['west'], zoom)
        x_se, y_se = deg2num(bbox['south'], bbox['east'], zoom)
        
        x_min = min(x_nw, x_se)
        x_max = max(x_nw, x_se)
        y_min = min(y_nw, y_se) 
        y_max = max(y_nw, y_se)
        
        total_estimate += (x_max - x_min + 1) * (y_max - y_min + 1)
    
    print(f"\n📊 Estimated total tiles: {total_estimate}")
    print(f"📊 Estimated download size: {total_estimate * 15 / 1024:.1f} MB")
    print(f"📊 Zoom levels: {ZOOM_LEVELS}")
    print(f"📁 Output directory: {TILES_DIR}")
    
    # Ask for confirmation
    print()
    response = input("🤔 Proceed with download? (y/n): ")
    if response.lower() != 'y':
        print("❌ Download cancelled.")
        exit()
    
    # Create output directory
    os.makedirs(TILES_DIR, exist_ok=True)
    
    # Download tiles
    print(f"\n🌍 Starting download from OpenStreetMap...")
    print("⏱️  This may take a few minutes...")
    
    success = download_tiles_for_bbox(bbox, ZOOM_LEVELS, TILES_DIR)
    
    # Create info file
    create_tile_info_file(center_lat, center_lon, bbox, ZOOM_LEVELS, TILES_DIR)
    
    if success:
        print(f"\n✅ All tiles downloaded successfully to '{TILES_DIR}/'")
        print("\n📝 Next steps:")
        print("1. Copy the coordinates above to your app.py file")
        print("2. Start tile server: python tile_server.py")
        print("3. Start dashboard: python app.py")
        print("4. Open browser to: http://localhost:8051")
    else:
        print(f"\n⚠️  Some tiles failed to download. Check the '{TILES_DIR}/' directory.")
        print("You can re-run this script to retry failed downloads.")
    
    print(f"\n📂 Tile directory structure:")
    print(f"{TILES_DIR}/")
    print("├── 13/               # Wide area view")
    print("├── 14/               # District level")
    print("├── 15/               # Street level")
    print("├── 16/               # High detail")
    print("└── tile_info.txt     # Download summary")
    
    print(f"\n🎯 Coverage area: 2km x 2km around {center_lat:.6f}, {center_lon:.6f}")
