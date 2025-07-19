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

app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 50)) * 1024 * 1024  # Default to 50 MB

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
            height: 85vh; /* Increased height for a larger map view */
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
            <img src="/static/Mylo_Logo.png" alt="Mylo Logo" class="w-24 h-auto mb-5 rounded-2xl shadow-xl"> <h1 class="text-4xl font-extrabold text-gray-900 text-center leading-tight">
                <i class="fa fa-map-marker text-blue-600 mr-5"></i> Employee Route Tracker
            </h1>
            <p class="text-gray-600 mt-3 text-xl">Visualize employee routes and visit patterns with precision.</p> </div>

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

        <hr class="my-6 border-gray-200">

            <div class="grid grid-cols-1 md:grid-cols-7 gap-8 mb-10 items-end">
                <div class="flex flex-col md:col-span-2">
                    <label for="startDateFilter" class="text-gray-700 font-semibold mb-3 text-l">Start Date:</label>
                    <select id="startDateFilter" class="input-field w-full">
                        <option value="">All Dates</option>
                    </select>
                </div>
                <div class="flex flex-col md:col-span-2">
                    <label for="endDateFilter" class="text-gray-700 font-semibold mb-3 text-l">End Date:</label>
                    <select id="endDateFilter" class="input-field w-full">
                        <option value="">All Dates</option>
                    </select>
                </div>
            </div>
                <div class="flex flex-col md:col-span-2 mb-6"> <label for="employeeFilter" class="text-gray-700 font-semibold mb-3 text-l">Select Employee:</label>
                    <select id="employeeFilter" class="input-field" disabled>
                        <option value="">All Employees</option>
                    </select>
                </div>
                <div class="flex justify-center gap-4">
                    <button id="loadMapBtn" class="btn-base btn-blue btn-small">
                        <i class="fa fa-refresh"></i> Load Map
                        <div id="loadingSpinnerMap" class="loading-spinner ml-3"></div>
                    </button>
                    <button id="downloadMapBtn" class="btn-base btn-purple btn-small" disabled>
                        <i class="fa fa-download"></i> Download Map
                    </button>
                    <button id="resetFiltersBtn" class="btn-base btn-red btn-small" disabled>
                        <i class="fa fa-undo"></i> Reset Filters
                    </button>
                </div>

        <div id="mapContainer" class="map-container">
            <p class="text-center text-gray-500 text-xl font-medium">Please upload your data file to get started.</p>
        </div>
        <div id="messageBox" class="message-box mt-8 hidden"></div>
    </div>

            <div class="footer">
            &copy; 2025 - Sugandh Mishra. All rights reserved.
        </div>

        <style>
        .footer {
    text-align: center; /* Center the text */
    margin-top: 20px; /* Add some space above the footer */
    font-size: 0.875rem; /* Small font size */
    color: #6b7280; /* Gray-500 color */
}
        </style>

    <style>
    .btn-small {
        padding: 0.5rem 1rem; /* Reduced padding */
        font-size: 0.75rem; /* Smaller font size */
        border-radius: 0.75rem; /* Slightly less rounded */
        gap: 0.5rem; /* Reduced gap between icon and text */
    }

    .start-date-field {
        padding: 0.75rem 1.25rem; /* Adjusted padding for Start Date */
        font-size: 0.875rem; /* Smaller font size */
        border-radius: 0.5rem; /* Slightly rounded corners */
        border: 1px solid #cbd5e1; /* Subtle border */
        background-color: #ffffff; /* White background */
        color: #475569; /* Slightly darker text */
    }

    .end-date-field {
        padding: 0.85rem 1.5rem; /* Adjusted padding for End Date */
        font-size: 1rem; /* Slightly larger font size */
        border-radius: 0.75rem; /* More rounded corners */
        border: 1px solid #cbd5e1; /* Subtle border */
        background-color: #f9fafb; /* Light gray background */
        color: #334155; /* Darker text */
    }

    .start-date-field:focus,
    .end-date-field:focus {
        border-color: #3b82f6; /* Blue border on focus */
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3); /* Focus ring */
        outline: none;
    }

</style>

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

        // Function to populate date dropdowns
        async function populateDateDropdowns() {
            try {
                const response = await fetch('/get_unique_dates');
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to fetch unique dates.');
                }
                const dates = await response.json();

                startDateFilter.innerHTML = '<option value="">All Dates</option>';
                endDateFilter.innerHTML = '<option value="">All Dates</option>';

                dates.forEach(date => {
                    const startOption = document.createElement('option');
                    startOption.value = date.value; // YYYY-MM-DD for backend
                    startOption.textContent = date.text; // DD-MM-YYYY for display
                    startDateFilter.appendChild(startOption);

                    const endOption = document.createElement('option');
                    endOption.value = date.value; // YYYY-MM-DD for backend
                    endOption.textContent = date.text; // DD-MM-YYYY for display
                    endDateFilter.appendChild(endOption);
                });
            } catch (error) {
                console.error('Error populating date dropdowns:', error);
                showMessage(`Error loading dates: ${error.message}`, true);
            }
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
                
                populateDateDropdowns(); // Populate date dropdowns after successful upload

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

            const selectedStartDate = startDateFilter.value; // This will be YYYY-MM-DD
            const selectedEndDate = endDateFilter.value;     // This will be YYYY-MM-DD
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
                downloadMapBtn.disabled = false; // Re-enable download button
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
                a.download = 'employee_route_map.html'; // Suggested filename
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                showMessage("Map downloaded successfully as HTML!", false);
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
        data[time_col] = data[time_col].astype(str) # Convert to string first
        
        if date_col and date_col in data.columns:
            data[date_col] = data[date_col].astype(str) # Ensure date column is string

            # Attempt to parse date_col assuming DD-MM-YYYY or MM-DD-YYYY, preferring DD-MM-YYYY
            parsed_date = pd.to_datetime(data[date_col], dayfirst=True, infer_datetime_format=True, errors='coerce')
            data[date_col] = parsed_date.dt.strftime('%d-%m-%Y').fillna('')

            combined_datetime_series = data.apply(lambda row: f"{row[date_col]} {row[time_col]}" if row[date_col] else row[time_col], axis=1)
            
            # Parse the combined string, again preferring dayfirst
            parsed_dt = pd.to_datetime(combined_datetime_series, dayfirst=True, infer_datetime_format=True, errors='coerce')
            data[time_col] = parsed_dt.dt.strftime('%d-%m-%Y %H:%M:%S').fillna("Invalid Time")
        else:
            # If no separate date_col, assume time_col contains full datetime.
            # Parse it preferring DD-MM-YYYY.
            parsed_dt = pd.to_datetime(data[time_col], dayfirst=True, infer_datetime_format=True, errors='coerce')
            data[time_col] = parsed_dt.dt.strftime('%d-%m-%Y %H:%M:%S').fillna("Invalid Time")
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
    R = 6371 # Radius of Earth in kilometers
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
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_data', methods=['POST'])
def upload_data():
    global global_data, global_columns
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Determine file type and read accordingly
        if file.filename.endswith('.csv'):
            data = pd.read_csv(file)
        elif file.filename.endswith(('.xls', '.xlsx')):
            data = pd.read_excel(file)
        else:
            return jsonify({'error': 'Unsupported file type. Please upload a CSV or Excel file.'}), 400
        
        # Convert all column names to string type
        data.columns = data.columns.astype(str)

        # Detect and store globally
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
            # Create the column with 'N/A' if it's not found, so it's always accessible
            data[global_columns.get('visit_time_col', 'visit_time_placeholder')] = 'N/A' 


        global_data = data # Store processed data globally

        employees = data[global_columns['name_col']].unique().tolist()
        return jsonify({'message': 'File processed successfully!', 'employees': employees}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_unique_dates', methods=['GET'])
def get_unique_dates():
    global global_data, global_columns
    if global_data is None:
        return jsonify({'error': 'No data uploaded yet. Please upload a file first.'}), 400

    punch_in_time_col_name = global_columns.get('punch_in_time_col')
    if not punch_in_time_col_name or punch_in_time_col_name not in global_data.columns:
        return jsonify({'error': 'Punch In Time column not found in the uploaded data.'}), 400

    try:
        # Convert to datetime using the expected DD-MM-YYYY HH:MM:SS format
        # This is crucial for correct parsing before extracting date
        unique_dates = pd.to_datetime(global_data[punch_in_time_col_name], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.date.dropna().unique()
        
        # Sort dates
        sorted_dates = sorted(unique_dates)

        # Format for dropdown (value as YYYY-MM-DD for backend, text as DD-MM-YYYY for display)
        formatted_dates = [{'value': date.strftime('%Y-%m-%d'), 'text': date.strftime('%d-%m-%Y')} for date in sorted_dates]
        
        return jsonify(formatted_dates), 200
    except Exception as e:
        return jsonify({'error': f"Error processing dates: {str(e)}"}), 500


def generate_map_html(start_date_str, end_date_str, employee_name):
    global global_data, global_columns
    if global_data is None:
        return None, "No data uploaded. Please upload a file first."

    filtered_data = global_data.copy()

    # Convert filter dates to datetime objects for comparison
    start_date_filter_dt = None
    end_date_filter_dt = None
    
    # Try parsing dates if they are provided from YYYY-MM-DD (from JS dropdown value)
    if start_date_str:
        try:
            start_date_filter_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, "Invalid Start Date format. Please use YYYY-MM-DD."
    if end_date_str:
        try:
            end_date_filter_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, "Invalid End Date format. Please use YYYY-MM-DD."

    # Filter by date range
    punch_in_time_col_name = global_columns.get('punch_in_time_col')
    if not punch_in_time_col_name or punch_in_time_col_name not in filtered_data.columns:
        return None, 'Punch In Time column not found for date filtering.'

    try:
        # Ensure the column is datetime objects for filtering, explicitly parsing DD-MM-YYYY HH:MM:SS
        filtered_data['ParsedPunchInTime'] = pd.to_datetime(filtered_data[punch_in_time_col_name], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        filtered_data = filtered_data.dropna(subset=['ParsedPunchInTime']) # Drop rows where date parsing failed
        
        if start_date_filter_dt:
            filtered_data = filtered_data[filtered_data['ParsedPunchInTime'].dt.date >= start_date_filter_dt]
        if end_date_filter_dt:
            filtered_data = filtered_data[filtered_data['ParsedPunchInTime'].dt.date <= end_date_filter_dt]
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

    # Calculate bounds for zooming
    min_lat = filtered_data[global_columns['punch_lat_col']].min()
    max_lat = filtered_data[global_columns['punch_lat_col']].max()
    min_lon = filtered_data[global_columns['punch_lon_col']].min()
    max_lon = filtered_data[global_columns['punch_lon_col']].max()

    # Center the map around the filtered data
    avg_lat = filtered_data[global_columns['punch_lat_col']].mean() if not filtered_data.empty else 20.5937
    avg_lon = filtered_data[global_columns['punch_lon_col']].mean() if not filtered_data.empty else 78.9629

    fmap = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=5,
        tiles='CartoDB positron'
    )

    # Adjust the map to fit the bounds if an employee is selected
    if employee_name and not filtered_data.empty:
        fmap.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

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

    # To keep track of added markers to avoid duplicates
    added_markers = set()

    for emp in employees:
        employee_route_group = FeatureGroup(name=f"Routes: {emp}")
        emp_data = filtered_data[filtered_data[global_columns['name_col']] == emp].copy()
        color = employee_colors[emp]

        # Ensure datetime columns are properly parsed for sorting
        if global_columns['punch_in_time_col'] in emp_data.columns:
            emp_data['PunchInDateTime'] = pd.to_datetime(emp_data[global_columns['punch_in_time_col']], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        else:
            emp_data['PunchInDateTime'] = pd.NaT # Not a Time

        emp_data = emp_data.sort_values(by='PunchInDateTime').reset_index(drop=True)

        current_employee_distance = 0
        prev_punch_lat, prev_punch_lon = None, None

        for idx, row in emp_data.iterrows():
            current_punch_lat = row[global_columns['punch_lat_col']]
            current_punch_lon = row[global_columns['punch_lon_col']]
            current_visit_lat = row[global_columns['visit_lat_col']]
            current_visit_lon = row[global_columns['visit_lon_col']]
            current_punch_in_time_display = row[global_columns['punch_in_time_col']]
            
            # Safely get visit time display
            current_visit_time_display = row.get(global_columns.get('visit_time_col', 'visit_time_placeholder'), 'N/A')

            current_outlet_name = row[global_columns['outlet_name_col']] if global_columns['outlet_name_col'] else 'N/A'
            current_outlet_id = row[global_columns['outlet_id_col']] if global_columns['outlet_id_col'] else 'N/A'
            
            current_date = pd.to_datetime(current_punch_in_time_display, format='%d-%m-%Y %H:%M:%S', errors='coerce').strftime('%Y-%m-%d') if pd.notna(pd.to_datetime(current_punch_in_time_display, format='%d-%m-%Y %H:%M:%S', errors='coerce')) else 'N/A'

            # Format punch in time for display - EXPLICITLY specify format
            try:
                punch_in_dt = pd.to_datetime(current_punch_in_time_display, format='%d-%m-%Y %H:%M:%S', errors='coerce')
                punch_in_time_display_fmt = punch_in_dt.strftime('%d-%m-%Y %H:%M:%S') if not pd.isnull(punch_in_dt) else current_punch_in_time_display
            except Exception:
                punch_in_time_display_fmt = current_punch_in_time_display

            # Format visit time for display - EXPLICITLY specify format
            try:
                visit_in_dt = pd.to_datetime(current_visit_time_display, format='%d-%m-%Y %H:%M:%S', errors='coerce')
                visit_time_display_fmt = visit_in_dt.strftime('%d-%m-%Y %H:%M:%S') if not pd.isnull(visit_in_dt) else current_visit_time_display
            except Exception:
                visit_time_display_fmt = current_visit_time_display

            punch_lat_display = f"{current_punch_lat:.4f}" if pd.notna(current_punch_lat) else 'N/A'
            punch_lon_display = f"{current_punch_lon:.4f}" if pd.notna(current_punch_lon) else 'N/A'
            visit_lat_display = f"{current_visit_lat:.4f}" if pd.notna(current_visit_lat) else 'N/A'
            visit_lon_display = f"{current_visit_lon:.4f}" if pd.notna(current_visit_lon) else 'N/A'
            outlet_name_display = current_outlet_name if pd.notna(current_outlet_name) else 'N/A'
            outlet_id_display = current_outlet_id if pd.notna(current_outlet_id) else 'N/A'


            # Add Punch In Marker (only if unique for the day at this location)
            punch_marker_key = (current_punch_lat, current_punch_lon, current_date, 'punch')
            if punch_marker_key not in added_markers:
                folium.Marker(
                    location=[current_punch_lat, current_punch_lon],
                    popup=f"""
                    <strong>Employee:</strong> {emp}<br>
                    <strong>Punch In Time:</strong> ⏰ {punch_in_time_display_fmt}<br>
                    <strong>Latitude:</strong> {punch_lat_display}<br>
                    <strong>Longitude:</strong> {punch_lon_display}
                    """,
                    tooltip=f"Name: {emp} | Punch In: {punch_in_time_display_fmt}",
                    icon=folium.Icon(color="blue", icon="user-clock", prefix='fa', icon_size=(30, 30))
                ).add_to(marker_cluster)
                added_markers.add(punch_marker_key)

            # Add Visit Marker (only if unique for the day at this location/outlet)
            visit_marker_key = (current_visit_lat, current_visit_lon, current_date, outlet_name_display, 'visit')
            if visit_marker_key not in added_markers:
                folium.Marker(
                    location=[current_visit_lat, current_visit_lon],
                    popup=f"""
                    <strong>Employee:</strong> {emp}<br>
                    <strong>Outlet:</strong> {outlet_name_display} (ID: {outlet_id_display})<br>
                    <strong>Visit Time:</strong> ⏱️ {visit_time_display_fmt}<br>
                    <strong>Latitude:</strong> {visit_lat_display}<br>
                    <strong>Longitude:</strong> {visit_lon_display}
                    """,
                    tooltip=f"Outlet: {outlet_name_display} | Visit: {visit_time_display_fmt}",
                    icon=folium.Icon(color="green", icon="briefcase", prefix='fa', icon_size=(30, 30))
                ).add_to(marker_cluster)
                added_markers.add(visit_marker_key)


            # Draw line between consecutive punch-in locations for the same employee
            if prev_punch_lat is not None and pd.notna(current_punch_lat) and pd.notna(current_punch_lon):
                folium.PolyLine(
                    locations=[(prev_punch_lat, prev_punch_lon), (current_punch_lat, current_punch_lon)],
                    color=color,
                    weight=4,
                    opacity=0.7
                ).add_to(employee_route_group)
                
                # Calculate and add distance to the total for the employee
                dist = haversine_distance(prev_punch_lat, prev_punch_lon, current_punch_lat, current_punch_lon)
                current_employee_distance += dist

            prev_punch_lat = current_punch_lat
            prev_punch_lon = current_punch_lon
        
        employee_route_group.add_to(fmap) # Add each employee's route group to the map
        employee_total_distances[emp] = current_employee_distance

    # Add LayerControl to toggle employee routes
    folium.LayerControl().add_to(fmap)

    # Custom Marker Type Legend HTML
    marker_type_legend_html = """
    <div class="marker-legend">
        <h4 style="margin-top:0; margin-bottom:12px; font-weight:bold; color:#333;">Marker Types (Clustered)</h4>
        <div class="marker-legend-item">
            <div class="marker-legend-icon"><i class="fa fa-user-clock" style="color: blue;"></i></div>
            <span>Punch In Location</span>
        </div>
        <div class="marker-legend-item">
            <div class="marker-legend-icon"><i class="fa fa-briefcase" style="color: green;"></i></div>
            <span>Visit Location</span>
        </div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(marker_type_legend_html))

    # Employee Color and Distance Legend HTML
    employee_legend_items_html = ""
    for emp, color in employee_colors.items():
        distance = employee_total_distances.get(emp, 0)
        employee_legend_items_html += f"""
        <div class="employee-legend-item">
            <div class="employee-legend-color-box" style="background-color:{color};"></div>
            <span>{emp} (Dist: {distance:.2f} km)</span>
        </div>
        """
    employee_color_legend_html = f"""
    <div class="employee-legend">
        <h4 style="margin-top:0; margin-bottom:12px; font-weight:bold; color:#333;">Employee Routes & Distance</h4>
        {employee_legend_items_html}
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(employee_color_legend_html))

    # Add the signature to the map
    signature_html = """
    <div style="position: fixed; bottom: 10px; right: 10px; z-index: 9999; font-size: 14px; color: #666; background-color: rgba(255,255,255,0.7); padding: 5px 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
        Map generated by Sugandh Mishra
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(signature_html))

    return fmap._repr_html_(), None # Return HTML and no error

@app.route('/get_map', methods=['POST'])
def get_map():
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
        return jsonify({'message': 'No map could be generated with the current filters. Try adjusting them.'}), 200

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
    app.run(host='0.0.0.0', port=5000)