import serial
import time
import pandas as pd
import numpy as np
from datetime import datetime
from app import telemetry, columns

SERIAL_PORT = "COM3"  
BAUD_RATE = 9600

# Open serial port
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

start_time = pd.to_datetime("00:00:00", format="%H:%M:%S")

def generate_missing_values():

    gps_lat = 28.5729 + np.random.Generator(0, 0.0001)  # Simulated GPS drift
    gps_lon = -80.6490 + np.random.Generator(0, 0.0001)
    gps_alt = np.random.Generator(0, 1000)  # Random altitude between 0-1000m
    gps_sats = np.random.Generator(4, 12)  # Random satellite count (4-12)
    gps_time = datetime.now()
    return {
        "GPS_LATITUDE": gps_lat, "GPS_LONGITUDE": gps_lon, "GPS_ALTITUDE": gps_alt, "GPS_SATS": gps_sats, "GPS_TIME": gps_time 
    }

def read_telemetry():
    global telemetry

    try:
        while True:

            line = ser.readline().decode('utf-8').strip()  # Read line from serial
            if line:
                values = line.split(",")
            if len(values) == len(columns):
                # Convert to dictionary
                telemetry_data = {
                    'TEAM_ID': int(values[0]),
                    'MISSION_TIME': datetime.strptime(values[1], "%H:%M:%S"),
                    'PACKET_COUNT': int(values[2]),
                    'MODE': values[3],
                    'STATE': values[4],
                    'ALTITUDE': float(values[5]),
                    'TEMPERATURE': float(values[6]),
                    'PRESSURE': float(values[7]),
                    'VOLTAGE': float(values[8]),
                    'GYRO_R': float(values[9]),
                    'GYRO_P': float(values[10]),
                    'GYRO_Y': float(values[11]),
                    "ACCEL_R": float(values[12]), 
                    "ACCEL_P": float(values[13]), 
                    "ACCEL_Y": float(values[14]),
                    "MAG_R": float(values[15]),
                    "MAG_P": float(values[16]),
                    "MAG_Y": float(values[17]),
                    "AUTO_GYRO_ROTATION_RATE": float(values[18]),
                    'CMD_ECHO': values[23]
                }

                print(f"Received: {telemetry_data}")

                generated_values = generate_missing_values()
                telemetry_data.update(generated_values)

                telemetry = pd.concat([telemetry, pd.DataFrame([telemetry_data])], ignore_index=True)

            else:
                print(f"Invalid Packet: {line}")

            time.sleep(1)  # Read every second

    except KeyboardInterrupt:
        print("Stopping telemetry read.")
    finally:
        ser.close()  # Close serial port

def send_pressure_via_xbee(pressure_value):
    """Send pressure data via XBee"""
    if pressure_value is not None:
        message = f"CMD,3134,SIMP,{pressure_value:.2f}"  # Format pressure value
        ser.write(message.encode())  # Send via XBee
        print(f"Sent Pressure via XBee: {message.strip()}")