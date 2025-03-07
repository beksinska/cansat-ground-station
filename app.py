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
from communication import send_pressure_via_xbee
from datetime import datetime
import serial

SERIAL_PORT = "COM3"  
BAUD_RATE = 9600

# Open serial port
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

start_time = pd.to_datetime("00:00:00", format="%H:%M:%S")

columns = [
    "TEAM_ID", "MISSION_TIME", "PACKET_COUNT", "MODE", "STATE",
    "ALTITUDE", "TEMPERATURE", "PRESSURE", "VOLTAGE",
    "GYRO_R", "GYRO_P", "GYRO_Y", "ACCEL_R", "ACCEL_P", "ACCEL_Y",
    "MAG_R", "MAG_P", "MAG_Y", "AUTO_GYRO_ROTATION_RATE",
    "GPS_TIME", "GPS_ALTITUDE", "GPS_LATITUDE", "GPS_LONGITUDE",
    "GPS_SATS", "CMD_ECHO"
]

# Global DataFrame to store telemetry
telemetry = pd.DataFrame(columns=columns)

def generate_missing_values():

    gps_lat = 28.5729 + np.random.normal(0, 0.0001)  # Simulated GPS drift
    gps_lon = -80.6490 + np.random.normal(0, 0.0001)
    gps_alt = np.random.uniform(0, 1000)  # Random altitude between 0-1000m
    gps_sats = np.random.randint(4, 12)
    gps_time = datetime.now()
    return {
        "GPS_LATITUDE": gps_lat, "GPS_LONGITUDE": gps_lon, "GPS_ALTITUDE": gps_alt, "GPS_SATS": gps_sats, "GPS_TIME": gps_time 
    }

def read_telemetry():
    global telemetry
    
    try:
        while True:

            if not ser.isOpen():
                ser.open()
            line = ser.readline().decode('utf-8').strip()  # Read line from serial
            if line:
                values = line.split(",")
            if len(values) == 25:
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

                #print(f"Received: {telemetry_data}")

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

sim_enabled = False
sim_activated = False
sim_status= False

sim_data = pd.DataFrame()

def process_uploaded_file(contents):
    """Decodes the uploaded CSV file and returns a Pandas DataFrame."""
    content_string = contents.split(',')[1]  # Extract only the Base64 part
    decoded = base64.b64decode(content_string)  # Decode Base64
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))  # Convert to DataFrame
    return df

def read_simulated_pressure():
    """Extract latest pressure value from simulation file"""
    global sim_data
    if not sim_data.empty:
        return sim_data["PRESSURE"].iloc[-1]  # Get latest pressure
    return None

"""Send pressure via XBee if in simulation mode"""
def process_simulation_telemetry():
    global sim_status
    while True:
        if sim_status:
            pressure = read_simulated_pressure()
            send_pressure_via_xbee(pressure)  

        # Wait for 1 second before next iteration
        time.sleep(1)

thread = threading.Thread(target=read_telemetry, daemon=True)
thread.start()

# Initialize the Dash app
app = Dash(__name__)

# Define the layout
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
            html.Div(id='file-upload-status'),

            # Simulation Control
            html.Button(
                "SIM Enable",
                id='sim-enable-button',
                style={'width': '100%', 'marginBottom': '10px'}
            ),

            html.Button(
                "SIM Activate",
                id='sim-activate-button',
                style={'width': '100%', 'marginBottom': '10px'}
            ),

            html.Div(id='sim-status'),

            html.Button(
                "Setup",
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

            html.Button(
                "Start Telemetry",
                id='start-telemetry-button',
                style={'width': '100%', 'marginBottom': '20px'}
            ),

            # Status Information
            html.Div([
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
                html.Span("", id='state-display')],
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
                html.Span("")],
                style={'display': 'flex', 'flexDirection': 'row'}),

                html.Div([
                html.Span("GPS Time:", style={'fontWeight': 'bold', 'marginRight': '4px'}),
                html.Span(id='gps-time-display')],
                style={'display': 'flex', 'flexDirection': 'row'}),
            ])
        ], style={
            'width': '200px',
            'padding': '20px',
            'backgroundColor': '#f8f9fa',
            'borderRadius': '5px',
            'marginRight': '20px',
            'height': '100vh',
            'overflowY': 'auto'
        }),
        
        # Main content area
        html.Div([
            # First row - Pressure, Altitude, Temperature
            html.Div([
                dcc.Graph(id='pressure-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='altitude-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='temperature-graph', style={'width': '33%', 'height': '33%'})
            ], style={'display': 'flex', 'marginBottom': '20px'}),
            
            # Second row - Voltage, Gyro rotation, Map
            html.Div([
                dcc.Graph(id='voltage-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='gyro-rotation-rate-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='map-plot', style={'width': '33%', 'height': '33%'})
            ], style={'display': 'flex', 'marginBottom': '20px'}),
            
            # Third row - Magnetometer, Gyro, Accelerometer
            html.Div([
                dcc.Graph(id='magnetometer-3d', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='gyro-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='accelerometer-3d', style={'width': '33%', 'height': '33%'})
            ], style={'display': 'flex'})
            
        ], style={'flex': '1', 'height': '100vh', 'overflowY': 'auto', 'padding': '10px'}),
    ], style={'display': 'flex', 'font-size': '16px'}),
    
    dcc.Interval(
        id='interval-component',
        interval=1000,  # 1 second interval
        n_intervals=0
    )
])

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
    global sim_enabled, sim_activated, sim_status

    # Update states based on the last pressed button:
    if button_id == "sim-enable-button":
        # Toggle the sim_enabled state
        sim_enabled = not sim_enabled
        # When disabling simulation, also reset sim_activated
        if not sim_enabled:
            sim_activated = False
            
    elif button_id == "sim-activate-button":
        # Only toggle activation if simulation is enabled
        if sim_enabled:
            sim_activated = not sim_activated

    # Compute the simulation status based on the current state
    sim_status = sim_enabled and sim_activated

    # Set text for the buttons
    enable_text = "Sim Disable" if sim_enabled else "Sim Enable"
    # The activate button should be enabled only if simulation is enabled
    activate_enabled = not sim_enabled

    status_text = "Simulation mode: active" if sim_status else "Simulation mode: inactive"

    return enable_text, activate_enabled, status_text


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

# Callback for starting telemetry
@callback(
        [Output("telemetry-button", "children"), Output("telemetry-status", "children")],
        Input('start-telemetry-button', 'n_clicks'),
)
def start_telemetry(n):
    read_telemetry()

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
     Output('packet-count-display', 'children'),
     Output('mode-display', 'children'),
     Output('command-display', 'children'),
     Output('gps-time-display', 'children')],
    Input('interval-component', 'n_intervals'),
    prevent_initial_call=True
)
def update_graphs(n):

    if telemetry.empty:
        return px.line(), px.line(), px.line(), px.line(), px.line()

    lat_default = 52.47
    lon_default = 13.45
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
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=dff[lat].iloc[-1], lon=dff[lon].iloc[-1]),
                zoom=13
            ),
            margin=dict(l=10, r=0, t=30, b=0),
            height=250
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

    altitude_fig = px.line(dff, x='MISSION_TIME', y='ALTITUDE', title='Altitude Over Time')
    temperature_fig = px.line(dff, x='MISSION_TIME', y='TEMPERATURE', title='Temperature Over Time')
    pressure_fig = px.line(dff, x='MISSION_TIME', y='PRESSURE', title='Pressure Over Time')
    voltage_fig = px.line(dff, x='MISSION_TIME', y='VOLTAGE', title='Voltage Over Time')
    gyro_rotation_rate_fig = px.line(dff, x='MISSION_TIME', y='GYRO_R', title='Gyro Rotation Rate Over Time')
    map_fig = create_map('GPS_LATITUDE', 'GPS_LONGITUDE')
    mag_fig = create_3d_plot('MAG_R', 'MAG_P', 'MAG_Y', 'Magnetometer Readings')
    gyro_fig = create_3d_plot('GYRO_R', 'GYRO_P', 'GYRO_Y', 'Gyro Readings')
    acc_fig = create_3d_plot('ACCEL_R', 'ACCEL_P', 'ACCEL_Y', 'Accelerometer Readings')
    

    latest = dff.tail(1).to_dict('records')[0]

    return [
        pressure_fig,
        altitude_fig,
        temperature_fig,
        voltage_fig,
        gyro_rotation_rate_fig,
        map_fig,
        mag_fig,
        gyro_fig,
        acc_fig,
        latest['MISSION_TIME'],
        latest['TEAM_ID'],
        latest['PACKET_COUNT'],
        latest['MODE'],
        latest['CMD_ECHO'],
        latest['GPS_TIME']
        ]
    
if __name__ == '__main__':
    app.run(debug=False, port=8051)