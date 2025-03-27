from dash import Dash, html, dcc, Output, Input, State, callback, ctx
import dash
import io
import base64
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import time
import threading
from datetime import datetime
import serial
import os
import re

SERIAL_PORT = "COM3"  
BAUD_RATE = 9600

# Open serial port
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

columns = [
    "TEAM_ID", "MISSION_TIME", "PACKET_COUNT", "MODE", "STATE",
    "ALTITUDE", "TEMPERATURE", "PRESSURE", "VOLTAGE",
    "GYRO_R", "GYRO_P", "GYRO_Y", "ACCEL_R", "ACCEL_P", "ACCEL_Y",
    "MAG_R", "MAG_P", "MAG_Y", "AUTO_GYRO_ROTATION_RATE",
    "GPS_TIME", "GPS_ALTITUDE", "GPS_LATITUDE", "GPS_LONGITUDE",
    "GPS_SATS", "CMD_ECHO"
]

TELEMETRY_FILE = "telemetry_data.csv"

# Global DataFrame to store telemetry
telemetry = pd.DataFrame(columns=columns)
packets_received = 0

if not os.path.exists(TELEMETRY_FILE):
    pd.DataFrame(columns=columns).to_csv(TELEMETRY_FILE, index=False)

def save_to_csv(telemetry_data):
    telemetry_dataframe = pd.DataFrame([telemetry_data])
    """Appends telemetry data to a CSV file."""
    telemetry_dataframe.to_csv(TELEMETRY_FILE, mode='a', header=False, index=False)

def generate_missing_values():
    gps_lat = 52.5729 + np.random.normal(0, 0.0001)  # Simulated GPS drift
    gps_lon = 13.4590 + np.random.normal(0, 0.0001)
    gps_alt = np.random.uniform(0, 1000)  # Random altitude between 0-1000m
    gps_sats = np.random.randint(4, 12)
    gps_time = datetime.now().strftime("%H:%M:%S")
    return {
        "GPS_LATITUDE": gps_lat, "GPS_LONGITUDE": gps_lon, "GPS_ALTITUDE": gps_alt, "GPS_SATS": gps_sats, "GPS_TIME": gps_time 
    }

def read_telemetry():
    global telemetry
    global packets_received
    try:
        while True:
            if not ser.isOpen():
                print("Serial port is not open.")
                break

            line = ser.readline().decode('utf-8').strip()  # Read line from serial
            
            if line:
                telemetry_data = {}
                values = line.split(",")
                if values[0] == "3134":
                    packets_received += 1
                    # Convert to dictionary
                    telemetry_data = {
                        'TEAM_ID': int(values[0]),
                        'MISSION_TIME': values[1],
                        'PACKET_COUNT': int(values[2]),
                        'MODE': values[3],
                        'STATE': values[4],
                        'ALTITUDE': float(values[5]) if values[5].strip() else 0.0,
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
                        'CMD_ECHO': values[24] if values[24].strip() else 'No command',
                        'COMPASS': values[26] if values[26].strip() else '-'
                    }

                    print(f"Received: {telemetry_data}")

                    #Save telemetry to CSV
                    save_to_csv(telemetry_data)

                generated_values = generate_missing_values()
                telemetry_data.update(generated_values)

                telemetry = pd.concat([telemetry, pd.DataFrame([telemetry_data])], ignore_index=True)

            else:
                print(f"Invalid Packet: {line}")

            time.sleep(1)  # Read every second

    except KeyboardInterrupt:
        print("Stopping telemetry read.")
    finally:
        ser.close()

sim_enabled = False
sim_activated = False
sim_status= False

sim_data = pd.DataFrame()
sim_index = 0

def process_uploaded_file(contents):
    """Decodes the uploaded .txt file and returns a Pandas DataFrame?"""
    content_string = contents.split(',')[1]  # Extract only the Base64 part
    decoded = base64.b64decode(content_string).decode('utf-8')  # Decode Base64
    lines = decoded.splitlines()
    
    pressure_values = []
    # Extract data from each line
    for line in lines:
        match = re.search(r"CMD,\$,SIMP,(\d+)", line)
        if match:
            pressure = float(match.group(1))
            pressure_values.append(pressure)
    if pressure_values:
        sim_data = pd.DataFrame({"PRESSURE": pressure_values})
    return sim_data

def read_simulated_pressure():
    """Extract latest pressure value from simulation file"""
    global sim_data
    if not sim_data.empty:
        return sim_data["PRESSURE"].iloc[-1]  # Get latest pressure
    return None

def send_pressure_via_xbee(pressure_value):
    """Send pressure data via XBee"""
    if pressure_value is not None:
        message = f"CMD,3134,SIMP,{pressure_value:.2f}"  # Format pressure value
        ser.write(message.encode())  # Send via XBee
        print(f"Sent Pressure via XBee: {message.strip()}")

"""Send pressure via XBee if in simulation mode"""
def process_simulation_telemetry():
    global sim_status
    while True:
        if sim_status:
            pressure = read_simulated_pressure()
            send_pressure_via_xbee(pressure)  

        # Wait for 1 second before next iteration
        time.sleep(1)

def apply_graph_styling(fig):
    """Applies consistent styling to all figures."""
    fig.update_layout(
        xaxis=dict(title_font=dict(size=12)),  # Set X-axis label font size
        yaxis=dict(title_font=dict(size=12)),  # Set Y-axis label font size
    )
    return fig

def apply_top_row_styling(fig):
    """Applies consistent styling to all figures in the top row."""
    fig.update_layout(
        xaxis=dict(title_font=dict(size=12)),
        yaxis=dict(title_font=dict(size=12)),
        title=dict(
            pad=dict(b=2)  # Reduce bottom padding (default is ~10)
        )
    )
    return fig

thread = threading.Thread(target=read_telemetry, daemon=True)
thread.start()

# Initialize the Dash app
app = Dash(__name__)

app.layout = html.Div([
    # Main container
    html.Div([
        # Sidebar
        html.Div([
            # File Upload
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                'Select Simulation File'
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'marginBottom': '10px'
                },
            ),
            html.Div(id='upload-status',
                     children='No file uploaded.',
                     style={'marginBottom': '10px'}),

            # Simulation Control
            html.Button(
                "SIM Enable",
                id='sim-enable-button',
                style={'width': '100%', 'marginBottom': '10px'}
            ),

            html.Button(
                "SIM Activate",
                id='sim-activate-button',
                disabled = True,
                style={'width': '100%', 'marginBottom': '5px'}
            ),
            html.Div(id='sim-status',
                     style={'marginBottom': '10px'}),

            dcc.Input(
                id='sim-pressure-input',
                type='number',
                placeholder='Enter Pressure Value',
                style={'width': '200px', 
                       'boxSizing': 'border-box',
                       'marginBottom': '5px'}
            ),
            html.Button(
                "Send Pressure",
                id='sim-pressure-button',
                disabled=True,
                style={'width': '100%', 'marginBottom': '10px'}
            ),

            html.Button(
                "Attach Container",
                id='setup-button',
                style={'width': '100%', 'marginBottom': '10px'}
            ),
            
            # Calibrate Button
            html.Button(
                "Calibrate Altitude",
                id='calibrate-button',
                style={'width': '100%', 'marginBottom': '10px'}
            ),
            
            html.Button(
                "Set Time",
                id='set-time-button',
                style={'width': '100%', 'marginBottom': '10px'}
            ),
            dcc.Dropdown(
                id = 'time-dropdown',
                options=[
                    {'label': 'UTC', 'value': 'UTC'},
                    {'label': 'GPS', 'value': 'GPS'}
                ],
                placeholder="Select Time",
                style={'display': 'none', 'marginBottom': '10px'}
            ),

            html.Button(
                "Start Telemetry",
                id='telemetry-button',
                style={'width': '100%', 'marginBottom': '20px'}
            ),

            # Status Information
            html.Div([

                html.Div([
                html.Span("Packets Received:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='received-packets-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("Mission Time:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='mission-time-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),
                
                html.Div([
                html.Span("Team ID:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='team-id-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("State:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='state-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("Packet Count:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='packet-count-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("Mode:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='mode-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("Last Command:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='command-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("Satellites:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='gps-sats-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("GPS Time:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='gps-time-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("Compass Reading:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='compass-reading-display')],
                style={'display': 'flex', 'flexDirection': 'row'})
            ])
        ], 
        style={
            'width': '200px',
            'padding': '20px',
            'backgroundColor': '#f8f9fa',
            'marginRight': '20px',
            'height': '100vh',
            'overflowY': 'auto'
        }),
        
        # Main content area
        html.Div([
            # First row - Pressure, Altitude, Temperature
            html.Div([
                dcc.Graph(id='pressure-graph', style={'width': '33%', 'height': 'calc(100vh/3)'}),
                dcc.Graph(id='altitude-graph', style={'width': '33%', 'height': 'calc(100vh/3)'}),
                dcc.Graph(id='temperature-graph', style={'width': '33%', 'height': 'calc(100vh/3)'})
            ], style={'display': 'flex', 'marginBottom': '10px'}),
            
            # Second row - Voltage, Gyro rotation, Map
            html.Div([
                dcc.Graph(id='voltage-graph', style={'width': '33%', 'height': 'calc(100vh/3)'}),
                dcc.Graph(id='gyro-rotation-rate-graph', style={'width': '33%', 'height': 'calc(100vh/3)'}),
                dcc.Graph(id='map-plot', style={'width': '33%', 'height': 'calc(100vh/3)', 'paddingTop': '20px'})
            ], style={'display': 'flex', 'marginBottom': '10px'}),
            
            # Third row - Magnetometer, Gyro, Accelerometer
            html.Div([
                dcc.Graph(id='magnetometer-3d', style={'width': '33%', 'height': 'calc(100vh/3)'}),
                dcc.Graph(id='gyro-graph', style={'width': '33%', 'height': 'calc(100vh/3)'}),
                dcc.Graph(id='accelerometer-3d', style={'width': '33%', 'height': 'calc(100vh/3)'})
            ], style={'display': 'flex'})
            
        ], style={'flex': '1', 'height': '100vh', 'justifyContent': 'space-between', 'display': 'flex', 'flexDirection': 'column'}),
    ], style={'display': 'flex', 'font-size': '16px', 'height': '100vh', 'overflow': 'hidden'}),
    
    dcc.Interval(
        id='interval-component',
        interval=1000,  # 1 second interval
        n_intervals=0
    ),
    dcc.Store(id='setup-state', data=False),
    dcc.Store(id='telemetry-state', data=False)
])

# Callback for sending attach/detach container command
@callback(
    Output("setup-button", "children"),
    Output("setup-state", "data"),
    Input("setup-button", "n_clicks"),
    State("setup-state", "data"),
    prevent_initial_call=True  
)
def send_attach_container_command(n_clicks, is_attached):
    # Toggle state
    setup_state = not is_attached
    setup_text = "Detach Container" if setup_state else "Attach Container"
    # Send appropriate command
    message = f"CMD,3134,MEC,SERVO,{'ON' if setup_state else 'OFF'}"
    ser.write(message.encode()) 
    
    return setup_text, setup_state

# Callback for sending calibration command
@callback(
    Input("calibrate-button", "n_clicks"),
    prevent_initial_call=True  
)
def send_calibration_command(n_clicks):
    message = "CMD,3134,CAL"  
    ser.write(message.encode())  

# Callback for updating simulation status
@callback(
    [
        Output("sim-enable-button", "children"),
        Output("sim-activate-button", "disabled"),
        Output("sim-status", "children")
    ],
    [
        Input("sim-enable-button", "n_clicks"),
        Input("sim-activate-button", "n_clicks")
    ],
    prevent_initial_call=True
)
def update_simulation(enable_clicks, activate_clicks):
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print(f"Button ID: {button_id}")
    global sim_enabled, sim_activated, sim_status, sim_index

    # Update states based on the last pressed button:
    if button_id == "sim-enable-button":
        # Toggle the sim_enabled state
        sim_enabled = not sim_enabled
        # When disabling simulation, also reset sim_activated
        if not sim_enabled:
            sim_activated = False
            message = f"CMD,3134,SIM,DISABLE"  
            ser.write(message.encode()) 
        else:
            message = f"CMD,3134,SIM,ENABLE"  
            ser.write(message.encode())
    elif button_id == "sim-activate-button":
        # Only toggle activation if simulation is enabled
        if sim_enabled:
            sim_activated = not sim_activated
            if sim_activated:
                sim_index = 0
                message = f"CMD,3134,SIM,ACTIVATE"  
                ser.write(message.encode())

    # Compute the simulation status based on the current state
    sim_status = sim_enabled and sim_activated

    # Set text for the buttons
    enable_text = "Sim Disable" if sim_enabled else "Sim Enable"
    # The activate button should be enabled only if simulation is enabled
    activate_enabled = not sim_enabled

    status_text = "Simulation mode: active" if sim_status else "Simulation mode: inactive"

    return enable_text, activate_enabled, status_text

# Callback for sending pressure value
@callback(
    Output("sim-pressure-button", "disabled"),
    Input("sim-pressure-button", "n_clicks"),
    State("sim-pressure-input", "value"),
    prevent_initial_call=True
)
def send_pressure(n_clicks, pressure_value):
    global sim_status
    if sim_status and pressure_value is not None:
        message = f"CMD,3134,SIMP,{pressure_value:.2f}"
        ser.write(message.encode())
        return False
    return True

# Callback for uploading simulation file
@callback(
    Output('upload-status', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def upload_simulation_file(contents, filename):
    global sim_data  # Store the uploaded DataFrame globally
    if contents is not None:
        try:
            sim_data = process_uploaded_file(contents)
            return f"Successfully uploaded {filename}. Simulation data is ready."
        except Exception as e:
            return f"Error processing file: {str(e)}"
    return "No file uploaded."

@callback(
    Input("interval-component", "n_intervals"),
    prevent_initial_call=True
)
def send_simulated_pressure(n_intervals):
    global sim_data, sim_status, sim_index

    # Only send pressure if both Sim Enable and Sim Activate are active
    if sim_status and not sim_data.empty:
        latest_pressure = sim_data["PRESSURE"].iloc[sim_index % len(sim_data)]
        sim_index += 1
        message = f"CMD,3134,SIMP,{latest_pressure}"
        ser.write(message.encode())

@callback(
    Output('time-dropdown', 'style'),
    Input('set-time-button', 'n_clicks'),
    State('time-dropdown', 'style'),
    prevent_initial_call=True
)
def toggle_time_dropdown(n_clicks, style):
    style['display'] = 'block' if style['display'] == 'none' else 'none'
    return style

# Callback for setting time
@callback(
    Input('time-dropdown', 'value'),
    State('gps-time-display', 'children'),
    prevent_initial_call=True
)
def set_time(time_source, gps_time):
    if time_source == 'GPS':
        time = gps_time
    else:
        time = datetime.now().strftime("%H:%M:%S")
    message = f"CMD,3134,ST,{time}"
    ser.write(message.encode())

# Callback for starting telemetry
@callback(
    Output("telemetry-button", "children"),
    Output("telemetry-state", "data"),
    Input("telemetry-button", "n_clicks"),
    State("telemetry-state", "data"),
    prevent_initial_call=True  
)
def send_attach_container_command(n_clicks, is_on):
    # Toggle state
    state = not is_on
    text = "Stop Telemetry" if state else "Start Telemetry"
    # Send appropriate command
    message = f"CMD,3134,CX,{'ON' if state else 'OFF'}"
    ser.write(message.encode()) 
    
    return text, state

# Main callback for updating all visualizations
@callback(
    [Output('pressure-graph', 'figure'), 
     Output('altitude-graph', 'figure'),
     Output('temperature-graph', 'figure'),
     Output('voltage-graph', 'figure'),
     Output('gyro-rotation-rate-graph', 'figure'),
     Output('map-plot', 'figure'),
     Output('magnetometer-3d', 'figure'),
     Output('gyro-graph', 'figure'),
     Output('accelerometer-3d', 'figure'),
     Output('mission-time-display', 'children'),
     Output('team-id-display', 'children'),
     Output('state-display', 'children'),
     Output('packet-count-display', 'children'),
     Output('mode-display', 'children'),
     Output('command-display', 'children'),
     Output('gps-sats-display', 'children'),
     Output('gps-time-display', 'children'),
     Output('received-packets-display', 'children'),
     Output('compass-reading-display', 'children')],
    Input('interval-component', 'n_intervals'),
    prevent_initial_call=True
)
def update_graphs(n):
    if telemetry.empty:
        return px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), px.line(), "0", datetime.now(), "-", "-"

    # Limit to last 100 readings for smoother visualization
    dff = telemetry.tail(100)

    # Create map
    def create_map(lat, lon):

        fig = go.Figure()

        fig.add_trace(go.Scattermapbox(
            lat=dff[lat],
            lon=dff[lon],
            mode='lines+markers',
            marker=dict(size=10)
        ))
        fig.update_layout(
            title='Real Time Location',
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=dff[lat].iloc[-1], lon=dff[lon].iloc[-1]),
                zoom=13
            ),
            margin=dict(l=10, r=0, t=30, b=0),
            height=300
        )
        return fig
    
    # Create 3D plots
    def create_3d_plot(x_data, y_data, z_data, title):
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=dff[x_data],
            y=dff[y_data],
            z=dff[z_data],
            mode='lines',
            name=title
        ))
        fig.update_layout(
            title=title,
            margin=dict(l=0, r=0, t=30, b=0),
            height=300
        )
        return fig

    top_row_figures = [
        px.line(dff, x='MISSION_TIME', y='ALTITUDE', title='Altitude (m) Over Time'),
        px.line(dff, x='MISSION_TIME', y='TEMPERATURE', title='Temperature (°C) Over Time'),
        px.line(dff, x='MISSION_TIME', y='PRESSURE', title='Pressure (kPa) Over Time'),
    ]

    top_row_figures = [apply_top_row_styling(fig) for fig in top_row_figures]

    figures = [
        px.line(dff, x='MISSION_TIME', y='VOLTAGE', title='Voltage (V) Over Time'),
        px.line(dff, x='MISSION_TIME', y='AUTO_GYRO_ROTATION_RATE', title='Gyro Rotation Rate (°/s) Over Time'),
        create_map('GPS_LATITUDE', 'GPS_LONGITUDE'),
        create_3d_plot('MAG_R', 'MAG_P', 'MAG_Y', 'Magnetometer Readings (G)'),
        create_3d_plot('GYRO_R', 'GYRO_P', 'GYRO_Y', 'Gyro Readings (°/s)'),
        create_3d_plot('ACCEL_R', 'ACCEL_P', 'ACCEL_Y', 'Accelerometer Readings (°/s²)')
    ]

    figures = [apply_graph_styling(fig) for fig in figures]

    latest = dff.tail(1).to_dict('records')[0]

    """
        pressure_fig,
        altitude_fig,
        temperature_fig,
        voltage_fig,
        gyro_rotation_rate_fig,
        map_fig,
        mag_fig,
        gyro_fig,
        acc_fig,
        """
    return top_row_figures + figures + [
        latest['MISSION_TIME'],
        latest['TEAM_ID'],
        latest['STATE'],
        latest['PACKET_COUNT'],
        latest['MODE'],
        latest['CMD_ECHO'],
        latest['GPS_SATS'],
        latest['GPS_TIME'],
        packets_received,
        latest['COMPASS']
    ]
    
if __name__ == '__main__':
    app.run(debug=False, port=8051)