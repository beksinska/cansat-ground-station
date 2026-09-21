#!/usr/bin/env python3
"""
Simple tile server to serve offline tiles for the rocket tracker
Run this in a separate terminal: python tile_server.py
"""

import http.server
import socketserver
import os
from pathlib import Path
import threading
import time

TILES_DIR = "offline_tiles"
PORT = 8000

class TileHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Handle tile requests in format: /tiles/z/x/y.png
        if self.path.startswith('/tiles/'):
            try:
                # Parse tile request: /tiles/z/x/y.png
                parts = self.path.strip('/').split('/')
                if len(parts) == 4 and parts[0] == 'tiles':
                    z, x, y_with_ext = parts[1], parts[2], parts[3]
                    y = y_with_ext.replace('.png', '')
                    
                    # Find the tile file in structure: offline_tiles/z/x/y.png
                    tile_path = Path(TILES_DIR) / z / x / f"{y}.png"
                    
                    print(f"Looking for tile: {tile_path}")  # Debug output
                    
                    if tile_path.exists():
                        self.send_response(200)
                        self.send_header('Content-Type', 'image/png')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Cache-Control', 'max-age=86400')  # Cache for 1 day
                        self.end_headers()
                        
                        with open(tile_path, 'rb') as f:
                            self.wfile.write(f.read())
                        print(f"Served tile: {z}/{x}/{y}")
                        return
                    else:
                        print(f"Tile not found: {tile_path}")
                        
            except Exception as e:
                print(f"Error processing tile request: {e}")
        
        # Default response for non-tile requests or missing tiles
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(f'Tile not found: {self.path}'.encode())

def start_tile_server():
    """Start the tile server in a separate thread"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), TileHandler) as httpd:
        print(f"Tile server running at http://localhost:{PORT}")
        print(f"Serving tiles from: {os.path.abspath(TILES_DIR)}")
        print("Tile URL format: http://localhost:8000/tiles/{z}/{x}/{y}.png")
        httpd.serve_forever()

if __name__ == "__main__":
    if not os.path.exists(TILES_DIR):
        print(f"Error: {TILES_DIR} directory not found!")
        print("Make sure you've downloaded the tiles first.")
        exit(1)
    
    # Show what tiles we have available
    print(f"Checking tiles in: {os.path.abspath(TILES_DIR)}")
    zoom_dirs = [d for d in os.listdir(TILES_DIR) if os.path.isdir(os.path.join(TILES_DIR, d)) and d.isdigit()]
    zoom_dirs.sort()
    
    if zoom_dirs:
        print(f"Available zoom levels: {zoom_dirs}")
        for zoom in zoom_dirs[:2]:  # Show first 2 zoom levels as examples
            zoom_path = Path(TILES_DIR) / zoom
            x_dirs = [d for d in os.listdir(zoom_path) if os.path.isdir(zoom_path / d)]
            if x_dirs:
                x_sample = x_dirs[0]
                y_files = list((zoom_path / x_sample).glob("*.png"))
                if y_files:
                    y_sample = y_files[0].stem
                    print(f"  Example tile: {TILES_DIR}/{zoom}/{x_sample}/{y_sample}.png")
    else:
        print("No tile directories found!")
        exit(1)
    
    start_tile_server()