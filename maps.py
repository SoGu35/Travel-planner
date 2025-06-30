from dotenv import load_dotenv
import os
import gradio as gr
import googlemaps
import requests
import ast

# Load API keys from .env file
load_dotenv()
google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
# Google Maps Client
gmaps = googlemaps.Client(key=google_api_key)
# Autocomplete suggestions
def autocomplete_suggest(input_text):
    if not input_text:
        return []
    try:
        results = gmaps.places_autocomplete(input_text, language='en')
        suggestions = [option['description'] for option in results]
        return suggestions[:5]
    except Exception as e:
        print(f"Error during autocomplete: {e}")
        return []
# Update UI with suggestion buttons
def show_suggestions(input_text):
    suggestions = autocomplete_suggest(input_text)
    btn_updates = []
    for i in range(5):
        if i < len(suggestions):
            btn_updates.append(gr.update(value=suggestions[i], visible=True))
        else:
            btn_updates.append(gr.update(visible=False))
    return btn_updates
# Convert list of locations to coordinates
def geocode_location(locations):
    coords = []
    for location in locations:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location, "key": google_api_key}
        response = requests.get(url, params=params).json()
        if response['status'] == 'OK':
            coords.append(response['results'][0]['geometry']['location'])
        else:
            print(f"Geocoding error for {location}: {response['status']}")
    return coords
def reverse_geocode_location(coord):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    lat = coord[0]
    lng = coord[1]
    params = {
        "latlng": f"{lat},{lng}",
        "key": google_api_key
    }
    response = requests.get(url, params=params).json()
    if response['status'] == 'OK':
        return response['results'][0]['formatted_address']
    else:
        return "Reverse geocoding error"  
# Add a clicked suggestion to selected list
def add_locations(clicked_text, selected_locations):
    if clicked_text not in selected_locations:
        selected_locations.append(clicked_text)
    coords = geocode_location(selected_locations)
    return "\n".join(selected_locations), coords
# Generate static map image
def generate_map(selected_coords, encoded_polyline):
    base_url = "https://maps.googleapis.com/maps/api/staticmap?size=600x400"
    if selected_coords:
        markers = []
        for i, loc in enumerate(selected_coords):
            label = i + 1  # numbering starts at 1
            markers.append(f"label:{label}|{loc['lat']},{loc['lng']}")
            markers_str = "&markers=".join(markers)
            base_url += f"&markers={markers_str}"
            
    ## Uncomment this part for polyline, but sometimes it breaks when too many points are added ##       
    #if encoded_polyline:
    #    base_url += f"&path=enc:{encoded_polyline}"
    base_url += f"&key={google_api_key}"

    return f"<img src='{base_url}' width='600' height='400'/>"
# Compute route between locations
def generate_route(markers):
    if len(markers) < 2:
        return {"error": "Add at least two locations to generate a route."}, ""
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_api_key,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.legs,routes.legs.steps,routes.polyline.encodedPolyline"
    }

    def format_coord(coord):
        return {"location": {"latLng": {"latitude": coord["lat"], "longitude": coord["lng"]}}}

    body = {
        "origin": format_coord(markers[0]),
        "destination": format_coord(markers[-1]),
        "intermediates": [format_coord(loc) for loc in markers[1:-1]],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL"
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        data = response.json()
        encoded_polyline = data['routes'][0]['polyline']['encodedPolyline']
        return data, encoded_polyline
    except Exception as e:
        print(f"Error generating route: {e}")
# Plot the full map view with the route
def plot_map(selected_coords):
    route_data = generate_route(selected_coords)
    if not route_data:
        return None, None, "No driving route data available."
    route_data, encoded_polyline = route_data
    map_html = generate_map(selected_coords, encoded_polyline)
    return route_data, encoded_polyline, map_html
# Extract route information and format it for display
def extract_route_info(route_data):
    def convert_seconds_to_hms(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours}h {minutes}m {seconds}s"
    #  Get the route
    if not route_data or "routes" not in route_data:
        print( "❌ No route data found.❌ ")
        return None
    routes = route_data.get("routes")
    summary = []
    # Extract the first route
    best_route = routes[0]
    best_route_legs = best_route.get("legs", [])
    for leg_index, leg in enumerate(best_route_legs):
        distance = leg.get("distanceMeters", 0) / 1000  # Convert to kilometers
        duration = leg.get("duration", 0)
        if isinstance(duration, int):
            duration = convert_seconds_to_hms(duration)
        elif isinstance(duration, str):
            if duration.endswith('s'):
                duration = int(duration[:-1])
        duration = convert_seconds_to_hms(duration)
        # format (latitude, longitude)
        lats = leg.get('startLocation', {}).get('latLng', {}).get('latitude')
        lngs= leg.get('startLocation', {}).get('latLng', {}).get('longitude')
        coords = (lats, lngs)
        end_lats = leg.get('endLocation', {}).get('latLng', {}).get('latitude')
        end_lngs = leg.get('endLocation', {}).get('latLng', {}).get('longitude')
        end_coords = (end_lats, end_lngs)
        #reverse geocode to get address
        start_address = reverse_geocode_location(coords)
        end_address = reverse_geocode_location(end_coords)
        steps = leg.get("steps", [])
        instruction_list_leg = [
            step.get("navigationInstruction", {}).get("instructions")
            for step in steps
            if step.get("navigationInstruction", {}).get("instructions")
        ]
        summary.append(f" Travelling from {start_address} to {end_address}")
        summary.append(f"  Distance: {distance} km")
        summary.append(f"  Duration: {duration}")
        summary.append(f"  Instructions:")
        # Append step instructions
        for i, instruction in enumerate(instruction_list_leg):
            summary.append(f"    {i + 1}. {instruction}")

    return "\n".join(summary) if summary else "No route information available."

def add_generated_locations_to_map(generated_locations, selected_locations):
    generated_locations = ast.literal_eval(generated_locations) if isinstance(generated_locations, str) else generated_locations
    for location in generated_locations:
        _ , coords = add_locations(location, selected_locations)
    route_data, encoded_polyline, map_html = plot_map(coords)
    
    return route_data, encoded_polyline, map_html, selected_locations
