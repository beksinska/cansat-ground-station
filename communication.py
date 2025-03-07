import serial
import time
import pandas as pd
import numpy as np
from datetime import datetime

def send_pressure_via_xbee(pressure_value):
    """Send pressure data via XBee"""
    if pressure_value is not None:
        message = f"CMD,3134,SIMP,{pressure_value:.2f}"  # Format pressure value
        ser.write(message.encode())  # Send via XBee
        print(f"Sent Pressure via XBee: {message.strip()}")