# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PAKISTAN CROP CLASSIFICATION SYSTEM - HEALTH ASSESSMENT                   ║
# ║  NDVI-based crop health analysis                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

from config import HealthConfig, TemporalConfig, ModelConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthAssessment:
    """
    Crop health assessment based on NDVI values.
    Compares current NDVI against expected thresholds for crop type and growth stage.
    """
    
    def __init__(self):
        """Initialize health assessment module."""
        self.health_config = HealthConfig
        self.temporal_config = TemporalConfig
    
    def calculate_ndvi(self, nir: np.ndarray, red: np.ndarray) -> float:
        """
        Calculate NDVI from NIR and Red bands.
        
        NDVI = (NIR - Red) / (NIR + Red)
        
        Args:
            nir: NIR band array (B8)
            red: Red band array (B4)
            
        Returns:
            Mean NDVI value
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            ndvi = (nir - red) / (nir + red + 1e-10)
            ndvi = np.clip(ndvi, -1, 1)
            mean_ndvi = float(np.nanmean(ndvi))
        
        return mean_ndvi
    
    def calculate_ndvi_from_image(self, 
                                   image: np.ndarray, 
                                   availability: list) -> Optional[float]:
        """
        Calculate NDVI from temporal image stack.
        Uses the latest available month's data.
        
        Args:
            image: Array of shape (channels, height, width)
            availability: List indicating available months
            
        Returns:
            Mean NDVI or None if no data available
        """
        # Find latest available month
        for i in range(ModelConfig.NUM_MONTHS - 1, -1, -1):
            if availability[i] == 1:
                start_ch = i * ModelConfig.NUM_BANDS
                
                # Extract Red (B4) and NIR (B8)
                # Band order: B2, B3, B4, B8 (indices 0, 1, 2, 3)
                red = image[start_ch + 2]  # B4
                nir = image[start_ch + 3]  # B8
                
                return self.calculate_ndvi(nir, red)
        
        return None
    
    def get_health_status(self, 
                          ndvi: float, 
                          crop: str, 
                          growth_stage: str) -> Dict:
        """
        Determine health status based on NDVI, crop type, and growth stage.
        
        Args:
            ndvi: Current NDVI value
            crop: Crop type ('Rice', 'Wheat', or 'Other')
            growth_stage: Current growth stage
            
        Returns:
            Dictionary with health assessment results
        """
        # Get thresholds for this crop and stage
        thresholds = self.health_config.get_ndvi_thresholds(crop, growth_stage)
        
        healthy_min = thresholds['healthy_min']
        stress_threshold = thresholds['stress_threshold']
        expected_range = thresholds['expected_range']
        
        # Determine health status
        if ndvi >= healthy_min:
            status = 'healthy'
            status_label = HealthConfig.HEALTH_STATUS['healthy']
            severity = 0
        elif ndvi >= stress_threshold:
            status = 'moderate_stress'
            status_label = HealthConfig.HEALTH_STATUS['moderate_stress']
            severity = 1
        elif ndvi >= stress_threshold * 0.7:
            status = 'severe_stress'
            status_label = HealthConfig.HEALTH_STATUS['severe_stress']
            severity = 2
        else:
            status = 'critical'
            status_label = HealthConfig.HEALTH_STATUS['critical']
            severity = 3
        
        # Calculate deviation from expected
        expected_mid = (expected_range[0] + expected_range[1]) / 2
        deviation = ((ndvi - expected_mid) / expected_mid) * 100
        
        # Interpret NDVI in general terms
        general_interpretation = self._interpret_ndvi_general(ndvi)
        
        result = {
            'status': status,
            'status_label': status_label,
            'severity': severity,
            'current_ndvi': ndvi,
            'healthy_threshold': healthy_min,
            'stress_threshold': stress_threshold,
            'expected_range': expected_range,
            'deviation_percent': deviation,
            'general_interpretation': general_interpretation,
            'crop': crop,
            'growth_stage': growth_stage,
        }
        
        logger.info(f"Health assessment: {status_label} (NDVI: {ndvi:.3f})")
        
        return result
    
    def _interpret_ndvi_general(self, ndvi: float) -> str:
        """
        Provide general interpretation of NDVI value.
        
        Args:
            ndvi: NDVI value
            
        Returns:
            Human-readable interpretation
        """
        if ndvi < 0.1:
            return "Bare soil or water - no active vegetation"
        elif ndvi < 0.2:
            return "Sparse vegetation - very low plant density"
        elif ndvi < 0.4:
            return "Moderate vegetation - developing crop"
        elif ndvi < 0.6:
            return "Dense vegetation - healthy growing crop"
        else:
            return "Very dense, healthy vegetation - peak growth"
    
    def analyze_temporal_trend(self, 
                                image: np.ndarray, 
                                availability: list,
                                crop: str) -> Dict:
        """
        Analyze NDVI trend over available months.
        
        Args:
            image: Temporal image stack
            availability: List indicating available months
            crop: Crop type
            
        Returns:
            Temporal analysis results
        """
        ndvi_values = []
        months_with_data = []
        
        # Get month names based on crop
        if crop == 'Rice':
            month_names = TemporalConfig.RICE_MONTHS
        else:
            month_names = TemporalConfig.WHEAT_MONTHS
        
        # Calculate NDVI for each available month
        for i in range(ModelConfig.NUM_MONTHS):
            if availability[i] == 1:
                start_ch = i * ModelConfig.NUM_BANDS
                red = image[start_ch + 2]
                nir = image[start_ch + 3]
                
                ndvi = self.calculate_ndvi(nir, red)
                ndvi_values.append(ndvi)
                months_with_data.append(month_names[i])
        
        if len(ndvi_values) < 2:
            return {
                'trend': 'insufficient_data',
                'trend_description': 'Not enough data points for trend analysis',
                'ndvi_values': ndvi_values,
                'months': months_with_data,
            }
        
        # Calculate trend
        ndvi_diff = ndvi_values[-1] - ndvi_values[0]
        avg_change = ndvi_diff / len(ndvi_values)
        
        if ndvi_diff > 0.1:
            trend = 'improving'
            trend_description = f"NDVI increasing (+{ndvi_diff:.2f}) - crop vigor improving"
        elif ndvi_diff < -0.1:
            trend = 'declining'
            trend_description = f"NDVI decreasing ({ndvi_diff:.2f}) - possible stress or natural senescence"
        else:
            trend = 'stable'
            trend_description = "NDVI stable - consistent crop condition"
        
        # Check for anomalies
        ndvi_std = np.std(ndvi_values)
        anomalies = []
        for i, (month, ndvi) in enumerate(zip(months_with_data, ndvi_values)):
            if i > 0:
                change = ndvi - ndvi_values[i-1]
                if abs(change) > 0.2:
                    anomalies.append({
                        'month': month,
                        'change': change,
                        'type': 'sudden_increase' if change > 0 else 'sudden_decrease'
                    })
        
        return {
            'trend': trend,
            'trend_description': trend_description,
            'ndvi_values': ndvi_values,
            'months': months_with_data,
            'average_ndvi': float(np.mean(ndvi_values)),
            'ndvi_std': float(ndvi_std),
            'total_change': float(ndvi_diff),
            'anomalies': anomalies,
        }
    
    def assess(self,
               image: np.ndarray = None,
               availability: list = None,
               ndvi: float = None,
               crop: str = None,
               growth_stage: str = None,
               month: int = None) -> Dict:
        """
        Complete health assessment.
        
        Args:
            image: Temporal image stack (optional if ndvi provided)
            availability: Month availability list
            ndvi: Pre-calculated NDVI (optional)
            crop: Crop type
            growth_stage: Growth stage (optional, derived from month if not provided)
            month: Current month (1-12)
            
        Returns:
            Complete health assessment dictionary
        """
        # Calculate NDVI if not provided
        if ndvi is None:
            if image is not None and availability is not None:
                ndvi = self.calculate_ndvi_from_image(image, availability)
            else:
                raise ValueError("Either ndvi or (image + availability) must be provided")
        
        if ndvi is None:
            return {
                'error': 'Could not calculate NDVI - no valid data',
                'status': 'unknown',
            }
        
        # Get growth stage if not provided
        if growth_stage is None and crop is not None and month is not None:
            growth_stage = TemporalConfig.get_growth_stage(crop, month)
        
        if growth_stage is None:
            growth_stage = 'Unknown'
        
        if crop is None:
            crop = 'Other'
        
        # Get health status
        health_result = self.get_health_status(ndvi, crop, growth_stage)
        
        # Add temporal analysis if image data available
        if image is not None and availability is not None:
            temporal_analysis = self.analyze_temporal_trend(image, availability, crop)
            health_result['temporal_analysis'] = temporal_analysis
        
        # Add recommendations summary
        health_result['needs_attention'] = health_result['severity'] > 0
        health_result['priority'] = self._get_priority(health_result['severity'])
        
        return health_result
    
    def _get_priority(self, severity: int) -> str:
        """Convert severity to priority level."""
        priority_map = {
            0: 'low',
            1: 'medium',
            2: 'high',
            3: 'critical'
        }
        return priority_map.get(severity, 'unknown')


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def create_health_assessor() -> HealthAssessment:
    """Factory function to create HealthAssessment instance."""
    return HealthAssessment()


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Health Assessment Module...")
    
    assessor = HealthAssessment()
    
    # Test scenarios
    test_cases = [
        {'ndvi': 0.65, 'crop': 'Rice', 'stage': 'Flowering / Grain Filling'},
        {'ndvi': 0.45, 'crop': 'Rice', 'stage': 'Flowering / Grain Filling'},
        {'ndvi': 0.30, 'crop': 'Rice', 'stage': 'Flowering / Grain Filling'},
        {'ndvi': 0.55, 'crop': 'Wheat', 'stage': 'Heading / Flowering'},
        {'ndvi': 0.35, 'crop': 'Wheat', 'stage': 'Heading / Flowering'},
    ]
    
    print("\n" + "="*70)
    for i, test in enumerate(test_cases, 1):
        result = assessor.get_health_status(
            test['ndvi'], 
            test['crop'], 
            test['stage']
        )
        
        print(f"\nTest {i}: {test['crop']} - {test['stage']}")
        print(f"  NDVI: {test['ndvi']:.2f}")
        print(f"  Status: {result['status_label']}")
        print(f"  Expected Range: {result['expected_range']}")
        print(f"  Deviation: {result['deviation_percent']:.1f}%")
    
    print("\n" + "="*70)
    print("Health Assessment module tests complete!")
