# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  WEATHER SERVICE - Open-Meteo API Integration                             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """Fetches weather forecast from Open-Meteo API (free, no API key needed)."""
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    @classmethod
    def get_forecast(cls, lat: float, lon: float, days: int = 7) -> Dict:
        
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,windspeed_10m_max,et0_fao_evapotranspiration',
                'timezone': 'auto',
                'forecast_days': min(days, 16)
            }
            
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse daily data
            daily = data.get('daily', {})
            dates = daily.get('time', [])
            
            forecast = []
            for i, date_str in enumerate(dates[:days]):
                forecast.append({
                    'date': date_str,
                    'date_formatted': datetime.strptime(date_str, '%Y-%m-%d').strftime('%a, %d %b'),
                    'temp_max': daily.get('temperature_2m_max', [0])[i],
                    'temp_min': daily.get('temperature_2m_min', [0])[i],
                    'precipitation': daily.get('precipitation_sum', [0])[i] or 0,
                    'precipitation_prob': daily.get('precipitation_probability_max', [0])[i] or 0,
                    'wind_speed': daily.get('windspeed_10m_max', [0])[i] or 0,
                    'evapotranspiration': daily.get('et0_fao_evapotranspiration', [0])[i] or 0,
                })
            
            # Summary for next 3 days
            rain_3d = sum(f['precipitation'] for f in forecast[:3])
            max_temp_3d = max(f['temp_max'] for f in forecast[:3]) if forecast else 0
            avg_rain_prob = sum(f['precipitation_prob'] for f in forecast[:3]) / 3 if forecast else 0
            
            return {
                'success': True,
                'forecast': forecast,
                'summary': {
                    'rain_3d': rain_3d,
                    'max_temp_3d': max_temp_3d,
                    'avg_rain_prob_3d': avg_rain_prob,
                    'rain_expected': rain_3d > 5 or avg_rain_prob > 60,
                },
                'location': {'lat': lat, 'lon': lon}
            }
            
        except Exception as e:
            logger.error(f"Weather API error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'forecast': [],
                'summary': {
                    'rain_3d': 0,
                    'max_temp_3d': 30,
                    'avg_rain_prob_3d': 0,
                    'rain_expected': False,
                }
            }
    
    @classmethod
    def get_conditions_summary(cls, weather_data: Dict) -> Dict:
        """Get human-readable weather conditions."""
        summary = weather_data.get('summary', {})
        
        conditions = []
        irrigation_advice = "proceed"
        
        if summary.get('rain_expected'):
            conditions.append("🌧️ Rain expected")
            irrigation_advice = "delay"
        
        if summary.get('max_temp_3d', 0) > 38:
            conditions.append("🔥 Extreme heat")
            irrigation_advice = "increase"
        elif summary.get('max_temp_3d', 0) > 35:
            conditions.append("☀️ Hot weather")
        
        if summary.get('max_temp_3d', 0) < 5:
            conditions.append("❄️ Frost risk")
            irrigation_advice = "delay"
        
        if not conditions:
            conditions.append("✅ Favorable conditions")
        
        return {
            'conditions': conditions,
            'irrigation_advice': irrigation_advice,
            'description': ", ".join(conditions)
        }