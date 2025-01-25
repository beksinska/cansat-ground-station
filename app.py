from dash import Dash, html, dcc, Output, Input, State, callback
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from datetime import datetime
import random
import pandas as pd

def generate_values():

    # Generate the value chain as specified
    value_chain = random.sample(range(86166, 93948), 1) + random.sample(range(1, 300), 1) + \
                 [random.getrandbits(1)] + random.sample(range(0, 20), 8)
    
    # Additional values not in value_chain
    voltage = random.uniform(3.0, 4.2)  # Typical battery voltage range
    
    # Generate GPS coordinates (small random walk)
    # Starting from a fixed point
    if not hasattr(generate_values, 'lat'):
        generate_values.lat = 51.5074  # London latitude
        generate_values.lon = -0.1278  # London longitude
    
    # Add small random changes
    generate_values.lat += random.uniform(-0.0001, 0.0001)
    generate_values.lon += random.uniform(-0.0001, 0.0001)
    
    # Create data dictionary
    data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pressure': value_chain[0],
        'altitude': value_chain[1],
        'state': value_chain[2],
        'temperature': value_chain[3],
        'packet': value_chain[4],
        'gyro_x': value_chain[5],
        'gyro_y': value_chain[6],
        'gyro_z': value_chain[7],
        'mag_x': value_chain[8],
        'mag_y': value_chain[9],
        'mag_z': value_chain[10],
        'acc_x': value_chain[8],  # Using same values as magnetometer for this example
        'acc_y': value_chain[9],
        'acc_z': value_chain[10],
        'voltage': voltage,
        'latitude': generate_values.lat,
        'longitude': generate_values.lon,
        'team_id': '3134',  
        'mode': 'F',  # Example mode
        'last_command': 'CMD',  # Example command
    }
    
    return data

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
                'Select CSV File '
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
            
            # Calibrate Button
            html.Button(
                "Calibrate",
                id='calibrate-button',
                style={'width': '100%', 'marginBottom': '10px'}
            ),
            
            html.Button(
                "Set Time",
                id='set-time-button',
                style={'width': '100%', 'marginBottom': '20px'}
            ),

            # Status Information
            html.Div([
                html.P("Mission Time:", style={'fontWeight': 'bold'}),
                html.Div(id='mission-time-display', style={'marginBottom': '10px'}),
                
                html.P("Team ID:", style={'fontWeight': 'bold'}),
                html.Div(id='team-id-display', style={'marginBottom': '10px'}),
                
                html.P("State:", style={'fontWeight': 'bold'}),
                html.Div(id='state-display', style={'marginBottom': '10px'}),
                
                html.P("Packet Count:", style={'fontWeight': 'bold'}),
                html.Div(id='packet-count-display', style={'marginBottom': '10px'}),
                
                html.P("Mode:", style={'fontWeight': 'bold'}),
                html.Div(id='mode-display', style={'marginBottom': '10px'}),
                
                html.P("Last Command:", style={'fontWeight': 'bold'}),
                html.Div(id='command-display', style={'marginBottom': '10px'}),
                
                html.P("Satellites:", style={'fontWeight': 'bold'}),
                html.Div("4", style={'marginBottom': '10px'}),
                
                html.P("GPS Time:", style={'fontWeight': 'bold'}),
                html.Div(id='gps-time-display', style={'marginBottom': '10px'}),
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
                dcc.Graph(id='pressure-graph', style={'width': '33%'}),
                dcc.Graph(id='altitude-graph', style={'width': '33%'}),
                dcc.Graph(id='temperature-graph', style={'width': '33%'})
            ], style={'display': 'flex', 'marginBottom': '20px'}),
            
            # Second row
            html.Div([
                dcc.Graph(id='voltage-graph', style={'width': '33%'}),
                dcc.Graph(id='gyro-graph', style={'width': '33%'}),
                dcc.Graph(id='map-plot', style={'width': '33%'})
            ], style={'display': 'flex', 'marginBottom': '20px'}),
            
            # Third row
            html.Div([
                dcc.Graph(id='magnetometer-3d', style={'width': '50%'}),
                dcc.Graph(id='accelerometer-3d', style={'width': '50%'})
            ], style={'display': 'flex'})
            
        ], style={'flex': '1', 'padding': '20px'}),
    ], style={'display': 'flex'}),
    
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
    Output('start-time-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('telemetry-data-store', 'data')
)
def update_data_store(n, current_data):
    if n == 0:
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return [generate_values()], start_time
    
    current_data.append(generate_values())
    return current_data, dash.no_update

# Main callback for updating all visualizations
@callback(
    [Output('pressure-graph', 'figure'),
     Output('altitude-graph', 'figure'),
     Output('temperature-graph', 'figure'),
     Output('voltage-graph', 'figure'),
     Output('gyro-graph', 'figure'),
     Output('map-plot', 'figure'),
     Output('magnetometer-3d', 'figure'),
     Output('accelerometer-3d', 'figure'),
     Output('mission-time-display', 'children'),
     Output('team-id-display', 'children'),
     Output('state-display', 'children'),
     Output('packet-count-display', 'children'),
     Output('mode-display', 'children'),
     Output('command-display', 'children'),
     Output('gps-time-display', 'children')],
    Input('interval-component', 'n_intervals'),
    State('telemetry-data-store', 'data'),
    State('start-time-store', 'data'),
    prevent_initial_call=True
)
def update_telemetry(n_intervals, stored_data, start_time):
    if not stored_data or not start_time:
        return [dash.no_update] * 15
    
    df = pd.DataFrame(stored_data)
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    
    # Create mission times for x-axis
    df['mission_time'] = [(datetime.strptime(t, '%Y-%m-%d %H:%M:%S') - start_dt).total_seconds() for t in df['timestamp']]
    df['mission_time'] = [f"{int(t//60):02d}:{int(t%60):02d}" for t in df['mission_time']]
    
    # Create line plots
    def create_line_plot(y_data, title, y_label):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['mission_time'], y=df[y_data], mode='lines', name=y_label))
        fig.update_layout(
            title=title,
            xaxis_title='Mission Time (MM:SS)',
            yaxis_title=y_label,
            margin=dict(l=0, r=0, t=30, b=0),
            height=300
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
            height=400
        )
        return fig
    
    # Create gyro plot with all three axes
    def create_gyro_plot():
        fig = go.Figure()
        for axis in ['x', 'y', 'z']:
            fig.add_trace(go.Scatter(
                x=df['mission_time'],
                y=df[f'gyro_{axis}'],
                mode='lines',
                name=f'Gyro {axis.upper()}'
            ))
        fig.update_layout(
            title='Gyro Rotation Rate vs Time',
            xaxis_title='Mission Time (MM:SS)',
            yaxis_title='Rotation Rate',
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
            margin=dict(l=0, r=0, t=30, b=0),
            height=300
        )
        return fig
    
    # Create all plots
    pressure_fig = create_line_plot('pressure', 'Pressure vs Time', 'Pressure')
    altitude_fig = create_line_plot('altitude', 'Altitude vs Time', 'Altitude')
    temperature_fig = create_line_plot('temperature', 'Temperature vs Time', 'Temperature')
    voltage_fig = create_line_plot('voltage', 'Voltage vs Time', 'Voltage')
    gyro_fig = create_gyro_plot()
    map_fig = create_map('latitude', 'longitude')
    mag_fig = create_3d_plot('mag_x', 'mag_y', 'mag_z', 'Magnetometer Readings')
    acc_fig = create_3d_plot('acc_x', 'acc_y', 'acc_z', 'Accelerometer Readings')
    
    # Calculate mission time (MM:SS format)
    mission_seconds = (datetime.now() - start_dt).total_seconds()
    mission_time = f"{int(mission_seconds//60):02d}:{int(mission_seconds%60):02d}"
    
    # Get latest values
    latest = df.iloc[-1]
    
    return [
        pressure_fig,
        altitude_fig,
        temperature_fig,
        voltage_fig,
        gyro_fig,
        map_fig,
        mag_fig,
        acc_fig,
        mission_time,
        latest['team_id'],
        latest['state'],
        len(df),  # packet count
        latest['mode'],
        latest['last_command'],
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # GPS time
    ]

if __name__ == "__main__":
    app.run(debug=True, port=8051)