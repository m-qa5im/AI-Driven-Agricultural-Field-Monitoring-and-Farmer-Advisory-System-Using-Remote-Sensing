# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  FILE 1: gemini_advisor.py                                                ║
# ║  Location: src/gemini_advisor.py                                          ║
# ║  COMPLETE & READY TO USE - Just copy-paste this entire file               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. Run: pip install google-generativeai")


class GeminiAdvisor:
    """Gemini AI advisor for generating concise Urdu explanations"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.initialized = False
        self.model = None
        
        if not GENAI_AVAILABLE:
            print("❌ Gemini not available")
            return
        
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            print("❌ GEMINI_API_KEY not found in .env")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.initialized = True
            print("✅ Gemini AI initialized (gemini-2.5-flash)")
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
    
    def explain_health_assessment(self, health_result: Dict) -> Optional[str]:
        """Generate CONCISE Urdu explanation (200-250 words)"""
        if not self.initialized:
            return None
        
        try:
            crop = health_result.get('crop', 'Unknown')
            stage = health_result.get('stage', 'Unknown')
            health_status = health_result.get('health_status', {})
            indices = health_result.get('indices', {})
            diagnosis = health_result.get('diagnosis', {})
            
            prompt = f"""
آپ پاکستانی کسانوں کے لیے زرعی مشیر ہیں۔ آپ کو فصل کی صحت کی تشخیص کو سادہ اردو میں سمجھانا ہے۔

اہم: جواب مختصر اور واضح ہو (200-250 الفاظ)۔ صرف ضروری معلومات دیں۔

فصل کی تفصیلات:
- فصل: {crop}
- مرحلہ: {stage}
- صحت کی حالت: {health_status.get('label', 'Unknown')}

سیٹلائٹ ڈیٹا:
- NDVI: {indices.get('ndvi', {}).get('mean', 0):.2f}
- EVI: {indices.get('evi', {}).get('mean', 0):.2f}
- SAVI: {indices.get('savi', {}).get('mean', 0):.2f}
- GNDVI: {indices.get('gndvi', {}).get('mean', 0):.2f}
- NDWI: {indices.get('ndwi', {}).get('mean', 0):.2f}

تشخیص:
مسائل: {', '.join(diagnosis.get('issues', ['کوئی نہیں']))}
تجاویز: {', '.join(diagnosis.get('recommendations', ['کوئی نہیں']))}

مندرجہ ذیل فارمیٹ میں مختصر جواب دیں:

🌱 فصل کی صحت
(2-3 جملوں میں: فصل کی موجودہ حالت کیا ہے؟)

📊 اہم اعداد و شمار
(ہر انڈیکس کو 1 جملے میں سمجھائیں - کیا اچھا ہے، کیا خراب ہے)

🔍 مسائل
(اگر کوئی مسئلہ ہے تو 2-3 جملوں میں بتائیں)

💡 فوری اقدامات
(3-4 نکات، ہر نکتہ 1 جملے میں - کیا کرنا ہے)

یاد رکھیں: مختصر، سادہ، اور عملی رہیں۔ پیچیدہ الفاظ استعمال نہ کریں۔
"""
            response = self.model.generate_content(prompt)
            return response.text if response and response.text else None
            
        except Exception as e:
            print(f"Error generating health explanation: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def explain_weekly_plan(self, weekly_plan: Dict) -> Optional[str]:
        """Generate CONCISE Urdu explanation (200-250 words) - FIXED VERSION"""
        if not self.initialized:
            return None
        
        try:
            crop = weekly_plan.get('crop', 'Unknown')
            stage = weekly_plan.get('stage', 'Unknown')
            irrigation_summary = weekly_plan.get('irrigation_summary', {})
            fertilizer_summary = weekly_plan.get('fertilizer_summary', {})
            schedule = weekly_plan.get('schedule', [])
            
            # ✅ FIX: Safe schedule text building with None checks
            schedule_lines = []
            for i, day in enumerate(schedule[:7]):
                day_name = day.get('day_name', f'Day {i+1}')
                
                # Safe irrigation recommendation
                irrigation_rec = 'کوئی نہیں'
                if day.get('irrigation') and isinstance(day['irrigation'], dict):
                    irrigation_rec = day['irrigation'].get('recommendation', 'کوئی نہیں')
                
                # Safe fertilizer recommendation
                fertilizer_rec = 'کوئی نہیں'
                if day.get('fertilizer') and isinstance(day['fertilizer'], dict):
                    fertilizer_rec = day['fertilizer'].get('recommendation', 'کوئی نہیں')
                
                schedule_lines.append(
                    f"دن {i+1} ({day_name}): پانی - {irrigation_rec}, کھاد - {fertilizer_rec}"
                )
            
            schedule_text = "\n".join(schedule_lines)
            
            # ✅ FIX: Safe dictionary access with defaults
            best_irr_day = 'ضرورت نہیں'
            if irrigation_summary.get('best_day'):
                best_irr_day = irrigation_summary['best_day'].get('date_formatted', 'ضرورت نہیں')
            
            best_fert_day = 'ضرورت نہیں'
            if fertilizer_summary.get('best_day'):
                best_fert_day = fertilizer_summary['best_day'].get('date_formatted', 'ضرورت نہیں')
            
            prompt = f"""
آپ پاکستانی کسانوں کے لیے زرعی مشیر ہیں۔ آپ کو ہفتہ وار منصوبہ سادہ اردو میں سمجھانا ہے۔

اہم: جواب مختصر اور واضح ہو (200-250 الفاظ)۔ صرف ضروری معلومات دیں۔

فصل کی تفصیلات:
- فصل: {crop}
- مرحلہ: {stage}

پانی دینے کی خلاصہ:
- آخری بار: {irrigation_summary.get('days_since_last', 0)} دن پہلے
- بہترین دن: {best_irr_day}
- فوریت: {irrigation_summary.get('urgency', 'normal')}

کھاد ڈالنے کی خلاصہ:
- آخری بار: {fertilizer_summary.get('days_since_last', 0)} دن پہلے
- بہترین دن: {best_fert_day}
- تجویز کردہ کھاد: {fertilizer_summary.get('recommended_type', 'کوئی نہیں')}

7 دن کی منصوبہ بندی:
{schedule_text}

مندرجہ ذیل فارمیٹ میں مختصر جواب دیں:

📅 اس ہفتے کا خلاصہ
(2-3 جملوں میں: اس ہفتے کیا اہم ہے؟)

💧 پانی دینے کی ہدایات
(2-3 جملے: کب اور کیوں پانی دیں)

🧪 کھاد ڈالنے کی ہدایات
(2-3 جملے: کب اور کون سی کھاد استعمال کریں)

⚠️ اہم نکات
(3-4 مختصر نکات جو کسان کو یاد رکھنے چاہیں)

یاد رکھیں: مختصر، سادہ، اور عملی رہیں۔ پیچیدہ الفاظ استعمال نہ کریں۔
"""
            response = self.model.generate_content(prompt)
            return response.text if response and response.text else None
            
        except Exception as e:
            print(f"Error generating weekly plan explanation: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    advisor = GeminiAdvisor()
    
    if advisor.initialized:
        print("✅ Gemini advisor ready!")
        print("✅ Generates concise Urdu explanations (200-250 words)")
        print("✅ NoneType error fixed in weekly planner")
    else:
        print("❌ Failed to initialize. Check GEMINI_API_KEY in .env")