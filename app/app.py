# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI-Driven Agricultural Field Monitoring and Farmer Advisory System       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import numpy as np
  
# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import UIConfig, DateConfig, TemporalConfig, PathConfig, GEEConfig

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AgriVision | Smart Crop Monitoring",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

st.markdown("""
<style> 
    header {
        visibility: visible !important;
        background: transparent !important;
    }

    header [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 999999 !important;
        background-color: #22c55e !important; /* Green Color */
        border-radius: 0 8px 8px 0 !important;
        left: 0 !important;
        top: 10px !important;
        width: 45px !important;
        height: 40px !important;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3) !important;
    }

    [data-testid="collapsedControl"] svg {
        fill: white !important;
        color: white !important;
    }

    .main .block-container {
        padding-top: 4rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# INITIALIZE SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.health_result = None
    st.session_state.last_analysis = None


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS - LIGHT THEME
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════════════════════════
       GLOBAL STYLES - LIGHT THEME
       ═══════════════════════════════════════════════════════════════════════ */
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main {
        background: linear-gradient(180deg, #0b0f0d 0%, #111827 50%, #0b0f0d 100%);
    }
    
    .stApp {
        background: linear-gradient(180deg, #0b0f0d 0%, #111827 50%, #0b0f0d 100%);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ═══════════════════════════════════════════════════════════════════════
       SIDEBAR STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    [data-testid="stSidebar"] {
        background: #0f172a;
        border-right: 1px solid rgba(34, 197, 94, 0.25);
    }
    
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #166534;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 20px;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(34, 197, 94, 0.2);
    }
            
    body, .stMarkdown, .stText, p, span, label {
    color: #e5e7eb;
    }

    
    /* ══════════════════════════════════════════════════════════════════════
       CARD STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .glass-card {
        background: #ffffff;
        border: 1px solid rgba(34, 197, 94, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(34, 197, 94, 0.3);
        box-shadow: 0 8px 30px rgba(34, 197, 94, 0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
        border: 1px solid rgba(34, 197, 94, 0.2);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(34, 197, 94, 0.15);
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #16a34a;
        margin: 8px 0;
    }
    
    .metric-label {
        font-size: 12px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       HEADER STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .main-header {
        
        border: 1px solid rgba(34, 197, 94, 0.2);
        border-radius: 20px;
        padding: 30px 40px;
        margin-bottom: 40px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #22c55e, #16a34a, #15803d, #16a34a, #22c55e);
    }
    
    .main-header h1 {
        font-size: 28px;
        font-weight: 700;
        color: #000000;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .main-header .subtitle {
        color: #4b5563;
        font-size: 14px;
        margin-top: 8px;
    }
    
    .main-header .badge {
        display: inline-block;
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: #ffffff;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        margin-top: 12px;
        box-shadow: 0 2px 10px rgba(34, 197, 94, 0.3);
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       SECTION HEADERS
       ═══════════════════════════════════════════════════════════════════════ */
    
    .section-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 2px solid rgba(34, 197, 94, 0.15);
    }
    
    .section-header .icon {
        width: 42px;
        height: 42px;
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
    }
    
    .section-header h3 {
        color: #14532d;
        font-size: 18px;
        font-weight: 600;
        margin: 0;
    }
    
    .section-header .subtitle {
        color: #6b7280;
        font-size: 13px;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       BUTTON STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .stButton > button {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.3px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(34, 197, 94, 0.4);
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       INPUT STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
        color: #1f2937 !important;
    }
    
    .stSelectbox > div > div:focus-within,
    .stNumberInput > div > div:focus-within {
        border-color: #22c55e !important;
        box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.15) !important;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       TAB STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .stTabs [data-baseweb="tab-list"] {
        background: #f3f4f6;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #4b5563;
        font-weight: 500;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
        color: white !important;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       PROGRESS BAR
       ═══════════════════════════════════════════════════════════════════════ */
    
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #22c55e, #16a34a);
        border-radius: 10px;
    }
    
    .stProgress > div > div {
        background: #e5e7eb;
        border-radius: 10px;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       ALERT STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .success-alert {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #86efac;
        border-left: 4px solid #22c55e;
        border-radius: 8px;
        padding: 16px 20px;
        color: #166534;
    }
    
    .warning-alert {
        background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%);
        border: 1px solid #fde047;
        border-left: 4px solid #eab308;
        border-radius: 8px;
        padding: 16px 20px;
        color: #854d0e;
    }
    
    .error-alert {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border: 1px solid #fca5a5;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 16px 20px;
        color: #991b1b;
    }
    
    .info-alert {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #93c5fd;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 16px 20px;
        color: #1e40af;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       RESULT CARD STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .result-highlight {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 2px solid #86efac;
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        margin: 20px 0;
    }
    
    .result-highlight .crop-name {
        font-size: 36px;
        font-weight: 700;
        color: #16a34a;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .result-highlight .confidence {
        font-size: 16px;
        color: #4b5563;
        margin-top: 8px;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       SCHEDULE STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .schedule-row {
        display: flex;
        align-items: center;
        padding: 16px;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-bottom: 8px;
        transition: all 0.2s ease;
    }
    
    .schedule-row:hover {
        background: #f0fdf4;
        border-color: #86efac;
    }
    
    .schedule-row.best-day {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 2px solid #22c55e;
        box-shadow: 0 4px 15px rgba(34, 197, 94, 0.2);
    }
    
    .schedule-row.urgent {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border: 2px solid #ef4444;
    }
    
    .best-day-badge {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 10px;
    }
    
    .deadline-badge {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       SEASON BADGE
       ═══════════════════════════════════════════════════════════════════════ */
    
    .season-badge {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #86efac;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    
    .season-badge .season-name {
        color: #166534;
        font-weight: 600;
        font-size: 16px;
    }
    
    .season-badge .season-info {
        color: #4b5563;
        font-size: 13px;
        margin-top: 4px;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       EMPTY STATE
       ═══════════════════════════════════════════════════════════════════════ */
    
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        background: #ffffff;
        border: 2px dashed #d1d5db;
        border-radius: 16px;
    }
    
    .empty-state .icon {
        font-size: 64px;
        margin-bottom: 20px;
    }
    
    .empty-state h3 {
        color: #1f2937;
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .empty-state p {
        color: #6b7280;
        font-size: 14px;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       INDEX CARDS
       ═══════════════════════════════════════════════════════════════════════ */
    
    .index-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    
    .index-card .index-name {
        font-size: 11px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .index-card .index-value {
        font-size: 24px;
        font-weight: 700;
        margin: 8px 0;
    }
    
    .index-card.healthy { 
        border-top: 4px solid #22c55e; 
        background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
    }
    .index-card.healthy .index-value { color: #16a34a; }
    
    .index-card.warning { 
        border-top: 4px solid #eab308; 
        background: linear-gradient(180deg, #fefce8 0%, #ffffff 100%);
    }
    .index-card.warning .index-value { color: #ca8a04; }
    
    .index-card.danger { 
        border-top: 4px solid #ef4444; 
        background: linear-gradient(180deg, #fef2f2 0%, #ffffff 100%);
    }
    .index-card.danger .index-value { color: #dc2626; }
    
    /* ═══════════════════════════════════════════════════════════════════════
       CUSTOM DIVIDER
       ═══════════════════════════════════════════════════════════════════════ */
    
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.3), transparent);
        margin: 24px 0;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       ACTION CARDS
       ═══════════════════════════════════════════════════════════════════════ */
    
    .action-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    
    .action-card.irrigation {
        border-top: 4px solid #3b82f6;
    }
    
    .action-card.fertilizer {
        border-top: 4px solid #a855f7;
    }
    
    .action-card .action-icon {
        font-size: 36px;
        margin-bottom: 10px;
    }
    
    .action-card .action-label {
        font-size: 12px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .action-card .action-date {
        font-size: 24px;
        font-weight: 700;
        margin: 8px 0;
    }
    
    .action-card.irrigation .action-date { color: #2563eb; }
    .action-card.fertilizer .action-date { color: #9333ea; }
    
    .action-card .action-status {
        font-size: 12px;
        margin-top: 8px;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
    }
    
    .action-card .action-status.urgent {
        background: #fee2e2;
        color: #dc2626;
    }
    
    .action-card .action-status.due-soon {
        background: #fef3c7;
        color: #d97706;
    }
    
    .action-card .action-status.on-track {
        background: #dcfce7;
        color: #16a34a;
    }
    
    /* ═══════════════════════════════════════════════════════════════════════
       RADIO BUTTON STYLES
       ═══════════════════════════════════════════════════════════════════════ */
    
    .stRadio > div {
        background: rgba(13, 21, 18, 0.4);
        border-radius: 10px;
        padding: 8px;
    }
    
    .stRadio > div > label {
        background: transparent;
        padding: 10px 16px;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    
    .stRadio > div > label:hover {
        background: rgba(34, 197, 94, 0.1);
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        color: #16a34a;
    }
    
    [data-testid="stMetricLabel"] {
        color: #4b5563;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #f9fafb !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        color: #1f2937 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    # Logo/Brand
    st.markdown("""
    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px; background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-radius: 12px;">
        <div style="font-size: 48px; margin-bottom: 8px;">🌾</div>
        <div style="font-size: 22px; font-weight: 700; color: #166534;">AgriVision</div>
        <div style="font-size: 11px; color: #4b5563; text-transform: uppercase; letter-spacing: 2px;">Smart Farming</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("## 📖 Quick Guide")
    st.markdown("""
    <div style="font-size: 13px; color: #4b5563; line-height: 1.8;">
        <div style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;">
            <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">1</span>
            <span style="margin-left: 10px;">Select location on map</span>
        </div>
        <div style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;">
            <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">2</span>
            <span style="margin-left: 10px;">Choose analysis type</span>
        </div>
        <div style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;">
            <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">3</span>
            <span style="margin-left: 10px;">Click Run Analysis</span>
        </div>
        <div style="padding: 10px 0;">
            <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">4</span>
            <span style="margin-left: 10px;">Get insights & recommendations</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🌍 Coverage")
    st.markdown("""
    <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 12px; font-size: 13px;">
        <div style="color: #166534; font-weight: 600; margin-bottom: 8px;">Punjab, Pakistan</div>
        <div style="color: #4b5563;">
            Lat: 28°N - 34°N<br>
            Lon: 69.5°E - 75.5°E
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🌾 Crop Seasons")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="background: #fef3c7; border: 1px solid #fde047; border-radius: 8px; padding: 10px; text-align: center;">
            <div style="font-size: 24px;">🌾</div>
            <div style="color: #b45309; font-weight: 600; font-size: 12px;">Rice</div>
            <div style="color: #78716c; font-size: 10px;">May - Oct</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 10px; text-align: center;">
            <div style="font-size: 24px;">🌾</div>
            <div style="color: #166534; font-weight: 600; font-size: 12px;">Wheat</div>
            <div style="color: #78716c; font-size: 10px;">Nov - Apr</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("## 📊 System Status")
    
    import os
    v4_exists = os.path.exists(PathConfig.V4_MODEL_PATH)
    v6_exists = os.path.exists(PathConfig.V6_MODEL_PATH)
    gee_key = PathConfig.GEE_SERVICE_ACCOUNT_KEY
    gee_exists = os.path.exists(gee_key) if gee_key else False
    
    status_items = [
        ("V4 Model", v4_exists, "93.5% accuracy"),
        ("V6 Model", v6_exists, "89.3% accuracy"),
        ("GEE API", gee_exists, "Satellite data"),
    ]
    
    for name, status, desc in status_items:
        bg_color = "#f0fdf4" if status else "#fef2f2"
        border_color = "#86efac" if status else "#fca5a5"
        icon_bg = "#22c55e" if status else "#ef4444"
        icon = "✓" if status else "✗"
        text_color = "#166534" if status else "#991b1b"
        
        st.markdown(f"""
        <div style="display: flex; align-items: center; padding: 10px; margin-bottom: 8px;
                    background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px;">
            <div style="width: 24px; height: 24px; background: {icon_bg}; border-radius: 6px; 
                        display: flex; align-items: center; justify-content: center; 
                        color: white; font-size: 12px; font-weight: bold;">{icon}</div>
            <div style="margin-left: 12px;">
                <div style="color: {text_color}; font-size: 13px; font-weight: 500;">{name}</div>
                <div style="color: #6b7280; font-size: 11px;">{desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
        <div style="color: #9ca3af; font-size: 11px;">Version 1.0.0</div>
        <div style="color: #9ca3af; font-size: 10px; margin-top: 4px;">Powered by Sentinel-2</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🌾 Agriculture Field Monitoring & Advisory System </h1>
    <p class="subtitle">AI-Powered Crop Classification, Health Assessment & Smart Planning for Pakistani Farmers</p>
    <span class="badge">✨ Powered by Deep Learning & Satellite Imagery</span>
</div>
""", unsafe_allow_html=True) 

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

left_col, right_col = st.columns([1, 1.4], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT COLUMN - INPUT PANEL
# ═══════════════════════════════════════════════════════════════════════════

with left_col:
    st.markdown("""
    <div class="section-header">
        <div class="icon">📍</div>
        <div>
            <h3>Location & Parameters</h3>
            <span class="subtitle">Select your field location and analysis options</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Season indicator
    season_info = TemporalConfig.get_season_info(datetime.now().month)
    season_color = "#166534" if season_info['name'] == "Rabi (Wheat)" else "#b45309"
    season_bg = "#f0fdf4" if season_info['name'] == "Rabi (Wheat)" else "#fef3c7"
    
    st.markdown(f"""
    <div class="season-badge" style="background: {season_bg};">
        <div class="season-name" style="color: {season_color};">{season_info['icon']} {season_info['name']} Season Active</div>
        <div class="season-info">{season_info['months']} • Detecting: {', '.join(season_info['valid_crops'])}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Location Input
    st.markdown("##### 📍 Field Location")
    
    input_method = st.radio(
        "Select input method:",
        ["🗺️ Map Selection", "✏️ Manual Entry"],
        horizontal=True,
        key="input_method",
        label_visibility="collapsed"
    )
    
    lat, lon = 31.5, 73.0
    
    if input_method == "🗺️ Map Selection":
        try:
            import folium
            from streamlit_folium import st_folium
            from folium.plugins import LocateControl
            
            m = folium.Map(location=[31.5, 73.0], zoom_start=7, tiles='OpenStreetMap')
            LocateControl(auto_start=False, position='topright').add_to(m)
            m.add_child(folium.LatLngPopup())
            
            # Add Punjab boundary
            folium.Polygon(
                locations=[
                    [GEEConfig.PUNJAB_BOUNDS['min_lat'], GEEConfig.PUNJAB_BOUNDS['min_lon']],
                    [GEEConfig.PUNJAB_BOUNDS['min_lat'], GEEConfig.PUNJAB_BOUNDS['max_lon']],
                    [GEEConfig.PUNJAB_BOUNDS['max_lat'], GEEConfig.PUNJAB_BOUNDS['max_lon']],
                    [GEEConfig.PUNJAB_BOUNDS['max_lat'], GEEConfig.PUNJAB_BOUNDS['min_lon']],
                ],
                color='#22c55e',
                weight=2,
                fill=True,
                fillColor='#22c55e',
                fillOpacity=0.1
            ).add_to(m)
            
            st.info("📍 **Click on map** to select location OR use **📍 button** to auto-detect")
            
            map_data = st_folium(m, width=None, height=280, key="location_map")
            
            if map_data and map_data.get("last_clicked"):
                lat = map_data["last_clicked"]["lat"]
                lon = map_data["last_clicked"]["lng"]
                st.session_state['selected_lat'] = lat
                st.session_state['selected_lon'] = lon
                st.success(f"✅ Selected: {lat:.7f}°N, {lon:.7f}°E")
            
            # Use session state if available
            if 'selected_lat' in st.session_state:
                lat = st.session_state['selected_lat']
                lon = st.session_state['selected_lon']
                
        except ImportError:
            st.info("📦 Install `folium streamlit-folium` for map selection")
    
    else:  # Manual Entry
        default_lat = st.session_state.get('selected_lat', 31.5)
        default_lon = st.session_state.get('selected_lon', 73.0)
        
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", 28.0, 34.0, float(default_lat), 0.0001, format="%.4f", key="lat_manual")
        with col2:
            lon = st.number_input("Longitude", 69.5, 75.5, float(default_lon), 0.0001, format="%.4f", key="lon_manual")
        
        st.session_state['selected_lat'] = lat
        st.session_state['selected_lon'] = lon
    
    # ═══ FIXED: Validation OUTSIDE the if/else blocks ═══
    is_valid = GEEConfig.is_in_punjab(lat, lon)
    if is_valid:
        st.markdown(f"""
        <div class="success-alert">
            <strong>✓ Valid Location</strong> — Coordinates: {lat:.4f}°N, {lon:.4f}°E
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="warning-alert">
            <strong>⚠️ Outside Coverage Area</strong> — Coordinates may be outside Punjab region
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # Analysis Module Selection
    st.markdown("##### 🎯 Analysis Type")
    
    module = st.radio(
        "Select module:",
        ["🌾 Crop Classification", "🏥 Health Assessment", "📅 Weekly Planner"],
        key="module_select",
        label_visibility="collapsed"
    )
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # Module-specific options
    st.markdown("##### ⚙️ Parameters")
    
    analysis_date = st.date_input(
        "📅 Analysis Date",
        value=datetime.now(),
        min_value=DateConfig.get_min_date(),
        max_value=DateConfig.get_max_date(),
        key="analysis_date"
    )
    
    if module == "🏥 Health Assessment":
        crop_type = st.selectbox("🌱 Crop Type", ["Wheat", "Rice"], key="health_crop")
    
    elif module == "📅 Weekly Planner":
        planner_crop = st.selectbox("🌱 Crop Type", ["Wheat", "Rice"], key="planner_crop")
        
        col1, col2 = st.columns(2)
        with col1:
            last_irrigation = st.date_input("💧 Last Irrigation", value=datetime.now() - timedelta(days=10), key="last_irr")
        with col2:
            last_fertilizer = st.date_input("🧪 Last Fertilization", value=datetime.now() - timedelta(days=20), key="last_fert")
    
    # Advanced Options
    with st.expander("🔧 Advanced Options", expanded=False):
        use_tta = st.checkbox("Enable Test-Time Augmentation", value=True, key="tta")
        season_validation = st.checkbox("Enable Season Validation", value=True, key="season_val")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ═══ ANALYZE BUTTON - Must be here! ═══
    analyze_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True, key="analyze_btn")


# ═══════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN - RESULTS PANEL
# ═══════════════════════════════════════════════════════════════════════════

with right_col:
    st.markdown("""
    <div class="section-header">
        <div class="icon">📊</div>
        <div>
            <h3>Analysis Results</h3>
            <span class="subtitle">AI-powered insights and recommendations</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not analyze_btn:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">🛰️</div>
            <h3>Ready to Analyze</h3>
            <p>Select a location and click "Run Analysis" to get started.<br>
            Our AI will process satellite imagery and provide detailed insights.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div style="font-size: 32px; margin-bottom: 8px;">🌾</div>
                <div class="metric-label">Classification</div>
                <div style="color: #6b7280; font-size: 12px; margin-top: 8px;">Identify crop types with 93%+ accuracy</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="metric-card">
                <div style="font-size: 32px; margin-bottom: 8px;">🏥</div>
                <div class="metric-label">Health Check</div>
                <div style="color: #6b7280; font-size: 12px; margin-top: 8px;">NDVI, EVI, SAVI vegetation analysis</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="metric-card">
                <div style="font-size: 32px; margin-bottom: 8px;">📅</div>
                <div class="metric-label">Smart Planner</div>
                <div style="color: #6b7280; font-size: 12px; margin-top: 8px;">Weather-based irrigation & fertilization</div>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        # ─────────────────────────────────────────────────────────────────
        # CLASSIFICATION MODULE
        # ─────────────────────────────────────────────────────────────────
        if module == "🌾 Crop Classification":
            with st.spinner("🛰️ Fetching satellite data..."):
                try:
                    from gee_fetcher import GEEFetcher
                    from model_inference import CropClassifier
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.markdown("*Connecting to Google Earth Engine...*")
                    progress_bar.progress(20)
                    
                    fetcher = GEEFetcher(PathConfig.GEE_SERVICE_ACCOUNT_KEY)
                    
                    status_text.markdown("*Fetching Sentinel-2 imagery...*")
                    progress_bar.progress(40)
                    
                    data = fetcher.fetch_temporal_stack(lat, lon, datetime.combine(analysis_date, datetime.min.time()))
                    
                    status_text.markdown("*Running AI classification...*")
                    progress_bar.progress(70)
                    
                    classifier = CropClassifier(enable_season_validation=season_validation)
                    result = classifier.predict(
                        image_stack=data['image_stack'],
                        availability_mask=data['availability_mask'],
                        analysis_date=datetime.combine(analysis_date, datetime.min.time()),
                        use_tta=use_tta
                    )
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    progress_bar.empty()
                    
                    # Calculate NDVI from latest available month
                    mask = data['availability_mask']
                    stack = data['image_stack']
                    
                    current_ndvi = 0.0
                    for i in range(5, -1, -1):
                        if mask[i] == 1:
                            start_ch = i * 4
                            red = stack[start_ch + 2]  # B4
                            nir = stack[start_ch + 3]  # B8
                            with np.errstate(divide='ignore', invalid='ignore'):
                                ndvi_arr = (nir - red) / (nir + red + 1e-10)
                                ndvi_arr = np.clip(ndvi_arr, -1, 1)
                                current_ndvi = float(np.nanmean(ndvi_arr[ndvi_arr > -1]))
                            break
                    
                    # Success message
                    st.markdown(f"""
                    <div class="success-alert">
                        ✓ Analysis complete • {data['months_available']}/6 months data • Model: {result['model_used']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Main result
                    crop_emoji = "🌾" if result['predicted_class'] in ['Rice', 'Wheat'] else "🏞️"
                    confidence_color = "#16a34a" if result['confidence'] > 0.8 else "#ca8a04" if result['confidence'] > 0.6 else "#dc2626"
                    
                    st.markdown(f"""
                    <div class="result-highlight">
                        <div style="font-size: 48px; margin-bottom: 12px;">{crop_emoji}</div>
                        <div class="crop-name">{result['predicted_class']}</div>
                        <div class="confidence">
                            Confidence: <span style="color: {confidence_color}; font-weight: 600;">{result['confidence']:.1%}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Probability bars
                    st.markdown("##### 📊 Class Probabilities")
                    for cls, prob in sorted(result['probabilities'].items(), key=lambda x: x[1], reverse=True):
                        bar_color = "#22c55e" if cls == result['predicted_class'] else "#e5e7eb"
                        text_color = "#166534" if cls == result['predicted_class'] else "#4b5563"
                        st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="color: {text_color}; font-size: 13px; font-weight: 500;">{cls}</span>
                                <span style="color: {text_color}; font-weight: 600;">{prob:.1%}</span>
                            </div>
                            <div style="background: #f3f4f6; border-radius: 4px; height: 10px; overflow: hidden;">
                                <div style="background: {bar_color}; width: {prob*100}%; height: 100%; border-radius: 4px;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Season validation warning
                    if result.get('season_validation', {}).get('was_adjusted'):
                        st.markdown(f"""
                        <div class="warning-alert">
                            ⚠️ <strong>Season Adjustment Applied</strong><br>
                            {result['season_validation']['adjustment_reason']}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Additional info with NDVI
                    st.markdown("##### 📋 Analysis Details")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Data Quality:** {result['data_quality']}")
                        st.markdown(f"**Season:** {data['season']}")
                    with col2:
                        st.markdown(f"**Growth Stage:** {data['growth_stage']}")
                        ndvi_status = "🟢 Healthy" if current_ndvi > 0.4 else "🟡 Moderate" if current_ndvi > 0.25 else "🔴 Low"
                        st.markdown(f"**Current NDVI:** {current_ndvi:.3f} ({ndvi_status})")
                    
                except Exception as e:
                    st.markdown(f"""
                    <div class="error-alert">
                        <strong>❌ Classification Failed</strong><br>
                        {str(e)}
                    </div>
                    """, unsafe_allow_html=True)

        
        # ─────────────────────────────────────────────────────────────────
        # HEALTH ASSESSMENT MODULE
        # ─────────────────────────────────────────────────────────────────
        elif module == "🏥 Health Assessment":
            with st.spinner("🔬 Analyzing crop health..."):
                try:
                    from gee_fetcher import GEEFetcher
                    from health_assessment import HealthAssessor, assess_crop_health
                    
                    progress_bar = st.progress(0)
                    
                    fetcher = GEEFetcher(PathConfig.GEE_SERVICE_ACCOUNT_KEY)
                    progress_bar.progress(30)
                    
                    data = fetcher.fetch_temporal_stack(lat, lon, datetime.combine(analysis_date, datetime.min.time()))
                    progress_bar.progress(60)
                    
                    mask = data['availability_mask']
                    stack = data['image_stack']
                    
                    # Find last available month
                    last_idx = -1
                    for i in range(5, -1, -1):
                        if mask[i] == 1:
                            last_idx = i
                            break
                    
                    if last_idx == -1:
                        st.markdown("""
                        <div class="error-alert">
                            <strong>❌ No Data Available</strong><br>
                            No satellite data available for this location/date. Try a different date or location.
                        </div>
                        """, unsafe_allow_html=True)
                        st.stop()
                    
                    # Extract bands (data already scaled from GEE)
                    start_ch = last_idx * 4
                    band_data = stack[start_ch:start_ch + 4].copy()
                    
                    if np.max(band_data) == 0:
                        st.markdown("""
                        <div class="warning-alert">
                            <strong>⚠️ Limited Data Quality</strong><br>
                            Satellite data appears to have low signal. Results may be less accurate.
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Use health assessor with already_scaled=True
                    health_result = assess_crop_health(
                        band_data=band_data, 
                        crop=crop_type,
                        already_scaled=True
                    )
                    
                    # Extract values
                    indices = health_result['indices']
                    ndvi_mean = indices['ndvi']['mean']
                    evi_mean = indices['evi']['mean']
                    savi_mean = indices['savi']['mean']
                    gndvi_mean = indices['gndvi']['mean']
                    ndwi_mean = indices['ndwi']['mean']
                    
                    health_status = health_result['health_status']
                    status_label = health_status['label']
                    status_color = health_status['color']
                    status_key = health_status['status']
                    
                    status_backgrounds = {
                        'healthy': '#f0fdf4',
                        'moderate_stress': '#fefce8',
                        'severe_stress': '#fef2f2',
                        'critical': '#faf5ff'
                    }
                    status_bg = status_backgrounds.get(status_key, '#f8f9fa')
                    
                    diagnosis = health_result['diagnosis']
                    current_stage = health_result['stage']
                    
                    progress_bar.progress(100)
                    progress_bar.empty()
                    
                    # Health Status Banner
                    st.markdown(f"""
                    <div class="result-highlight" style="background: {status_bg}; border-color: {status_color}40;">
                        <div style="font-size: 48px; margin-bottom: 12px;">{status_label.split()[0]}</div>
                        <div class="crop-name" style="color: {status_color};">{status_label.split(' ', 1)[1] if ' ' in status_label else 'Status'}</div>
                        <div class="confidence">{crop_type} • {current_stage} Stage</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Vegetation Indices
                    st.markdown("##### 📈 Vegetation Indices")
                    
                    index_data = [
                        ("NDVI", ndvi_mean, "Vegetation vigor"),
                        ("EVI", evi_mean, "Enhanced index"),
                        ("SAVI", savi_mean, "Soil adjusted"),
                        ("GNDVI", gndvi_mean, "Chlorophyll"),
                        ("NDWI", ndwi_mean, "Water content"),
                    ]
                    
                    cols = st.columns(5)
                    for i, (name, value, desc) in enumerate(index_data):
                        if name == "NDWI":
                            card_class = "healthy" if value > -0.1 else "warning" if value > -0.3 else "danger"
                        else:
                            card_class = "healthy" if value > 0.4 else "warning" if value > 0.25 else "danger"
                        
                        with cols[i]:
                            st.markdown(f"""
                            <div class="index-card {card_class}">
                                <div class="index-name">{name}</div>
                                <div class="index-value">{value:.2f}</div>
                                <div style="font-size: 10px; color: #6b7280;">{desc}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Diagnosis and Recommendations
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("##### 🔍 Diagnosis")
                        for issue in diagnosis['issues']:
                            st.markdown(f"• {issue}")
                    
                    with col2:
                        st.markdown("##### 💡 Recommendations")
                        for rec in diagnosis['recommendations']:
                            st.markdown(f"• {rec}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Detailed metrics
                    with st.expander("📊 Detailed Health Metrics", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**NDVI Statistics**")
                            st.markdown(f"- Mean: {indices['ndvi']['mean']:.3f}")
                            st.markdown(f"- Min: {indices['ndvi']['min']:.3f}")
                            st.markdown(f"- Max: {indices['ndvi']['max']:.3f}")
                            st.markdown(f"- Std Dev: {indices['ndvi']['std']:.3f}")
                            
                            st.markdown("**EVI Statistics**")
                            st.markdown(f"- Mean: {indices['evi']['mean']:.3f}")
                            st.markdown(f"- Range: [{indices['evi']['min']:.3f}, {indices['evi']['max']:.3f}]")
                        
                        with col2:
                            st.markdown("**Expected Range**")
                            expected = health_result['thresholds']['ndvi']
                            st.markdown(f"- Min: {expected[0]:.2f}")
                            st.markdown(f"- Max: {expected[1]:.2f}")
                            st.markdown(f"- Healthy Threshold: {health_result['thresholds']['healthy_min']:.2f}")
                            
                            st.markdown("**Assessment Confidence**")
                            st.markdown(f"- Level: {diagnosis['confidence'].upper()}")
                            st.markdown(f"- Based on NDVI variability")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # ═══ GEMINI AI EXPLANATION IN URDU ═══
                    # 1. ENSURE THE FONT IS IMPORTED (Add this once at the top of your app)
                    st.markdown("""
                        <style>
                        @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400..700&display=swap');
                        
                        .urdu-text {
                            font-family: 'Noto Nastaliq Urdu', serif;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                    # 2. UPDATED HEADER
                    st.markdown("""
                        <div class="section-header urdu-text" style="direction: rtl; text-align: right;">
                            <div class="icon">🤖</div>
                            <div>
                                <h3 style="margin: 0;">زرعی مشیر - اردو میں رہنمائی</h3>
                                <span class="subtitle" style="font-family: sans-serif;">Detailed guidance in Urdu</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with st.spinner("🤖 تشریح تیار کی جا رہی ہے..."):
                        try:
                            from gemini_advisor import GeminiAdvisor
                            
                            advisor = GeminiAdvisor()
                            if advisor.initialized:
                                explanation = advisor.explain_health_assessment(health_result)
                                
                                if explanation:
                                    # ✅ FONT FIX + LINE BREAK FIX (.replace)
                                    formatted_explanation = explanation.replace('\n', '<br>')
                                    
                                    st.markdown(f"""
                                    <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); 
                                                border: 2px solid #86efac; 
                                                border-radius: 12px; 
                                                padding: 24px; 
                                                margin-top: 16px; 
                                                font-family: 'Noto Nastaliq Urdu', serif; 
                                                font-size: 20px; 
                                                line-height: 2.6; 
                                                text-align: right; 
                                                direction: rtl; 
                                                color: #166534;">
                                        {formatted_explanation}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # ✅ UPDATED NOTE SECTION
                                    st.markdown("""
                                    <div style="margin-top: 12px; 
                                                padding: 12px; 
                                                background: #fffbeb; 
                                                border-right: 4px solid #f59e0b; 
                                                border-radius: 8px; 
                                                font-family: 'Noto Nastaliq Urdu', serif; 
                                                direction: rtl; 
                                                text-align: right;
                                                font-size: 16px;">
                                        💡 <strong>نوٹ:</strong> یہ تشریح AI زرعی مشیر نے دی ہے۔ عملی نفاذ سے پہلے مقامی زرعی ماہر سے ضرور مشورہ کریں۔
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.warning("⚠️ تشریح تیار نہیں ہو سکی۔")
                            else:
                                st.info("📝 AI مشیر دستیاب نہیں۔ .env میں GEMINI_API_KEY شامل کریں۔")
                        except Exception as e:
                            st.error(f"Error: {e}")
                    
                except Exception as e:
                    st.markdown(f"""
                    <div class="error-alert">
                        <strong>❌ Health Assessment Failed</strong><br>
                        {str(e)}
                    </div>
                    """, unsafe_allow_html=True)
                    import traceback
                    st.code(traceback.format_exc())

        
        # ─────────────────────────────────────────────────────────────────
        # WEEKLY PLANNER MODULE
        # ─────────────────────────────────────────────────────────────────
        elif module == "📅 Weekly Planner":
            with st.spinner("📅 Generating weekly plan..."):
                try:
                    from weather_service import WeatherService
                    from weekly_planner import WeeklyPlanner  # Make sure this imports the FIXED version
                    
                    progress_bar = st.progress(0)
                    
                    weather = WeatherService.get_forecast(lat, lon, 7)
                    progress_bar.progress(30)
                    
                    # ═══════════════════════════════════════════════════════════════
                    # ✅ NEW: Get vegetation indices from health assessment
                    # ═══════════════════════════════════════════════════════════════
                    ndvi = 0.45  # Default if no health assessment
                    evi = 0.42
                    ndwi = 0.0
                    gndvi = 0.43
                    savi = 0.44
                    
                    if 'health_result' in st.session_state and st.session_state['health_result']:
                        # Extract indices from health assessment
                        indices = st.session_state['health_result']['indices']
                        ndvi = indices['ndvi']['mean']
                        evi = indices['evi']['mean']
                        ndwi = indices['ndwi']['mean']
                        gndvi = indices['gndvi']['mean']
                        savi = indices['savi']['mean']
                    
                    progress_bar.progress(50)
                    
                    # ═══════════════════════════════════════════════════════════════
                    # ✅ FIXED: Pass vegetation indices instead of health_status
                    # ═══════════════════════════════════════════════════════════════
                    planner = WeeklyPlanner(planner_crop, lat, lon)
                    plan = planner.generate_weekly_plan(
                        last_irrigation=last_irrigation.strftime('%Y-%m-%d'),
                        last_fertilizer=last_fertilizer.strftime('%Y-%m-%d'),
                        weather_forecast=weather['forecast'],
                        ndvi=ndvi,      # ✅ REQUIRED
                        evi=evi,        # ✅ Recommended
                        ndwi=ndwi,      # ✅ Recommended (water stress)
                        gndvi=gndvi,    # ✅ Recommended (nutrients)
                        savi=savi       # Optional
                    )
                    progress_bar.progress(100)
                    progress_bar.empty()
                    
                    # ═══════════════════════════════════════════════════════════════
                    # ✅ UPDATED: Use new plan structure with health_assessment
                    # ═══════════════════════════════════════════════════════════════
                    
                    # Header - Show health status from assessment
                    health_status = plan['health_assessment']['status']
                    health_label = plan['health_assessment'].get('label', health_status)
                    
                    st.markdown(f"""
                    <div class="success-alert">
                        ✓ Plan generated for <strong>{plan['crop']}</strong> • Stage: <strong>{plan['stage']}</strong>
                        <br>
                        <span style="margin-top: 8px; display: inline-block;">
                            Health: {health_label} (NDVI: {plan['health_assessment']['ndvi']:.3f})
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Best days summary
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        irr = plan['irrigation_summary']
                        irr_date = irr['best_day']['date_formatted'] if irr['best_day'] else 'Not needed'
                        irr_day = irr['best_day']['day_name'] if irr['best_day'] else ''
                        
                        # ✅ UPDATED: Use new urgency levels
                        health_urgency = irr.get('health_urgency', 'normal')
                        
                        if health_urgency == 'immediate':
                            status_class = "urgent"
                            status_text = f"🔴 IMMEDIATE ACTION REQUIRED"
                            deadline_text = "IRRIGATE NOW - Crop critically stressed"
                        elif health_urgency == 'urgent':
                            status_class = "urgent"
                            status_text = f"⚠️ URGENT - Crop health declining"
                            deadline_text = "Irrigate within 48 hours"
                        elif health_urgency == 'high':
                            status_class = "due-soon"
                            status_text = f"HIGH PRIORITY • {irr['days_since_last']} days since last"
                            deadline_text = f"Action needed by {irr_date}"
                        elif irr['days_since_last'] >= 25:  # Overdue by normal schedule
                            status_class = "due-soon"
                            status_text = f"Due • {irr['days_since_last']} days since last"
                            deadline_text = f"Best day: {irr_date}"
                        else:
                            status_class = "on-track"
                            status_text = f"On track • {irr['days_since_last']} days since last"
                            deadline_text = f"Next: {irr_date}"
                        
                        st.markdown(f"""
                        <div class="action-card irrigation">
                            <div class="action-icon">💧</div>
                            <div class="action-label">Next Irrigation</div>
                            <div class="action-date">{irr_date}</div>
                            <div style="color: #6b7280; font-size: 12px;">{irr_day}</div>
                            <div class="action-status {status_class}">{status_text}</div>
                            <div style="margin-top: 10px; padding: 8px; background: #eff6ff; border-radius: 6px; font-size: 12px; color: #1e40af;">
                                📌 {deadline_text}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        fert = plan['fertilizer_summary']
                        fert_date = fert['best_day']['date_formatted'] if fert['best_day'] else 'Not needed'
                        fert_day = fert['best_day']['day_name'] if fert['best_day'] else ''
                        fert_type = fert['recommended_type'][:30] if fert['recommended_type'] else 'None'
                        
                        # ✅ UPDATED: Use new urgency levels
                        fert_urgency = fert.get('health_urgency', 'none')
                        
                        if fert_urgency == 'urgent':
                            fert_status_class = "urgent"
                            fert_status_text = f"🔴 URGENT - Nutrient deficiency detected"
                            fert_deadline = f"Apply: {fert_type}"
                        elif fert_urgency == 'high':
                            fert_status_class = "due-soon"
                            fert_status_text = f"HIGH PRIORITY • {fert['days_since_last']} days since last"
                            fert_deadline = f"Apply: {fert_type}"
                        elif fert['status'] == 'due':
                            fert_status_class = "due-soon"
                            fert_status_text = f"Due now • {fert['days_since_last']} days since last"
                            fert_deadline = f"Apply: {fert_type}"
                        else:
                            fert_status_class = "on-track"
                            fert_status_text = f"On track • {fert['days_since_last']} days since last"
                            fert_deadline = f"Recommended: {fert_type}"
                        
                        st.markdown(f"""
                        <div class="action-card fertilizer">
                            <div class="action-icon">🧪</div>
                            <div class="action-label">Next Fertilization</div>
                            <div class="action-date">{fert_date}</div>
                            <div style="color: #6b7280; font-size: 12px;">{fert_day}</div>
                            <div class="action-status {fert_status_class}">{fert_status_text}</div>
                            <div style="margin-top: 10px; padding: 8px; background: #faf5ff; border-radius: 6px; font-size: 12px; color: #7c3aed;">
                                📌 {fert_deadline}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # ═══════════════════════════════════════════════════════════════
                    # ✅ NEW: Show key recommendations from health assessment
                    # ═══════════════════════════════════════════════════════════════
                    if plan.get('key_recommendations'):
                        st.markdown("##### 🎯 Key Recommendations")
                        for rec in plan['key_recommendations']:
                            st.markdown(f"""
                            <div style="padding: 8px 12px; background: #fef3c7; border-left: 4px solid #f59e0b; 
                                        border-radius: 6px; margin-bottom: 8px; font-size: 14px;">
                                {rec}
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                    
                    # 7-Day Schedule
                    st.markdown("##### 📅 7-Day Schedule")
                    
                    best_irr_date = irr['best_day']['date'] if irr['best_day'] else None
                    best_fert_date = fert['best_day']['date'] if fert['best_day'] else None
                    
                    for day in plan['schedule']:
                        is_best_irr = day['date'] == best_irr_date
                        is_best_fert = day['date'] == best_fert_date
                        is_best = is_best_irr or is_best_fert
                        
                        # ✅ UPDATED: Handle new recommendation types
                        row_class = "best-day" if is_best else ""
                        if day['priority'] == 'urgent':
                            row_class = "urgent"
                        elif day['priority'] == 'high':
                            row_class = "due-soon"
                        
                        rain = day['weather']['rain']
                        weather_icon = "🌧️" if rain > 5 else "⛅" if rain > 0 else "☀️"
                        
                        irr_badge = ""
                        fert_badge = ""
                        
                        if is_best_irr:
                            irr_badge = '<span class="best-day-badge">✓ BEST DAY</span>'
                        elif day['irrigation']['recommendation'] == 'irrigate':
                            if day['irrigation'].get('urgency_level') in ['immediate', 'urgent']:
                                irr_badge = '<span class="deadline-badge">URGENT</span>'
                            else:
                                irr_badge = '<span class="deadline-badge">Due</span>'
                        
                        if is_best_fert:
                            fert_badge = '<span class="best-day-badge">✓ BEST DAY</span>'
                        elif day['fertilizer']['recommendation'] == 'apply':
                            if day['fertilizer'].get('urgency_level') == 'urgent':
                                fert_badge = '<span class="deadline-badge">URGENT</span>'
                        
                        # ✅ UPDATED: Handle 'not_possible' recommendation
                        if day['irrigation']['recommendation'] == 'not_possible':
                            irr_text = '<span style="color: #dc2626; font-weight: 600;">⛔ Too soon</span>'
                        elif day['irrigation']['recommendation'] == 'irrigate':
                            irr_text = f'<span style="color: #2563eb; font-weight: 600;">💧 Irrigate</span> {irr_badge}'
                        elif day['irrigation']['recommendation'] == 'monitor':
                            irr_text = '<span style="color: #f59e0b; font-weight: 600;">👁️ Monitor</span>'
                        elif day['irrigation']['recommendation'] == 'skip':
                            irr_text = '<span style="color: #6b7280;">⏭️ Skip (rain)</span>'
                        else:
                            irr_text = '<span style="color: #9ca3af;">◽ No action</span>'
                        
                        # ✅ UPDATED: Handle fertilizer 'not_possible'
                        if day['fertilizer']['recommendation'] == 'not_possible':
                            fert_text = '<span style="color: #dc2626; font-weight: 600;">⛔ Too soon</span>'
                        elif day['fertilizer']['recommendation'] in ['apply', 'urgent']:
                            fert_text = f'<span style="color: #9333ea; font-weight: 600;">🧪 {day["fertilizer"]["fertilizer_type"][:15] if day["fertilizer"]["fertilizer_type"] else "Apply"}</span> {fert_badge}'
                        else:
                            fert_text = '<span style="color: #9ca3af;">◽ No action</span>'
                        
                        st.markdown(f"""
                        <div class="schedule-row {row_class}">
                            <div style="flex: 0 0 90px;">
                                <div style="font-weight: 600; color: #1f2937; font-size: 15px;">{day['day_name'][:3]}</div>
                                <div style="font-size: 12px; color: #6b7280;">{day['date_formatted']}</div>
                            </div>
                            <div style="flex: 0 0 100px; text-align: center;">
                                <div style="font-size: 24px;">{weather_icon}</div>
                                <div style="font-size: 11px; color: #6b7280;">{day['weather']['temp_max']}°C • {rain}mm</div>
                            </div>
                            <div style="flex: 1; display: flex; gap: 30px; justify-content: center; align-items: center;">
                                <div style="min-width: 150px;">{irr_text}</div>
                                <div style="min-width: 180px;">{fert_text}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Legend
                    st.markdown("""
                    <div style="margin-top: 20px; padding: 15px; background: #f9fafb; border-radius: 8px; font-size: 12px; color: #6b7280;">
                        <strong>Legend:</strong> 
                        <span style="background: #22c55e; color: white; padding: 2px 8px; border-radius: 10px; margin-left: 10px;">✓ BEST DAY</span> = Optimal conditions
                        <span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 10px; margin-left: 10px;">URGENT</span> = Health-based priority
                        <span style="background: #dc2626; color: white; padding: 2px 8px; border-radius: 10px; margin-left: 10px;">⛔ Too soon</span> = Recently applied
                        <span style="margin-left: 10px;">☀️ = Clear</span>
                        <span style="margin-left: 10px;">🌧️ = Rain expected</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # ═══ GEMINI AI EXPLANATION IN URDU ═══
                    st.markdown("""
                        <style>
                        @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400..700&display=swap');
                        
                        .nastaleeq-text {
                            font-family: 'Noto Nastaliq Urdu', serif;
                            line-height: 2.2;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                    st.markdown("""
                        <div class="section-header nastaleeq-text" style="direction: rtl; text-align: right;">
                            <div class="icon">🤖</div>
                            <div>
                                <h3 style="margin: 0;">ہفتہ وار منصوبہ - اردو میں رہنمائی</h3>
                                <span class="subtitle" style="font-family: sans-serif;">Weekly guidance in Urdu</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with st.spinner("🤖 ہفتہ وار منصوبہ تیار کیا جا رہا ہے..."):
                        try:
                            from gemini_advisor import GeminiAdvisor
                            
                            advisor = GeminiAdvisor()
                            if advisor.initialized:
                                explanation = advisor.explain_weekly_plan(plan)
                                
                                if explanation:
                                    formatted_explanation = explanation.replace("\n", "<br>")

                                    st.markdown(f"""
                                    <div style="background: #f8fafc; 
                                                border: 2px solid #93c5fd; 
                                                border-radius: 12px; 
                                                padding: 24px; 
                                                margin-top: 16px; 
                                                font-family: 'Noto Nastaliq Urdu', serif; 
                                                font-size: 20px; 
                                                line-height: 2.5; 
                                                text-align: right; 
                                                direction: rtl; 
                                                color: #1e293b;">
                                         {formatted_explanation}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown("""
                                    <div style="margin-top: 12px; 
                                                padding: 12px; 
                                                background: #fefce8; 
                                                border-right: 4px solid #eab308; 
                                                border-radius: 8px; 
                                                font-family: 'Noto Nastaliq Urdu', serif; 
                                                direction: rtl; 
                                                text-align: right;">
                                        <span style="font-size: 16px;">
                                        💡 <strong>نوٹ:</strong> اس منصوبے پر عمل کرتے وقت اپنے علاقے کے موسم اور زمین کی حالت کا بھی خیال رکھیں۔
                                        </span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.warning("⚠️ تشریح تیار نہیں ہو سکی۔")
                            else:
                                st.info("📝 AI مشیر دستیاب نہیں۔ .env میں GEMINI_API_KEY شامل کریں۔")
                        except Exception as e:
                            st.error(f"Error: {e}")
                    
                except Exception as e:
                    st.markdown(f"""
                    <div class="error-alert">
                        <strong>❌ Planner Failed</strong><br>
                        {str(e)}
                    </div>
                    """, unsafe_allow_html=True)
                    import traceback
                    st.code(traceback.format_exc())

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="margin-top: 50px; padding: 30px 0; border-top: 2px solid #e5e7eb; text-align: center;">
    <div style="color: #4b5563; font-size: 13px; font-weight: 500;">
        AI-Driven Agricultural Field Monitoring and Farmer Advisory System
    </div>
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">
        Final Year Project • Powered by Google Earth Engine, Sentinel-2 & PyTorch
    </div>
    <div style="margin-top: 12px;">
        <span style="background: linear-gradient(135deg, #22c55e, #16a34a); color: white; padding: 6px 16px; border-radius: 20px; font-size: 11px; font-weight: 500;">
            Made with ❤️ in Pakistan
        </span>
    </div>
</div>
""", unsafe_allow_html=True)