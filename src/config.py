# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                         CONFIGURATION FILE                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import os
from datetime import datetime, date
from typing import Dict, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# PATHS CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class PathConfig:
        
    V4_MODEL_PATH = "models/best_model_v4.pth"
    V6_MODEL_PATH = "models/best_model_v6_variable.pth"
    
    GEE_SERVICE_ACCOUNT_KEY = "credentials/gee_service_account.json"
    



# ─────────────────────────────────────────────────────────────────────────────
# MODEL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class ModelConfig:
    
    IMAGE_SIZE = (64, 64)
    NUM_BANDS = 4  # B2, B3, B4, B8
    NUM_MONTHS = 6
    NUM_CHANNELS = NUM_BANDS * NUM_MONTHS  # 24
    
    
    CLASS_NAMES = ['Other', 'Rice', 'Wheat']
    NUM_CLASSES = 3
    CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}
    IDX_TO_CLASS = {idx: name for idx, name in enumerate(CLASS_NAMES)}
    
   
    MIN_MONTHS_FOR_V4 = 5  # Use V4 if >= 5 months available
    MIN_MONTHS_FOR_CLASSIFICATION = 3  # Minimum months needed for reliable classification
    
    
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.70
    LOW_CONFIDENCE_THRESHOLD = 0.50


# ─────────────────────────────────────────────────────────────────────────────
# DATE RANGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class DateConfig:
    """Date range and temporal settings."""
    
    
    MIN_DATE = date(2022, 4, 1)  # April 2022
    
    # Maximum date (today)
    @classmethod
    def get_max_date(cls) -> date:
        """Get maximum date (today)."""
        return date.today()
    
    @classmethod
    def get_min_date(cls) -> date:
        """Get minimum date."""
        return cls.MIN_DATE
    
    @classmethod
    def is_valid_date(cls, check_date: date) -> Tuple[bool, str]:
       
        if check_date < cls.MIN_DATE:
            return False, f"Date must be after {cls.MIN_DATE.strftime('%B %Y')}"
        
        if check_date > date.today():
            return False, "Date cannot be in the future"
        
        return True, "Valid date"
    
    @classmethod
    def get_available_years(cls) -> List[int]:
        return list(range(cls.MIN_DATE.year, date.today().year + 1))


# ─────────────────────────────────────────────────────────────────────────────
# TEMPORAL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class TemporalConfig:
    
    RICE_MONTHS = ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']
    WHEAT_MONTHS = ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr']
    
    MONTH_TO_IDX = {
        'Rice': {month: idx for idx, month in enumerate(RICE_MONTHS)},
        'Wheat': {month: idx for idx, month in enumerate(WHEAT_MONTHS)},
    }
    
    
    RICE_SEASON = {
        'start': 5,   # May
        'end': 10,    # October
        'peak': 9,    # September (flowering)
        'months': [5, 6, 7, 8, 9, 10],  # May to October
    }
    
    WHEAT_SEASON = {
        'start': 11,  # November
        'end': 4,     # April
        'peak': 3,    # March (heading)
        'months': [11, 12, 1, 2, 3, 4],  # November to April
    }
    
    
    RICE_GROWTH_STAGES = {
        5: 'Land Preparation / Nursery',
        6: 'Transplanting',
        7: 'Tillering',
        8: 'Tillering / Panicle Initiation',
        9: 'Flowering / Grain Filling',
        10: 'Grain Filling / Maturity',
    }
    
    WHEAT_GROWTH_STAGES = {
        11: 'Sowing / Germination',
        12: 'Seedling / Crown Root',
        1: 'Tillering',
        2: 'Stem Extension / Booting',
        3: 'Heading / Flowering',
        4: 'Grain Filling / Maturity',
    }
    
    @classmethod
    def get_current_season(cls) -> str:

        month = datetime.now().month
        if month in cls.RICE_SEASON['months']:
            return 'Rice'
        else:
            return 'Wheat'
    
    @classmethod
    def get_season_for_month(cls, month: int) -> str:
        
        if month in cls.RICE_SEASON['months']:
            return 'Rice'
        else:
            return 'Wheat'
    
    @classmethod
    def get_growth_stage(cls, crop: str, month: int) -> str:
        
        if crop == 'Rice':
            return cls.RICE_GROWTH_STAGES.get(month, 'Off-season')
        elif crop == 'Wheat':
            return cls.WHEAT_GROWTH_STAGES.get(month, 'Off-season')
        return 'Unknown'
    
    @classmethod
    def get_valid_crops_for_season(cls, month: int) -> List[str]:
        
        if month in cls.RICE_SEASON['months']:
            # Rice season: Can classify Rice or Other (NOT Wheat)
            return ['Rice', 'Other']
        else:
            # Wheat season: Can classify Wheat or Other (NOT Rice)
            return ['Wheat', 'Other']
    
    @classmethod
    def is_crop_valid_for_season(cls, crop: str, month: int) -> Tuple[bool, str]:
        
        valid_crops = cls.get_valid_crops_for_season(month)
        season = cls.get_season_for_month(month)
        
        if crop in valid_crops:
            return True, f"{crop} is valid for {season} season"
        else:
            return False, f"{crop} cannot be grown during {season} season (Month: {month})"
    
    @classmethod
    def get_season_info(cls, month: int = None) -> Dict:
        
        if month is None:
            month = datetime.now().month
        
        season = cls.get_season_for_month(month)
        
        if season == 'Rice':
            return {
                'name': 'Rice (Kharif)',
                'season': 'Rice',
                'months': 'May - October',
                'valid_crops': ['Rice', 'Other'],
                'invalid_crops': ['Wheat'],
                'icon': '🌾',
                'color': '#27ae60',
            }
        else:
            return {
                'name': 'Wheat (Rabi)',
                'season': 'Wheat',
                'months': 'November - April',
                'valid_crops': ['Wheat', 'Other'],
                'invalid_crops': ['Rice'],
                'icon': '🌿',
                'color': '#f39c12',
            }


# ─────────────────────────────────────────────────────────────────────────────
# GEE CONFIGURATION 
# ─────────────────────────────────────────────────────────────────────────────

class GEEConfig:
    """Google Earth Engine settings."""
    
    # Sentinel-2 collection
    SENTINEL2_COLLECTION = 'COPERNICUS/S2_SR_HARMONIZED'
    
    # Bands to extract
    BANDS = ['B2', 'B3', 'B4', 'B8']  # Blue, Green, Red, NIR
    BAND_NAMES = {
        'B2': 'Blue',
        'B3': 'Green', 
        'B4': 'Red',
        'B8': 'NIR',
    }
    
    
    CLOUD_FILTER_PERCENT = 90  
    CLOUD_FILTER_PERCENT_FALLBACK = 95  
    
    # Scale (resolution in meters)
    SCALE = 10  # Sentinel-2 resolution
    
    
    BUFFER_SIZE = 500  # Increased from 320 to 500 meters (~100 pixels at 10m)
    BUFFER_SIZE_FALLBACK = 800  # Fallback larger buffer
    
    # Punjab, Pakistan bounding box (approximate)
    PUNJAB_BOUNDS = {
        'min_lon': 69.5,
        'max_lon': 75.5,
        'min_lat': 28.0,
        'max_lat': 34.0,
    }
    
    
    DATE_RANGE_EXPANSION_DAYS = 7  
    
    @classmethod
    def is_in_punjab(cls, lat: float, lon: float) -> bool:
        
        return (cls.PUNJAB_BOUNDS['min_lat'] <= lat <= cls.PUNJAB_BOUNDS['max_lat'] and
                cls.PUNJAB_BOUNDS['min_lon'] <= lon <= cls.PUNJAB_BOUNDS['max_lon'])


# ─────────────────────────────────────────────────────────────────────────────
# NDVI THRESHOLDS FOR HEALTH ASSESSMENT
# ─────────────────────────────────────────────────────────────────────────────

class HealthConfig:
    
    
    # Rice NDVI thresholds by growth stage
    RICE_NDVI = {
        'Land Preparation / Nursery': {
            'healthy_min': 0.15,
            'stress_threshold': 0.10,
            'expected_range': (0.10, 0.25),
        },
        'Transplanting': {
            'healthy_min': 0.20,
            'stress_threshold': 0.15,
            'expected_range': (0.15, 0.30),
        },
        'Tillering': {
            'healthy_min': 0.40,
            'stress_threshold': 0.30,
            'expected_range': (0.35, 0.55),
        },
        'Tillering / Panicle Initiation': {
            'healthy_min': 0.50,
            'stress_threshold': 0.40,
            'expected_range': (0.45, 0.65),
        },
        'Flowering / Grain Filling': {
            'healthy_min': 0.55,
            'stress_threshold': 0.45,
            'expected_range': (0.50, 0.75),
        },
        'Grain Filling / Maturity': {
            'healthy_min': 0.40,
            'stress_threshold': 0.30,
            'expected_range': (0.35, 0.55),
        },
    }
    
    # Wheat NDVI thresholds by growth stage
    WHEAT_NDVI = {
        'Sowing / Germination': {
            'healthy_min': 0.15,
            'stress_threshold': 0.10,
            'expected_range': (0.10, 0.25),
        },
        'Seedling / Crown Root': {
            'healthy_min': 0.25,
            'stress_threshold': 0.18,
            'expected_range': (0.20, 0.35),
        },
        'Tillering': {
            'healthy_min': 0.40,
            'stress_threshold': 0.30,
            'expected_range': (0.35, 0.50),
        },
        'Stem Extension / Booting': {
            'healthy_min': 0.55,
            'stress_threshold': 0.45,
            'expected_range': (0.50, 0.70),
        },
        'Heading / Flowering': {
            'healthy_min': 0.60,
            'stress_threshold': 0.50,
            'expected_range': (0.55, 0.75),
        },
        'Grain Filling / Maturity': {
            'healthy_min': 0.40,
            'stress_threshold': 0.30,
            'expected_range': (0.35, 0.55),
        },
    }
    
    # General NDVI interpretation
    NDVI_GENERAL = {
        'bare_soil': (-0.1, 0.1),
        'sparse_vegetation': (0.1, 0.2),
        'moderate_vegetation': (0.2, 0.4),
        'dense_vegetation': (0.4, 0.6),
        'very_healthy': (0.6, 1.0),
    }
    
    # Health status labels
    HEALTH_STATUS = {
        'healthy': '✅ Healthy',
        'moderate_stress': '⚠️ Moderate Stress',
        'severe_stress': '🔴 Severe Stress',
        'critical': '❌ Critical',
    }
    
    @classmethod
    def get_ndvi_thresholds(cls, crop: str, growth_stage: str) -> dict:
        """Get NDVI thresholds for a specific crop and growth stage."""
        if crop == 'Rice':
            return cls.RICE_NDVI.get(growth_stage, cls.RICE_NDVI['Tillering'])
        elif crop == 'Wheat':
            return cls.WHEAT_NDVI.get(growth_stage, cls.WHEAT_NDVI['Tillering'])
        else:
            # Default thresholds for 'Other' crops
            return {
                'healthy_min': 0.35,
                'stress_threshold': 0.25,
                'expected_range': (0.25, 0.55),
            }


# ─────────────────────────────────────────────────────────────────────────────
# ADVISORY SYSTEM CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class AdvisoryConfig:
    
    
    # Stress types
    STRESS_TYPES = [
        'water_stress',
        'nutrient_deficiency',
        'general',
    ]
    
    # Rice recommendations (same as before - truncated for brevity)
    RICE_ADVISORY = {
        'water_stress': {
            'Transplanting': [
                "Maintain 2-5 cm standing water in the field",
                "Ensure proper bund maintenance to prevent water loss",
            ],
        },
    }
    
    # Wheat recommendations (same as before)
    WHEAT_ADVISORY = {
        'water_stress': {
            'Sowing / Germination': [
                "Apply pre-sowing irrigation (rauni) for proper germination",
            ],
        },
    }
    
    GENERAL_ADVISORY = {
        'healthy': [
            "Crop appears healthy - continue regular monitoring",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# UI CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class UIConfig:
    """User interface settings."""
    
    #APP_TITLE = "🌾 AI-Driven Agricultural Field Monitoring"
    #APP_SUBTITLE = "AI-Powered Agricultural Monitoring for Pakistan"
    #APP_VERSION = "1.0.0"  
    
    DEFAULT_CENTER = [31.5, 73.0]  # Punjab center
    DEFAULT_ZOOM = 8
    
    COLORS = {
        'rice': '#27ae60',
        'wheat': '#f39c12',
        'other': '#3498db',
        'healthy': '#2ecc71',
        'moderate': '#f1c40f',
        'severe': '#e74c3c',
    }
    
    CONFIDENCE_BADGES = {
        'high': ('🟢', 'High Confidence'),
        'medium': ('🟡', 'Medium Confidence'),
        'low': ('🔴', 'Low Confidence'),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class LogConfig:
    """Logging settings."""
    
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT ALL CONFIGS
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    'PathConfig',
    'ModelConfig', 
    'DateConfig',
    'TemporalConfig',
    'GEEConfig',
    'HealthConfig',
    'AdvisoryConfig',
    'UIConfig',
    'LogConfig',
]