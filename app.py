import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import time

# --- Configuration ---
st.set_page_config(page_title="Open House Optimizer", layout="wide")

# Valid User Agent is required for Nominatim
USER_AGENT = "open_house_optimizer_v1"

# --- Helper Functions ---

@st.cache_data
def get_coordinates(address):
    """
    Geocode an address string to (lat, lon).
    Returns None if not found.
    Using time.sleep to respect Nominatim rate limits (1 request per second).
    """
    geolocator = Nominatim(user_agent=USER_AGENT)
    try:
        # Rate limit protection
        time.sleep(1.1) 
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        return None
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
        return None

def calculate_route(start_node, nodes):
    """
    Nearest Neighbor Algorithm.
    start_node: {'address': str, 'lat': float, 'lon': float}
    nodes: list of dicts [{'address': str, 'lat': float, 'lon': float}, ...]
    
    Returns: ordered list of nodes (start -> visit 1 -> ... -> visit N -> start)
    """
    unvisited = nodes.copy()
    route = [start_node]
    current_node = start_node

    while unvisited:
        nearest_node = None
        min_dist = float('inf')

        for node in unvisited:
            dist = geodesic((current_node['lat'], (current_node['lon'])), (node['lat'], node['lon'])).miles
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
        
        if nearest_node:
            route.append(nearest_node)
            unvisited.remove(nearest_node)
            current_node = nearest_node
            
    # Return to start
    route.append(start_node)
    return route

def generate_google_maps_link(route):
    """
    Constructs a Google Maps direction URL for the given route.
    Route is a list of node dicts.
    """
    base_url = "https://www.google.com/maps/dir/"
    
    # Extract addresses/coords. Using coordinates is safer for ambiguous addresses,
    # but addresses are more human readable. Let's use coordinates for precision.
    # format: /lat,lon/lat,lon/...
    
    path_segments = []
    for node in route:
        # Use simple formatting, standard for Google Maps URL
        path_segments.append(f"{node['lat']},{node['lon']}")
        
    full_url = base_url + "/".join(path_segments)
    return full_url

# --- UI Layout ---

st.title("🏡 Open House Route Optimizer")
st.markdown("Paste addresses, optimize your route, and go!")

# Sidebar for inputs if desired, or main area. Let's do main area for inputs to be mobile friendly (larger).
# But Requirements asked for Sidebar for Tour Schedule, so let's put inputs in sidebar or top.
# "Display a sidebar with the 'Tour Schedule' and a button..." implies output in sidebar? 
# Let's keep input on top main, output map main, schedule in sidebar.

with st.expander("📝 Configuration", expanded=True):
    home_address = st.text_input("Home Address (Start/End)", "1600 Amphitheatre Parkway, Mountain View, CA")
    
    address_input = st.text_area(
        "List of Open House Addresses (one per line)",
        height=150,
        placeholder="123 Main St, Mountain View, CA\n456 Oak Ave, Mountain View, CA\n..."
    )

    # Placeholder for API Key (not used in this logic, but requested)
    api_key = st.text_input("Google Maps API Key (Optional - for future use)", type="password")

if "optimized_route" not in st.session_state:
    st.session_state.optimized_route = None
if "dest_nodes" not in st.session_state:
    st.session_state.dest_nodes = []

if st.button("🚀 Optimize Route", type="primary"):
    if not home_address or not address_input.strip():
        st.error("Please provide a home address and at least one destination.")
    else:
        with st.spinner("Geocoding addresses... (this may take a moment)"):
            
            # 1. Process Home
            home_coords = get_coordinates(home_address)
            if not home_coords:
                st.error(f"Could not locate home address: {home_address}")
            else:
                home_node = {'address': home_address, 'lat': home_coords[0], 'lon': home_coords[1], 'type': 'Home'}

                # 2. Process List
                raw_addresses = [line.strip() for line in address_input.split('\n') if line.strip()]
                dest_nodes = []
                
                progress_bar = st.progress(0)
                for i, addr in enumerate(raw_addresses):
                    coords = get_coordinates(addr)
                    if coords:
                        dest_nodes.append({'address': addr, 'lat': coords[0], 'lon': coords[1], 'type': 'Stop'})
                    else:
                        st.warning(f"Skipping address (could not locate): {addr}")
                    progress_bar.progress((i + 1) / len(raw_addresses))
                
                if not dest_nodes:
                    st.error("No valid destination addresses found.")
                else:
                    # 3. Optimize
                    optimized_route = calculate_route(home_node, dest_nodes)
                    
                    # Store in session state
                    st.session_state.optimized_route = optimized_route
                    st.session_state.dest_nodes = dest_nodes

# --- Display Results from Session State ---
if st.session_state.optimized_route:
    optimized_route = st.session_state.optimized_route
    dest_nodes = st.session_state.dest_nodes
    
    # Map
    m = folium.Map(location=[optimized_route[0]['lat'], optimized_route[0]['lon']], zoom_start=12)
    
    # Draw Route Line
    route_coords = [(node['lat'], node['lon']) for node in optimized_route]
    folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.7).add_to(m)
    
    # Add Markers
    for i, node in enumerate(optimized_route):
        # Start/End are the same node, handled by logic. 
        # Sequence: 0 (Start), 1 (First Stop), ... N (Last Stop), N+1 (End=Start)
        
        label = ""
        icon_color = "blue"
        
        if i == 0:
            label = "🏠 Start"
            icon_color = "green"
        elif i == len(optimized_route) - 1:
            # This is the return to home marker, might overlap with start.
            continue 
        else:
            label = f"{i}" # Stop Number
            icon_color = "red"
        
        folium.Marker(
            location=[node['lat'], node['lon']],
            popup=node['address'],
            tooltip=f"{label}: {node['address']}",
            icon=folium.Icon(color=icon_color, icon="info-sign" if i==0 else "home", prefix='fa')
        ).add_to(m)

    st_folium(m, width="100%", height=500)
    
    # Sidebar Schedule and Link
    with st.sidebar:
        st.header("Tour Schedule")
        
        # We skip the last item for the schedule list implicitly as it's just 'Return Home'
        # But explicit is better.
        
        for i, node in enumerate(optimized_route):
            if i == 0:
                st.markdown(f"**START**: {node['address']}")
            elif i == len(optimized_route) - 1:
                st.markdown(f"**END**: Return to {node['address']}")
            else:
                st.markdown(f"**{i}.** {node['address']}")
        
        st.divider()
        
        gmaps_link = generate_google_maps_link(optimized_route)
        st.link_button("🗺️ Open in Google Maps", gmaps_link)
        
        st.success(f"Total stops: {len(dest_nodes)}")

