# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI-DRIVEN AGRICULTURAL FIELD MONITORING SYSTEM                            ║
# ║  Input Form Component                                                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import GEEConfig, UIConfig
from app.utils.helpers import validate_coordinates, get_current_season


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE LOCATIONS
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_LOCATIONS = {
    "Select a location...": (None, None),
    "📍 Hafizabad (Rice Belt)": (32.0714, 73.6881),
    "📍 Sheikhupura (Rice/Wheat)": (31.7131, 73.9850),
    "📍 Gujranwala (Mixed Crops)": (32.1617, 74.1883),
    "📍 Faisalabad (Wheat Belt)": (31.4504, 73.1350),
    "📍 Multan (Cotton/Wheat)": (30.1575, 71.5249),
    "📍 Lahore (Peri-urban)": (31.5204, 74.3587),
    "📍 Sahiwal (Mixed Agriculture)": (30.6682, 73.1114),
    "📍 Okara (Wheat/Sugarcane)": (30.8138, 73.4534),
}


# ─────────────────────────────────────────────────────────────────────────────
# INPUT FORM COMPONENT
# ─────────────────────────────────────────────────────────────────────────────

def render_input_form() -> Optional[Dict]:
    """
    Render the input form for coordinates and analysis options.
    
    Returns:
        Dictionary with form data if submitted, None otherwise
    """
    
    # Current season info
    season_info = get_current_season()
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); 
                padding: 15px; border-radius: 10px; margin-bottom: 20px;">
        <h4 style="margin: 0; color: #2e7d32;">
            {season_info['icon']} Current Season: {season_info['name']}
        </h4>
        <p style="margin: 5px 0 0 0; color: #558b2f; font-size: 14px;">
            {season_info['months']} • Status: {season_info['status']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Input method tabs
    tab1, tab2 = st.tabs(["📍 Enter Coordinates", "🗺️ Select from Map"])
    
    with tab1:
        form_data = _render_coordinate_input()
    
    with tab2:
        form_data_map = _render_map_selection()
        if form_data_map:
            form_data = form_data_map
    
    return form_data


def _render_coordinate_input() -> Optional[Dict]:
    """Render manual coordinate input form."""
    
    # Quick location selector
    st.markdown("##### 🎯 Quick Select (Sample Locations)")
    
    selected_location = st.selectbox(
        "Choose a sample location:",
        options=list(SAMPLE_LOCATIONS.keys()),
        key="sample_location",
        help="Select a sample location to auto-fill coordinates"
    )
    
    # Get coordinates from selection
    default_lat, default_lon = SAMPLE_LOCATIONS.get(selected_location, (None, None))
    
    st.markdown("##### 📐 Or Enter Coordinates Manually")
    
    col1, col2 = st.columns(2)
    
    with col1:
        latitude = st.number_input(
            "Latitude",
            min_value=20.0,
            max_value=40.0,
            value=default_lat if default_lat else 31.5,
            step=0.0001,
            format="%.4f",
            help="Enter latitude (e.g., 31.5204 for Lahore)"
        )
    
    with col2:
        longitude = st.number_input(
            "Longitude",
            min_value=60.0,
            max_value=80.0,
            value=default_lon if default_lon else 73.0,
            step=0.0001,
            format="%.4f",
            help="Enter longitude (e.g., 74.3587 for Lahore)"
        )
    
    # Validate coordinates
    is_valid, validation_message = validate_coordinates(latitude, longitude)
    
    if is_valid:
        if "outside" in validation_message.lower():
            st.warning(validation_message)
        else:
            st.success(validation_message)
    else:
        st.error(validation_message)
    
    # Analysis options
    st.markdown("##### ⚙️ Analysis Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_date = st.date_input(
            "Analysis Date",
            value=datetime.now(),
            max_value=datetime.now(),
            min_value=datetime.now() - timedelta(days=365),
            help="Select the date for analysis (affects which months are fetched)"
        )
    
    with col2:
        include_health = st.checkbox(
            "Include Health Assessment",
            value=True,
            help="Analyze crop health based on NDVI"
        )
        
        include_advisory = st.checkbox(
            "Include Advisory",
            value=True,
            help="Generate recommendations based on results"
        )
    
    # Advanced options (collapsible)
    with st.expander("🔧 Advanced Options"):
        use_tta = st.checkbox(
            "Use Test-Time Augmentation (TTA)",
            value=True,
            help="Improves accuracy but takes slightly longer"
        )
        
        force_model = st.selectbox(
            "Force Model Selection",
            options=["Auto (Recommended)", "V4 (Full Data)", "V6 (Variable Input)"],
            help="Auto selects the best model based on data availability"
        )
    
    # Submit button
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        submitted = st.button(
            "🔍 Analyze Location",
            type="primary",
            use_container_width=True,
            disabled=not is_valid
        )
    
    if submitted and is_valid:
        return {
            'latitude': latitude,
            'longitude': longitude,
            'analysis_date': datetime.combine(analysis_date, datetime.min.time()),
            'include_health': include_health,
            'include_advisory': include_advisory,
            'use_tta': use_tta,
            'force_model': None if "Auto" in force_model else force_model.split()[0],
        }
    
    return None


def _render_map_selection() -> Optional[Dict]:
    """Render map-based location selection."""
    
    st.markdown("""
    <div style="background-color: #fff3e0; padding: 15px; border-radius: 10px; 
                border-left: 4px solid #ff9800; margin-bottom: 20px;">
        <strong>📍 Click on the map to select a location</strong><br>
        <span style="font-size: 14px; color: #666;">
            The map shows Punjab, Pakistan region. Click anywhere to set coordinates.
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        import folium
        from streamlit_folium import st_folium
        
        # Create map centered on Punjab
        m = folium.Map(
            location=UIConfig.DEFAULT_CENTER,
            zoom_start=UIConfig.DEFAULT_ZOOM,
            tiles='OpenStreetMap'
        )
        
        # Add Punjab boundary (approximate)
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
        
        # Add click functionality
        m.add_child(folium.LatLngPopup())
        
        # Render map
        map_data = st_folium(
            m,
            width=700,
            height=400,
            returned_objects=["last_clicked"],
        )
        
        # Handle click
        if map_data and map_data.get("last_clicked"):
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lon = map_data["last_clicked"]["lng"]
            
            st.success(f"📍 Selected: {clicked_lat:.4f}°N, {clicked_lon:.4f}°E")
            
            # Validate
            is_valid, validation_message = validate_coordinates(clicked_lat, clicked_lon)
            
            if not is_valid:
                st.error(validation_message)
                return None
            
            if "outside" in validation_message.lower():
                st.warning(validation_message)
            
            # Analysis options
            col1, col2 = st.columns(2)
            
            with col1:
                include_health = st.checkbox(
                    "Include Health Assessment",
                    value=True,
                    key="map_health"
                )
            
            with col2:
                include_advisory = st.checkbox(
                    "Include Advisory",
                    value=True,
                    key="map_advisory"
                )
            
            # Submit button
            if st.button("🔍 Analyze Selected Location", type="primary", use_container_width=True):
                return {
                    'latitude': clicked_lat,
                    'longitude': clicked_lon,
                    'analysis_date': datetime.now(),
                    'include_health': include_health,
                    'include_advisory': include_advisory,
                    'use_tta': True,
                    'force_model': None,
                }
        else:
            st.info("👆 Click on the map to select a location")
    
    except ImportError:
        st.error("Map component not available. Please use coordinate input instead.")
    
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR INFO
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar_info():
    """Render helpful information in the sidebar."""
    
    st.sidebar.markdown("## ℹ️ How to Use")
    
    st.sidebar.markdown("""
    1. **Enter Coordinates** or select from map
    2. Click **Analyze Location**
    3. View crop classification results
    4. Check health assessment
    5. Follow advisory recommendations
    """)
    
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("## 🌍 Supported Region")
    st.sidebar.markdown("""
    **Punjab, Pakistan**
    - Latitude: 28°N - 34°N
    - Longitude: 69.5°E - 75.5°E
    """)
    
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("## 🌾 Supported Crops")
    st.sidebar.markdown("""
    - 🌾 **Rice** (Kharif: May-Nov)
    - 🌿 **Wheat** (Rabi: Nov-Apr)
    - 🌱 **Other** (Mixed/Fallow)
    """)
    
    st.sidebar.markdown("---")
    
    # System status
    st.sidebar.markdown("## 🔧 System Status")
    
    from app.utils.helpers import check_model_files
    status = check_model_files()
    
    for name, exists in status.items():
        icon = "✅" if exists else "❌"
        label = name.replace('_', ' ').title()
        st.sidebar.markdown(f"{icon} {label}")
