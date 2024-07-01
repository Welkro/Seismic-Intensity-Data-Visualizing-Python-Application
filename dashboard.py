import rasterio
import geopandas as gpd
import numpy as np
import lightningchart as lc
from scipy.interpolate import griddata

# Set the license for LightningChart Python
lc.set_license("LICENSE_KEY")

# Initialize a dashboard with 2x2 grid layout and white theme
dashboard = lc.Dashboard(columns=2, rows=2, theme=lc.Themes.White)
dashboard.open(live=True)

# Initialize charts for different earthquake parameters
chart_intensity = dashboard.ChartXY(
    column_index=0, row_index=0, column_span=1, row_span=1, title='Modified Mercalli Intensity (mmi)')
chart_pga = dashboard.ChartXY(column_index=1, row_index=0,
                              column_span=1, row_span=1, title='Peak Ground Acceleration (g)')
chart_pgv = dashboard.ChartXY(column_index=0, row_index=1,
                              column_span=1, row_span=1, title='Peak Ground Velocity (cm/s)')
chart_psa = dashboard.ChartXY(column_index=1, row_index=1, column_span=1,
                              row_span=1, title='Peak Spectral Acceleration at 1.0s (g)')

# Function to read a TIFF file and return the data and transformation matrix
def read_tiff(file_path):
    with rasterio.open(file_path) as src:
        data = src.read(1)
        transform = src.transform
    return data, transform

# Dictionary containing file paths for each parameter's TIFF file
tiff_paths = {
    'intensity': 'TongariroAndBayOfPlenty/intensity_mmi.tif',
    'pga': 'TongariroAndBayOfPlenty/pga_g.tif',
    'pgv': 'TongariroAndBayOfPlenty/pgv_cms.tif',
    'psa_1.0': 'TongariroAndBayOfPlenty/psa_1p0_g.tif',
}

# Read all data from TIFF files and store in a dictionary
data_dict = {}
for key, path in tiff_paths.items():
    data, transform = read_tiff(path)
    data_dict[key] = (data, transform)

# Function to extract coordinates and values from the TIFF data
def extract_coordinates_and_values(data, transform):
    rows, cols = data.shape
    x_coords = []
    y_coords = []
    values = []

    for row in range(rows):
        for col in range(cols):
            x, y = transform * (col, row)
            x_coords.append(x)
            y_coords.append(y)
            values.append(data[row, col])

    return x_coords, y_coords, values

# Dictionary to store GeoDataFrames for each parameter
gdfs = {}

# Create GeoDataFrames for each parameter using extracted coordinates and values
for key, (data, transform) in data_dict.items():
    x_coords, y_coords, values = extract_coordinates_and_values(data, transform)
    gdfs[key] = gpd.GeoDataFrame({'value': values},
                                 geometry=gpd.points_from_xy(x=x_coords, y=y_coords))
    gdfs[key].set_crs(epsg=4326, inplace=True)  # Assuming WGS84

# Function to create a grid and interpolate data
def create_interpolated_grid(x_values, y_values, values, grid_size=500):
    grid_x, grid_y = np.mgrid[min(x_values):max(x_values):complex(grid_size), min(y_values):max(y_values):complex(grid_size)]
    grid_z = griddata((x_values, y_values), values, (grid_x, grid_y), method='nearest')
    return grid_x, grid_y, grid_z

# Function to create heatmap using Heatmap Grid Series
def create_heatmap(chart, x_values, y_values, values, title, value_description, grid_size=500, palette_steps=None):
    grid_x, grid_y, grid_z = create_interpolated_grid(x_values, y_values, values, grid_size)

    data = grid_z.tolist()

    series = chart.add_heatmap_grid_series(
        columns=grid_size,
        rows=grid_size,
    )
    series.set_start(x=min(x_values), y=min(y_values))
    series.set_step(x=(max(x_values) - min(x_values)) / grid_size,
                    y=(max(y_values) - min(y_values)) / grid_size)
    series.set_intensity_interpolation(True)
    series.invalidate_intensity_values(data)
    series.hide_wireframe()

    if palette_steps:
        series.set_palette_colors(
            steps=palette_steps,
            look_up_property='value',
            percentage_values=False
        )
    else:
        series.set_palette_colors(
            steps=[
                    {'value': 0, 'color': lc.Color(0, 0, 139)},    # Deep blue
                    {'value': 0.25, 'color': lc.Color(0, 104, 204)},  # Bright blue
                    {'value': 0.5, 'color': lc.Color(255, 140, 0)},  # Bright orange
                    {'value': 0.75, 'color': lc.Color(255, 185, 110)}, # Light orange
                    {'value': 1.0, 'color': lc.Color(255, 255, 255)},  # White
            ],
            look_up_property='value',
            percentage_values=True
        )

    chart.get_default_x_axis().set_title('Longitude')
    chart.get_default_y_axis().set_title('Latitude')

    # Set axis limits based on the actual data ranges
    chart.get_default_x_axis().set_interval(min(x_values), max(x_values))
    chart.get_default_y_axis().set_interval(min(y_values), max(y_values))

    chart.add_legend(data=series, horizontal=True).set_title('').set_position(23.5, 19.5)

# Extract values for plotting for intensity
x_values_intensity = [point.x for point in gdfs['intensity'].geometry]
y_values_intensity = [point.y for point in gdfs['intensity'].geometry]
values_intensity = gdfs['intensity']['value'].tolist()

# Create the intensity heatmap with specified palette
create_heatmap(chart_intensity, x_values_intensity, y_values_intensity, values_intensity, 'Modified Mercalli Intensity', 'mmi') #palette_steps=[
#    {'value': min(values_intensity), 'color': lc.Color(0, 64, 128)},
#    {'value': max(values_intensity), 'color': lc.Color(255, 128, 64)},
#])

# Extract values for plotting for pga
x_values_pga = [point.x for point in gdfs['pga'].geometry]
y_values_pga = [point.y for point in gdfs['pga'].geometry]
values_pga = gdfs['pga']['value'].tolist()

# Create the pga heatmap
create_heatmap(chart_pga, x_values_pga, y_values_pga, values_pga, 'Peak Ground Acceleration', 'g')

# Extract values for plotting for pgv
x_values_pgv = [point.x for point in gdfs['pgv'].geometry]
y_values_pgv = [point.y for point in gdfs['pgv'].geometry]
values_pgv = gdfs['pgv']['value'].tolist()

# Create the pgv heatmap
create_heatmap(chart_pgv, x_values_pgv, y_values_pgv, values_pgv, 'Peak Ground Velocity', 'cm/s')

# Extract values for plotting for psa at 1.0s
x_values_psa = [point.x for point in gdfs['psa_1.0'].geometry]
y_values_psa = [point.y for point in gdfs['psa_1.0'].geometry]
values_psa = gdfs['psa_1.0']['value'].tolist()

# Create the psa heatmap
create_heatmap(chart_psa, x_values_psa, y_values_psa, values_psa, 'Peak Spectral Acceleration at 1.0s', 'g')
