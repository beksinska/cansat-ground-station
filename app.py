from dash import Dash, html, dcc, Output, Input, State, callback
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from datetime import datetime
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import serial

SERIAL_PORT = "/dev/ttyUSB0"  
BAUD_RATE = 9600

num_points = 691

def generate_flight_data(num_points):
    # Start with a base location (example: Kennedy Space Center)
    base_lat = 28.5729
    base_lon = -80.6490
    base_alt = 0  # sea level

    # Generate timestamps
    start_time = datetime.now()
    timestamps = [(start_time + timedelta(seconds=i)).strftime('%H:%M:%S') for i in range(num_points)]

    # Generate flight path data
    data = []
    for i in range(num_points):
        # Calculate progress through flight (0 to 1)
        progress = i / num_points
        
        # Simulate launch trajectory
        # Add some randomness to make it more realistic
        lat = base_lat + (progress * 0.1) + np.random.normal(0, 0.0001)
        lon = base_lon + (progress * 0.1) + np.random.normal(0, 0.0001)
        
        # Simulate altitude profile (parabolic trajectory)
        if progress < 0.5:
            altitude = 1000 * (4 * progress * (1 - progress))  # Rising
        else:
            altitude = 1000 * (4 * (progress - 0.5) * (1.5 - progress))  # Falling
        
        # Add some noise to altitude
        altitude = max(0, altitude + np.random.normal(0, 10))

        # Simulate accelerometer data (m/s²)
        accel_x = np.random.normal(0, 0.2)  # Small variations around 0
        accel_y = np.random.normal(0, 0.2)
        accel_z = np.random.normal(9.81, 0.2)  # Gravity effect
        
        # Simulate magnetometer data (Gauss)
        mag_x = np.random.normal(0.5, 0.05)  # Earth's magnetic field
        mag_y = np.random.normal(0.3, 0.05)
        mag_z = np.random.normal(0.2, 0.05)

        row = {
            'GPS_TIME': timestamps[i],
            'GPS_ALTITUDE': altitude,
            'GPS_LATITUDE': lat,
            'GPS_LONGITUDE': lon,
            'GPS_SATS': str(np.random.randint(4, 12)),
            'CMD_ECHO': 'CMD',
            'ACCEL_R': accel_x,
            'ACCEL_P': accel_y,
            'ACCEL_Y': accel_z,
            'MAG_R': mag_x,
            'MAG_P': mag_y,
            'MAG_Y': mag_z
        }
        data.append(row)
    
    # Create DataFrame and save to CSV
    gps = pd.DataFrame(data)
    #gps['GPS_LONGITUDE'] = gps['GPS_LONGITUDE'].astype(float)
    #gps['GPS_LATITUDE'] = gps['GPS_LATITUDE'].astype(float)
    #gps['GPS_ALTITUDE'] = gps['GPS_ALTITUDE'].astype(float)
    #gps['GPS_SATS'] = gps['GPS_SATS'].astype(float)
    return gps

df = pd.read_csv('flight_simulation.csv', skipinitialspace=True) 
df.columns = df.columns.str.strip()

start_time = pd.to_datetime("00:00:00", format="%H:%M:%S")

# Generate mission times (increments every second)
mission_times = [start_time + pd.to_timedelta(i, unit='s') for i in range(num_points)]

# Convert to hh:mm:ss format
mission_times = [t.strftime("%H:%M:%S") for t in mission_times]

# Convert numeric values (removing units where necessary)
def clean_numeric(value):
    if isinstance(value, str):
        value = value.strip()  # Remove leading/trailing spaces
        parts = value.split()  # Split value from unit (if any)
        try:
            return float(parts[0])  # Extract only the number
        except ValueError:
            return value  # Return original string if conversion fails
    return value 

# Replace "INVALID" values with NaN
df.replace("INVALID", np.nan, inplace=True)

numeric_columns = ['Packet_Count', 'Altitude', 'Temperature', 'Pressure', 'Voltage',
                   'Gyro_R', 'Gyro_P', 'Gyro_Y']
for col in numeric_columns:
    df[col] = df[col].astype(str).apply(clean_numeric)

# Convert Mission_Time to a numerical format (seconds)
df["Mission_Time"] = mission_times

values = df.to_dict('records')
gps = generate_flight_data(num_points)
print(gps.head())
gps_values = gps.to_dict('records')

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
                'Select Simulation File '
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
            html.Div(id='output-data-upload'),
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
                html.Span("ASCENT", id='state-display')],
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
                html.Span("4")],
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
            
            # Second row
            html.Div([
                dcc.Graph(id='voltage-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='gyro-rotation-rate-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='map-plot', style={'width': '33%', 'height': '33%'})
            ], style={'display': 'flex', 'marginBottom': '20px'}),
            
            # Third row
            html.Div([
                dcc.Graph(id='magnetometer-3d', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='gyro-graph', style={'width': '33%', 'height': '33%'}),
                dcc.Graph(id='accelerometer-3d', style={'width': '33%', 'height': '33%'})
            ], style={'display': 'flex'})
            
        ], style={'flex': '1', 'height': '100vh', 'overflowY': 'auto', 'padding': '10px'}),
    ], style={'display': 'flex', 'font-size': '16px'}),
    
    # Hidden storage
    dcc.Store(id='telemetry-data-store', data=[]),
    dcc.Store(id='start-time-store'),
    dcc.Interval(
        id='interval-component',
        interval=1000,  # 1 second interval
        n_intervals=0
    )
])

# Callback for sim button state
@callback(
    Output('sim-enable-button', 'children'),
    Input('sim-enable-button', 'n_clicks'),
    State('sim-enable-button', 'children')
)
def toggle_sim_button(n_clicks, current_text):
    if n_clicks is None:
        return "SIM enable"
    return "SIM disable" if current_text == "SIM enable" else "SIM enable"

# Load data at startup
@callback(
    Output('telemetry-data-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('telemetry-data-store', 'data')
)
def update_data_store(n, current_data):
    if n == 0:
        current_data.append((values[0] | gps_values[0]))
        print(f"Initial Data: {current_data}") 
        return current_data  # Return first row
    
    if n < len(values):  # Check if we still have data to read
        current_data.append((values[n] | gps_values[n]))  # Add next row
        print(f"Updated Data: {current_data[-1]}")  
        return current_data
    
    return dash.no_update

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
    State('telemetry-data-store', 'data'),
    State('start-time-store', 'data'),
    prevent_initial_call=True
)
def update_telemetry(n_intervals, current_data, start_time):
    if not current_data:
        return [dash.no_update] * 15
    
    df = pd.DataFrame(current_data)
    
    # Create line plots
    def create_line_plot(y_data, title, y_label):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Mission_Time'], y=df[y_data], mode='lines', name=y_label))
        fig.update_layout(
            title=title,
            xaxis_title='Mission Time (MM:SS)',
            yaxis_title=y_label,
            margin=dict(l=0, r=0, t=30, b=0),
            height=250
        )
        return fig
    
    # Create 3D plots
    def create_3d_plot(x_data, y_data, z_data, title):
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=df[x_data],
            y=df[y_data],
            z=df[z_data],
            mode='lines',
            name=title
        ))
        fig.update_layout(
            title=title,
            margin=dict(l=0, r=0, t=30, b=0),
            height=300
        )
        return fig

    # Create map
    def create_map(lat, lon):
        fig = go.Figure()
        fig.add_trace(go.Scattermapbox(
            lat=df[lat],
            lon=df[lon],
            mode='lines+markers',
            marker=dict(size=10)
        ))
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=df[lat].iloc[-1], lon=df[lon].iloc[-1]),
                zoom=13
            ),
            margin=dict(l=10, r=0, t=30, b=0),
            height=250
        )
        return fig
    
    # Create all plots
    pressure_fig = create_line_plot('Pressure', 'Pressure vs Time', 'Pressure (kPa)')
    altitude_fig = create_line_plot('Altitude', 'Altitude vs Time', 'Altitude (m)')
    temperature_fig = create_line_plot('Temperature', 'Temperature vs Time', 'Temperature (°C)')
    voltage_fig = create_line_plot('Voltage', 'Voltage vs Time', 'Voltage (V)')
    gyro_rotation_rate_fig = create_line_plot('Gyro_R', 'Gyro Rotation Rate vs Time', 'Gyro Rotation Rate (°/s)')
    map_fig = create_map('GPS_LATITUDE', 'GPS_LONGITUDE')
    mag_fig = create_3d_plot('MAG_R', 'MAG_P', 'MAG_Y', 'Magnetometer Readings (G)')
    gyro_fig = create_3d_plot('Gyro_R', 'Gyro_P', 'Gyro_Y', 'Gyro Readings (°/s)')
    acc_fig = create_3d_plot('ACCEL_R', 'ACCEL_P', 'ACCEL_Y', 'Accelerometer Readings (m/s²)')
    
    # Get latest values
    latest = df.iloc[-1]
    
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
        latest['Mission_Time'],
        latest['Team_ID'],
        latest['Packet_Count'],
        latest['Mode'],
        latest['CMD_ECHO'],
        latest['GPS_TIME']
    ]

if __name__ == "__main__":
    app.run(debug=False, port=8051)