import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap
from folium.features import FeatureGroup
from flask import Flask, render_template_string, request, jsonify, send_file
from datetime import datetime
import random
import os
import io
import math # Import the math module for distance calculations

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024  # 50 MB

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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #f0f4f8; /* Lighter, more neutral background */
            color: #334155; /* Darker text for better contrast */
        }
        .map-container {
            height: 70vh; /* Responsive height */
            width: 100%;
            border-radius: 1.25rem; /* Even more rounded corners */
            overflow: hidden; /* Hide overflow for rounded corners */
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); /* Deeper shadow */
            background-color: #ffffff; /* White background for map area */
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #e2e8f0; /* Subtle border */
        }
        .loading-spinner {
            border: 4px solid rgba(255, 255, 255, 0.4); /* Lighter border */
            border-top: 4px solid #3b82f6; /* Blue top border */
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
            border-radius: 1rem !important; /* More rounded */
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15) !important;
            background-color: #ffffff !important;
            padding: 12px !important;
            border: 1px solid #cbd5e1 !important; /* Subtle border */
        }
        .leaflet-bar a {
            border-radius: 0.75rem !important;
        }
        /* Button styling */
        .btn-base {
            padding: 1rem 2rem; /* Increased padding */
            font-weight: 700; /* Bolder text */
            border-radius: 1.25rem; /* More rounded */
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); /* Stronger shadow */
            transition: all 0.3s ease-in-out; /* Smoother transition */
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem; /* Increased gap */
            text-transform: uppercase;
            letter-spacing: 0.075em; /* More letter spacing */
            font-size: 1rem; /* Consistent font size */
        }
        .btn-green {
            background: linear-gradient(to right, #16a34a, #15803d); /* Deeper green gradient */
            color: white;
            border: 1px solid #15803d;
        }
        .btn-green:hover {
            background: linear-gradient(to right, #15803d, #14532d);
            transform: translateY(-4px); /* More pronounced lift */
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.25); /* Even stronger shadow */
        }
        .btn-blue {
            background: linear-gradient(to right, #2563eb, #1d4ed8); /* Deeper blue gradient */
            color: white;
            border: 1px solid #1d4ed8;
        }
        .btn-blue:hover {
            background: linear-gradient(to right, #1d4ed8, #1e40af);
            transform: translateY(-4px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.25);
        }
        .btn-red {
            background: linear-gradient(to right, #dc2626, #b91c1c); /* Deeper red gradient */
            color: white;
            border: 1px solid #b91c1c;
        }
        .btn-red:hover {
            background: linear-gradient(to right, #b91c1c, #991b1b);
            transform: translateY(-4px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.25);
        }
        .btn-purple { /* New style for Download button */
            background: linear-gradient(to right, #8b5cf6, #7c3aed); /* Purple gradient */
            color: white;
            border: 1px solid #7c3aed;
        }
        .btn-purple:hover {
            background: linear-gradient(to right, #7c3aed, #6d28d9);
            transform: translateY(-4px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.25);
        }
        /* Input/Select styling */
        .input-field {
            padding: 0.85rem 1.5rem; /* Increased padding */
            border: 1px solid #cbd5e1; /* Gray-300 */
            border-radius: 1rem; /* More rounded */
            background-color: #ffffff; /* White background */
            transition: all 0.2s ease-in-out;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.08); /* More prominent inner shadow */
            font-size: 1rem; /* Consistent font size */
            color: #475569; /* Slightly darker text for inputs */
        }
        .input-field:focus {
            border-color: #3b82f6; /* Blue-500 */
            box-shadow: 0 0 0 5px rgba(59, 130, 246, 0.4); /* More prominent focus ring */
            outline: none;
            background-color: #ffffff;
        }
        .message-box {
            padding: 1.25rem 1.75rem; /* More padding */
            border-radius: 1rem; /* More rounded */
            font-weight: 600; /* Bolder message text */
            text-align: center;
            transition: all 0.4s ease-in-out; /* Smoother transition */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); /* More pronounced shadow */
            font-size: 1.05rem;
        }
        .message-box.error {
            background-color: #fee2e2; /* Red-100 */
            color: #dc2626; /* Red-700 */
            border: 1px solid #fca5a5; /* Red-300 */
        }
        .message-box.success {
            background-color: #d1fae5; /* Green-100 */
            color: #15803d; /* Green-700 */
            border: 1px solid #6ee7b7; /* Green-300 */
        }
        .message-box.info { /* New style for info messages */
            background-color: #e0f2fe; /* Light blue-100 */
            color: #2563eb; /* Blue-700 */
            border: 1px solid #93c5fd; /* Blue-300 */
        }
        /* Custom Marker Legend */
        .marker-legend {
            position: fixed; 
            top: 20px; right: 20px; 
            width: 220px; height: auto; 
            background-color: rgba(255, 255, 255, 0.98); /* Almost opaque white */
            z-index:9999; font-size:16px; /* Slightly larger font */
            border:1px solid #cfd8dc; /* Lighter, more subtle border */
            border-radius: 1rem; /* More rounded */
            padding:18px; /* More padding */
            box-shadow: 0 8px 16px rgba(0,0,0,0.2); /* Stronger, softer shadow */
        }
        .marker-legend-item {
            display: flex; 
            align-items: center; 
            margin-bottom: 10px; /* More space */
        }
        .marker-legend-icon {
            width: 32px; /* Larger icon area */
            height: 32px; 
            margin-right: 12px; /* More space */
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .marker-legend-icon .fa {
            font-size: 22px; /* Larger icon */
        }
        .marker-legend-icon .circle {
            width: 20px; /* Larger circle */
            height: 20px;
            border-radius: 50%;
            border: 2px solid;
            background-color: green;
        }
        /* Employee Color Legend */
        .employee-legend {
            position: fixed; 
            bottom: 20px; left: 20px; 
            width: 260px; height: auto; 
            background-color: rgba(255, 255, 255, 0.98); /* Almost opaque white */
            z-index:9999; font-size:16px; /* Slightly larger font */
            border:1px solid #cfd8dc; /* Lighter, more subtle border */
            border-radius: 1rem; /* More rounded */
            padding:18px; /* More padding */
            box-shadow: 0 8px 16px rgba(0,0,0,0.2); /* Stronger, softer shadow */
        }
        .employee-legend-item {
            display: flex; 
            align-items: center; 
            margin-bottom: 10px;
        }
        .employee-legend-color-box {
            width: 24px; /* Larger color box */
            height: 24px; 
            border-radius: 50%; 
            margin-right: 12px; 
            border: 1px solid #a0aec0; /* More prominent border for color box */
        }
        /* Heading and Label styling */
        h1 {
            color: #1a202c; /* Darker heading color */
        }
        label {
            color: #475569; /* Slightly darker label color */
            font-size: 1.15rem; /* Larger labels */
        }
    </style>
</head>
<body class="bg-gray-100 p-8">
    <div class="max-w-7xl mx-auto bg-white p-10 rounded-3xl shadow-2xl border border-gray-200">
        <div class="flex flex-col items-center mb-10">
            <img src="/static/Mylo_Logo.png" alt="Mylo Logo" class="w-24 h-auto mb-5 rounded-2xl shadow-xl"> <!-- Larger logo, more rounded -->
            <h1 class="text-4xl font-extrabold text-gray-900 text-center leading-tight">
                <i class="fa fa-map-marker text-blue-600 mr-5"></i> Employee Route Tracker
            </h1>
            <p class="text-gray-600 mt-3 text-xl">Visualize employee routes and visit patterns with precision.</p> <!-- Larger, more descriptive tagline -->
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10 items-end">
            <div class="flex flex-col col-span-2">
                <label for="fileUpload" class="text-gray-700 font-semibold mb-3 text-xl">Upload Data File:</label>
                <input type="file" id="fileUpload" accept=".csv, .xls, .xlsx" class="input-field file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-base file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200 file:cursor-pointer">
            </div>
            <button id="uploadFileBtn" class="btn-base btn-green md:col-span-1">
                <i class="fa fa-upload"></i> Upload File
                <div id="loadingSpinnerUpload" class="loading-spinner ml-3"></div>
            </button>
        </div>

        <hr class="my-10 border-gray-200">

        <div class="grid grid-cols-1 md:grid-cols-7 gap-8 mb-10 items-end">
            <div class="flex flex-col md:col-span-1">
                <label for="startDateFilter" class="text-gray-700 font-semibold mb-3 text-xl">Start Date:</label>
                <input type="date" id="startDateFilter" class="input-field" disabled>
            </div>
            <div class="flex flex-col md:col-span-1">
                <label for="endDateFilter" class="text-gray-700 font-semibold mb-3 text-xl">End Date:</label>
                <input type="date" id="endDateFilter" class="input-field" disabled>
            </div>
            <div class="flex flex-col md:col-span-2">
                <label for="employeeFilter" class="text-gray-700 font-semibold mb-3 text-xl">Select Employee:</label>
                <select id="employeeFilter" class="input-field" disabled>
                    <option value="">All Employees</option>
                </select>
            </div>
            <button id="loadMapBtn" class="btn-base btn-blue md:col-span-1">
                <i class="fa fa-refresh"></i> Load Map
                <div id="loadingSpinnerMap" class="loading-spinner ml-3"></div>
            </button>
            <button id="downloadMapBtn" class="btn-base btn-purple md:col-span-1" disabled>
                <i class="fa fa-download"></i> Download Map
            </button>
            <button id="resetFiltersBtn" class="btn-base btn-red md:col-span-1" disabled>
                <i class="fa fa-undo"></i> Reset Filters
            </button>
        </div>

        <div id="mapContainer" class="map-container">
            <p class="text-center text-gray-500 text-xl font-medium">Please upload your data file to get started.</p>
        </div>
        <div id="messageBox" class="message-box mt-8 hidden"></div>
    </div>

    <script>
        const fileUpload = document.getElementById('fileUpload');
        const uploadFileBtn = document.getElementById('uploadFileBtn');
        const startDateFilter = document.getElementById('startDateFilter');
        const endDateFilter = document.getElementById('endDateFilter');
        const employeeFilter = document.getElementById('employeeFilter');
        const loadMapBtn = document.getElementById('loadMapBtn');
        const downloadMapBtn = document.getElementById('downloadMapBtn'); // New button
        const resetFiltersBtn = document.getElementById('resetFiltersBtn');
        const mapContainer = document.getElementById('mapContainer');
        const loadingSpinnerUpload = document.getElementById('loadingSpinnerUpload');
        const loadingSpinnerMap = document.getElementById('loadingSpinnerMap');
        const messageBox = document.getElementById('messageBox');

        // Initial state: empty dates
        startDateFilter.value = '';
        endDateFilter.value = '';

        // Function to show messages
        function showMessage(message, isError = false, isInfo = false) {
            messageBox.textContent = message;
            messageBox.classList.remove('hidden', 'error', 'success', 'info');
            if (isError) {
                messageBox.classList.add('error');
            } else if (isInfo) {
                messageBox.classList.add('info');
            }
            else {
                messageBox.classList.add('success');
            }
            // Optional: Auto-hide message after a few seconds
            setTimeout(() => {
                hideMessage();
            }, 8000); // Increased timeout for info messages
        }

        // Function to hide messages
        function hideMessage() {
            messageBox.classList.add('hidden');
        }

        // Function to enable/disable filter controls
        function setFilterControlsEnabled(enabled) {
            startDateFilter.disabled = !enabled;
            endDateFilter.disabled = !enabled;
            employeeFilter.disabled = !enabled;
            loadMapBtn.disabled = !enabled;
            downloadMapBtn.disabled = !enabled; // Enable/disable download button
            resetFiltersBtn.disabled = !enabled;
        }

        // --- File Upload Logic ---
        uploadFileBtn.addEventListener('click', async () => {
            hideMessage();
            const file = fileUpload.files[0];
            if (!file) {
                showMessage("Please select a file to upload.", true);
                return;
            }

            loadingSpinnerUpload.style.display = 'block';
            uploadFileBtn.disabled = true;
            setFilterControlsEnabled(false);
            mapContainer.innerHTML = '<p class="text-center text-gray-500 text-xl font-medium mt-20">Uploading and processing data...</p>';

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/upload_data', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to upload and process file.');
                }

                const data = await response.json();
                showMessage(data.message || "File uploaded successfully!");
                setFilterControlsEnabled(true);

                // Populate employee dropdown
                employeeFilter.innerHTML = '<option value="">All Employees</option>'; // Clear existing options
                if (data.employees) {
                    data.employees.forEach(emp => {
                        const option = document.createElement('option');
                        option.value = emp;
                        option.textContent = emp;
                        employeeFilter.appendChild(option);
                    });
                }
                
                // Removed automatic loadMap() call here
                // loadMap(); 

            } catch (error) {
                console.error('Error uploading file:', error);
                showMessage(`Error: ${error.message}`, true);
                mapContainer.innerHTML = `<p class="text-center text-red-500 text-xl font-medium mt-20">Error: ${error.message}</p>`;
            } finally {
                loadingSpinnerUpload.style.display = 'none';
                uploadFileBtn.disabled = false;
            }
        });

        // --- Map Loading Logic ---
        async function loadMap() {
            hideMessage();
            loadingSpinnerMap.style.display = 'block';
            loadMapBtn.disabled = true;
            downloadMapBtn.disabled = true; // Disable download during map load
            resetFiltersBtn.disabled = true;
            mapContainer.innerHTML = '<p class="text-center text-gray-500 text-xl font-medium mt-20">Loading map...</p>';

            const selectedStartDate = startDateFilter.value;
            const selectedEndDate = endDateFilter.value;
            const selectedEmployee = employeeFilter.value;

            try {
                const response = await fetch('/get_map', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        start_date: selectedStartDate,
                        end_date: selectedEndDate,
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
                    showMessage("Map loaded successfully!");
                } else if (data.message) {
                    mapContainer.innerHTML = `<p class="text-center text-gray-500 text-xl font-medium mt-20">${data.message}</p>`;
                    showMessage(data.message, false);
                } else {
                    mapContainer.innerHTML = `<p class="text-center text-gray-500 text-xl font-medium mt-20">No map data received.</p>`;
                    showMessage("No map data received.", true);
                }

            } catch (error) {
                console.error('Error loading map:', error);
                mapContainer.innerHTML = `<p class="text-center text-red-500 text-xl font-medium mt-20">Error: ${error.message}</p>`;
                showMessage(`Error: ${error.message}`, true);
            } finally {
                loadingSpinnerMap.style.display = 'none';
                loadMapBtn.disabled = false;
                downloadMapBtn.disabled = false; // Re-enable download after map load
                resetFiltersBtn.disabled = false;
            }
        }

        // --- Download Map Logic ---
        downloadMapBtn.addEventListener('click', async () => {
            hideMessage();
            showMessage("Preparing map for download...", false, true); // Info message

            const selectedStartDate = startDateFilter.value;
            const selectedEndDate = endDateFilter.value;
            const selectedEmployee = employeeFilter.value;

            try {
                const response = await fetch('/download_map_html', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        start_date: selectedStartDate,
                        end_date: selectedEndDate,
                        employee_name: selectedEmployee
                    }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to download map.');
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'employee_route_map.html'; // File name
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                showMessage("Map downloaded successfully as HTML. Open the file and use your browser's print function to save as PDF.", false, true);

            } catch (error) {
                console.error('Error downloading map:', error);
                showMessage(`Error: ${error.message}`, true);
            }
        });


        // --- Reset Filters Logic ---
        resetFiltersBtn.addEventListener('click', () => {
            startDateFilter.value = '';
            endDateFilter.value = '';
            employeeFilter.value = '';
            loadMap(); // Reload map with all filters cleared
        });

        loadMapBtn.addEventListener('click', loadMap);

        // Initial state: disable filters until file is uploaded
        setFilterControlsEnabled(false);

    </script>
</body>
</html>
"""

# Helper functions (from your original script)
def parse_datetime_columns(data, time_col, date_col=None):
    try:
        # Convert time column to string to handle mixed types
        data[time_col] = data[time_col].astype(str)
        
        if date_col and date_col in data.columns:
            # Ensure date_col is parsed to datetime if it's not already, then format to YYYY-MM-DD string
            # This handles cases where date column might be object or datetime64[ns]
            # Use errors='coerce' to turn unparseable dates into NaT
            data[date_col] = pd.to_datetime(data[date_col], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
            
            # Combine date and time strings
            # Only combine if date part is not empty
            combined_datetime_series = data.apply(lambda row: f"{row[date_col]} {row[time_col]}" if row[date_col] else row[time_col], axis=1)
            
            # Parse the combined string. Strict parsing is default now.
            parsed_dt = pd.to_datetime(combined_datetime_series, errors='coerce')
            
            # Format to DD-MM-YYYY HH:MM:SS
            data[time_col] = parsed_dt.dt.strftime('%d-%m-%Y %H:%M:%S').fillna("Invalid Time")
        else:
            # Only time column available, parse it assuming HH:MM:SS format
            parsed_dt = pd.to_datetime(data[time_col], format='%H:%M:%S', errors='coerce')
            
            # For display, we only want the time part if no date was provided in original data
            data[time_col] = parsed_dt.dt.strftime('%H:%M:%M').fillna("Invalid Time") 

    except Exception as e:
        print(f"Error parsing time column '{time_col}' (and optional date column '{date_col}'): {e}")
    return data

def find_column(data, keywords):
    """Find a column in the DataFrame based on a list of keywords."""
    for col in data.columns:
        if any(keyword.lower() in col.lower() for keyword in keywords):
            return col
    return None

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Radius of Earth in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


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
            # Determine file type from extension
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension == '.csv':
                data = pd.read_csv(file, encoding="utf-8")
            elif file_extension in ['.xls', '.xlsx']:
                data = pd.read_excel(file, engine="openpyxl")
            else:
                return jsonify({'error': 'Unsupported file type. Please upload a CSV or Excel file.'}), 400

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
            mandatory_cols_keys = [
                'punch_lat_col', 'punch_lon_col', 'visit_lat_col', 'visit_lon_col',
                'punch_in_time_col', 'name_col', 'outlet_name_col', 'outlet_id_col'
            ]
            missing_cols = [k for k in mandatory_cols_keys if global_columns.get(k) is None]
            if missing_cols:
                return jsonify({'error': f"Missing required columns: {', '.join(missing_cols)}. Please check your file headers. Detected: {data.columns.tolist()}"}), 400

            # Parse time columns
            # Ensure the column exists before attempting to parse
            if global_columns['punch_in_time_col'] in data.columns:
                data = parse_datetime_columns(data, global_columns['punch_in_time_col'], global_columns['punch_in_date_col'])
            else:
                data[global_columns['punch_in_time_col']] = "Column Not Found" # Fallback if column not in data

            if global_columns['visit_time_col'] and global_columns['visit_time_col'] in data.columns:
                data = parse_datetime_columns(data, global_columns['visit_time_col'], global_columns['visit_date_col'])
            else:
                data['Visit Time Display'] = 'N/A' # Placeholder if visit time column is missing or not found

            global_data = data # Store processed data globally

            employees = data[global_columns['name_col']].unique().tolist()
            return jsonify({'message': 'File uploaded and processed successfully!', 'employees': employees}), 200

        except Exception as e:
            return jsonify({'error': f"Error processing file: {e}"}), 500
    return jsonify({'error': 'Something went wrong'}), 500


def generate_map_html(start_date_str, end_date_str, employee_name):
    """Generates the Folium map HTML based on filters.
    This function is now reusable by both /get_map and /download_map_html.
    """
    global global_data, global_columns

    if global_data is None:
        return None, 'No data loaded. Please upload a file first.'

    filtered_data = global_data.copy()

    # Filter by date range
    if start_date_str or end_date_str:
        try:
            punch_in_time_col_name = global_columns.get('punch_in_time_col')
            if punch_in_time_col_name and punch_in_time_col_name in filtered_data.columns:
                temp_datetime_series = pd.to_datetime(
                    filtered_data[punch_in_time_col_name], 
                    format='%d-%m-%Y %H:%M:%S', 
                    errors='coerce'
                )
                filtered_data['FullDateTime'] = temp_datetime_series
                
                filtered_data = filtered_data.dropna(subset=['FullDateTime'])

                if start_date_str:
                    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                    filtered_data = filtered_data[filtered_data['FullDateTime'] >= start_dt]
                
                if end_date_str:
                    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                    filtered_data = filtered_data[filtered_data['FullDateTime'] <= end_dt]
                
                filtered_data = filtered_data.drop(columns=['FullDateTime'])
            else:
                return None, 'Punch In Time column not found for date filtering.'
        except Exception as e:
            return None, f"Error filtering by date range: {e}"

    # Filter by employee
    if employee_name:
        name_col_name = global_columns.get('name_col')
        if name_col_name and name_col_name in filtered_data.columns:
            filtered_data = filtered_data[filtered_data[name_col_name] == employee_name]
        else:
            return None, 'Employee Name column not found for employee filtering.'


    if filtered_data.empty:
        return None, 'No data found for the selected filters.'

    # Create a map centered around the average of filtered data or India
    avg_lat = filtered_data[global_columns['punch_lat_col']].mean() if not filtered_data.empty else 20.5937
    avg_lon = filtered_data[global_columns['punch_lon_col']].mean() if not filtered_data.empty else 78.9629
    
    fmap = folium.Map(
        location=[avg_lat, avg_lon], 
        zoom_start=5, 
        tiles='CartoDB positron'
    )

    Fullscreen().add_to(fmap)
    MiniMap().add_to(fmap)

    marker_cluster = MarkerCluster(name="Locations").add_to(fmap)

    color_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"
    ]
    
    employees = filtered_data[global_columns['name_col']].unique()
    employee_colors = {emp: color_palette[i % len(color_palette)] for i, emp in enumerate(employees)}

    employee_total_distances = {} # Dictionary to store total distance for each employee

    for emp in employees:
        employee_route_group = FeatureGroup(name=f"Routes: {emp}")
        
        emp_data = filtered_data[filtered_data[global_columns['name_col']] == emp].copy()
        color = employee_colors[emp]

        # Ensure datetime columns are properly parsed for sorting
        if global_columns['punch_in_time_col'] in emp_data.columns:
            emp_data['PunchInDateTime'] = pd.to_datetime(emp_data[global_columns['punch_in_time_col']], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        else:
            emp_data['PunchInDateTime'] = pd.NaT # Not a Time

        if global_columns['visit_time_col'] in emp_data.columns:
            emp_data['VisitDateTime'] = pd.to_datetime(emp_data[global_columns['visit_time_col']], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        else:
            emp_data['VisitDateTime'] = pd.NaT # Not a Time

        # Sort data by punch-in time to ensure chronological order for routes
        emp_data = emp_data.sort_values(by='PunchInDateTime').dropna(subset=['PunchInDateTime'])

        total_distance_for_employee = 0
        
        # Store unique markers to avoid duplicates on the map (even with clustering)
        # This will be a set of tuples: (lat, lon, date, type, outlet_name)
        added_markers = set() 

        previous_visit_lat = None
        previous_visit_lon = None
        previous_date = None # To track same-day visits

        for idx, row in emp_data.iterrows():
            current_punch_lat = row[global_columns['punch_lat_col']]
            current_punch_lon = row[global_columns['punch_lon_col']]
            current_visit_lat = row[global_columns['visit_lat_col']]
            current_visit_lon = row[global_columns['visit_lon_col']]
            current_date = row['PunchInDateTime'].date() # Get date part for same-day check
            current_visit_time_display = row.get(global_columns.get('visit_time_col', 'Visit Time Display'), 'N/A')
            outlet_name_display = row.get(global_columns.get('outlet_name_col', 'FallbackKey'), 'N/A')
            outlet_id_display = row.get(global_columns.get('outlet_id_col', 'FallbackKey'), 'N/A')

            # Add Punch In Marker (only if unique for the day at this location)
            punch_marker_key = (current_punch_lat, current_punch_lon, current_date, 'punch')
            if punch_marker_key not in added_markers:
                punch_in_time_display = row.get(global_columns.get('punch_in_time_col', 'FallbackKey'), 'Column Not Found')
                punch_lat_display = f"{current_punch_lat:.4f}" if pd.notna(current_punch_lat) else 'N/A'
                punch_lon_display = f"{current_punch_lon:.4f}" if pd.notna(current_punch_lon) else 'N/A'
                
                folium.Marker(
                    location=[current_punch_lat, current_punch_lon],
                    popup=f"""
                    <strong>Employee:</strong> {emp}<br>
                    <strong>Punch In Time:</strong> ⏰ {punch_in_time_display}<br>
                    <strong>Latitude:</strong> {punch_lat_display}<br>
                    <strong>Longitude:</strong> {punch_lon_display}
                    """,
                    tooltip=f"Name: {emp} | Punch In: {punch_in_time_display}",
                    icon=folium.Icon(color=color, icon="sign-in", prefix='fa', icon_size=(20, 20)) # Changed to sign-in icon, and color is now employee-specific
                ).add_to(marker_cluster)
                added_markers.add(punch_marker_key)

            # Add Visit Marker (only if unique for the day at this location/outlet)
            visit_marker_key = (current_visit_lat, current_visit_lon, current_date, outlet_name_display, 'visit')
            if visit_marker_key not in added_markers:
                visit_lat_display = f"{current_visit_lat:.4f}" if pd.notna(current_visit_lat) else 'N/A'
                visit_lon_display = f"{current_visit_lon:.4f}" if pd.notna(current_visit_lon) else 'N/A'

                folium.Marker(
                    location=[current_visit_lat, current_visit_lon],
                    popup=f"""
                    <strong>Employee:</strong> {emp}<br>
                    <strong>Visit Time:</strong> ⏰ {current_visit_time_display}<br>
                    <strong>Outlet Name:</strong> 🏢 {outlet_name_display}<br>
                    <strong>Outlet ID:</strong> # {outlet_id_display}<br>
                    <strong>Latitude:</strong> {visit_lat_display}<br>
                    <strong>Longitude:</strong> {visit_lon_display}
                    """,
                    tooltip=f"Name: {emp} | Visit: {current_visit_time_display} | Outlet: {outlet_name_display}",
                    icon=folium.Icon(color=color, icon="map-pin", prefix='fa', icon_size=(30, 30)) # Changed to map-pin icon
                ).add_to(marker_cluster)
                added_markers.add(visit_marker_key)

            # Calculate distance between consecutive visits on the same day
            segment_distance_visit_to_visit = 0
            if previous_visit_lat is not None and previous_visit_lon is not None and previous_date == current_date:
                if pd.notna(previous_visit_lat) and pd.notna(previous_visit_lon) and \
                   pd.notna(current_visit_lat) and pd.notna(current_visit_lon):
                    segment_distance_visit_to_visit = haversine_distance(previous_visit_lat, previous_visit_lon, current_visit_lat, current_visit_lon)
                    total_distance_for_employee += segment_distance_visit_to_visit
                
            # Calculate distance from current punch-in to current visit
            punch_to_visit_distance = 0
            if pd.notna(current_punch_lat) and pd.notna(current_punch_lon) and \
               pd.notna(current_visit_lat) and pd.notna(current_visit_lon):
                punch_to_visit_distance = haversine_distance(current_punch_lat, current_punch_lon, current_visit_lat, current_visit_lon)
                total_distance_for_employee += punch_to_visit_distance


            # Add PolyLine for the current route segment (Punch In to Visit)
            polyline_popup = f"<strong>Route for {row[global_columns['name_col']]}</strong><br>"
            polyline_tooltip = f"Name: {row[global_columns['name_col']]}"
            
            if punch_to_visit_distance > 0:
                polyline_popup += f"<strong>Punch-in to Visit:</strong> {punch_to_visit_distance:.2f} km<br>"
                polyline_tooltip += f" | P-V: {punch_to_visit_distance:.2f} km"

            if segment_distance_visit_to_visit > 0:
                polyline_popup += f"<strong>Prev. Visit to Current Visit:</strong> {segment_distance_visit_to_visit:.2f} km"
                polyline_tooltip += f" | V-V: {segment_distance_visit_to_visit:.2f} km"

            folium.PolyLine(
                locations=[
                    [current_punch_lat, current_punch_lon],
                    [current_visit_lat, current_visit_lon]
                ],
                color=color,
                weight=4, 
                dash_array=None,
                popup=polyline_popup,
                tooltip=polyline_tooltip
            ).add_to(employee_route_group)
            
            # Update previous visit location for the next iteration
            previous_visit_lat = current_visit_lat
            previous_visit_lon = current_visit_lon
            previous_date = current_date
        
        employee_route_group.add_to(fmap)
        employee_total_distances[emp] = total_distance_for_employee # Store total distance

    folium.LayerControl().add_to(fmap)

    # Custom Marker Type Legend
    marker_type_legend_html = """
    <div class="marker-legend">
        <h4 style="margin-top:0; margin-bottom:12px; font-weight:bold; color:#333;">Marker Types (Clustered)</h4>
        <div class="marker-legend-item">
            <div class="marker-legend-icon"><i class="fa fa-sign-in" style="color: darkblue; font-size: 16px;"></i></div> 
            <span>Punch In Location</span>
        </div>
        <div class="marker-legend-item">
            <div class="marker-legend-icon"><i class="fa fa-map-pin" style="color: #2ca02c; font-size: 24px;"></i></div> 
            <span>Visit Location</span>
        </div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(marker_type_legend_html))


    # Removed the Employee Color Legend (Routes) section as requested.
    # employee_color_legend_html = """
    # <div class="employee-legend">
    # <h4 style="margin-top:0; margin-bottom:12px; font-weight:bold; color:#333;">Employee Legend (Routes)</h4>
    # """
    # for emp, color in employee_colors.items():
    #     total_dist_str = f" (Total Route: {employee_total_distances.get(emp, 0):.2f} km)"
    #     employee_color_legend_html += f"""
    #     <div class="employee-legend-item">
    #         <div class="employee-legend-color-box" style="background-color: {color};"></div>
    #         <span>{emp}{total_dist_str}</span>
    #     </div>
    #     """
    # employee_color_legend_html += "</div>"
    # fmap.get_root().html.add_child(folium.Element(employee_color_legend_html))

    return fmap._repr_html_(), None # Return HTML and no error


@app.route('/get_map', methods=['POST'])
def get_map():
    """Generates and returns the Folium map HTML based on filters."""
    req_data = request.get_json()
    selected_start_date_str = req_data.get('start_date')
    selected_end_date_str = req_data.get('end_date')
    selected_employee = req_data.get('employee_name')

    map_html, error_message = generate_map_html(selected_start_date_str, selected_end_date_str, selected_employee)

    if error_message:
        return jsonify({'error': error_message}), 500
    if map_html:
        return jsonify({'map_html': map_html}), 200
    else:
        return jsonify({'message': 'No map data received.'}), 200


@app.route('/download_map_html', methods=['POST'])
def download_map_html():
    """Generates the Folium map HTML and sends it as a downloadable file."""
    req_data = request.get_json()
    selected_start_date_str = req_data.get('start_date')
    selected_end_date_str = req_data.get('end_date')
    selected_employee = req_data.get('employee_name')

    map_html, error_message = generate_map_html(selected_start_date_str, selected_end_date_str, selected_employee)

    if error_message:
        return jsonify({'error': error_message}), 500
    
    if map_html:
        # Create a BytesIO object to hold the HTML content
        buffer = io.BytesIO()
        buffer.write(map_html.encode('utf-8'))
        buffer.seek(0) # Rewind to the beginning of the buffer

        # Send the file
        return send_file(
            buffer,
            mimetype='text/html',
            as_attachment=True,
            download_name='employee_route_map.html'
        )
    else:
        return jsonify({'error': 'Failed to generate map for download.'}), 500


if __name__ == '__main__':
    # Create a 'static' directory if it doesn't exist
    os.makedirs('static', exist_ok=True) # Use exist_ok=True to prevent error if it exists
    
    # Removed the Pillow-based logo creation code as requested.
    # Please ensure you have a 'Mylo_Logo.png' file in the 'static' directory
    # for the application to display the logo correctly.

    from werkzeug.exceptions import RequestEntityTooLarge

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': 'File is too large. Maximum allowed size is 150 MB.'}), 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)