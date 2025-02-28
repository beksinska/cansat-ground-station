from dash import Dash, html, dcc, Output, Input, State, callback
import dash
import io
import base64
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import time
import threading
from communication import send_pressure_via_xbee, read_telemetry

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
    global sim_enabled, sim_activated, sim_status

    # Toggle Sim Enable / Disable
    if enable_clicks % 2 == 1:  # Odd clicks -> Sim Enabled
        sim_enabled = True
        button_text = "Sim Disable"
        activate_disabled = False  # Enable Sim Activate button
        print("Sim Enabled")
    else:  # Even clicks -> Sim Disabled
        sim_enabled = False
        sim_activated = False
        sim_status = False
        button_text = "Sim Enable"
        activate_disabled = True  # Disable Sim Activate button
        print("Sim Disabled")
        return button_text, activate_disabled, "Simulation Mode: INACTIVE"
    
    # Check Sim Activate
    if sim_enabled and activate_clicks > 0:
        sim_activated = True
        print("Sim Activated")

    # Update Sim Status
    sim_status = sim_enabled and sim_activated

    # Set Status Text
    status_text = "Simulation Mode: ACTIVE" if sim_status else "Simulation Mode: INACTIVE"

    return button_text, activate_disabled, status_text


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
    
    latest = dff.iloc[-1]

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