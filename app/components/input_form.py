'''
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  INPUT FORM - Map with Auto-Location + Manual Entry (No Quick Select)     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import streamlit as st
from datetime import datetime, date
from typing import Dict, Optional
import streamlit.components.v1 as components

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import GEEConfig, UIConfig, DateConfig, TemporalConfig
from utils.helpers import validate_coordinates


# ─────────────────────────────────────────────────────────────────────────────
# MAP COMPONENT WITH AUTO-LOCATION
# ─────────────────────────────────────────────────────────────────────────────

def render_map_with_location() -> Optional[Dict]:
    """Render interactive map with auto-location and click selection."""
    
    # Season info
    render_season_info()
    
    st.markdown("### 📍 Select Location")
    
    # Only Manual Entry and Map Selection (NO Quick Select)
    input_method = st.radio(
        "Select input method:",
        ["🗺️ Map Selection", "✏️ Manual Entry"],
        horizontal=True,
        key="input_method",
        label_visibility="collapsed"
    )
    
    lat, lon = 31.5, 73.0
    
    if input_method == "🗺️ Map Selection":
        try:
            import folium
            from streamlit_folium import st_folium
            from folium.plugins import LocateControl
            
            # Create map
            m = folium.Map(
                location=UIConfig.DEFAULT_CENTER,
                zoom_start=UIConfig.DEFAULT_ZOOM,
                tiles='OpenStreetMap'
            )
            
            # Add locate control (auto-detect button)
            LocateControl(
                auto_start=False,
                position='topright',
                strings={'title': 'Click to detect your location'}
            ).add_to(m)
            
            # Add Punjab boundary
            punjab_bounds = [
                [GEEConfig.PUNJAB_BOUNDS['min_lat'], GEEConfig.PUNJAB_BOUNDS['min_lon']],
                [GEEConfig.PUNJAB_BOUNDS['min_lat'], GEEConfig.PUNJAB_BOUNDS['max_lon']],
                [GEEConfig.PUNJAB_BOUNDS['max_lat'], GEEConfig.PUNJAB_BOUNDS['max_lon']],
                [GEEConfig.PUNJAB_BOUNDS['max_lat'], GEEConfig.PUNJAB_BOUNDS['min_lon']],
            ]
            
            folium.Polygon(
                locations=punjab_bounds,
                color='green',
                weight=2,
                fill=True,
                fillColor='green',
                fillOpacity=0.1,
                popup='Punjab Region'
            ).add_to(m)
            
            # Add click popup
            m.add_child(folium.LatLngPopup())
            
            # Instructions
            st.info("📍 **Click anywhere on the map** to select location OR use the **📍 button** (top-right) to auto-detect")
            
            # Render map
            map_data = st_folium(
                m,
                width=700,
                height=450,
                returned_objects=["last_clicked", "center", "zoom", "all_drawings"],
                key=f"location_map_{st.session_state.get('map_refresh', 0)}"
            )
            
            # Get coordinates from map click
            if map_data and map_data.get("last_clicked"):
                lat = map_data["last_clicked"]["lat"]
                lon = map_data["last_clicked"]["lng"]
                
                # Auto-populate session state
                st.session_state['selected_lat'] = lat
                st.session_state['selected_lon'] = lon
                
                st.success(f"✅ Location selected: **{lat:.6f}°N, {lon:.6f}°E**")
            
            # Return coordinates from session state if available
            if 'selected_lat' in st.session_state and 'selected_lon' in st.session_state:
                return {
                    'latitude': st.session_state['selected_lat'], 
                    'longitude': st.session_state['selected_lon']
                }
            
            return None
            
        except ImportError as e:
            st.error(f"Map requires: `pip install folium streamlit-folium` - Error: {e}")
            return _render_fallback_input()
    
    else:  # Manual Entry
        # Use session state if available, otherwise use defaults
        default_lat = st.session_state.get('selected_lat', 31.5)
        default_lon = st.session_state.get('selected_lon', 73.0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            lat = st.number_input(
                "Latitude", 
                min_value=28.0, 
                max_value=34.0, 
                value=float(default_lat), 
                step=0.0000001, 
                format="%.7f", 
                key="manual_lat"
            )
        with col2:
            lon = st.number_input(
                "Longitude", 
                min_value=69.5, 
                max_value=75.5, 
                value=float(default_lon), 
                step=0.0000001, 
                format="%.7f", 
                key="manual_lon"
            )
        
        st.session_state['selected_lat'] = lat
        st.session_state['selected_lon'] = lon
        
        return {'latitude': lat, 'longitude': lon}


def _render_fallback_input() -> Optional[Dict]:
    """Fallback coordinate input if map unavailable."""
    st.warning("Map view unavailable. Please enter coordinates manually.")
    
    col1, col2 = st.columns(2)
    
    default_lat = st.session_state.get('selected_lat', 31.5)
    default_lon = st.session_state.get('selected_lon', 73.0)
    
    with col1:
        lat = st.number_input(
            "Latitude", 
            min_value=28.0, 
            max_value=34.0, 
            value=float(default_lat), 
            step=0.0001, 
            format="%.6f"
        )
    with col2:
        lon = st.number_input(
            "Longitude", 
            min_value=69.5, 
            max_value=75.5, 
            value=float(default_lon), 
            step=0.0001, 
            format="%.6f"
        )
    
    st.session_state['selected_lat'] = lat
    st.session_state['selected_lon'] = lon
    
    return {'latitude': lat, 'longitude': lon}


def render_season_info(analysis_date: date = None):
    """Render season info banner."""
    if analysis_date is None:
        analysis_date = date.today()
    
    season_info = TemporalConfig.get_season_info(analysis_date.month)
    valid_crops = ', '.join(season_info['valid_crops'])
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); 
                padding: 12px 15px; border-radius: 8px; margin-bottom: 15px;
                border-left: 4px solid {season_info['color']};">
        <strong>{season_info['icon']} Current Season:</strong> {season_info['name']} ({season_info['months']})<br>
        <small>Can detect: {valid_crops}</small>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_info():
    """Render sidebar information."""
    st.sidebar.markdown("## 📅 Data Availability")
    st.sidebar.markdown(f"**{DateConfig.get_min_date().strftime('%B %Y')}** to **Today**")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🌾 Crop Seasons")
    st.sidebar.markdown("""
    **Rice (Kharif):** May - October  
    **Wheat (Rabi):** November - April
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🌍 Supported Region")
    st.sidebar.markdown("**Punjab, Pakistan**")
    '''