import json
import folium
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString
from folium.plugins import MarkerCluster
import geopy.distance
import math
import requests
import pyttsx3
import pygame
import pymysql

# Function to extract border points
def extract_border_points(json_data):
    border_points = []
    features = json_data.get("features", [])
    for feature in features:
        geometry = feature.get("geometry", {})
        if geometry.get("type") == "MultiPolygon":
            for polygon in geometry.get("coordinates", []):
                for point in polygon[0]:
                    border_points.append((point[1], point[0]))  # GeoJSON uses [lon, lat]
    return border_points

# Function to find the nearest border point
def find_nearest_border(user_location, border_points):
    distances = [(point, geopy.distance.geodesic(user_location, point).km) for point in border_points]
    nearest_point, nearest_distance = min(distances, key=lambda x: x[1])
    return nearest_point, nearest_distance

# Function to find the nearest harbor
def find_nearest_harbor(user_location, harbors):
    distances = [(harbor, geopy.distance.geodesic(user_location, (harbor['latitude'], harbor['longitude'])).km) for _, harbor in harbors.iterrows()]
    nearest_harbor, nearest_distance = min(distances, key=lambda x: x[1])
    return nearest_harbor, nearest_distance

# Bearing calculation function
def calculate_bearing(start_point, end_point):
    start_lat, start_lon = math.radians(start_point[0]), math.radians(start_point[1])
    end_lat, end_lon = math.radians(end_point[0]), math.radians(end_point[1])

    delta_lon = end_lon - start_lon
    x = math.sin(delta_lon) * math.cos(end_lat)
    y = math.cos(start_lat) * math.sin(end_lat) - math.sin(start_lat) * math.cos(end_lat) * math.cos(delta_lon)

    initial_bearing = math.atan2(x, y)
    compass_bearing = (math.degrees(initial_bearing) + 360) % 360
    return compass_bearing


# Function to play police warning sound
def play_warning_sound_for_duration(duration=10):
    pygame.mixer.music.load(SIREN_SOUND_PATH)  # Load the siren sound file
    pygame.mixer.music.play(-1)  # Play the sound on loop
    pygame.time.wait(duration * 1000)  # Wait for the specified duration in milliseconds
    pygame.mixer.music.stop()  # Stop the sound after the duration

# Function to speak the warning using text-to-speech
def speak_warning(message):
    engine.say(message)
    engine.runAndWait()



# Function to check user status and trigger sound alerts
def check_user_status(user_location, indian_eez, border_countries, high_seas):
    """
    Check the user's status based on their proximity to different maritime zones.

    Parameters:
        user_location (tuple): The user's current location as (latitude, longitude).
        indian_eez_gdf (GeoDataFrame): GeoDataFrame for the EEZ zone (blue layer).
        danger_gdfs (list of GeoDataFrame): List of GeoDataFrames for the danger zones (red layer).
        high_seas_gdf (GeoDataFrame): GeoDataFrame for the high seas.

    Returns:
        tuple: A message indicating the status and a boolean (True if safe, False if in danger).
    """
    user_point = Point(user_location[1], user_location[0])  # GeoPandas uses (lon, lat)

    # Check if the user is inside the EEZ (safe zone)
    if indian_eez.contains(user_point).any():
        return "You are in the Indian EEZ (safe zone).", True

    # Check if the user is inside any danger zone
    for danger_gdf in border_countries:
        if danger_gdf.contains(user_point).any():
            return "Warning: You are in a danger zone (red zone).", False

    # Check if the user is in the high seas
    if high_seas.contains(user_point).any():
        return "You are in the high seas (safe zone).", True

    # Default case: not in any defined zone
    return "Warning: Your location is unknown or not in a safe zone.", False

# Fetch weather data
def fetch_weather_data(lat, lon):
    params = {
        'lat': lat,
        'lon': lon,
        'appid': 'b2414e7d5e300e4a06980d910d649a9e',
        'units': 'metric'  # For temperature in Celsius
    }
    response = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching weather data:", response.status_code)
        return None

# Display weather on the map
def display_weather_on_map(weather_data, map_object, location):
    if weather_data:
        temp = weather_data['main']['temp']
        wind_speed = weather_data['wind']['speed']
        weather_desc = weather_data['weather'][0]['description']
        popup_text = f"""
            <strong>Weather Info:</strong><br>
            Temperature: {temp}°C<br>
            Wind Speed: {wind_speed} m/s<br>
            Condition: {weather_desc}
        """
        folium.Marker(
            location=location,
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="cloud")
        ).add_to(map_object)


# Function to speak out a message
def voice_warning(message):
    """
    This function uses the pyttsx3 library to generate voice warnings.
    """
    engine.say(message)
    engine.runAndWait()

# Function to initialize the database and create tables
# def initialize_database():
#     # Connect to MySQL server
#     conn = pymysql.connect(
#         host=HOST,
#         user=USER,
#         password=PASSWORD,
#         database=DATABASE
#     )
#     cursor = conn.cursor()
#     # Create a table if it doesn't exist
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS user_data (
#             id INT AUTO_INCREMENT PRIMARY KEY,
#             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#             user_latitude FLOAT,
#             user_longitude FLOAT,
#             nearest_border_lat FLOAT,
#             nearest_border_lon FLOAT,
#             distance_to_border FLOAT,
#             border_bearing FLOAT,
#             nearest_harbor_name VARCHAR(255),
#             harbor_latitude FLOAT,
#             harbor_longitude FLOAT,
#             distance_to_harbor FLOAT,
#             harbor_bearing FLOAT,
#             weather_temperature FLOAT,
#             weather_wind_speed FLOAT,
#             weather_description VARCHAR(255),
#             user_status VARCHAR(50)
#         )
#     """)
#     conn.commit()
#     conn.close()

# Function to save data to the database
def save_to_database(data,HOST,USER,PASSWORD,DATABASE):
    # Connect to MySQL server
    conn = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_data (
            user_latitude, user_longitude, 
            nearest_border_lat, nearest_border_lon, distance_to_border, border_bearing,
            nearest_harbor_name, harbor_latitude, harbor_longitude, distance_to_harbor, harbor_bearing,
            weather_temperature, weather_wind_speed, weather_description,
            user_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data['user_lat'], data['user_lon'],
        data['nearest_border_lat'], data['nearest_border_lon'], data['distance_to_border'], data['border_bearing'],
        data['nearest_harbor_name'], data['harbor_lat'], data['harbor_lon'], data['distance_to_harbor'], data['harbor_bearing'],
        data['weather_temp'], data['weather_wind_speed'], data['weather_desc'],
        data['user_status']
    ))
    conn.commit()
    conn.close()
    
from flask import Flask, request, jsonify, send_file
import time
import base64

app = Flask(__name__)

@app.route('/route11', methods = ['POST'])
def function1():
    
    lattitude = float(request.form['latt'])
    longitude = float(request.form['longi'])
    print('done')
  #  API_KEY = "b2414e7d5e300e4a06980d910d649a9e"  # Replace with your OpenWeatherMap API key
   # WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    indian_eez = gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\Indian Exclusive Economic Zone.json")
    andaman = gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\andaman.json")
    indian_land = gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\shore_and_whole_land.json")
    fishing_harbors = pd.read_csv(r"C:\Users\Aravind\Downloads\capestone 1\data\harbour.csv")
    high_seas = gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\high sea.json")
    border_countries = [
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\sri_lanka.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\maldives.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\indonesiya and.sea.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\indonesiya bb.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\indonesiya in ind ocean.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\bangladesh.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\malasiya.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\thailand.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\burma.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\yeman.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\oman.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\iran.json"),
        gpd.read_file(r"C:\Users\Aravind\Downloads\capestone 1\data\paksitan.json"),
    ]
    
    # MySQL database connection details
    HOST = "localhost"  # Replace with your MySQL host (e.g., localhost)
    USER = "root"       # Replace with your MySQL username
    PASSWORD = "imarticus"  # Replace with your MySQL password
    DATABASE = "mukund"  # Replace with your MySQL database name
    
    filtered_eez_gdf = indian_eez
    danger_gdfs = border_countries
    
    
    # Initialize base map
    mukund_map = folium.Map(location=[20, 80], zoom_start=5)
    
    # Add Indian EEZ in blue (including Andaman)
    eez_layer = folium.FeatureGroup(name="Indian EEZ (Blue)")
    folium.GeoJson(indian_eez, style_function=lambda x: {'color': 'blue'}).add_to(eez_layer)
    folium.GeoJson(andaman, style_function=lambda x: {'color': 'blue'}).add_to(eez_layer)
    eez_layer.add_to(mukund_map)
    
    # Add Indian Land in orange
    land_layer = folium.FeatureGroup(name="Indian Land (Orange)")
    folium.GeoJson(indian_land, style_function=lambda x: {'color': 'orange'}).add_to(land_layer)
    land_layer.add_to(mukund_map)
    
    # Add High Seas in dark blue
    high_seas_layer = folium.FeatureGroup(name="High Seas (Dark Blue)")
    folium.GeoJson(high_seas, style_function=lambda x: {'color': 'darkblue'}).add_to(high_seas_layer)
    high_seas_layer.add_to(mukund_map)
    
    # Add Danger Zones for Bordering Countries
    danger_layer = folium.FeatureGroup(name="Danger Zones (Red)")
    for country in border_countries:
        folium.GeoJson(country, style_function=lambda x: {'color': 'red'}).add_to(danger_layer)
    danger_layer.add_to(mukund_map)
    # Input user's current location
    user_lat = lattitude#float(input("Enter your current latitude: "))
    user_lon = longitude#float(input("Enter your current longitude: "))
    user_location = (user_lat, user_lon)
    
    # Extract border points from the JSON file
    with open(r"C:\Users\Aravind\Downloads\capestone 1\data\Indian Exclusive Economic Zone.json")as file:
        border_data = json.load(file)
    border_points = extract_border_points(border_data)
    
    # Find the nearest border point
    nearest_border_point, distance_to_nearest = find_nearest_border(user_location, border_points)
    
    # Find the nearest harbor
    nearest_harbor, distance_to_nearest_harbor = find_nearest_harbor(user_location, fishing_harbors)
    
    # Calculate bearings
    bearing_to_border = calculate_bearing(user_location, nearest_border_point)
    bearing_to_harbor = calculate_bearing(user_location, (nearest_harbor['latitude'], nearest_harbor['longitude']))
    
    # Check if the user is in a safe zone
    status, safe_water = check_user_status(user_location, filtered_eez_gdf, danger_gdfs, high_seas)
    # Initialize the database
    #initialize_database()
    
    
    # Display status and nearest details
    print(f"\n{status}")
    print(f"Nearest Border Point: {nearest_border_point}")
    print(f"Distance to Nearest Border: {distance_to_nearest:.2f} km")
    print(f"Direction to Nearest Border: {bearing_to_border:.2f}°")
    print(f"\nNearest Harbor: {nearest_harbor['name']}")
    print(f"Distance to Nearest Harbor: {distance_to_nearest_harbor:.2f} km")
    print(f"Direction to Nearest Harbor: {bearing_to_harbor:.2f}°")
    
    # Title HTML
    title_html = """
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 90%; 
                    text-align: center; font-size: 24px; 
                    font-weight: bold; color: darkblue; 
                    background-color: white; padding: 10px; 
                    border: 2px solid darkblue; border-radius: 5px; z-index:9999;">
            M.U.K.U.N.D: Maritime Utility for Keeping Users Near-safe from Danger
        </div>
    """
    mukund_map.get_root().html.add_child(folium.Element(title_html))
    # Add markers to the map
    folium.Marker(
        location=user_location,
        popup="Your Location",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(mukund_map)
    
    folium.Marker(
        location=nearest_border_point,
        popup=f"Nearest Border Point\nDistance: {distance_to_nearest:.2f} km\nBearing: {bearing_to_border:.2f}°",
        icon=folium.Icon(color="red")
    ).add_to(mukund_map)
    
    folium.Marker(
        location=(nearest_harbor['latitude'], nearest_harbor['longitude']),
        popup=f"Nearest Harbor\n{nearest_harbor['name']}\nDistance: {distance_to_nearest_harbor:.2f} km\nBearing: {bearing_to_harbor:.2f}°",
        icon=folium.Icon(color="green")
    ).add_to(mukund_map)
    
    # Fetch and display weather data
    weather_data = fetch_weather_data(user_lat, user_lon)
    display_weather_on_map(weather_data, mukund_map, user_location)
    # Initialize the database
    #initialize_database()
    
    # Collect and save data
    data_to_save = {
        'user_lat': user_lat,
        'user_lon': user_lon,
        'nearest_border_lat': nearest_border_point[0],
        'nearest_border_lon': nearest_border_point[1],
        'distance_to_border': distance_to_nearest,
        'border_bearing': bearing_to_border,
        'nearest_harbor_name': nearest_harbor['name'],
        'harbor_lat': nearest_harbor['latitude'],
        'harbor_lon': nearest_harbor['longitude'],
        'distance_to_harbor': distance_to_nearest_harbor,
        'harbor_bearing': bearing_to_harbor,
        'weather_temp': weather_data['main']['temp'] if weather_data else None,
        'weather_wind_speed': weather_data['wind']['speed'] if weather_data else None,
        'weather_desc': weather_data['weather'][0]['description'] if weather_data else None,
        'user_status': status
    }
    
    # Save the collected data to the database
    save_to_database(data_to_save,HOST,USER,PASSWORD,DATABASE)
    
    print("\nData has been saved to the MySQL database.")
    # Save the map to an HTML file
    map_file_path = f"MUKUND_{time.time()}.html"
    mukund_map.save(map_file_path)
    print(f"\nMap has been saved as '{map_file_path}'. Open it in a browser to view.")
    # map_file_path = r"C:\Users\jeffryponlarkins_k\Downloads\image-4.html"
    with open(map_file_path, 'rb') as filesss:
        encoded_file = base64.b64encode(filesss.read()).decode('utf-8')
    #distance_to_nearest = lattitude
    return jsonify({'distance_to_nearest':distance_to_nearest, 
                    'safe_water':safe_water,
            'file_content':encoded_file})

app.run(port=5001)