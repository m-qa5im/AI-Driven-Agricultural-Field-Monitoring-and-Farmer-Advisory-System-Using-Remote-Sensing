# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  HEALTH ASSESSMENT - NDVI, EVI, SAVI Analysis                              ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

from config import TemporalConfig, HealthConfig

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# VEGETATION INDICES CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

class VegetationIndices:
    """Calculate vegetation indices from satellite bands."""
    
    # Band indices in our 4-band stack: B2(Blue), B3(Green), B4(Red), B8(NIR)
    BLUE = 0
    GREEN = 1
    RED = 2
    NIR = 3
    
    @classmethod
    def calculate_ndvi(cls, red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Normalized Difference Vegetation Index.
        NDVI = (NIR - Red) / (NIR + Red)
        Range: -1 to 1 (healthy vegetation: 0.3-0.8)
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            ndvi = (nir - red) / (nir + red + 1e-10)
            ndvi = np.clip(ndvi, -1, 1)
        return ndvi
    
    @classmethod
    def calculate_evi(cls, blue: np.ndarray, red: np.ndarray, nir: np.ndarray,
                      G: float = 2.5, C1: float = 6.0, C2: float = 7.5, L: float = 1.0) -> np.ndarray:
        """
        Enhanced Vegetation Index.
        EVI = G * (NIR - Red) / (NIR + C1*Red - C2*Blue + L)
        Range: -1 to 1 (more sensitive in high biomass regions)
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            evi = G * (nir - red) / (nir + C1 * red - C2 * blue + L + 1e-10)
            evi = np.clip(evi, -1, 1)
        return evi
    
    @classmethod
    def calculate_savi(cls, red: np.ndarray, nir: np.ndarray, L: float = 0.5) -> np.ndarray:
        """
        Soil Adjusted Vegetation Index.
        SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L)
        Range: -1 to 1 (reduces soil brightness influence)
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            savi = ((nir - red) / (nir + red + L + 1e-10)) * (1 + L)
            savi = np.clip(savi, -1, 1)
        return savi
    
    @classmethod
    def calculate_gndvi(cls, green: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Green Normalized Difference Vegetation Index.
        GNDVI = (NIR - Green) / (NIR + Green)
        Better for chlorophyll content estimation.
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            gndvi = (nir - green) / (nir + green + 1e-10)
            gndvi = np.clip(gndvi, -1, 1)
        return gndvi
    
    @classmethod
    def calculate_ndwi(cls, green: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Normalized Difference Water Index.
        NDWI = (Green - NIR) / (Green + NIR)
        Indicates water content in vegetation.
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            ndwi = (green - nir) / (green + nir + 1e-10)
            ndwi = np.clip(ndwi, -1, 1)
        return ndwi


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH ASSESSOR
# ─────────────────────────────────────────────────────────────────────────────

class HealthAssessor:
    """Comprehensive crop health assessment."""
    
    # Health thresholds by crop and stage
    THRESHOLDS = {
        'Wheat': {
            'Sowing': {'ndvi': (0.10, 0.25), 'healthy_min': 0.15},
            'Crown Root Initiation (CRI)': {'ndvi': (0.20, 0.40), 'healthy_min': 0.25},
            'Tillering': {'ndvi': (0.35, 0.55), 'healthy_min': 0.40},
            'Booting': {'ndvi': (0.45, 0.70), 'healthy_min': 0.50},
            'Heading/Flowering': {'ndvi': (0.50, 0.75), 'healthy_min': 0.55},
            'Grain Filling/Maturity': {'ndvi': (0.35, 0.55), 'healthy_min': 0.40}
        },
        'Rice': {
            'Nursery/Land Prep': {'ndvi': (0.10, 0.25), 'healthy_min': 0.15},
            'Transplanting': {'ndvi': (0.15, 0.30), 'healthy_min': 0.20},
            'Tillering': {'ndvi': (0.35, 0.55), 'healthy_min': 0.40},
            'Panicle Initiation': {'ndvi': (0.45, 0.65), 'healthy_min': 0.50},
            'Flowering/Grain Fill': {'ndvi': (0.50, 0.75), 'healthy_min': 0.55},
            'Maturity/Harvest': {'ndvi': (0.30, 0.50), 'healthy_min': 0.35}
        }
    }
    
    def __init__(self, crop: str):
        self.crop = crop
        self.current_month = datetime.now().month
        self.stage = self._get_stage()
        self.thresholds = self._get_thresholds()
    
    def _get_stage(self) -> str:
        """Get current growth stage."""
        stages = {
            'Wheat': {11: 'Sowing', 12: 'Crown Root Initiation (CRI)', 1: 'Tillering', 
                      2: 'Booting', 3: 'Heading/Flowering', 4: 'Grain Filling/Maturity'},
            'Rice': {5: 'Nursery/Land Prep', 6: 'Transplanting', 7: 'Tillering',
                     8: 'Panicle Initiation', 9: 'Flowering/Grain Fill', 10: 'Maturity/Harvest'}
        }
        return stages.get(self.crop, {}).get(self.current_month, 'Unknown')
    
    def _get_thresholds(self) -> Dict:
        """Get thresholds for current stage."""
        default = {'ndvi': (0.25, 0.55), 'healthy_min': 0.35}
        return self.THRESHOLDS.get(self.crop, {}).get(self.stage, default)
    
    def assess_from_bands(self, band_data: np.ndarray, already_scaled: bool = True) -> Dict:
        
        if not already_scaled:
            band_data = band_data.astype(np.float32) / 10000.0

        # Mask invalid reflectance
        band_data = band_data.copy()
        band_data[(band_data < 0) | (band_data > 1)] = np.nan

        blue = band_data[VegetationIndices.BLUE]
        green = band_data[VegetationIndices.GREEN]
        red = band_data[VegetationIndices.RED]
        nir = band_data[VegetationIndices.NIR]
        
        # Calculate all indices
        ndvi = VegetationIndices.calculate_ndvi(red, nir)
        evi = VegetationIndices.calculate_evi(blue, red, nir)
        savi = VegetationIndices.calculate_savi(red, nir)
        gndvi = VegetationIndices.calculate_gndvi(green, nir)
        ndwi = VegetationIndices.calculate_ndwi(green, nir)
        
        # Calculate statistics (exclude invalid values)
        indices = {
            'ndvi': self._calculate_stats(ndvi),
            'evi': self._calculate_stats(evi),
            'savi': self._calculate_stats(savi),
            'gndvi': self._calculate_stats(gndvi),
            'ndwi': self._calculate_stats(ndwi)
        }
        
        # Determine health status
        health_status = self._determine_health_status(indices['ndvi']['mean'])
        
        # Generate diagnosis
        diagnosis = self._generate_diagnosis(indices, health_status)
        
        return {
            'crop': self.crop,
            'stage': self.stage,
            'month': self.current_month,
            'indices': indices,
            'health_status': health_status,
            'diagnosis': diagnosis,
            'thresholds': self.thresholds,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    def _calculate_stats(self, index_array: np.ndarray) -> Dict:
        """Calculate statistics for an index."""
        valid = index_array[~np.isnan(index_array)]
        if len(valid) == 0:
            return {'mean': 0, 'min': 0, 'max': 0, 'std': 0}
        
        return {
            'mean': float(np.mean(valid)),
            'min': float(np.min(valid)),
            'max': float(np.max(valid)),
            'std': float(np.std(valid))
        }
    
    def _determine_health_status(self, ndvi_mean: float) -> Dict:
        """Determine health status from NDVI."""
        healthy_min = self.thresholds['healthy_min']
        expected_range = self.thresholds['ndvi']
        
        if ndvi_mean >= healthy_min:
            status = 'healthy'
            label = '✅ Healthy'
            color = '#2ecc71'
        elif ndvi_mean >= healthy_min - 0.10:
            status = 'moderate_stress'
            label = '⚠️ Moderate Stress'
            color = '#f1c40f'
        elif ndvi_mean >= healthy_min - 0.20:
            status = 'severe_stress'
            label = '🔴 Severe Stress'
            color = '#e74c3c'
        else:
            status = 'critical'
            label = '❌ Critical'
            color = '#8e44ad'
        
        return {
            'status': status,
            'label': label,
            'color': color,
            'ndvi': ndvi_mean,
            'expected_range': expected_range,
            'is_below_threshold': ndvi_mean < healthy_min
        }
    
    def _generate_diagnosis(self, indices: Dict, health_status: Dict) -> Dict:
        """Generate detailed diagnosis based on indices."""
        issues = []
        recommendations = []
        
        ndvi = indices['ndvi']['mean']
        evi = indices['evi']['mean']
        savi = indices['savi']['mean']
        gndvi = indices['gndvi']['mean']
        ndwi = indices['ndwi']['mean']
        
        # Analyze patterns
        if health_status['status'] in ['severe_stress', 'critical']:
            # Check for water stress
            if ndwi < -0.1:
                issues.append("💧 Water stress detected (low NDWI)")
                recommendations.append("Immediate irrigation recommended")
            
            # Check for chlorophyll issues
            if gndvi < 0.3:
                issues.append("🍃 Low chlorophyll content (low GNDVI)")
                recommendations.append("Consider nitrogen fertilization")
            
            # Soil influence
            if abs(ndvi - savi) > 0.1:
                issues.append("🌍 High soil background influence")
                recommendations.append("Sparse vegetation - check plant density")
        
        elif health_status['status'] == 'moderate_stress':
            if ndwi < 0:
                issues.append("💧 Mild water stress")
                recommendations.append("Monitor soil moisture, irrigate if no rain expected")
            
            if gndvi < ndvi - 0.05:
                issues.append("🍃 Slight chlorophyll reduction")
                recommendations.append("Consider foliar nutrient spray")
        
        else:  # Healthy
            issues.append("✅ No major issues detected")
            recommendations.append("Continue current management practices")
            recommendations.append("Regular monitoring recommended")
        
        # Stage-specific recommendations
        stage_advice = self._get_stage_advice()
        if stage_advice:
            recommendations.append(stage_advice)
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'confidence': 'high' if indices['ndvi']['std'] < 0.15 else 'medium'
        }
    
    def _get_stage_advice(self) -> Optional[str]:
        """Get stage-specific advice."""
        advice = {
            'Wheat': {
                'Sowing': "Ensure adequate soil moisture for germination",
                'Crown Root Initiation (CRI)': "Critical irrigation stage - do not skip",
                'Tillering': "Apply nitrogen fertilizer for tiller development",
                'Booting': "Maintain consistent moisture for head development",
                'Heading/Flowering': "Most water-sensitive stage - ensure irrigation",
                'Grain Filling/Maturity': "Reduce irrigation, prepare for harvest"
            },
            'Rice': {
                'Nursery/Land Prep': "Maintain flooded conditions",
                'Transplanting': "Keep 2-5cm standing water",
                'Tillering': "Apply first nitrogen split",
                'Panicle Initiation': "Critical stage - maintain water level",
                'Flowering/Grain Fill': "Do not let field dry",
                'Maturity/Harvest': "Drain field 10-15 days before harvest"
            }
        }
        return advice.get(self.crop, {}).get(self.stage)


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def assess_crop_health(band_data: np.ndarray, crop: str, already_scaled: bool = True) -> Dict:
    """
    Convenience function for health assessment.
    
    Args:
        band_data: numpy array (4, H, W) with [B2, B3, B4, B8]
        crop: 'Wheat' or 'Rice'
        already_scaled: True if data is already in 0-1 range (from GEE fetcher)
    """
    assessor = HealthAssessor(crop)
    return assessor.assess_from_bands(band_data, already_scaled=already_scaled)


def calculate_simple_indices(red: np.ndarray, nir: np.ndarray, 
                             green: np.ndarray = None, blue: np.ndarray = None) -> Dict:
    """Calculate basic vegetation indices."""
    result = {
        'ndvi': float(np.nanmean(VegetationIndices.calculate_ndvi(red, nir))),
        'savi': float(np.nanmean(VegetationIndices.calculate_savi(red, nir)))
    }
    
    if green is not None:
        result['gndvi'] = float(np.nanmean(VegetationIndices.calculate_gndvi(green, nir)))
        result['ndwi'] = float(np.nanmean(VegetationIndices.calculate_ndwi(green, nir)))
    
    if blue is not None and green is not None:
        result['evi'] = float(np.nanmean(VegetationIndices.calculate_evi(blue, red, nir)))
    
    return result