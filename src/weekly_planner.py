# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  WEEKLY PLANNER - Irrigation & Fertilization Scheduling                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from config import TemporalConfig

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CROP MANAGEMENT RULES
# ─────────────────────────────────────────────────────────────────────────────

CROP_CONFIG = {
    'Wheat': {
        'stages': {
            11: 'Sowing',
            12: 'Crown Root Initiation (CRI)',
            1: 'Tillering',
            2: 'Booting',
            3: 'Heading/Flowering',
            4: 'Grain Filling/Maturity'
        },
        'irrigation_interval': {
            'Sowing': 10,
            'Crown Root Initiation (CRI)': 21,
            'Tillering': 25,
            'Booting': 30,
            'Heading/Flowering': 20,
            'Grain Filling/Maturity': 25
        },
        'fertilizer_schedule': {
            'Sowing': {'type': 'DAP + Urea (Basal)', 'interval': None},
            'Crown Root Initiation (CRI)': {'type': 'Urea (1st Top Dress)', 'interval': 25},
            'Tillering': {'type': 'Urea + Zinc Sulfate', 'interval': 30},
            'Booting': {'type': 'Potash (if deficient)', 'interval': 35},
            'Heading/Flowering': {'type': 'Foliar Spray (2% Urea)', 'interval': None},
            'Grain Filling/Maturity': {'type': 'None Required', 'interval': None}
        },
        'critical_stages': ['Crown Root Initiation (CRI)', 'Heading/Flowering']
    },
    'Rice': {
        'stages': {
            5: 'Nursery/Land Prep',
            6: 'Transplanting',
            7: 'Tillering',
            8: 'Panicle Initiation',
            9: 'Flowering/Grain Fill',
            10: 'Maturity/Harvest'
        },
        'irrigation_interval': {
            'Nursery/Land Prep': 3,
            'Transplanting': 3,
            'Tillering': 5,
            'Panicle Initiation': 5,
            'Flowering/Grain Fill': 4,
            'Maturity/Harvest': 7
        },
        'fertilizer_schedule': {
            'Nursery/Land Prep': {'type': 'None', 'interval': None},
            'Transplanting': {'type': 'DAP + Zinc Sulfate', 'interval': None},
            'Tillering': {'type': 'Urea (1st Split)', 'interval': 21},
            'Panicle Initiation': {'type': 'Urea (2nd Split)', 'interval': 25},
            'Flowering/Grain Fill': {'type': 'MOP (Potash)', 'interval': 30},
            'Maturity/Harvest': {'type': 'None Required', 'interval': None}
        },
        'critical_stages': ['Transplanting', 'Flowering/Grain Fill']
    }
}


class WeeklyPlanner:
    """Generates weekly irrigation and fertilization plans."""
    
    def __init__(self, crop: str, lat: float, lon: float):
        self.crop = crop
        self.lat = lat
        self.lon = lon
        self.config = CROP_CONFIG.get(crop, CROP_CONFIG['Wheat'])
        self.current_month = datetime.now().month
        self.current_stage = self.config['stages'].get(self.current_month, 'Unknown')
    
    def get_current_stage(self) -> Dict:
        """Get current growth stage information."""
        return {
            'stage': self.current_stage,
            'month': self.current_month,
            'is_critical': self.current_stage in self.config['critical_stages']
        }
    
    def calculate_irrigation_schedule(self, 
                                       last_irrigation_date: str,
                                       weather_forecast: List[Dict],
                                       health_status: str = 'healthy') -> Dict:
        """
        Calculate irrigation schedule for next 7 days.
        
        Args:
            last_irrigation_date: Last irrigation in 'YYYY-MM-DD' format
            weather_forecast: List of daily weather forecasts
            health_status: 'healthy', 'moderate_stress', or 'severe_stress'
        """
        try:
            last_date = datetime.strptime(last_irrigation_date, '%Y-%m-%d')
        except:
            last_date = datetime.now() - timedelta(days=7)
        
        days_since = (datetime.now() - last_date).days
        ideal_interval = self.config['irrigation_interval'].get(self.current_stage, 20)
        
        # Adjust based on health status
        if health_status == 'severe_stress':
            ideal_interval = max(3, ideal_interval - 5)
        elif health_status == 'moderate_stress':
            ideal_interval = max(5, ideal_interval - 3)
        
        days_until_due = ideal_interval - days_since
        
        # Generate 7-day schedule
        schedule = []
        today = datetime.now()
        
        for i in range(7):
            day_date = today + timedelta(days=i)
            day_weather = weather_forecast[i] if i < len(weather_forecast) else {}
            
            rain_expected = day_weather.get('precipitation', 0) > 5 or day_weather.get('precipitation_prob', 0) > 60
            
            # Determine if irrigation needed this day
            days_from_last = days_since + i
            is_due = days_from_last >= ideal_interval
            
            recommendation = 'not_needed'
            reason = ''
            
            if is_due or days_until_due <= i:
                if rain_expected:
                    recommendation = 'skip'
                    reason = f"Rain expected ({day_weather.get('precipitation', 0):.1f}mm)"
                else:
                    recommendation = 'irrigate'
                    reason = f"Due after {ideal_interval} days"
            else:
                reason = f"Not due yet ({ideal_interval - days_from_last} days left)"
            
            schedule.append({
                'date': day_date.strftime('%Y-%m-%d'),
                'day_name': day_date.strftime('%A'),
                'date_formatted': day_date.strftime('%d %b'),
                'recommendation': recommendation,
                'reason': reason,
                'weather': {
                    'temp_max': day_weather.get('temp_max', 'N/A'),
                    'rain': day_weather.get('precipitation', 0),
                    'rain_prob': day_weather.get('precipitation_prob', 0)
                }
            })
        
        # Find best day for irrigation
        best_day = None
        for day in schedule:
            if day['recommendation'] == 'irrigate':
                best_day = day
                break
        
        if not best_day:
            # Find first suitable day
            for day in schedule:
                if day['weather']['rain'] < 5 and day['weather']['rain_prob'] < 50:
                    best_day = day
                    best_day['recommendation'] = 'suggested'
                    break
        
        return {
            'schedule': schedule,
            'best_day': best_day,
            'days_since_last': days_since,
            'ideal_interval': ideal_interval,
            'status': 'overdue' if days_since > ideal_interval else 'on_track',
            'urgency': 'high' if days_since > ideal_interval + 5 else ('medium' if days_since > ideal_interval else 'low')
        }
    
    def calculate_fertilizer_schedule(self,
                                       last_fertilizer_date: str,
                                       health_status: str = 'healthy') -> Dict:
        """
        Calculate fertilizer schedule for next 7 days.
        
        Args:
            last_fertilizer_date: Last fertilization in 'YYYY-MM-DD' format
            health_status: 'healthy', 'moderate_stress', or 'severe_stress'
        """
        try:
            last_date = datetime.strptime(last_fertilizer_date, '%Y-%m-%d')
        except:
            last_date = datetime.now() - timedelta(days=30)
        
        days_since = (datetime.now() - last_date).days
        
        fert_info = self.config['fertilizer_schedule'].get(
            self.current_stage, 
            {'type': 'Routine monitoring', 'interval': None}
        )
        
        recommended_type = fert_info['type']
        ideal_interval = fert_info['interval']
        
        # Generate 7-day schedule
        schedule = []
        today = datetime.now()
        
        for i in range(7):
            day_date = today + timedelta(days=i)
            
            recommendation = 'not_needed'
            reason = ''
            
            if ideal_interval is None:
                reason = 'Not required at this stage'
            elif days_since + i >= ideal_interval:
                recommendation = 'apply'
                reason = f"Due: {recommended_type}"
            else:
                days_left = ideal_interval - (days_since + i)
                reason = f"Not due yet ({days_left} days left)"
            
            # Adjust for health
            if health_status == 'severe_stress' and 'Urea' in recommended_type:
                if i <= 2:
                    recommendation = 'urgent'
                    reason = f"URGENT: {recommended_type} (crop stressed)"
            
            schedule.append({
                'date': day_date.strftime('%Y-%m-%d'),
                'day_name': day_date.strftime('%A'),
                'date_formatted': day_date.strftime('%d %b'),
                'recommendation': recommendation,
                'fertilizer_type': recommended_type if recommendation in ['apply', 'urgent'] else None,
                'reason': reason
            })
        
        # Find best day
        best_day = None
        for day in schedule:
            if day['recommendation'] in ['apply', 'urgent']:
                best_day = day
                break
        
        return {
            'schedule': schedule,
            'best_day': best_day,
            'days_since_last': days_since,
            'recommended_type': recommended_type,
            'ideal_interval': ideal_interval,
            'status': 'due' if (ideal_interval and days_since >= ideal_interval) else 'on_track'
        }
    
    def generate_weekly_plan(self,
                             last_irrigation: str,
                             last_fertilizer: str,
                             weather_forecast: List[Dict],
                             health_status: str = 'healthy',
                             ndvi: float = None) -> Dict:
        """
        Generate complete weekly plan.
        
        Args:
            last_irrigation: Last irrigation date 'YYYY-MM-DD'
            last_fertilizer: Last fertilization date 'YYYY-MM-DD'
            weather_forecast: 7-day weather forecast
            health_status: Crop health status
            ndvi: Current NDVI value
        """
        irrigation = self.calculate_irrigation_schedule(
            last_irrigation, weather_forecast, health_status
        )
        
        fertilizer = self.calculate_fertilizer_schedule(
            last_fertilizer, health_status
        )
        
        # Combine into daily plan
        combined_schedule = []
        for i in range(7):
            irr = irrigation['schedule'][i]
            fert = fertilizer['schedule'][i]
            
            actions = []
            if irr['recommendation'] in ['irrigate', 'suggested']:
                actions.append(f"💧 Irrigate")
            if fert['recommendation'] in ['apply', 'urgent']:
                actions.append(f"🧪 {fert['fertilizer_type']}")
            
            combined_schedule.append({
                'date': irr['date'],
                'day_name': irr['day_name'],
                'date_formatted': irr['date_formatted'],
                'irrigation': irr,
                'fertilizer': fert,
                'actions': actions if actions else ['No action needed'],
                'weather': irr['weather'],
                'priority': 'high' if (irr['recommendation'] == 'irrigate' or fert['recommendation'] == 'urgent') else 'normal'
            })
        
        # Summary
        return {
            'crop': self.crop,
            'stage': self.current_stage,
            'stage_info': self.get_current_stage(),
            'health_status': health_status,
            'ndvi': ndvi,
            'schedule': combined_schedule,
            'irrigation_summary': {
                'best_day': irrigation['best_day'],
                'status': irrigation['status'],
                'urgency': irrigation['urgency'],
                'days_since_last': irrigation['days_since_last']
            },
            'fertilizer_summary': {
                'best_day': fertilizer['best_day'],
                'recommended_type': fertilizer['recommended_type'],
                'status': fertilizer['status'],
                'days_since_last': fertilizer['days_since_last']
            },
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }