import pandas as pd
import folium
from tkinter import Tk, filedialog
from datetime import datetime
import random
import re

# Get current date & time for filename
current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

def parse_datetime_columns(data, time_col):
    """Parse the datetime columns to a standard format."""
    try:
        # Try to convert to a datetime object, if not already
        data[time_col] = pd.to_datetime(data[time_col], errors='coerce')  # Optionally specify format here
    except Exception as e:
        print(f"Error parsing time column: {e}")
    return data

def generate_map():
    # Open file picker dialog
    Tk().withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a File",
        filetypes=[("Excel Files", "*.xlsx;*.xls"), ("CSV Files", "*.csv")]
    )

    if file_path:
        # Load file based on format
        if file_path.endswith(".csv"):
            data = pd.read_csv(file_path, encoding="utf-8")
        else:
            data = pd.read_excel(file_path, engine="openpyxl")

        # Dynamically detect the required columns
        lat_col = [col for col in data.columns if "lat" in col.lower()]
        lon_col = [col for col in data.columns if "lon" in col.lower()]
        time_col = [col for col in data.columns if "time" in col.lower()]
        name_col = [col for col in data.columns if "name" in col.lower()]

        if lat_col and lon_col and time_col and name_col:
            latitude_col = lat_col[0]
            longitude_col = lon_col[0]
            time_column = time_col[0]
            name_column = name_col[0]
        else:
            print("Error: Required columns (Latitude, Longitude, Time, Name) not found!")
            return

        # Parse datetime columns
        data = parse_datetime_columns(data, time_column)

        # Create a map centered around India (no markers in Python)
        fmap = folium.Map(location=[20.5937, 78.9629], zoom_start=5)

        # Extract unique employee names & assign random colors
        employees = data[name_column].unique()
        employee_colors = {emp: "#{:06x}".format(random.randint(0, 0xFFFFFF)) for emp in employees}

        # Combined search and dropdown HTML
        dropdown_html = """
        <div style="margin-bottom:10px;">
            <label for="employeeSearch"><b>Search Employee:</b></label>
            <input type="text" id="employeeSearch" onkeyup="filterDropdown()" placeholder="Type to search..." style="margin-right:10px;">
            <select id="employeeDropdown" onchange="filterMarkers()">
                <option value="all">All Employees</option>
        """
        for emp in employees:
            dropdown_html += f"<option value='{emp}'>{emp}</option>"
        dropdown_html += "</select></div>"

        # Prepare marker data for JavaScript
        marker_js_data = []
        for index, row in data.iterrows():
            hover_info = f"{row[name_column]} | Date: {row.get('Date', '')} | Time: {row[time_column]}"
            popup_info = f"""
            <strong>Name:</strong> {row[name_column]}<br>
            <strong>Date:</strong> {row.get('Date', '')}<br>
            <strong>Time:</strong> {row[time_column]}<br>
            <strong>Latitude:</strong> {row[latitude_col]}<br>
            <strong>Longitude:</strong> {row[longitude_col]}
            """
            marker_js_data.append({
                "lat": row[latitude_col],
                "lon": row[longitude_col],
                "name": row[name_column],
                "color": employee_colors[row[name_column]],
                "popup": popup_info.replace('\n', '').replace('"', '\\"'),
                "tooltip": hover_info.replace('"', '\\"')
            })

        # JavaScript for filtering and displaying markers
        marker_script = f"""
        <script>
            var markerData = {marker_js_data};
            var allMarkers = [];
            function getMap() {{
                for (var key in window) {{
                    if (window[key] && window[key]._initControlPos) {{
                        return window[key];
                    }}
                }}
                return null;
            }}

            function createMarkers() {{
                var map = getMap();
                if (!map) {{
                    console.log("Map not ready, retrying...");
                    setTimeout(createMarkers, 500);
                    return;
                }}
                allMarkers.forEach(function(m) {{ map.removeLayer(m); }});
                allMarkers = [];
                markerData.forEach(function(d) {{
                    var marker = L.circleMarker([d.lat, d.lon], {{
                        radius: 7,
                        color: d.color,
                        fill: true,
                        fillColor: d.color,
                        fillOpacity: 1
                    }}).bindPopup(d.popup).bindTooltip(d.tooltip);
                    allMarkers.push(marker);
                    marker.addTo(map);
                }});
                // Show all markers initially
                filterMarkers();
            }}

            function filterDropdown() {{
                var input = document.getElementById('employeeSearch').value.toLowerCase();
                var dropdown = document.getElementById('employeeDropdown');
                for (var i = 0; i < dropdown.options.length; i++) {{
                    var txt = dropdown.options[i].text.toLowerCase();
                    dropdown.options[i].style.display = txt.includes(input) ? "" : "none";
                }}
            }}

            function filterMarkers() {{
                var map = getMap();
                var selected = document.getElementById('employeeDropdown').value;
                allMarkers.forEach(function(marker) {{
                    map.removeLayer(marker);
                }});
                if (selected === "all") {{
                    allMarkers.forEach(function(marker) {{ marker.addTo(map); }});
                }} else {{
                    allMarkers.forEach(function(marker, idx) {{
                        if (markerData[idx].name === selected) marker.addTo(map);
                    }});
                }}
            }}

            // Call createMarkers after script is loaded
            createMarkers();
        </script>
        """

        # Save the map first
        file_name = f"map_employee_{current_datetime}.html"
        fmap.save(file_name)

        # Read the HTML
        with open(file_name, "r", encoding="utf-8") as f:
            html = f.read()

        # Insert dropdown just after <body> for visibility
        html = re.sub(r'(<body[^>]*>)', r'\1\n' + dropdown_html, html, count=1)

        # Insert script just before </body>
        html = html.replace("</body>", f"{marker_script}\n</body>")

        with open(file_name, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Map saved as {file_name}. Open it in your browser!")

# Run function
generate_map()
