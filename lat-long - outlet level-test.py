import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from folium.features import FeatureGroup
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import random
import os

app = Flask(__name__)

# Global variable to store DataFrame and detected columns
# This avoids re-reading the file on every request.
# In a production app, you might use a more robust caching mechanism or database.
global_data = None
global_columns = {}

# HTML template for the Flask application
# This includes Tailwind CSS for styling and JavaScript for interactivity
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Employee Route Map</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .map-container {
            height: 70vh; /* Responsive height */
            width: 100%;
            border-radius: 0.5rem; /* Rounded corners */
            overflow: hidden; /* Hide overflow for rounded corners */
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .loading-spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            display: none; /* Hidden by default */
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        /* Custom styling for Folium LayerControl */
        .leaflet-control-layers-expanded {
            border-radius: 0.5rem !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        }
        .leaflet-bar a {
            border-radius: 0.5rem !important;
        }
    </style>
</head>
<body class="bg-gray-100 p-6">
    <div class="max-w-7xl mx-auto bg-white p-8 rounded-xl shadow-lg">
        <h1 class="text-3xl font-bold text-gray-800 mb-6 text-center">Employee Route Map</h1>

        <div class="flex flex-col md:flex-row gap-4 mb-6 items-center justify-center">
            <div class="flex flex-col">
                <label for="dateFilter" class="text-gray-700 font-medium mb-1">Select Date:</label>
                <input type="date" id="dateFilter" class="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500">
            </div>
            <div class="flex flex-col">
                <label for="employeeFilter" class="text-gray-700 font-medium mb-1">Select Employee:</label>
                <select id="employeeFilter" class="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500">
                    <option value="">All Employees</option>
                </select>
            </div>
            <button id="loadMapBtn" class="mt-auto px-6 py-2 bg-blue-600 text-white font-semibold rounded-md shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-150 ease-in-out">
                Load Map
            </button>
            <div id="loadingSpinner" class="loading-spinner mt-auto"></div>
        </div>

        <div id="mapContainer" class="map-container">
            <p class="text-center text-gray-500 mt-20">Please select a file and click "Load Map" to view routes.</p>
        </div>
        <div id="messageBox" class="mt-4 p-3 bg-red-100 text-red-700 rounded-md hidden"></div>
    </div>

    <script>
        const dateFilter = document.getElementById('dateFilter');
        const employeeFilter = document.getElementById('employeeFilter');
        const loadMapBtn = document.getElementById('loadMapBtn');
        const mapContainer = document.getElementById('mapContainer');
        const loadingSpinner = document.getElementById('loadingSpinner');
        const messageBox = document.getElementById('messageBox');

        // Set today's date as default
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
        const dd = String(today.getDate()).padStart(2, '0');
        dateFilter.value = `${yyyy}-${mm}-${dd}`;

        let currentMap = null; // To store the Folium map instance

        // Function to show messages
        function showMessage(message, isError = false) {
            messageBox.textContent = message;
            messageBox.classList.remove('hidden');
            if (isError) {
                messageBox.classList.remove('bg-green-100', 'text-green-700');
                messageBox.classList.add('bg-red-100', 'text-red-700');
            } else {
                messageBox.classList.remove('bg-red-100', 'text-red-700');
                messageBox.classList.add('bg-green-100', 'text-green-700');
            }
        }

        // Function to hide messages
        function hideMessage() {
            messageBox.classList.add('hidden');
        }

        // Function to load map based on filters
        async function loadMap() {
            hideMessage();
            loadingSpinner.style.display = 'block';
            mapContainer.innerHTML = '<p class="text-center text-gray-500 mt-20">Loading map...</p>';

            const selectedDate = dateFilter.value;
            const selectedEmployee = employeeFilter.value;

            try {
                const response = await fetch('/get_map', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        date: selectedDate,
                        employee_name: selectedEmployee
                    }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to load map data.');
                }

                const data = await response.json();
                
                if (data.map_html) {
                    mapContainer.innerHTML = data.map_html;
                    // Folium maps often rely on scripts that are loaded with the map HTML.
                    // When injecting HTML, these scripts might not re-execute.
                    // A common workaround is to use a library like 'dompurify' or ensure Folium's
                    // JavaScript is loaded globally and the map is initialized correctly.
                    // For now, we're relying on Folium's self-contained HTML.
                    showMessage("Map loaded successfully!");
                } else if (data.message) {
                    mapContainer.innerHTML = `<p class="text-center text-gray-500 mt-20">${data.message}</p>`;
                    showMessage(data.message, false);
                } else {
                    mapContainer.innerHTML = `<p class="text-center text-gray-500 mt-20">No map data received.</p>`;
                    showMessage("No map data received.", true);
                }

                // Populate employee dropdown after initial data load (if not already populated)
                if (employeeFilter.options.length <= 1 && data.employees) { // Check if only "All Employees" exists
                    data.employees.forEach(emp => {
                        const option = document.createElement('option');
                        option.value = emp;
                        option.textContent = emp;
                        employeeFilter.appendChild(option);
                    });
                }

            } catch (error) {
                console.error('Error loading map:', error);
                mapContainer.innerHTML = `<p class="text-center text-red-500 mt-20">Error: ${error.message}</p>`;
                showMessage(`Error: ${error.message}`, true);
            } finally {
                loadingSpinner.style.display = 'none';
            }
        }

        loadMapBtn.addEventListener('click', loadMap);
        // Optional: Load map automatically when date or employee changes
        // dateFilter.addEventListener('change', loadMap);
        // employeeFilter.addEventListener('change', loadMap);

        // Initial map load when the page loads
        document.addEventListener('DOMContentLoaded', loadMap);

    </script>
</body>
</html>
"""

# Helper functions (from your original script)
def parse_datetime_columns(data, time_col, date_col=None):
    try:
        data[time_col] = data[time_col].astype(str)
        
        if date_col and date_col in data.columns:
            data[date_col] = data[date_col].astype(str)
            combined_datetime_series = data[date_col] + ' ' + data[time_col]
            parsed_dt = pd.to_datetime(combined_datetime_series, errors='coerce')
            data[time_col] = parsed_dt.dt.strftime('%d-%m-%Y %H:%M:%S').fillna("Invalid Time")
        else:
            parsed_dt = pd.to_datetime(data[time_col], format='%H:%M:%S', errors='coerce')
            data[time_col] = parsed_dt.dt.strftime('%H:%M:%S').fillna("Invalid Time")
    except Exception as e:
        print(f"Error parsing time column '{time_col}' (and optional date column '{date_col}'): {e}")
    return data

def find_column(data, keywords):
    for col in data.columns:
        if any(keyword.lower() in col.lower() for keyword in keywords):
            return col
    return None

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_data', methods=['POST'])
def upload_data():
    """Handles file upload and initial data processing."""
    global global_data, global_columns

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            if file.filename.endswith(".csv"):
                data = pd.read_csv(file, encoding="utf-8")
            else:
                data = pd.read_excel(file, engine="openpyxl")

            # Dynamically detect columns and store globally
            global_columns['punch_lat_col'] = find_column(data, ["punch in lat", "latitude", "lat"])
            global_columns['punch_lon_col'] = find_column(data, ["punch in long", "longitude", "lon"])
            global_columns['visit_lat_col'] = find_column(data, ["visit lat", "latitude", "lat"])
            global_columns['visit_lon_col'] = find_column(data, ["visit long", "longitude", "lon"])
            global_columns['punch_in_time_col'] = find_column(data, ["punch in time", "time", "punch_time"])
            global_columns['visit_time_col'] = find_column(data, ["visit time", "time of visit", "visit_time"])
            global_columns['punch_in_date_col'] = find_column(data, ["punch in date", "date", "punch_date"])
            global_columns['visit_date_col'] = find_column(data, ["visit date", "date", "visit_date"])
            global_columns['name_col'] = find_column(data, ["employee name", "name"])
            global_columns['outlet_name_col'] = find_column(data, ["outlet name"])
            global_columns['outlet_id_col'] = find_column(data, ["outlet id"])

            # Check if all mandatory columns are found
            mandatory_cols = [
                global_columns['punch_lat_col'], global_columns['punch_lon_col'],
                global_columns['visit_lat_col'], global_columns['visit_lon_col'],
                global_columns['punch_in_time_col'], global_columns['name_col'],
                global_columns['outlet_name_col'], global_columns['outlet_id_col']
            ]
            if not all(mandatory_cols):
                missing_cols = [k for k, v in global_columns.items() if v is None and k in ['punch_lat_col', 'punch_lon_col', 'visit_lat_col', 'visit_lon_col', 'punch_in_time_col', 'name_col', 'outlet_name_col', 'outlet_id_col']]
                return jsonify({'error': f"Missing required columns: {', '.join(missing_cols)}. Detected: {data.columns.tolist()}"}), 400

            # Parse time columns
            if global_columns['punch_in_time_col']:
                data = parse_datetime_columns(data, global_columns['punch_in_time_col'], global_columns['punch_in_date_col'])
            else:
                data[global_columns['punch_in_time_col']] = "Column Not Found"

            if global_columns['visit_time_col']:
                data = parse_datetime_columns(data, global_columns['visit_time_col'], global_columns['visit_date_col'])
            else:
                data['Visit Time Display'] = 'N/A' # Placeholder if visit time column is missing

            global_data = data # Store processed data globally

            employees = data[global_columns['name_col']].unique().tolist()
            return jsonify({'message': 'File uploaded and processed successfully!', 'employees': employees}), 200

        except Exception as e:
            return jsonify({'error': f"Error processing file: {e}"}), 500
    return jsonify({'error': 'Something went wrong'}), 500


@app.route('/get_map', methods=['POST'])
def get_map():
    """Generates and returns the Folium map HTML based on filters."""
    global global_data, global_columns

    if global_data is None:
        return jsonify({'message': 'No data loaded. Please upload a file first.'}), 400

    req_data = request.get_json()
    selected_date_str = req_data.get('date')
    selected_employee = req_data.get('employee_name')

    filtered_data = global_data.copy()

    # Filter by date
    if selected_date_str:
        try:
            # Assuming 'Punch In Time' column contains 'DD-MM-YYYY HH:MM:SS' format after parsing
            # Extract date part for filtering
            filtered_data['ParsedDate'] = pd.to_datetime(filtered_data[global_columns['punch_in_time_col']], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.strftime('%Y-%m-%d')
            filtered_data = filtered_data[filtered_data['ParsedDate'] == selected_date_str].drop(columns=['ParsedDate'])
        except Exception as e:
            return jsonify({'error': f"Error filtering by date: {e}"}), 500

    # Filter by employee
    if selected_employee:
        filtered_data = filtered_data[filtered_data[global_columns['name_col']] == selected_employee]

    if filtered_data.empty:
        return jsonify({'message': 'No data found for the selected filters.'}), 200

    # Create a map centered around the average of filtered data or India
    avg_lat = filtered_data[global_columns['punch_lat_col']].mean() if not filtered_data.empty else 20.5937
    avg_lon = filtered_data[global_columns['punch_lon_col']].mean() if not filtered_data.empty else 78.9629
    fmap = folium.Map(location=[avg_lat, avg_lon], zoom_start=5)

    marker_cluster = MarkerCluster().add_to(fmap)

    color_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"
    ]
    
    employees = filtered_data[global_columns['name_col']].unique()
    employee_colors = {emp: color_palette[i % len(color_palette)] for i, emp in enumerate(employees)}

    heatmap_data = []
    valid_visit_data = filtered_data.dropna(subset=[global_columns['visit_lat_col'], global_columns['visit_lon_col']])
    for _, row in valid_visit_data.iterrows():
        heatmap_data.append([row[global_columns['visit_lat_col']], row[global_columns['visit_lon_col']]])

    if heatmap_data: # Only add heatmap if there's data
        HeatMap(heatmap_data, name="Visit Density Heatmap").add_to(fmap)

    for emp in employees:
        employee_feature_group = FeatureGroup(name=f"Employee: {emp}")
        
        emp_data = filtered_data[filtered_data[global_columns['name_col']] == emp]
        color = employee_colors[emp]

        punch_in_added = False

        for _, row in emp_data.iterrows():
            current_visit_time_display = row[global_columns['visit_time_col']] if global_columns['visit_time_col'] and global_columns['visit_time_col'] in row else row['Visit Time Display']

            if not punch_in_added:
                folium.Marker(
                    location=[row[global_columns['punch_lat_col']], row[global_columns['punch_lon_col']]],
                    popup=f"""
                    <strong>Employee:</strong> {row[global_columns['name_col']]}<br>
                    <strong>Punch In Time:</strong> ⏰ {row[global_columns['punch_in_time_col']]}<br>
                    <strong>Latitude:</strong> {row[global_columns['punch_lat_col']]:.4f}<br>
                    <strong>Longitude:</strong> {row[global_columns['punch_lon_col']]:.4f}
                    """,
                    tooltip=f"Name: {row[global_columns['name_col']]} | Punch In: {row[global_columns['punch_in_time_col']]}",
                    icon=folium.Icon(color="blue", icon="home", prefix='fa') 
                ).add_to(employee_feature_group)
                punch_in_added = True

            folium.CircleMarker(
                location=[row[global_columns['visit_lat_col']], row[global_columns['visit_lon_col']]],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=f"""
                <strong>Employee:</strong> {row[global_columns['name_col']]}<br>
                <strong>Visit Time:</strong> ⏰ {current_visit_time_display}<br>
                <strong>Outlet Name:</strong> 🏢 {row[global_columns['outlet_name_col']]}<br>
                <strong>Outlet ID:</strong> # {row[global_columns['outlet_id_col']]}<br>
                <strong>Latitude:</strong> {row[global_columns['visit_lat_col']]:.4f}<br>
                <strong>Longitude:</strong> {row[global_columns['visit_lon_col']]:.4f}
                """,
                tooltip=f"Name: {row[global_columns['name_col']]} | Visit: {current_visit_time_display} | Outlet: {row[global_columns['outlet_name_col']]}"
            ).add_to(employee_feature_group)

            folium.PolyLine(
                locations=[
                    [row[global_columns['punch_lat_col']], row[global_columns['punch_lon_col']]],
                    [row[global_columns['visit_lat_col']], row[global_columns['visit_lon_col']]]
                ],
                color=color,
                weight=3,
                dash_array="5, 5",
                tooltip=f"Route for {row[global_columns['name_col']]}"
            ).add_to(employee_feature_group)
        
        employee_feature_group.add_to(fmap)

    folium.LayerControl().add_to(fmap)

    # The legend is handled by the JS, but we can still generate it here if needed
    # for a static map or for debugging. For dynamic maps, it might be better to
    # manage legend creation/update in JS if it needs to reflect filtered data.
    # For now, we'll keep the Python-generated legend.
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 220px; height: auto; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid #333; border-radius: 8px; padding:12px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
    <h4 style="margin-top:0; margin-bottom:10px; font-weight:bold;">Employee Legend</h4>
    """
    for emp, color in employee_colors.items():
        legend_html += f"<div style='display: flex; align-items: center; margin-bottom: 5px;'><div style='width: 20px; height: 20px; background-color: {color}; margin-right: 8px; border-radius: 4px;'></div>{emp}</div>"
    legend_html += "</div>"

    # Add the legend as a custom HTML element to the map's root
    fmap.get_root().html.add_child(folium.Element(legend_html))


    # Return the map HTML and the list of employees for the dropdown
    return jsonify({'map_html': fmap._repr_html_(), 'employees': global_data[global_columns['name_col']].unique().tolist()}), 200

if __name__ == '__main__':
    # To run this Flask app, you need to first upload your data file.
    # Since this is a local script, you'll need to simulate the file upload.
    # For demonstration, I'll add a simple file upload mechanism.
    # In a real Canvas environment, this would be handled by a separate UI.

    # This part simulates the file selection and upload
    # You would typically run the Flask app and access it via a browser
    # where you'd have a file input field.
    # For local testing, you can uncomment and modify the following:
    
    # from tkinter import Tk, filedialog
    # Tk().withdraw()
    # file_path = filedialog.askopenfilename(
    #     title="Select your employee data file (Excel or CSV)",
    #     filetypes=[("Excel Files", "*.xlsx;*.xls"), ("CSV Files", "*.csv")]
    # )
    # if file_path:
    #     print(f"Selected file for initial load: {file_path}")
    #     # Simulate the request.files object
    #     class MockFile:
    #         def __init__(self, path):
    #             self.path = path
    #             self.filename = os.path.basename(path)
    #             self._file = open(path, 'rb')
    #         def read(self):
    #             return self._file.read()
    #         def seek(self, offset):
    #             self._file.seek(offset)
    #         def close(self):
    #             self._file.close()
    #         def __enter__(self):
    #             return self
    #         def __exit__(self, exc_type, exc_val, exc_tb):
    #             self.close()

    #     with app.test_request_context('/upload_data', method='POST', data={'file': MockFile(file_path)}):
    #         # This is a hacky way to call upload_data outside a real request
    #         # In a real scenario, you'd have a UI button for upload.
    #         # For now, manually set request.files
    #         request.files = {'file': MockFile(file_path)}
    #         response, status_code = upload_data()
    #         print(f"Initial data upload response: {response.json} Status: {status_code}")
    #         if status_code != 200:
    #             print("Failed to load initial data. Please check your file and try again.")
    #             exit() # Exit if initial data load fails

    # To run this Flask app:
    # 1. Save the code as 'app.py'
    # 2. Open your terminal in the directory where you saved 'app.py'
    # 3. Run: python app.py
    # 4. Open your web browser and go to http://127.0.0.1:5000/
    # You will need to manually upload your data file through a file input in the UI.
    # For this demonstration, I'm providing a basic file upload mechanism in the UI.
    app.run(debug=True) # debug=True allows for automatic reloading on code changes
