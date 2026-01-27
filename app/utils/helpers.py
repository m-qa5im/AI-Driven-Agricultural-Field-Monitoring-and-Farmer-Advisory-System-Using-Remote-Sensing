# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI-DRIVEN AGRICULTURAL FIELD MONITORING SYSTEM                            ║
# ║  App Utilities - Helper Functions                                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
from pathlib import Path

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import UIConfig, ModelConfig, GEEConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# COORDINATE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
    """
    Validate if coordinates are valid and within Punjab region.
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Check basic validity
    if latitude is None or longitude is None:
        return False, "Please enter both latitude and longitude"
    
    if not (-90 <= latitude <= 90):
        return False, "Latitude must be between -90 and 90"
    
    if not (-180 <= longitude <= 180):
        return False, "Longitude must be between -180 and 180"
    
    # Check if within Punjab region
    if not GEEConfig.is_in_punjab(latitude, longitude):
        return True, f"⚠️ Location is outside Punjab region. Results may be less accurate."
    
    return True, "✓ Valid coordinates within Punjab region"


def format_coordinates(latitude: float, longitude: float, precision: int = 4) -> str:
    """
    Format coordinates for display.
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
        precision: Decimal places
        
    Returns:
        Formatted string
    """
    lat_dir = "N" if latitude >= 0 else "S"
    lon_dir = "E" if longitude >= 0 else "W"
    
    return f"{abs(latitude):.{precision}f}° {lat_dir}, {abs(longitude):.{precision}f}° {lon_dir}"


# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE & STATUS FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def get_confidence_badge(confidence_level: str) -> Tuple[str, str, str]:
    """
    Get badge elements for confidence level.
    
    Args:
        confidence_level: 'high', 'medium', or 'low'
        
    Returns:
        Tuple of (icon, label, color)
    """
    badges = {
        'high': ('🟢', 'High Confidence', '#2ecc71'),
        'medium': ('🟡', 'Medium Confidence', '#f1c40f'),
        'low': ('🔴', 'Low Confidence', '#e74c3c'),
    }
    return badges.get(confidence_level, ('⚪', 'Unknown', '#95a5a6'))


def get_health_badge(health_status: str) -> Tuple[str, str, str]:
    """
    Get badge elements for health status.
    
    Args:
        health_status: 'healthy', 'moderate_stress', 'severe_stress', 'critical'
        
    Returns:
        Tuple of (icon, label, color)
    """
    badges = {
        'healthy': ('✅', 'Healthy', '#2ecc71'),
        'moderate_stress': ('⚠️', 'Moderate Stress', '#f1c40f'),
        'severe_stress': ('🔴', 'Severe Stress', '#e74c3c'),
        'critical': ('❌', 'Critical', '#c0392b'),
    }
    return badges.get(health_status, ('❓', 'Unknown', '#95a5a6'))


def get_crop_icon(crop: str) -> str:
    """Get icon for crop type."""
    icons = {
        'Rice': '🌾',
        'Wheat': '🌿',
        'Other': '🌱',
    }
    return icons.get(crop, '🌱')


def get_crop_color(crop: str) -> str:
    """Get color for crop type."""
    return UIConfig.COLORS.get(crop.lower() if crop else '', '#3498db')


# ─────────────────────────────────────────────────────────────────────────────
# DATA QUALITY INDICATORS
# ─────────────────────────────────────────────────────────────────────────────

def get_data_quality_indicator(months_available: int) -> Dict:
    """
    Get data quality indicator based on available months.
    
    Args:
        months_available: Number of months with satellite data
        
    Returns:
        Dictionary with quality information
    """
    if months_available >= 5:
        return {
            'level': 'excellent',
            'icon': '🟢',
            'label': 'Excellent Data Quality',
            'description': f'{months_available}/6 months available - Full seasonal coverage',
            'color': '#2ecc71',
            'percentage': (months_available / 6) * 100,
        }
    elif months_available >= 4:
        return {
            'level': 'good',
            'icon': '🟢',
            'label': 'Good Data Quality',
            'description': f'{months_available}/6 months available - Most seasonal data present',
            'color': '#27ae60',
            'percentage': (months_available / 6) * 100,
        }
    elif months_available >= 3:
        return {
            'level': 'moderate',
            'icon': '🟡',
            'label': 'Moderate Data Quality',
            'description': f'{months_available}/6 months available - Partial seasonal coverage',
            'color': '#f1c40f',
            'percentage': (months_available / 6) * 100,
        }
    elif months_available >= 2:
        return {
            'level': 'limited',
            'icon': '🟠',
            'label': 'Limited Data Quality',
            'description': f'{months_available}/6 months available - Limited accuracy',
            'color': '#e67e22',
            'percentage': (months_available / 6) * 100,
        }
    else:
        return {
            'level': 'insufficient',
            'icon': '🔴',
            'label': 'Insufficient Data',
            'description': f'{months_available}/6 months available - Results unreliable',
            'color': '#e74c3c',
            'percentage': (months_available / 6) * 100,
        }


# ─────────────────────────────────────────────────────────────────────────────
# PROBABILITY FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def format_probabilities(probabilities: Dict[str, float]) -> list:
    """
    Format class probabilities for display.
    
    Args:
        probabilities: Dictionary of class -> probability
        
    Returns:
        List of formatted probability dictionaries, sorted by probability
    """
    formatted = []
    for class_name, prob in probabilities.items():
        formatted.append({
            'class': class_name,
            'probability': prob,
            'percentage': f"{prob * 100:.1f}%",
            'icon': get_crop_icon(class_name),
            'color': get_crop_color(class_name),
        })
    
    # Sort by probability descending
    formatted.sort(key=lambda x: x['probability'], reverse=True)
    return formatted


# ─────────────────────────────────────────────────────────────────────────────
# NDVI FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def format_ndvi(ndvi: float) -> Dict:
    """
    Format NDVI value with interpretation.
    
    Args:
        ndvi: NDVI value (-1 to 1)
        
    Returns:
        Dictionary with formatted NDVI information
    """
    if ndvi is None:
        return {
            'value': None,
            'formatted': 'N/A',
            'interpretation': 'No data available',
            'color': '#95a5a6',
        }
    
    if ndvi < 0.1:
        interpretation = 'Bare soil / Water'
        color = '#8b4513'
    elif ndvi < 0.2:
        interpretation = 'Sparse vegetation'
        color = '#d4a574'
    elif ndvi < 0.4:
        interpretation = 'Moderate vegetation'
        color = '#90EE90'
    elif ndvi < 0.6:
        interpretation = 'Dense vegetation'
        color = '#228B22'
    else:
        interpretation = 'Very healthy vegetation'
        color = '#006400'
    
    return {
        'value': ndvi,
        'formatted': f"{ndvi:.3f}",
        'interpretation': interpretation,
        'color': color,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DATE & TIME UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def get_current_season() -> Dict:
    """
    Get current growing season information.
    
    Returns:
        Dictionary with season information
    """
    month = datetime.now().month
    
    if 5 <= month <= 11:
        return {
            'name': 'Kharif (Rice)',
            'crop': 'Rice',
            'icon': '🌾',
            'months': 'May - November',
            'status': 'Active' if 5 <= month <= 10 else 'Harvesting',
        }
    else:
        return {
            'name': 'Rabi (Wheat)',
            'crop': 'Wheat',
            'icon': '🌿',
            'months': 'November - April',
            'status': 'Active' if month in [12, 1, 2, 3] else 'Harvesting',
        }


def format_date(date: datetime, format_type: str = 'full') -> str:
    """
    Format date for display.
    
    Args:
        date: DateTime object
        format_type: 'full', 'short', 'date_only'
        
    Returns:
        Formatted date string
    """
    formats = {
        'full': '%B %d, %Y at %I:%M %p',
        'short': '%b %d, %Y',
        'date_only': '%Y-%m-%d',
    }
    return date.strftime(formats.get(format_type, formats['full']))


# ─────────────────────────────────────────────────────────────────────────────
# FILE PATH UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def get_project_paths() -> Dict[str, Path]:
    """
    Get important project paths.
    
    Returns:
        Dictionary of path names to Path objects
    """
    project_root = Path(__file__).parent.parent.parent
    
    return {
        'root': project_root,
        'src': project_root / 'src',
        'app': project_root / 'app',
        'models': project_root / 'models',
        'credentials': project_root / 'credentials',
        'outputs': project_root / 'outputs',
        'logs': project_root / 'outputs' / 'logs',
    }


def check_model_files() -> Dict[str, bool]:
    """
    Check if required model files exist.
    
    Returns:
        Dictionary of model names to existence status
    """
    paths = get_project_paths()
    
    return {
        'v4_model': (paths['models'] / 'best_model_v4.pth').exists(),
        'v6_model': (paths['models'] / 'best_model_v6_variable.pth').exists(),
        'gee_credentials': (paths['credentials'] / 'gee_service_account.json').exists(),
    }


def get_model_path(model_name: str) -> Optional[Path]:
    """
    Get path for a specific model.
    
    Args:
        model_name: 'v4' or 'v6'
        
    Returns:
        Path object or None if not found
    """
    paths = get_project_paths()
    
    model_files = {
        'v4': paths['models'] / 'best_model_v4.pth',
        'v6': paths['models'] / 'best_model_v6_variable.pth',
    }
    
    path = model_files.get(model_name)
    if path and path.exists():
        return path
    return None


def get_credentials_path() -> Optional[Path]:
    """
    Get path for GEE credentials.
    
    Returns:
        Path object or None if not found
    """
    paths = get_project_paths()
    cred_path = paths['credentials'] / 'gee_service_account.json'
    
    if cred_path.exists():
        return cred_path
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ERROR MESSAGES
# ─────────────────────────────────────────────────────────────────────────────

ERROR_MESSAGES = {
    'no_coordinates': "Please enter valid coordinates to analyze.",
    'invalid_coordinates': "Invalid coordinates. Please check your input.",
    'outside_region': "Location is outside the supported region (Punjab, Pakistan).",
    'no_satellite_data': "No satellite data available for this location and time period.",
    'model_not_found': "Model files not found. Please ensure models are in the 'models' folder.",
    'gee_auth_failed': "Failed to authenticate with Google Earth Engine. Check credentials.",
    'insufficient_data': "Insufficient satellite data for reliable classification.",
    'processing_error': "An error occurred during processing. Please try again.",
}


def get_error_message(error_key: str, details: str = None) -> str:
    """
    Get formatted error message.
    
    Args:
        error_key: Key for error message
        details: Additional details to append
        
    Returns:
        Formatted error message
    """
    message = ERROR_MESSAGES.get(error_key, "An unknown error occurred.")
    if details:
        message += f"\n\nDetails: {details}"
    return message


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def log_analysis_request(latitude: float, longitude: float, user_info: str = None):
    """Log an analysis request."""
    logger.info(f"Analysis requested: ({latitude}, {longitude})")
    if user_info:
        logger.info(f"User info: {user_info}")


def log_analysis_result(result: Dict):
    """Log analysis result summary."""
    logger.info(f"Analysis complete: {result.get('predicted_class', 'N/A')} "
                f"({result.get('confidence', 0):.1%} confidence)")
