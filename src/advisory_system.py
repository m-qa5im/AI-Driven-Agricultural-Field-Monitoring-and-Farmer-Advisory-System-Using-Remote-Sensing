# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                             ADVISORY SYSTEM                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

from typing import Dict, List, Optional
from datetime import datetime
import logging

from config import AdvisoryConfig, TemporalConfig, HealthConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvisorySystem:
    """
    Generates actionable recommendations for farmers based on:
    - Crop type
    - Growth stage
    - Health status
    - NDVI values
    
    Future enhancement: Weather API integration for weather-based recommendations
    """
    
    def __init__(self):
        """Initialize advisory system."""
        self.advisory_config = AdvisoryConfig
        self.temporal_config = TemporalConfig
    
    def _get_stress_type(self, health_result: Dict) -> str:
        """
        Infer most likely stress type from health assessment.
        
        In a production system, this could use additional indicators like:
        - Spectral indices (chlorophyll, water stress indices)
        - Weather data
        - Historical patterns
        
        For now, uses simplified heuristics.
        """
        ndvi = health_result.get('current_ndvi', 0)
        deviation = health_result.get('deviation_percent', 0)
        
        # Simple heuristic - in production, this would be more sophisticated
        if deviation < -20:
            return 'water_stress'  # Large negative deviation often indicates water stress
        elif deviation < -10:
            return 'nutrient_deficiency'  # Moderate deviation may indicate nutrients
        else:
            return 'general'
    
    def _get_rice_recommendations(self, 
                                   growth_stage: str, 
                                   stress_type: str,
                                   severity: int) -> List[str]:
        """Get recommendations specific to rice crop."""
        recommendations = []
        
        # Get stress-specific recommendations
        if stress_type in AdvisoryConfig.RICE_ADVISORY:
            stage_recommendations = AdvisoryConfig.RICE_ADVISORY[stress_type]
            if growth_stage in stage_recommendations:
                recommendations.extend(stage_recommendations[growth_stage])
        
        # Add severity-based general recommendations
        if severity >= 2:  # Severe or critical
            recommendations.extend([
                "🚨 Immediate field inspection recommended",
                "Consider consulting local agricultural extension officer",
                "Document affected areas for insurance/support purposes",
            ])
        
        # Add growth-stage specific general advice
        stage_advice = self._get_rice_stage_advice(growth_stage)
        recommendations.extend(stage_advice)
        
        return recommendations
    
    def _get_wheat_recommendations(self, 
                                    growth_stage: str, 
                                    stress_type: str,
                                    severity: int) -> List[str]:
        """Get recommendations specific to wheat crop."""
        recommendations = []
        
        # Get stress-specific recommendations
        if stress_type in AdvisoryConfig.WHEAT_ADVISORY:
            stage_recommendations = AdvisoryConfig.WHEAT_ADVISORY[stress_type]
            if growth_stage in stage_recommendations:
                recommendations.extend(stage_recommendations[growth_stage])
        
        # Add severity-based general recommendations
        if severity >= 2:
            recommendations.extend([
                "🚨 Immediate field inspection recommended",
                "Consider consulting local agricultural extension officer",
                "Check for visual symptoms of disease or pest damage",
            ])
        
        # Add growth-stage specific general advice
        stage_advice = self._get_wheat_stage_advice(growth_stage)
        recommendations.extend(stage_advice)
        
        return recommendations
    
    def _get_rice_stage_advice(self, growth_stage: str) -> List[str]:
        """Get general advice for rice growth stage."""
        advice = {
            'Land Preparation / Nursery': [
                "Ensure nursery bed is well-leveled and puddled",
                "Use certified seed at 20-25 kg/acre for nursery",
            ],
            'Transplanting': [
                "Transplant 25-30 day old seedlings",
                "Maintain 2-3 seedlings per hill, 20×15 cm spacing",
            ],
            'Tillering': [
                "This is the critical stage for yield determination",
                "Monitor for stem borer damage (dead hearts)",
            ],
            'Tillering / Panicle Initiation': [
                "Nitrogen application critical at panicle initiation",
                "Maintain adequate water level",
            ],
            'Flowering / Grain Filling': [
                "Avoid water stress - most critical stage",
                "Monitor for neck blast disease",
            ],
            'Grain Filling / Maturity': [
                "Begin draining field 10-15 days before harvest",
                "Monitor grain moisture for harvest timing",
            ],
            'Harvesting': [
                "Harvest when 80-85% grains are golden yellow",
                "Avoid delays to prevent shattering losses",
            ],
        }
        return advice.get(growth_stage, [])
    
    def _get_wheat_stage_advice(self, growth_stage: str) -> List[str]:
        """Get general advice for wheat growth stage."""
        advice = {
            'Sowing / Germination': [
                "Optimal sowing time: Nov 1-20 for timely varieties",
                "Use seed rate 40-50 kg/acre",
            ],
            'Seedling / Crown Root': [
                "First irrigation 21-25 days after sowing (crown root stage)",
                "Monitor for termite damage in sandy soils",
            ],
            'Tillering': [
                "Critical stage for yield potential",
                "Apply first nitrogen dose with irrigation",
            ],
            'Stem Extension / Booting': [
                "Monitor for rust diseases in humid conditions",
                "Second irrigation at jointing stage",
            ],
            'Heading / Flowering': [
                "Most critical stage for grain number",
                "Avoid any stress during this period",
            ],
            'Grain Filling / Maturity': [
                "Last irrigation at milking stage",
                "Monitor for lodging in high-yielding varieties",
            ],
        }
        return advice.get(growth_stage, [])
    
    def _get_general_recommendations(self, status: str, severity: int) -> List[str]:
        """Get general recommendations when crop type is unknown."""
        return AdvisoryConfig.GENERAL_ADVISORY.get(status, [
            "Continue monitoring crop condition",
            "Consult local agricultural expert if concerned",
        ])
    
    def _format_recommendation(self, 
                                recommendation: str, 
                                priority: str) -> Dict:
        """Format a single recommendation with metadata."""
        # Assign icon based on content
        if recommendation and ('🚨' in recommendation or 'immediate' in recommendation.lower()):
            icon = '🚨'
            rec_priority = 'high'
        elif recommendation and ('monitor' in recommendation.lower() or 'check' in recommendation.lower()):
            icon = '👁️'
            rec_priority = 'medium'
        elif recommendation and ('apply' in recommendation.lower() or 'use' in recommendation.lower()):
            icon = '💧' if recommendation and ('water' in recommendation.lower() or 'irrigation' in recommendation.lower()) else '🌿'
            rec_priority = 'medium'
        else:
            icon = '📋'
            rec_priority = 'low'
        
        return {
            'text': recommendation.replace('🚨', '').strip(),
            'icon': icon,
            'priority': rec_priority,
        }
    
    def generate_advisory(self,
                          crop: str,
                          growth_stage: str,
                          health_result: Dict,
                          include_general: bool = True) -> Dict:
        """
        Generate comprehensive advisory based on crop and health assessment.
        
        Args:
            crop: Crop type ('Rice', 'Wheat', 'Other')
            growth_stage: Current growth stage
            health_result: Health assessment dictionary
            include_general: Include general stage-specific advice
            
        Returns:
            Advisory dictionary with recommendations
        """
        status = health_result.get('status', 'unknown')
        severity = health_result.get('severity', 0)
        ndvi = health_result.get('current_ndvi', 0)
        
        # Determine stress type
        stress_type = self._get_stress_type(health_result)
        
        # Get crop-specific recommendations
        if crop == 'Rice':
            recommendations = self._get_rice_recommendations(growth_stage, stress_type, severity)
        elif crop == 'Wheat':
            recommendations = self._get_wheat_recommendations(growth_stage, stress_type, severity)
        else:
            recommendations = self._get_general_recommendations(status, severity)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        # Format recommendations
        formatted_recommendations = [
            self._format_recommendation(rec, health_result.get('priority', 'low'))
            for rec in unique_recommendations
        ]
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        formatted_recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        # Generate summary
        summary = self._generate_summary(crop, growth_stage, status, ndvi)
        
        # Create action plan
        action_plan = self._create_action_plan(formatted_recommendations, severity)
        
        advisory = {
            'summary': summary,
            'crop': crop,
            'growth_stage': growth_stage,
            'health_status': status,
            'stress_type': stress_type,
            'recommendations': formatted_recommendations,
            'action_plan': action_plan,
            'total_recommendations': len(formatted_recommendations),
            'high_priority_count': sum(1 for r in formatted_recommendations if r['priority'] == 'high'),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        logger.info(f"Generated advisory with {len(formatted_recommendations)} recommendations")
        
        return advisory
    
    def _generate_summary(self, 
                          crop: str, 
                          growth_stage: str, 
                          status: str, 
                          ndvi: float) -> str:
        """Generate a brief summary of the situation."""
        status_text = {
            'healthy': 'is healthy and developing normally',
            'moderate_stress': 'is showing signs of moderate stress',
            'severe_stress': 'is experiencing severe stress',
            'critical': 'is in critical condition',
        }
        
        base_summary = f"Your {(crop.lower() if crop else 'unknown')} crop at {(growth_stage.lower() if growth_stage else 'unknown')} stage {status_text.get(status, 'needs attention')}."
        
        if status == 'healthy':
            return f"{base_summary} Current NDVI ({ndvi:.2f}) indicates good vegetation health. Continue regular monitoring."
        elif status == 'moderate_stress':
            return f"{base_summary} Current NDVI ({ndvi:.2f}) is below optimal. Review recommendations below."
        else:
            return f"{base_summary} Current NDVI ({ndvi:.2f}) indicates significant issues. Immediate action recommended."
    
    def _create_action_plan(self, 
                            recommendations: List[Dict], 
                            severity: int) -> Dict:
        """Create a structured action plan."""
        immediate_actions = [r['text'] for r in recommendations if r['priority'] == 'high']
        short_term_actions = [r['text'] for r in recommendations if r['priority'] == 'medium'][:3]
        monitoring_actions = [r['text'] for r in recommendations if r['priority'] == 'low'][:2]
        
        if severity >= 2:
            timeframe = "Take immediate action within 24-48 hours"
        elif severity == 1:
            timeframe = "Address within the next 3-5 days"
        else:
            timeframe = "Continue regular monitoring schedule"
        
        return {
            'timeframe': timeframe,
            'immediate': immediate_actions,
            'short_term': short_term_actions,
            'monitoring': monitoring_actions,
        }
    
    def get_quick_tips(self, crop: str, month: int) -> List[str]:
        """
        Get quick seasonal tips for a crop.
        Useful for general guidance even without health assessment.
        
        Args:
            crop: Crop type
            month: Current month (1-12)
            
        Returns:
            List of quick tips
        """
        growth_stage = TemporalConfig.get_growth_stage(crop, month)
        
        tips = []
        
        if crop == 'Rice':
            tips = self._get_rice_stage_advice(growth_stage)
        elif crop == 'Wheat':
            tips = self._get_wheat_stage_advice(growth_stage)
        
        if not tips:
            tips = [
                "Monitor crop condition regularly",
                "Ensure adequate irrigation based on weather",
                "Scout for pests and diseases weekly",
            ]
        
        return tips


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER INTEGRATION PLACEHOLDER
# ─────────────────────────────────────────────────────────────────────────────

class WeatherAdvisory:
    """
    Placeholder for weather-based recommendations.
    To be implemented with Weather API integration.
    """
    
    def __init__(self, api_key: str = None):
        """Initialize weather advisory (placeholder)."""
        self.api_key = api_key
        self.enabled = False
        logger.info("Weather advisory initialized (API integration pending)")
    
    def get_weather_recommendations(self, 
                                     latitude: float, 
                                     longitude: float,
                                     crop: str) -> List[str]:
        """
        Get weather-based recommendations.
        Placeholder - returns empty list until weather API is integrated.
        """
        if not self.enabled:
            return []
        
        return []


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def create_advisory_system() -> AdvisorySystem:
    """Factory function to create AdvisorySystem instance."""
    return AdvisorySystem()


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Advisory System...")
    
    advisor = AdvisorySystem()
    
    # Test scenarios
    test_cases = [
        {
            'crop': 'Rice',
            'growth_stage': 'Flowering / Grain Filling',
            'health_result': {
                'status': 'moderate_stress',
                'severity': 1,
                'current_ndvi': 0.45,
                'deviation_percent': -15,
                'priority': 'medium',
            }
        },
        {
            'crop': 'Wheat',
            'growth_stage': 'Heading / Flowering',
            'health_result': {
                'status': 'severe_stress',
                'severity': 2,
                'current_ndvi': 0.35,
                'deviation_percent': -25,
                'priority': 'high',
            }
        },
        {
            'crop': 'Rice',
            'growth_stage': 'Tillering',
            'health_result': {
                'status': 'healthy',
                'severity': 0,
                'current_ndvi': 0.55,
                'deviation_percent': 5,
                'priority': 'low',
            }
        },
    ]
    
    print("\n" + "="*70)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {test['crop']} - {test['growth_stage']}")
        print(f"Health Status: {test['health_result']['status']}")
        print("="*70)
        
        advisory = advisor.generate_advisory(
            test['crop'],
            test['growth_stage'],
            test['health_result']
        )
        
        print(f"\n📋 Summary:")
        print(f"   {advisory['summary']}")
        
        print(f"\n📝 Recommendations ({advisory['total_recommendations']} total):")
        for rec in advisory['recommendations'][:5]:
            print(f"   {rec['icon']} [{rec['priority'].upper()}] {rec['text']}")
        
        print(f"\n⏱️ Action Plan:")
        print(f"   Timeframe: {advisory['action_plan']['timeframe']}")
        if advisory['action_plan']['immediate']:
            print(f"   Immediate: {advisory['action_plan']['immediate'][0]}")
    
    print("\n" + "="*70)
    print("Advisory System tests complete!")
