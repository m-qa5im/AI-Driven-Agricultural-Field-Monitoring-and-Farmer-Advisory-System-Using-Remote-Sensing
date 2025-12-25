# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI-DRIVEN AGRICULTURAL FIELD MONITORING AND FARMER ADVISORY SYSTEM        ║
# ║  Using Remote Sensing                                                      ║
# ║                                                                            ║
# ║  Main Streamlit Application                                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# ─────────────────────────────────────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────────────────────────────────────

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION (Must be first Streamlit command)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Agricultural Monitoring System",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

from config import UIConfig, PathConfig
from app.utils.helpers import (
    get_project_paths, check_model_files, get_error_message,
    log_analysis_request, log_analysis_result
)
from app.components.input_form import render_input_form, render_sidebar_info
from app.components.map_view import render_result_map, render_data_availability
from app.components.results_display import (
    render_classification_results,
    render_health_results,
    render_advisory_results,
    render_loading_state,
    render_error_state,
    render_no_data_state,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────

def load_custom_css():
    """Load custom CSS styles."""
    st.markdown("""
    <style>
        /* Main container */
        .main > div {
            padding-top: 2rem;
        }
        
        /* Header styling */
        .main-header {
            background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 50%, #43a047 100%);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            color: white;
            text-align: center;
        }
        
        .main-header h1 {
            margin: 0;
            font-size: 2.2rem;
            font-weight: 700;
        }
        
        .main-header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }
        
        /* Card styling */
        .result-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        
        /* Button styling */
        .stButton > button {
            width: 100%;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            padding-top: 2rem;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 10px 20px;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Expander styling */
        .streamlit-expanderHeader {
            font-weight: 600;
            font-size: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

def render_header():
    """Render the main application header."""
    st.markdown(f"""
    <div class="main-header">
        <h1>🌾 {UIConfig.APP_TITLE}</h1>
        <p>{UIConfig.APP_SUBTITLE}</p>
        <p style="font-size: 0.85rem; margin-top: 15px; opacity: 0.7;">
            Version {UIConfig.APP_VERSION} | Powered by Sentinel-2 Satellite Imagery
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def initialize_system():
    """
    Initialize the system components (cached).
    Returns initialized GEE fetcher, classifier, health assessor, and advisory system.
    """
    paths = get_project_paths()
    
    # Initialize components
    components = {
        'gee_fetcher': None,
        'classifier': None,
        'health_assessor': None,
        'advisory_system': None,
        'errors': [],
    }
    
    # Initialize GEE Fetcher
    try:
        from gee_fetcher import GEEFetcher
        cred_path = paths['credentials'] / 'gee_service_account.json'
        
        if cred_path.exists():
            components['gee_fetcher'] = GEEFetcher(str(cred_path))
            logger.info("GEE Fetcher initialized with service account")
        else:
            # Try default authentication
            components['gee_fetcher'] = GEEFetcher()
            logger.info("GEE Fetcher initialized with default auth")
            
    except Exception as e:
        components['errors'].append(f"GEE initialization failed: {str(e)}")
        logger.error(f"GEE initialization failed: {str(e)}")
    
    # Initialize Classifier
    try:
        from model_inference import CropClassifier
        
        v4_path = paths['models'] / 'best_model_v4.pth'
        v6_path = paths['models'] / 'best_model_v6_variable.pth'
        
        components['classifier'] = CropClassifier(
            v4_model_path=str(v4_path) if v4_path.exists() else None,
            v6_model_path=str(v6_path) if v6_path.exists() else None,
        )
        logger.info("Classifier initialized")
        
    except Exception as e:
        components['errors'].append(f"Classifier initialization failed: {str(e)}")
        logger.error(f"Classifier initialization failed: {str(e)}")
    
    # Initialize Health Assessor
    try:
        from health_assessment import HealthAssessment
        components['health_assessor'] = HealthAssessment()
        logger.info("Health Assessor initialized")
        
    except Exception as e:
        components['errors'].append(f"Health Assessor initialization failed: {str(e)}")
        logger.error(f"Health Assessor initialization failed: {str(e)}")
    
    # Initialize Advisory System
    try:
        from advisory_system import AdvisorySystem
        components['advisory_system'] = AdvisorySystem()
        logger.info("Advisory System initialized")
        
    except Exception as e:
        components['errors'].append(f"Advisory System initialization failed: {str(e)}")
        logger.error(f"Advisory System initialization failed: {str(e)}")
    
    return components


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_analysis(form_data: dict, components: dict) -> dict:
    """
    Run the complete analysis pipeline.
    
    Args:
        form_data: Form data from user input
        components: Initialized system components
        
    Returns:
        Dictionary with all analysis results
    """
    results = {
        'success': False,
        'satellite_data': None,
        'classification': None,
        'health': None,
        'advisory': None,
        'error': None,
    }
    
    latitude = form_data['latitude']
    longitude = form_data['longitude']
    analysis_date = form_data['analysis_date']
    
    # Log request
    log_analysis_request(latitude, longitude)
    
    # Step 1: Fetch satellite data
    try:
        if components['gee_fetcher'] is None:
            raise RuntimeError("GEE Fetcher not initialized")
        
        with st.spinner("🛰️ Fetching satellite data..."):
            satellite_data = components['gee_fetcher'].fetch_temporal_data(
                latitude=latitude,
                longitude=longitude,
                query_date=analysis_date,
            )
        
        results['satellite_data'] = satellite_data
        
        if satellite_data['months_available'] == 0:
            results['error'] = "No satellite data available for this location"
            return results
            
    except Exception as e:
        results['error'] = f"Failed to fetch satellite data: {str(e)}"
        logger.error(results['error'])
        return results
    
    # Step 2: Classify crop
    try:
        if components['classifier'] is None:
            raise RuntimeError("Classifier not initialized")
        
        with st.spinner("🔍 Classifying crop type..."):
            classification = components['classifier'].predict(
                image=satellite_data['image'],
                availability=satellite_data['availability'],
                use_tta=form_data.get('use_tta', True),
            )
        
        results['classification'] = classification
        log_analysis_result(classification)
        
    except Exception as e:
        results['error'] = f"Classification failed: {str(e)}"
        logger.error(results['error'])
        return results
    
    # Step 3: Health assessment (if requested)
    if form_data.get('include_health', True):
        try:
            if components['health_assessor'] is None:
                raise RuntimeError("Health Assessor not initialized")
            
            with st.spinner("🌿 Assessing crop health..."):
                health = components['health_assessor'].assess(
                    image=satellite_data['image'],
                    availability=satellite_data['availability'],
                    crop=classification['predicted_class'],
                    growth_stage=satellite_data['growth_stage'],
                    month=analysis_date.month,
                )
            
            results['health'] = health
            
        except Exception as e:
            logger.warning(f"Health assessment failed: {str(e)}")
            # Non-fatal error, continue
    
    # Step 4: Generate advisory (if requested)
    if form_data.get('include_advisory', True) and results['health']:
        try:
            if components['advisory_system'] is None:
                raise RuntimeError("Advisory System not initialized")
            
            with st.spinner("📋 Generating recommendations..."):
                advisory = components['advisory_system'].generate_advisory(
                    crop=classification['predicted_class'],
                    growth_stage=satellite_data['growth_stage'],
                    health_result=results['health'],
                )
            
            results['advisory'] = advisory
            
        except Exception as e:
            logger.warning(f"Advisory generation failed: {str(e)}")
            # Non-fatal error, continue
    
    results['success'] = True
    return results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Main application entry point."""
    
    # Load custom CSS
    load_custom_css()
    
    # Render header
    render_header()
    
    # Render sidebar
    render_sidebar_info()
    
    # Initialize system
    components = initialize_system()
    
    # Check for initialization errors
    if components['errors']:
        st.warning("⚠️ Some components failed to initialize:")
        for error in components['errors']:
            st.error(error)
        st.info("Please check your configuration and model files.")
    
    # Main content area
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📍 Location Input")
        form_data = render_input_form()
    
    with col2:
        st.markdown("### 📊 Analysis Results")
        
        # Check if analysis was requested
        if form_data:
            # Store form data in session state
            st.session_state['last_form_data'] = form_data
            
            # Run analysis
            results = run_analysis(form_data, components)
            
            # Store results in session state
            st.session_state['last_results'] = results
        
        # Display results (from session state)
        if 'last_results' in st.session_state:
            results = st.session_state['last_results']
            form_data = st.session_state.get('last_form_data', {})
            
            if results.get('error'):
                render_error_state(
                    "Analysis Failed",
                    results['error']
                )
            
            elif not results.get('success'):
                render_no_data_state()
            
            else:
                # Successful analysis - display results
                
                # Map view
                if results['satellite_data']:
                    render_result_map(
                        latitude=form_data['latitude'],
                        longitude=form_data['longitude'],
                        classification_result=results['classification'],
                        health_result=results['health'],
                    )
                    
                    # Data availability
                    render_data_availability(
                        availability=results['satellite_data']['availability'],
                        season=results['satellite_data']['season'],
                    )
                
                st.markdown("---")
                
                # Results tabs
                tabs = st.tabs(["🌾 Classification", "🌿 Health", "📋 Advisory"])
                
                with tabs[0]:
                    if results['classification']:
                        render_classification_results(results['classification'])
                    else:
                        st.info("Classification not available")
                
                with tabs[1]:
                    if results['health']:
                        render_health_results(results['health'])
                    else:
                        st.info("Health assessment not available")
                
                with tabs[2]:
                    if results['advisory']:
                        render_advisory_results(results['advisory'])
                    else:
                        st.info("Advisory not available")
        
        else:
            # No analysis yet - show placeholder
            st.markdown("""
            <div style="background: #f5f5f5; border-radius: 15px; padding: 50px; 
                        text-align: center; color: #666;">
                <div style="font-size: 60px; margin-bottom: 20px;">🛰️</div>
                <h3>Ready to Analyze</h3>
                <p>Enter coordinates and click "Analyze Location" to get started.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px;">
        <p>
            AI-Driven Agricultural Field Monitoring and Farmer Advisory System<br>
            Final Year Project | Powered by Google Earth Engine & PyTorch
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
