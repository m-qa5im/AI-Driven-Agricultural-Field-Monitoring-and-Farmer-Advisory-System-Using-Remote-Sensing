# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PAKISTAN CROP CLASSIFICATION SYSTEM - CONFIGURATION                       ║
# ║  All settings, thresholds, and constants                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import os
from datetime import datetime, date
from typing import Dict, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# PATHS CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class PathConfig:
    """File paths configuration."""
    
    # Model paths (update these for your deployment)
    V4_MODEL_PATH = "models/best_model_v4.pth"
    V6_MODEL_PATH = "models/best_model_v6_variable.pth"
    
    # Service account key (keep this secure!)
    GEE_SERVICE_ACCOUNT_KEY = "credentials/gee_service_account.json"
    
    # Output directories
    OUTPUT_DIR = "outputs"
    TEMP_DIR = "temp"
    LOGS_DIR = "logs"


# ─────────────────────────────────────────────────────────────────────────────
# MODEL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class ModelConfig:
    """Model architecture and inference settings."""
    
    # Input specifications
    IMAGE_SIZE = (64, 64)
    NUM_BANDS = 4  # B2, B3, B4, B8
    NUM_MONTHS = 6
    NUM_CHANNELS = NUM_BANDS * NUM_MONTHS  # 24
    
    # Classes
    CLASS_NAMES = ['Other', 'Rice', 'Wheat']
    NUM_CLASSES = 3
    CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}
    IDX_TO_CLASS = {idx: name for idx, name in enumerate(CLASS_NAMES)}
    
    # Model selection thresholds
    MIN_MONTHS_FOR_V4 = 5  # Use V4 if >= 5 months available
    MIN_MONTHS_FOR_CLASSIFICATION = 3  # Minimum months needed for reliable classification
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.70
    LOW_CONFIDENCE_THRESHOLD = 0.50


# ─────────────────────────────────────────────────────────────────────────────
# DATE RANGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class DateConfig:
    """Date range and temporal settings."""
    
    # Minimum date for data availability (Sentinel-2 reliable data)
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
        """
        Check if date is within valid range.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if check_date < cls.MIN_DATE:
            return False, f"Date must be after {cls.MIN_DATE.strftime('%B %Y')}"
        
        if check_date > date.today():
            return False, "Date cannot be in the future"
        
        return True, "Valid date"
    
    @classmethod
    def get_available_years(cls) -> List[int]:
        """Get list of available years for analysis."""
        return list(range(cls.MIN_DATE.year, date.today().year + 1))


# ─────────────────────────────────────────────────────────────────────────────
# TEMPORAL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class TemporalConfig:
    """Crop seasons and temporal settings for Pakistan."""
    
    # Month names for each season
    RICE_MONTHS = ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']  # Updated: Jul instead of Aug twice
    WHEAT_MONTHS = ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr']
    
    # Month to index mapping
    MONTH_TO_IDX = {
        'Rice': {month: idx for idx, month in enumerate(RICE_MONTHS)},
        'Wheat': {month: idx for idx, month in enumerate(WHEAT_MONTHS)},
    }
    
    # Growing seasons (month numbers)
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
    
    # Growth stages by month
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
        """Determine current growing season based on date."""
        month = datetime.now().month
        if month in cls.RICE_SEASON['months']:
            return 'Rice'
        else:
            return 'Wheat'
    
    @classmethod
    def get_season_for_month(cls, month: int) -> str:
        """Determine season for a specific month."""
        if month in cls.RICE_SEASON['months']:
            return 'Rice'
        else:
            return 'Wheat'
    
    @classmethod
    def get_growth_stage(cls, crop: str, month: int) -> str:
        """Get growth stage for a crop in a given month."""
        if crop == 'Rice':
            return cls.RICE_GROWTH_STAGES.get(month, 'Off-season')
        elif crop == 'Wheat':
            return cls.WHEAT_GROWTH_STAGES.get(month, 'Off-season')
        return 'Unknown'
    
    @classmethod
    def get_valid_crops_for_season(cls, month: int) -> List[str]:
        """
        Get valid crop classes for a given month/season.
        
        Args:
            month: Month number (1-12)
            
        Returns:
            List of valid crop classes for classification
        """
        if month in cls.RICE_SEASON['months']:
            # Rice season: Can classify Rice or Other (NOT Wheat)
            return ['Rice', 'Other']
        else:
            # Wheat season: Can classify Wheat or Other (NOT Rice)
            return ['Wheat', 'Other']
    
    @classmethod
    def is_crop_valid_for_season(cls, crop: str, month: int) -> Tuple[bool, str]:
        """
        Check if a crop classification is valid for the given season.
        
        Args:
            crop: Predicted crop class
            month: Month of analysis
            
        Returns:
            Tuple of (is_valid, reason_message)
        """
        valid_crops = cls.get_valid_crops_for_season(month)
        season = cls.get_season_for_month(month)
        
        if crop in valid_crops:
            return True, f"{crop} is valid for {season} season"
        else:
            return False, f"{crop} cannot be grown during {season} season (Month: {month})"
    
    @classmethod
    def get_season_info(cls, month: int = None) -> Dict:
        """
        Get detailed season information.
        
        Args:
            month: Month number (default: current month)
            
        Returns:
            Dictionary with season details
        """
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
    
    # Cloud masking
    CLOUD_FILTER_PERCENT = 50  # Max cloud cover percentage
    
    # Scale (resolution in meters)
    SCALE = 10  # Sentinel-2 resolution
    
    # Region of interest buffer (meters)
    BUFFER_SIZE = 320  # ~64 pixels at 10m resolution (for 64x64 image)
    
    # Punjab, Pakistan bounding box (approximate)
    PUNJAB_BOUNDS = {
        'min_lon': 69.5,
        'max_lon': 75.5,
        'min_lat': 28.0,
        'max_lat': 34.0,
    }
    
    @classmethod
    def is_in_punjab(cls, lat: float, lon: float) -> bool:
        """Check if coordinates are within Punjab region."""
        return (cls.PUNJAB_BOUNDS['min_lat'] <= lat <= cls.PUNJAB_BOUNDS['max_lat'] and
                cls.PUNJAB_BOUNDS['min_lon'] <= lon <= cls.PUNJAB_BOUNDS['max_lon'])


# ─────────────────────────────────────────────────────────────────────────────
# NDVI THRESHOLDS FOR HEALTH ASSESSMENT
# ─────────────────────────────────────────────────────────────────────────────

class HealthConfig:
    """NDVI thresholds for crop health assessment."""
    
    # NDVI calculation
    # NDVI = (NIR - Red) / (NIR + Red) = (B8 - B4) / (B8 + B4)
    
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
    """Advisory system settings and recommendations database."""
    
    # Stress types
    STRESS_TYPES = [
        'water_stress',
        'nutrient_deficiency',
        'pest_disease',
        'general',
    ]
    
    # Rice recommendations by stress type and growth stage
    RICE_ADVISORY = {
        'water_stress': {
            'Transplanting': [
                "Maintain 2-5 cm standing water in the field",
                "Ensure proper bund maintenance to prevent water loss",
                "If water shortage, prioritize irrigation for this critical stage",
            ],
            'Tillering': [
                "Maintain 5 cm water depth during active tillering",
                "Apply Alternate Wetting and Drying (AWD) technique if water is limited",
                "Drain field briefly to promote root growth, then re-flood",
            ],
            'Flowering / Grain Filling': [
                "This is the most critical stage for water - do not let field dry",
                "Maintain 5-7 cm water depth during flowering",
                "Water stress now will significantly reduce grain yield",
            ],
            'Grain Filling / Maturity': [
                "Gradually reduce water supply",
                "Drain field 10-15 days before expected harvest",
                "Monitor for moisture stress if leaves roll during midday",
            ],
        },
        'nutrient_deficiency': {
            'Transplanting': [
                "Apply basal dose: DAP 50 kg/acre or NPK as per soil test",
                "Ensure proper incorporation of fertilizer before transplanting",
                "Zinc deficiency common in rice - apply Zinc Sulfate 5 kg/acre if needed",
            ],
            'Tillering': [
                "Apply first nitrogen top-dressing: Urea 35-40 kg/acre",
                "Apply in standing water for better absorption",
                "Yellow leaves indicate nitrogen deficiency - increase urea dose",
            ],
            'Flowering / Grain Filling': [
                "Apply final nitrogen dose: Urea 25-30 kg/acre",
                "Potassium important now - apply MOP 25 kg/acre if deficient",
                "Foliar application of micronutrients can help if deficiency symptoms visible",
            ],
        },
        'pest_disease': {
            'Tillering': [
                "Monitor for Stem Borer - look for dead hearts",
                "Check for Brown Plant Hopper (BPH) at plant base",
                "Apply Cartap Hydrochloride or Fipronil if pest threshold exceeded",
            ],
            'Flowering / Grain Filling': [
                "Watch for Rice Blast - diamond-shaped lesions on leaves",
                "BPH attack common - check for honeydew and sooty mold",
                "Apply Tricyclazole for blast, Imidacloprid for BPH",
            ],
        },
    }
    
    # Wheat recommendations by stress type and growth stage
    WHEAT_ADVISORY = {
        'water_stress': {
            'Sowing / Germination': [
                "Apply pre-sowing irrigation (rauni) for proper germination",
                "Soil moisture at sowing should be at field capacity",
                "If late sowing, ensure adequate moisture for quick emergence",
            ],
            'Tillering': [
                "First irrigation critical - apply 21-25 days after sowing",
                "Water stress now reduces tiller number significantly",
                "Apply irrigation when soil moisture drops below 50% field capacity",
            ],
            'Heading / Flowering': [
                "Most critical stage for irrigation - do not skip",
                "Apply irrigation at boot/heading stage (75-80 days after sowing)",
                "Water stress now directly reduces grain number and yield",
            ],
            'Grain Filling / Maturity': [
                "Apply last irrigation during milking stage",
                "Avoid irrigation after hard dough stage",
                "Late irrigation can delay maturity and cause lodging",
            ],
        },
        'nutrient_deficiency': {
            'Sowing / Germination': [
                "Apply basal dose: DAP 50 kg/acre + Urea 25 kg/acre",
                "Phosphorus critical for root development",
                "In zinc-deficient soils, apply Zinc Sulfate 5 kg/acre",
            ],
            'Tillering': [
                "Apply first nitrogen top-dressing: Urea 50 kg/acre",
                "Apply with first irrigation for best results",
                "Pale yellow color indicates nitrogen deficiency",
            ],
            'Heading / Flowering': [
                "Apply remaining nitrogen: Urea 25 kg/acre",
                "Foliar spray of 2% urea if deficiency symptoms visible",
                "Potassium spray can improve grain quality",
            ],
        },
        'pest_disease': {
            'Tillering': [
                "Monitor for aphids on lower leaves",
                "Check for Yellow Rust - yellow pustules on leaves",
                "Apply Imidacloprid for aphids if threshold exceeded",
            ],
            'Heading / Flowering': [
                "Critical period for rust diseases",
                "Apply Propiconazole or Tebuconazole for rust control",
                "Monitor for Karnal Bunt in humid conditions",
            ],
        },
    }
    
    # General recommendations (when crop type is 'Other' or unknown)
    GENERAL_ADVISORY = {
        'healthy': [
            "Crop appears healthy - continue regular monitoring",
            "Maintain current management practices",
            "Scout for any early signs of pest or disease",
        ],
        'moderate_stress': [
            "Crop showing signs of stress - investigate cause",
            "Check soil moisture levels",
            "Inspect for pest or disease symptoms",
            "Review recent weather conditions for possible causes",
        ],
        'severe_stress': [
            "Immediate attention required",
            "Check irrigation system and water availability",
            "Inspect closely for pest infestation or disease",
            "Consider soil testing if nutrient deficiency suspected",
            "Consult local agricultural extension officer",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# UI CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class UIConfig:
    """User interface settings."""
    
    # App metadata
    APP_TITLE = "🌾 AI-Driven Agricultural Field Monitoring and Farmer Advisory System"
    APP_SUBTITLE = "AI-Powered Agricultural Monitoring for Pakistan using Remote Sensing"
    APP_VERSION = "1.0.0"  # Updated version
    
    # Map settings
    DEFAULT_CENTER = [31.5, 73.0]  # Punjab center
    DEFAULT_ZOOM = 8
    
    # Color scheme
    COLORS = {
        'rice': '#27ae60',      # Green
        'wheat': '#f39c12',     # Orange
        'other': '#3498db',     # Blue
        'healthy': '#2ecc71',   # Light green
        'moderate': '#f1c40f',  # Yellow
        'severe': '#e74c3c',    # Red
    }
    
    # Confidence display
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