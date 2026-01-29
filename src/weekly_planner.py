# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                           WEEKLY PLANNER                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import numpy as np

from config import TemporalConfig
from health_assessment import HealthAssessor, assess_crop_health

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
    """
    Generates weekly irrigation and fertilization plans.
    
    PRIORITY ORDER (As Per Requirement):
    1. Crop health condition (from vegetation indices)
    2. Days since last application
    3. Weather forecast
    4. Growth stage requirements
    """
    
    def __init__(self, crop: str, lat: float, lon: float):
        self.crop = crop
        self.lat = lat
        self.lon = lon
        self.config = CROP_CONFIG.get(crop, CROP_CONFIG['Wheat'])
        self.current_month = datetime.now().month
        self.current_stage = self.config['stages'].get(self.current_month, 'Unknown')
        self.health_assessor = HealthAssessor(crop)
    
    def get_current_stage(self) -> Dict:
        """Get current growth stage information."""
        return {
            'stage': self.current_stage,
            'month': self.current_month,
            'is_critical': self.current_stage in self.config['critical_stages']
        }
    
    def assess_health_from_indices(self, 
                                   ndvi: float,
                                   evi: Optional[float] = None,
                                   ndwi: Optional[float] = None,
                                   gndvi: Optional[float] = None) -> Dict:
        """
        Assess crop health from vegetation indices.
        
        This is the FIRST STEP - determines urgency level.
        
        Returns:
            Dict with status, urgency, and specific issues
        """
        # Get stage-specific thresholds
        thresholds = self.health_assessor.thresholds
        healthy_min = thresholds['healthy_min']
        expected_range = thresholds['ndvi']
        
        # Determine health status (PRIMARY FACTOR)
        if ndvi >= healthy_min:
            status = 'healthy'
            urgency = 'normal'
            irrigation_priority = 'standard'
            fertilizer_priority = 'standard'
            
        elif ndvi >= healthy_min - 0.10:
            status = 'moderate_stress'
            urgency = 'elevated'
            irrigation_priority = 'high'
            fertilizer_priority = 'medium'
            
        elif ndvi >= healthy_min - 0.20:
            status = 'severe_stress'
            urgency = 'high'
            irrigation_priority = 'urgent'
            fertilizer_priority = 'high'
            
        else:
            status = 'critical'
            urgency = 'critical'
            irrigation_priority = 'immediate'
            fertilizer_priority = 'urgent'
        
        # Analyze specific issues
        issues = []
        
        
        if ndwi is not None:
            if ndwi < -0.2:
                # SEVERE water stress - IMMEDIATE irrigation needed
                issues.append('severe_water_stress')
                irrigation_priority = 'immediate'  # Override everything
                if status == 'healthy':
                    status = 'severe_stress'  # Update status too
                    urgency = 'high'
                    
            elif ndwi < -0.1:
                # MODERATE water stress - HIGH priority irrigation
                issues.append('moderate_water_stress')
                # Upgrade priority if not already urgent/immediate
                if irrigation_priority not in ['urgent', 'immediate']:
                    irrigation_priority = 'high'
                if status == 'healthy' and urgency == 'normal':
                    status = 'moderate_stress'
                    urgency = 'elevated'
                    
            elif ndwi < 0:
                # MILD water stress - elevated monitoring
                issues.append('mild_water_stress')
                if irrigation_priority == 'standard':
                    irrigation_priority = 'high'
        
       
        if gndvi is not None:
            if gndvi < 0.25:
                # SEVERE nutrient deficiency
                issues.append('nutrient_deficiency')
                # Upgrade fertilizer priority
                if fertilizer_priority not in ['urgent', 'high']:
                    fertilizer_priority = 'urgent' if gndvi < 0.20 else 'high'
                    
            elif gndvi < 0.35:
                # MODERATE nutrient stress
                issues.append('mild_nutrient_stress')
                if fertilizer_priority == 'standard':
                    fertilizer_priority = 'medium'
        
        # EVI for biomass issues
        if evi is not None:
            if evi < 0.2 and status in ['severe_stress', 'critical']:
                issues.append('low_biomass')
        
        return {
            'status': status,
            'urgency': urgency,
            'ndvi': ndvi,
            'expected_range': expected_range,
            'healthy_min': healthy_min,
            'deviation': ndvi - healthy_min,
            'irrigation_priority': irrigation_priority,
            'fertilizer_priority': fertilizer_priority,
            'specific_issues': issues,
            'is_critical_stage': self.current_stage in self.config['critical_stages']
        }
    
    def calculate_irrigation_schedule(self, 
                                     last_irrigation_date: str,
                                     weather_forecast: List[Dict],
                                     health_assessment: Dict) -> Dict:
        """
        Calculate irrigation schedule - HEALTH-FIRST APPROACH.
        
        Logic Priority:
        1. Check crop health urgency
        2. Consider days since last irrigation
        3. Factor in weather
        4. Determine best action day
        """
        try:
            last_date = datetime.strptime(last_irrigation_date, '%Y-%m-%d')
        except:
            last_date = datetime.now() - timedelta(days=7)
        
        days_since = (datetime.now() - last_date).days
        ideal_interval = self.config['irrigation_interval'].get(self.current_stage, 20)
        
        # Extract health metrics
        irrigation_priority = health_assessment['irrigation_priority']
        status = health_assessment['status']
        issues = health_assessment['specific_issues']
        
        
        ABSOLUTE_MIN_DAYS = 2  # Physical constraint
        
        if days_since < ABSOLUTE_MIN_DAYS:
            # Recently irrigated - override all urgency levels
            urgency_level = 'none'
            action_deadline = ABSOLUTE_MIN_DAYS - days_since
            reason_base = f"Recently irrigated ({days_since} day(s) ago) - soil still moist"
            can_irrigate = False
        else:
            can_irrigate = True
        
        # ═══════════════════════════════════════════════════════════════
        # DECISION LOGIC - HEALTH FIRST (if irrigation is possible)
        # ═══════════════════════════════════════════════════════════════
        
        if can_irrigate:
            # IMMEDIATE: Critical health or severe water stress
            if irrigation_priority == 'immediate':
                urgency_level = 'immediate'
                action_deadline = 0  # Today or tomorrow
                reason_base = "CRITICAL: Crop severely stressed"
                
            # URGENT: Severe stress or water stress detected
            elif irrigation_priority == 'urgent':
                urgency_level = 'urgent'
                action_deadline = 2  # Within 2 days
                reason_base = "URGENT: Crop health declining"
                
            # HIGH: Moderate stress + significant time passed
            elif irrigation_priority == 'high':
                urgency_level = 'high'
                if days_since >= ideal_interval - 5:
                    action_deadline = 3  # Within 3 days
                else:
                    action_deadline = 5  # Within 5 days
                reason_base = "HIGH PRIORITY: Moderate stress detected"
                
            # STANDARD: Normal scheduling
            else:
                urgency_level = 'normal'
                if days_since >= ideal_interval:
                    action_deadline = 2
                    reason_base = f"Scheduled irrigation (every {ideal_interval} days)"
                else:
                    action_deadline = ideal_interval - days_since
                    reason_base = f"On schedule (next due in {action_deadline} days)"
        
        # Generate 7-day schedule
        schedule = []
        today = datetime.now()
        best_day = None
        
        for i in range(7):
            day_date = today + timedelta(days=i)
            day_weather = weather_forecast[i] if i < len(weather_forecast) else {}
            
            rain_expected = (day_weather.get('precipitation', 0) > 5 or 
                           day_weather.get('precipitation_prob', 0) > 60)
            
            # Determine recommendation for this day
            recommendation = 'not_needed'
            reason = ''
            priority_score = 0
            
            # CRITICAL CHECK: Cannot irrigate if too soon after last irrigation
            if days_since + i < ABSOLUTE_MIN_DAYS:
                recommendation = 'not_possible'
                reason = f"Too soon after last irrigation ({days_since + i} day(s)) - Wait {ABSOLUTE_MIN_DAYS - (days_since + i)} more day(s)"
                priority_score = 0
            
            # IMMEDIATE/URGENT: Override everything (but respect minimum days)
            elif urgency_level in ['immediate', 'urgent'] and i <= action_deadline:
                if rain_expected and i > 0:  # Skip if rain, but not for immediate today
                    recommendation = 'monitor'
                    reason = f"⚠️ {reason_base} but rain expected ({day_weather.get('precipitation', 0):.1f}mm) - Monitor closely"
                    priority_score = 8
                else:
                    recommendation = 'irrigate'
                    reason = f"🔴 {reason_base} - Irrigate despite only {days_since + i} days"
                    priority_score = 10
                    
            # HIGH: Need action soon
            elif urgency_level == 'high' and i <= action_deadline:
                if rain_expected:
                    recommendation = 'skip'
                    reason = f"⚠️ Skip irrigation - adequate rain expected ({day_weather.get('precipitation', 0):.1f}mm)"
                    priority_score = 5
                else:
                    recommendation = 'irrigate'
                    reason = f"💧 {reason_base} - Action recommended"
                    priority_score = 8
            
            # NORMAL: Follow standard schedule
            elif days_since + i >= ideal_interval:
                if rain_expected:
                    recommendation = 'skip'
                    reason = f"Skip - Rain expected ({day_weather.get('precipitation', 0):.1f}mm)"
                    priority_score = 3
                else:
                    recommendation = 'irrigate'
                    reason = f"💧 {reason_base}"
                    priority_score = 6
            
            else:
                reason = f"Not due yet ({ideal_interval - (days_since + i)} days remaining)"
                priority_score = 0
            
            day_info = {
                'date': day_date.strftime('%Y-%m-%d'),
                'day_name': day_date.strftime('%A'),
                'date_formatted': day_date.strftime('%d %b'),
                'recommendation': recommendation,
                'reason': reason,
                'priority_score': priority_score,
                'urgency_level': urgency_level if recommendation in ['irrigate', 'monitor'] else 'none',
                'weather': {
                    'temp_max': day_weather.get('temp_max', 'N/A'),
                    'rain': day_weather.get('precipitation', 0),
                    'rain_prob': day_weather.get('precipitation_prob', 0)
                }
            }
            
            schedule.append(day_info)
            
            # Select best day (highest priority score)
            if best_day is None or priority_score > best_day['priority_score']:
                if recommendation in ['irrigate', 'monitor']:
                    best_day = day_info
        
        # If no urgent action but health is concerning, suggest monitoring
        if best_day is None and status != 'healthy':
            # Find first day after minimum interval
            for day in schedule:
                if day['recommendation'] not in ['not_possible', 'not_needed']:
                    best_day = day
                    break
            
            # If still none found (e.g., just irrigated today), set monitoring message
            if best_day is None:
                best_day = schedule[min(ABSOLUTE_MIN_DAYS, 2)]  # Day 2 or 3
                best_day['recommendation'] = 'monitor'
                if days_since < ABSOLUTE_MIN_DAYS:
                    best_day['reason'] = f'⚠️ Crop stressed but recently irrigated - Monitor closely, re-assess in {ABSOLUTE_MIN_DAYS - days_since} days'
                else:
                    best_day['reason'] = 'Monitor crop health - consider irrigation if no improvement'
        
        return {
            'schedule': schedule,
            'best_day': best_day,
            'days_since_last': days_since,
            'ideal_interval': ideal_interval,
            'health_urgency': urgency_level,
            'status': 'urgent' if urgency_level in ['immediate', 'urgent'] else 
                     ('attention_needed' if urgency_level == 'high' else 'on_track'),
            'health_based_override': urgency_level in ['immediate', 'urgent'],
            'specific_concerns': issues
        }
    
    def calculate_fertilizer_schedule(self,
                                     last_fertilizer_date: str,
                                     health_assessment: Dict) -> Dict:
        """
        Calculate fertilizer schedule - HEALTH-FIRST APPROACH.
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
        
        # ═══════════════════════════════════════════════════════════════
        # MINIMUM CONSTRAINT: Cannot fertilize too soon
        # ═══════════════════════════════════════════════════════════════
        ABSOLUTE_MIN_DAYS_FERT = 5  # Minimum 5 days between fertilizations
        
        if days_since < ABSOLUTE_MIN_DAYS_FERT:
            can_fertilize = False
        else:
            can_fertilize = True
        
        # Extract health metrics
        fertilizer_priority = health_assessment['fertilizer_priority']
        status = health_assessment['status']
        issues = health_assessment['specific_issues']
        
        # ═══════════════════════════════════════════════════════════════
        # FERTILIZER DECISION LOGIC - HEALTH FIRST 
        # ═══════════════════════════════════════════════════════════════
        
        # Check for nutrient deficiency
        has_nutrient_issue = any(issue in issues for issue in 
                                ['nutrient_deficiency', 'mild_nutrient_stress'])
        
        if not can_fertilize:
            # Recently fertilized
            urgency_level = 'none'
            action_deadline = ABSOLUTE_MIN_DAYS_FERT - days_since
            reason_base = f"Recently fertilized ({days_since} day(s) ago) - nutrients still available"
            override_type = None
        else:
            # URGENT: Severe nutrient stress
            if fertilizer_priority == 'urgent' or (has_nutrient_issue and status == 'critical'):
                urgency_level = 'urgent'
                action_deadline = 1  # Within 1-2 days
                reason_base = "URGENT: Nutrient deficiency detected"
                override_type = "Emergency Foliar Feed (NPK + Micronutrients)"
                
            # HIGH: Moderate stress with nutrient signs
            elif fertilizer_priority == 'high' or has_nutrient_issue:
                urgency_level = 'high'
                action_deadline = 3
                reason_base = "HIGH: Nutrient stress indicated by indices"
                override_type = recommended_type
                
            # STANDARD: Follow schedule
            elif ideal_interval and days_since >= ideal_interval:
                urgency_level = 'normal'
                action_deadline = 2
                reason_base = f"Scheduled application ({recommended_type})"
                override_type = None
                
            else:
                urgency_level = 'none'
                action_deadline = ideal_interval - days_since if ideal_interval else 999
                reason_base = "Not required at this time"
                override_type = None
        
        # Generate schedule
        schedule = []
        today = datetime.now()
        best_day = None
        
        for i in range(7):
            day_date = today + timedelta(days=i)
            
            recommendation = 'not_needed'
            reason = ''
            priority_score = 0
            fertilizer_type = None
            
            # CRITICAL CHECK: Cannot fertilize if too soon
            if days_since + i < ABSOLUTE_MIN_DAYS_FERT:
                recommendation = 'not_possible'
                reason = f"Too soon after last fertilization ({days_since + i} day(s)) - Wait {ABSOLUTE_MIN_DAYS_FERT - (days_since + i)} more day(s)"
                priority_score = 0
            
            elif urgency_level == 'urgent' and i <= action_deadline:
                recommendation = 'apply'
                fertilizer_type = override_type
                reason = f"🔴 {reason_base}"
                priority_score = 10
                
            elif urgency_level == 'high' and i <= action_deadline:
                recommendation = 'apply'
                fertilizer_type = override_type or recommended_type
                reason = f"⚠️ {reason_base}"
                priority_score = 8
                
            elif urgency_level == 'normal' and i <= action_deadline:
                recommendation = 'apply'
                fertilizer_type = recommended_type
                reason = f"📅 {reason_base}"
                priority_score = 6
                
            elif ideal_interval:
                days_left = ideal_interval - (days_since + i)
                reason = f"Not due yet ({days_left} days remaining)" if days_left > 0 else reason_base
            else:
                reason = "Not required at this stage"
            
            day_info = {
                'date': day_date.strftime('%Y-%m-%d'),
                'day_name': day_date.strftime('%A'),
                'date_formatted': day_date.strftime('%d %b'),
                'recommendation': recommendation,
                'fertilizer_type': fertilizer_type,
                'reason': reason,
                'priority_score': priority_score,
                'urgency_level': urgency_level if recommendation == 'apply' else 'none'
            }
            
            schedule.append(day_info)
            
            if best_day is None or priority_score > best_day['priority_score']:
                if recommendation == 'apply':
                    best_day = day_info
        
        return {
            'schedule': schedule,
            'best_day': best_day,
            'days_since_last': days_since,
            'recommended_type': override_type or recommended_type,
            'ideal_interval': ideal_interval,
            'health_urgency': urgency_level,
            'status': 'urgent' if urgency_level == 'urgent' else 
                     ('attention_needed' if urgency_level == 'high' else 'on_track'),
            'nutrient_deficiency_detected': has_nutrient_issue
        }
    
    def generate_weekly_plan(self,
                           last_irrigation: str,
                           last_fertilizer: str,
                           weather_forecast: List[Dict],
                           ndvi: float,
                           evi: Optional[float] = None,
                           ndwi: Optional[float] = None,
                           gndvi: Optional[float] = None,
                           savi: Optional[float] = None) -> Dict:
        
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: ASSESS CROP HEALTH (PRIMARY INPUT)
        # ═══════════════════════════════════════════════════════════════
        
        health_assessment = self.assess_health_from_indices(
            ndvi=ndvi,
            evi=evi,
            ndwi=ndwi,
            gndvi=gndvi
        )
        
        logger.info(f"Health Assessment: {health_assessment['status']} "
                   f"(NDVI: {ndvi:.3f}, Priority: {health_assessment['irrigation_priority']})")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: CALCULATE SCHEDULES (HEALTH-AWARE)
        # ═══════════════════════════════════════════════════════════════
        
        irrigation = self.calculate_irrigation_schedule(
            last_irrigation, weather_forecast, health_assessment
        )
        
        fertilizer = self.calculate_fertilizer_schedule(
            last_fertilizer, health_assessment
        )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: COMBINE INTO DAILY PLAN
        # ═══════════════════════════════════════════════════════════════
        
        combined_schedule = []
        for i in range(7):
            irr = irrigation['schedule'][i]
            fert = fertilizer['schedule'][i]
            
            actions = []
            priority = 'normal'
            
            if irr['recommendation'] in ['irrigate', 'monitor']:
                if irr['urgency_level'] in ['immediate', 'urgent']:
                    actions.append(f"🔴 URGENT: Irrigate")
                    priority = 'urgent'
                elif irr['urgency_level'] == 'high':
                    actions.append(f"⚠️ HIGH PRIORITY: Irrigate")
                    priority = 'high'
                else:
                    actions.append(f"💧 Irrigate")
            
            if fert['recommendation'] == 'apply':
                if fert['urgency_level'] == 'urgent':
                    actions.append(f"🔴 URGENT: {fert['fertilizer_type']}")
                    priority = 'urgent'
                elif fert['urgency_level'] == 'high':
                    actions.append(f"⚠️ {fert['fertilizer_type']}")
                    if priority != 'urgent':
                        priority = 'high'
                else:
                    actions.append(f"🧪 {fert['fertilizer_type']}")
            
            if not actions:
                actions.append('✅ No action needed')
            
            combined_schedule.append({
                'date': irr['date'],
                'day_name': irr['day_name'],
                'date_formatted': irr['date_formatted'],
                'irrigation': irr,
                'fertilizer': fert,
                'actions': actions,
                'weather': irr['weather'],
                'priority': priority
            })
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: GENERATE SUMMARY & RECOMMENDATIONS
        # ═══════════════════════════════════════════════════════════════
        
        # Key recommendations based on health
        key_recommendations = []
        
        if health_assessment['status'] == 'critical':
            key_recommendations.append("⚠️ CRITICAL: Immediate intervention required")
        elif health_assessment['status'] == 'severe_stress':
            key_recommendations.append("🔴 URGENT: Crop health declining - act within 48 hours")
        elif health_assessment['status'] == 'moderate_stress':
            key_recommendations.append("⚠️ Attention needed: Monitor closely and take preventive action")
        else:
            key_recommendations.append("✅ Crop health good - maintain current practices")
        
        # Specific issue alerts
        if 'severe_water_stress' in health_assessment['specific_issues']:
            key_recommendations.append("💧 Severe water stress detected - prioritize irrigation")
        if 'nutrient_deficiency' in health_assessment['specific_issues']:
            key_recommendations.append("🧪 Nutrient deficiency indicated - apply fertilizer")
        
        # Stage-specific advice
        if health_assessment['is_critical_stage']:
            key_recommendations.append(f"📍 Currently in critical stage: {self.current_stage}")
        
        return {
            'crop': self.crop,
            'stage': self.current_stage,
            'stage_info': self.get_current_stage(),
            
            # HEALTH ASSESSMENT (PRIMARY)
            'health_assessment': health_assessment,
            'vegetation_indices': {
                'ndvi': ndvi,
                'evi': evi,
                'ndwi': ndwi,
                'gndvi': gndvi,
                'savi': savi
            },
            
            # SCHEDULE
            'schedule': combined_schedule,
            
            # SUMMARIES
            'irrigation_summary': {
                'best_day': irrigation['best_day'],
                'status': irrigation['status'],
                'health_urgency': irrigation['health_urgency'],
                'days_since_last': irrigation['days_since_last'],
                'health_override': irrigation['health_based_override']
            },
            'fertilizer_summary': {
                'best_day': fertilizer['best_day'],
                'recommended_type': fertilizer['recommended_type'],
                'status': fertilizer['status'],
                'health_urgency': fertilizer['health_urgency'],
                'days_since_last': fertilizer['days_since_last']
            },
            
            # KEY INSIGHTS
            'key_recommendations': key_recommendations,
            'overall_urgency': max(irrigation['health_urgency'], fertilizer['health_urgency'], 
                                  key=['none', 'normal', 'high', 'urgent', 'immediate'].index),
            
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def create_plan_from_satellite_data(crop: str,
                                   lat: float,
                                   lon: float,
                                   band_data: np.ndarray,
                                   last_irrigation: str,
                                   last_fertilizer: str,
                                   weather_forecast: List[Dict]) -> Dict:
    
    # First, do full health assessment
    full_health = assess_crop_health(band_data, crop, already_scaled=True)
    
    # Extract indices
    indices = full_health['indices']
    
    # Create planner and generate plan
    planner = WeeklyPlanner(crop, lat, lon)
    
    plan = planner.generate_weekly_plan(
        last_irrigation=last_irrigation,
        last_fertilizer=last_fertilizer,
        weather_forecast=weather_forecast,
        ndvi=indices['ndvi']['mean'],
        evi=indices['evi']['mean'],
        ndwi=indices['ndwi']['mean'],
        gndvi=indices['gndvi']['mean'],
        savi=indices['savi']['mean']
    )
    
    # Add full health diagnosis
    plan['full_health_diagnosis'] = full_health['diagnosis']
    
    return plan