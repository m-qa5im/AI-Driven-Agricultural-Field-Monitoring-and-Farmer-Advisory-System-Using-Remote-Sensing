# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI-DRIVEN AGRICULTURAL FIELD MONITORING SYSTEM                            ║
# ║  Results Display Component                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import streamlit as st
from typing import Dict, List
import plotly.graph_objects as go
import plotly.express as px

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import UIConfig, ModelConfig
from app.utils.helpers import (
    get_confidence_badge, get_health_badge, get_crop_icon, 
    get_crop_color, format_probabilities, get_data_quality_indicator,
    format_ndvi
)


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATION RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def render_classification_results(result: Dict) -> None:
    """
    Render crop classification results.
    
    Args:
        result: Classification result dictionary
    """
    
    predicted_class = result.get('predicted_class', 'Unknown')
    confidence = result.get('confidence', 0)
    confidence_level = result.get('confidence_level', 'low')
    probabilities = result.get('probabilities', {})
    model_used = result.get('model_used', 'Unknown')
    months_available = result.get('months_available', 0)
    
    # Get display elements
    crop_icon = get_crop_icon(predicted_class)
    crop_color = get_crop_color(predicted_class)
    conf_icon, conf_label, conf_color = get_confidence_badge(confidence_level)
    
    # Main result card
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {crop_color}22 0%, {crop_color}11 100%);
                border: 2px solid {crop_color}; border-radius: 15px; padding: 25px;
                margin-bottom: 20px;">
        
        <div style="text-align: center;">
            <div style="font-size: 60px; margin-bottom: 10px;">{crop_icon}</div>
            <h2 style="margin: 0; color: {crop_color};">{predicted_class}</h2>
            <p style="font-size: 14px; color: #666; margin: 5px 0;">Predicted Crop Type</p>
        </div>
        
        <div style="display: flex; justify-content: center; gap: 30px; margin-top: 20px;">
            <div style="text-align: center;">
                <div style="font-size: 28px; font-weight: bold; color: {conf_color};">
                    {confidence:.1%}
                </div>
                <div style="font-size: 12px; color: #666;">Confidence</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 28px;">{conf_icon}</div>
                <div style="font-size: 12px; color: #666;">{conf_label}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Probability distribution
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("##### 📊 Class Probabilities")
        _render_probability_bars(probabilities)
    
    with col2:
        st.markdown("##### ℹ️ Model Info")
        st.markdown(f"""
        <div style="background: #f5f5f5;color: #000000; padding: 15px; border-radius: 10px;">
            <p style="margin: 5px 0;"><strong>Model:</strong> {model_used}</p>
            <p style="margin: 5px 0;"><strong>Data:</strong> {months_available}/6 months</p>
            <p style="margin: 5px 0;"><strong>Quality:</strong> {_get_quality_label(months_available)}</p>
        </div>
        """, unsafe_allow_html=True)


def _render_probability_bars(probabilities: Dict) -> None:
    """Render horizontal probability bars."""
    
    formatted = format_probabilities(probabilities)
    
    for item in formatted:
        percentage = item['probability'] * 100
        color = item['color']
        
        st.markdown(f"""
        <div style="margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
                <span>{item['icon']} {item['class']}</span>
                <span style="font-weight: bold;">{item['percentage']}</span>
            </div>
            <div style="background: #e0e0e0; border-radius: 5px; height: 20px; overflow: hidden;">
                <div style="background: {color}; width: {percentage}%; height: 100%; 
                            border-radius: 5px; transition: width 0.5s ease;">
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _get_quality_label(months: int) -> str:
    """Get quality label based on months available."""
    if months >= 5:
        return "✅ Excellent"
    elif months >= 4:
        return "✅ Good"
    elif months >= 3:
        return "⚠️ Moderate"
    else:
        return "⚠️ Limited"


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH ASSESSMENT RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def render_health_results(result: Dict) -> None:
    """
    Render health assessment results.
    
    Args:
        result: Health assessment result dictionary
    """
    
    status = result.get('status', 'unknown')
    ndvi = result.get('current_ndvi', 0)
    growth_stage = result.get('growth_stage', 'Unknown')
    expected_range = result.get('expected_range', (0, 1))
    deviation = result.get('deviation_percent', 0)
    crop = result.get('crop', 'Unknown')
    
    # Get display elements
    health_icon, health_label, health_color = get_health_badge(status)
    ndvi_info = format_ndvi(ndvi)
    
    # Health status card
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {health_color}22 0%, {health_color}11 100%);
                border: 2px solid {health_color}; border-radius: 15px; padding: 25px;
                margin-bottom: 20px;">
        
        <div style="display: flex; align-items: center; gap: 20px;">
            <div style="font-size: 50px;">{health_icon}</div>
            <div>
                <h3 style="margin: 0; color: {health_color};">{health_label}</h3>
                <p style="margin: 5px 0 0 0; color: #666;">
                    {crop} • {growth_stage}
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # NDVI Details
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 🌿 NDVI Analysis")
        
        # NDVI gauge
        _render_ndvi_gauge(ndvi, expected_range)
        
        st.markdown(f"""
        <div style="text-align: center; margin-top: 10px;">
            <p style="margin: 0; color: #666;">
                <strong>Current:</strong> {ndvi:.3f} | 
                <strong>Expected:</strong> {expected_range[0]:.2f} - {expected_range[1]:.2f}
            </p>
            <p style="margin: 5px 0 0 0; font-size: 13px; color: {'#e74c3c' if deviation < -10 else '#27ae60'};">
                Deviation: {deviation:+.1f}%
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("##### 📈 Interpretation")
        
        st.markdown(f"""
        <div style="background: #f8f9fa;color: #000000; padding: 15px; border-radius: 10px;">
            <p style="margin: 0 0 10px 0;">
                <strong>NDVI Value:</strong> {ndvi:.3f}
            </p>
            <p style="margin: 0 0 10px 0;">
                <strong>Meaning:</strong> {ndvi_info['interpretation']}
            </p>
            <p style="margin: 0 0 10px 0;">
                <strong>Growth Stage:</strong> {growth_stage}
            </p>
            <p style="margin: 0;">
                <strong>Assessment:</strong> {_get_health_interpretation(status, deviation)}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Temporal trend if available
    if 'temporal_analysis' in result:
        _render_temporal_trend(result['temporal_analysis'])


def _render_ndvi_gauge(ndvi: float, expected_range: tuple) -> None:
    """Render NDVI gauge chart."""
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ndvi,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'suffix': "", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [-0.1, 1], 'tickwidth': 1},
            'bar': {'color': "#2e7d32"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#ccc",
            'steps': [
                {'range': [-0.1, 0.1], 'color': '#8B4513'},
                {'range': [0.1, 0.2], 'color': '#D2B48C'},
                {'range': [0.2, 0.4], 'color': '#90EE90'},
                {'range': [0.4, 0.6], 'color': '#32CD32'},
                {'range': [0.6, 1.0], 'color': '#006400'},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': expected_range[0]
            }
        }
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=30, b=10),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _get_health_interpretation(status: str, deviation: float) -> str:
    """Get human-readable health interpretation."""
    
    interpretations = {
        'healthy': "Crop is developing normally with good vegetation vigor.",
        'moderate_stress': "Crop shows signs of stress. Monitor closely and review recommendations.",
        'severe_stress': "Significant stress detected. Immediate attention recommended.",
        'critical': "Critical condition. Urgent intervention required.",
    }
    
    base = interpretations.get(status, "Unable to assess.")
    
    if deviation < -20:
        base += " NDVI is significantly below expected levels."
    elif deviation < -10:
        base += " NDVI is moderately below expected levels."
    
    return base


def _render_temporal_trend(analysis: Dict) -> None:
    """Render temporal NDVI trend chart."""
    
    if not analysis or analysis.get('trend') == 'insufficient_data':
        return
    
    st.markdown("##### 📊 Temporal NDVI Trend")
    
    ndvi_values = analysis.get('ndvi_values', [])
    months = analysis.get('months', [])
    
    if len(ndvi_values) < 2:
        return
    
    # Create trend chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=months,
        y=ndvi_values,
        mode='lines+markers',
        name='NDVI',
        line=dict(color='#2e7d32', width=3),
        marker=dict(size=10),
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=30, b=40),
        xaxis_title="Month",
        yaxis_title="NDVI",
        yaxis=dict(range=[0, 1]),
        showlegend=False,
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Trend description
    trend = analysis.get('trend', 'stable')
    trend_desc = analysis.get('trend_description', '')
    
    trend_colors = {
        'improving': '#27ae60',
        'stable': '#3498db',
        'declining': '#e74c3c',
    }
    
    st.markdown(f"""
    <p style="text-align: center; color: {trend_colors.get(trend, '#666')};">
        <strong>Trend:</strong> {trend_desc}
    </p>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ADVISORY RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def render_advisory_results(advisory: Dict) -> None:
    """
    Render advisory recommendations.
    
    Args:
        advisory: Advisory result dictionary
    """
    
    summary = advisory.get('summary', '')
    recommendations = advisory.get('recommendations', [])
    action_plan = advisory.get('action_plan', {})
    
    # Summary card
    st.markdown(f"""
    <div style="background: #e3f2fd; border-left: 4px solid #2196f3; 
                padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin: 0 0 10px 0; color: #1565c0;">📋 Summary</h4>
        <p style="margin: 0; color: #333;">{summary}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Action plan
    if action_plan:
        st.markdown("##### ⏱️ Action Plan")
        
        timeframe = action_plan.get('timeframe', '')
        st.markdown(f"""
        <div style="background: #fff8e1; padding: 10px 15px; border-radius: 5px; margin-bottom: 15px;">
            <strong>⏰ Timeframe:</strong> {timeframe}
        </div>
        """, unsafe_allow_html=True)
        
        # Immediate actions
        immediate = action_plan.get('immediate', [])
        if immediate:
            st.markdown("**🚨 Immediate Actions:**")
            for action in immediate:
                st.markdown(f"""
                <div style="background: #ffebee; padding: 10px; border-radius: 5px; 
                            margin: 5px 0; border-left: 3px solid #f44336;">
                    {action}
                </div>
                """, unsafe_allow_html=True)
        
        # Short-term actions
        short_term = action_plan.get('short_term', [])
        if short_term:
            st.markdown("**📅 Short-term Actions:**")
            for action in short_term:
                st.markdown(f"""
                <div style="background: #fff3e0; padding: 10px; border-radius: 5px; 
                            margin: 5px 0; border-left: 3px solid #ff9800;">
                    {action}
                </div>
                """, unsafe_allow_html=True)
    
    # All recommendations (expandable)
    if recommendations:
        with st.expander(f"📝 All Recommendations ({len(recommendations)})", expanded=False):
            for rec in recommendations:
                priority = rec.get('priority', 'low')
                icon = rec.get('icon', '📋')
                text = rec.get('text', '')
                
                priority_colors = {
                    'high': '#ffebee',
                    'medium': '#fff3e0',
                    'low': '#e8f5e9',
                }
                
                st.markdown(f"""
                <div style="background: {priority_colors.get(priority, '#f5f5f5')}; 
                            padding: 10px; border-radius: 5px; margin: 5px 0;">
                    {icon} <strong>[{priority.upper()}]</strong> {text}
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# LOADING & ERROR STATES
# ─────────────────────────────────────────────────────────────────────────────

def render_loading_state(message: str = "Analyzing...") -> None:
    """Render loading state."""
    
    st.markdown(f"""
    <div style="text-align: center; padding: 50px;">
        <div style="font-size: 50px; animation: pulse 1s infinite;">🛰️</div>
        <h3 style="color: #666;">{message}</h3>
        <p style="color: #999;">Please wait while we fetch and analyze satellite data...</p>
    </div>
    
    <style>
    @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.1); }}
        100% {{ transform: scale(1); }}
    }}
    </style>
    """, unsafe_allow_html=True)


def render_error_state(error_message: str, details: str = None) -> None:
    """Render error state."""
    
    st.markdown(f"""
    <div style="background: #ffebee; border: 1px solid #ef5350; 
                border-radius: 10px; padding: 20px; text-align: center;">
        <div style="font-size: 40px;">❌</div>
        <h4 style="color: #c62828; margin: 10px 0;">{error_message}</h4>
        {f'<p style="color: #666; font-size: 14px;">{details}</p>' if details else ''}
    </div>
    """, unsafe_allow_html=True)


def render_no_data_state() -> None:
    """Render no data state."""
    
    st.markdown("""
    <div style="background: #fff3e0; border: 1px solid #ffb74d; 
                border-radius: 10px; padding: 20px; text-align: center;">
        <div style="font-size: 40px;">📡</div>
        <h4 style="color: #e65100; margin: 10px 0;">No Satellite Data Available</h4>
        <p style="color: #666;">
            No cloud-free satellite imagery found for this location and time period.
            Try selecting a different date or location.
        </p>
    </div>
    """, unsafe_allow_html=True)
