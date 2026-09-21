# CanSat Ground Station

A Python Dash-based ground station for monitoring and interacting with a CanSat telemetry stream. The application reads live packets from a serial/XBee connection, renders telemetry as charts, displays the latest GPS position on a map, and supports simulation-based testing.

## Features

- Live telemetry monitoring from a serial device
- Real-time status cards for mission time, team ID, state, packet count, mode, and GPS fields
- Graphs for altitude, pressure, temperature, voltage, rotation sensors, and accelerometer data
- 3D plotting for magnetometer, gyro, and accelerometer readings
- Offline map view using Folium with the most recent GPS coordinates
- Simulation controls for uploading pressure files and sending simulated commands
- Command buttons for setup, calibration, telemetry start/stop, and time configuration

## Project Structure

- app.py — main Dash application and telemetry handling
- map.py — small helper script for generating the offline map HTML
- assets/offline_map.html — generated map used in the dashboard
- data.csv — sample dataset
- flight_simulation.csv — simulation/example telemetry data
- telemetry_data.csv — output file for received telemetry packets

## Requirements

Use Python 3.10 or newer.

Install the required packages:

pip install dash pandas plotly numpy folium pyserial

If you use the helper map generation script directly, you may also need:

pip install offline-folium

## Configuration

Before running the app, update the serial settings in app.py:

- SERIAL_PORT — default is COM3
- BAUD_RATE — default is 9600

On macOS or Linux, this may look like /dev/tty.usbserial or /dev/ttyUSB0 instead of COM3.

## Running the Application

1. Open a terminal in the project folder.
2. Install the required Python packages.
3. Start the app:

python app.py

4. Open the local dashboard in your browser:

http://localhost:8051

## How It Works

- The app starts a background thread that reads telemetry from the configured serial port.
- Each valid packet is parsed and appended to telemetry_data.csv.
- The dashboard refreshes every second and updates the live charts and status fields.
- The map is regenerated from the latest GPS coordinates so the mission location is always visible offline.
- Simulation mode can be used to upload a pressure log and send commands to the CanSat through the serial/XBee interface.

## Typical Workflow

1. Connect the receiver device to the serial port.
2. Start the ground station application.
3. Confirm that telemetry packets are appearing in the dashboard.
4. Use the buttons to configure and command the payload as needed.
5. Upload a simulation file when testing command flow or pressure events.

## Notes

- The app assumes a valid telemetry packet format matching the fields parsed in app.py.
- The offline map file is generated dynamically and stored under assets/.
- If the serial port is unavailable or the device is disconnected, the app may not receive data until the port is corrected.

## License

This project is intended for educational and research use. Add your preferred license information here if you want to publish or distribute it publicly.
