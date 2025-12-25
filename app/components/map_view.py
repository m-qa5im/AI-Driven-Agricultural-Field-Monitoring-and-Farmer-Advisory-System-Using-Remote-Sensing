# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI-DRIVEN AGRICULTURAL FIELD MONITORING SYSTEM                            ║
# ║  Map View Component                                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import streamlit as st
from typing import Dict, Optional
import folium
from folium import plugins

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import UIConfig, GEEConfig
from app.utils.helpers import get_crop_icon, get_crop_color, get_health_badge


# ─────────────────────────────────────────────────────────────────────────────
# RESULT MAP
# ─────────────────────────────────────────────────────────────────────────────

def render_result_map(
    latitude: float,
    longitude: float,
    classification_result: Dict = None,
    health_result: Dict = None,
) -> None:
    """
    Render an interactive map showing the analyzed location with results.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        classification_result: Crop classification results
        health_result: Health assessment results
    """
    try:
        from streamlit_folium import st_folium
        
        # Create map
        m = folium.Map(
            location=[latitude, longitude],
            zoom_start=14,
            tiles='OpenStreetMap'
        )
        
        # Add different tile layers
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
        ).add_to(m)
        
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='Street Map',
            overlay=False,
        ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Prepare popup content
        popup_html = _create_popup_html(
            latitude, longitude, 
            classification_result, 
            health_result
        )
        
        # Determine marker color based on results
        marker_color = _get_marker_color(classification_result, health_result)
        
        # Add marker for analyzed location
        folium.Marker(
            location=[latitude, longitude],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip="Click for details",
            icon=folium.Icon(color=marker_color, icon='leaf', prefix='fa')
        ).add_to(m)
        
        # Add circle showing analysis area (~640m diameter as per GEE buffer)
        folium.Circle(
            location=[latitude, longitude],
            radius=320,  # meters (matching GEE buffer)
            color=marker_color,
            weight=2,
            fill=True,
            fillColor=marker_color,
            fillOpacity=0.2,
            popup="Analysis Area (~640m × 640m)"
        ).add_to(m)
        
        # Add Punjab boundary (light overlay)
        punjab_bounds = [
            [GEEConfig.PUNJAB_BOUNDS['min_lat'], GEEConfig.PUNJAB_BOUNDS['min_lon']],
            [GEEConfig.PUNJAB_BOUNDS['min_lat'], GEEConfig.PUNJAB_BOUNDS['max_lon']],
            [GEEConfig.PUNJAB_BOUNDS['max_lat'], GEEConfig.PUNJAB_BOUNDS['max_lon']],
            [GEEConfig.PUNJAB_BOUNDS['max_lat'], GEEConfig.PUNJAB_BOUNDS['min_lon']],
        ]
        
        folium.Polygon(
            locations=punjab_bounds,
            color='green',
            weight=1,
            fill=False,
            popup='Punjab Region Boundary'
        ).add_to(m)
        
        # Add minimap
        minimap = plugins.MiniMap(toggle_display=True)
        m.add_child(minimap)
        
        # Add fullscreen option
        plugins.Fullscreen().add_to(m)
        
        # Add measure control
        plugins.MeasureControl(position='topleft').add_to(m)
        
        # Render map
        st_folium(m, width=700, height=450, returned_objects=[])
        
    except ImportError as e:
        st.error(f"Map component not available: {str(e)}")
        _render_fallback_location(latitude, longitude)


def _create_popup_html(
    latitude: float,
    longitude: float,
    classification_result: Dict = None,
    health_result: Dict = None
) -> str:
    """Create HTML content for map popup."""
    
    html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 200px;">
        <h4 style="margin: 0 0 10px 0; color: #2e7d32; border-bottom: 2px solid #4caf50; padding-bottom: 5px;">
            📍 Analysis Results
        </h4>
        
        <p style="margin: 5px 0; font-size: 12px; color: #666;">
            <strong>Location:</strong> {latitude:.4f}°N, {longitude:.4f}°E
        </p>
    """
    
    if classification_result:
        crop = classification_result.get('predicted_class', 'Unknown')
        confidence = classification_result.get('confidence', 0)
        crop_icon = get_crop_icon(crop)
        
        html += f"""
        <div style="background: #e8f5e9; padding: 8px; border-radius: 5px; margin: 10px 0;">
            <strong>Crop:</strong> {crop_icon} {crop}<br>
            <strong>Confidence:</strong> {confidence:.1%}
        </div>
        """
    
    if health_result:
        status = health_result.get('status', 'unknown')
        ndvi = health_result.get('current_ndvi', 0)
        icon, label, _ = get_health_badge(status)
        
        html += f"""
        <div style="background: #fff3e0; padding: 8px; border-radius: 5px; margin: 10px 0;">
            <strong>Health:</strong> {icon} {label}<br>
            <strong>NDVI:</strong> {ndvi:.3f}
        </div>
        """
    
    html += "</div>"
    return html


def _get_marker_color(
    classification_result: Dict = None,
    health_result: Dict = None
) -> str:
    """Determine marker color based on results."""
    
    # Priority: health status > crop type
    if health_result:
        status = health_result.get('status', 'unknown')
        if status == 'healthy':
            return 'green'
        elif status == 'moderate_stress':
            return 'orange'
        elif status in ['severe_stress', 'critical']:
            return 'red'
    
    if classification_result:
        crop = classification_result.get('predicted_class', 'Other')
        if crop == 'Rice':
            return 'green'
        elif crop == 'Wheat':
            return 'orange'
    
    return 'blue'


def _render_fallback_location(latitude: float, longitude: float):
    """Render simple location display when map is not available."""
    
    st.markdown(f"""
    <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; text-align: center;">
        <h4>📍 Analyzed Location</h4>
        <p style="font-size: 18px;">
            <strong>Latitude:</strong> {latitude:.4f}°N<br>
            <strong>Longitude:</strong> {longitude:.4f}°E
        </p>
        <p style="font-size: 12px; color: #666;">
            <a href="https://www.google.com/maps?q={latitude},{longitude}" target="_blank">
                View on Google Maps ↗
            </a>
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# NDVI MAP (HEATMAP STYLE)
# ─────────────────────────────────────────────────────────────────────────────

def render_ndvi_indicator(ndvi: float, expected_range: tuple = None) -> None:
    """
    Render a visual NDVI indicator.
    
    Args:
        ndvi: Current NDVI value
        expected_range: Expected NDVI range for comparison
    """
    
    # NDVI color scale
    if ndvi < 0.1:
        color = '#8B4513'  # Brown (bare soil)
        label = 'Bare Soil'
    elif ndvi < 0.2:
        color = '#D2B48C'  # Tan (sparse)
        label = 'Sparse'
    elif ndvi < 0.3:
        color = '#ADFF2F'  # Green-yellow
        label = 'Low'
    elif ndvi < 0.4:
        color = '#90EE90'  # Light green
        label = 'Moderate'
    elif ndvi < 0.5:
        color = '#32CD32'  # Lime green
        label = 'Good'
    elif ndvi < 0.6:
        color = '#228B22'  # Forest green
        label = 'Healthy'
    else:
        color = '#006400'  # Dark green
        label = 'Very Healthy'
    
    # Calculate position on scale (0-100%)
    position = min(max((ndvi + 0.1) / 1.1 * 100, 0), 100)
    
    st.markdown(f"""
    <div style="margin: 20px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-size: 14px; color: #666;">NDVI Scale</span>
            <span style="font-size: 14px; font-weight: bold; color: {color};">
                {ndvi:.3f} ({label})
            </span>
        </div>
        
        <!-- NDVI Scale Bar -->
        <div style="position: relative; height: 25px; border-radius: 5px; 
                    background: linear-gradient(to right, 
                        #8B4513 0%, 
                        #D2B48C 15%, 
                        #ADFF2F 25%, 
                        #90EE90 35%, 
                        #32CD32 50%, 
                        #228B22 70%, 
                        #006400 100%);">
            
            <!-- Marker -->
            <div style="position: absolute; left: {position}%; top: -5px; 
                        transform: translateX(-50%);">
                <div style="width: 0; height: 0; 
                            border-left: 8px solid transparent; 
                            border-right: 8px solid transparent; 
                            border-top: 10px solid #333;">
                </div>
            </div>
        </div>
        
        <!-- Scale Labels -->
        <div style="display: flex; justify-content: space-between; 
                    margin-top: 5px; font-size: 11px; color: #888;">
            <span>-0.1</span>
            <span>0.2</span>
            <span>0.4</span>
            <span>0.6</span>
            <span>1.0</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Show expected range if provided
    if expected_range:
        st.markdown(f"""
        <p style="font-size: 12px; color: #666; text-align: center;">
            Expected range for this growth stage: <strong>{expected_range[0]:.2f} - {expected_range[1]:.2f}</strong>
        </p>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# AVAILABILITY VISUALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def render_data_availability(availability: list, season: str = 'Rice') -> None:
    """
    Render visualization of monthly data availability.
    
    Args:
        availability: List of 0/1 indicating available months
        season: 'Rice' or 'Wheat' to determine month labels
    """
    
    if season == 'Rice':
        months = ['May', 'Jun', 'Aug', 'Sep', 'Oct', 'Nov']
    else:
        months = ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr']
    
    months_available = sum(availability)
    
    st.markdown(f"""
    <div style="margin: 15px 0;">
        <p style="margin-bottom: 10px; font-weight: bold;">
            📅 Data Availability: {months_available}/6 months
        </p>
        <div style="display: flex; gap: 5px;">
    """, unsafe_allow_html=True)
    
    # Create month boxes
    html_boxes = ""
    for i, (month, avail) in enumerate(zip(months, availability)):
        if avail:
            bg_color = "#4caf50"
            text_color = "white"
            icon = "✓"
        else:
            bg_color = "#e0e0e0"
            text_color = "#999"
            icon = "✗"
        
        html_boxes += f"""
        <div style="flex: 1; text-align: center; padding: 8px 5px; 
                    background: {bg_color}; border-radius: 5px;">
            <div style="font-size: 11px; color: {text_color};">{month}</div>
            <div style="font-size: 14px; color: {text_color};">{icon}</div>
        </div>
        """
    
    st.markdown(html_boxes + "</div></div>", unsafe_allow_html=True)
