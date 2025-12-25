#!/usr/bin/env python3
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI-DRIVEN AGRICULTURAL FIELD MONITORING AND FARMER ADVISORY SYSTEM        ║
# ║  Application Entry Point                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

"""
Run the Streamlit application.

Usage:
    python run.py
    
Or directly:
    streamlit run app/app.py
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    # Package name -> Import name mapping
    required = {
        'streamlit': 'streamlit',
        'torch': 'torch',
        'earthengine-api': 'ee',  # earthengine-api imports as 'ee'
        'folium': 'folium',
        'plotly': 'plotly',
        'Pillow': 'PIL',  # Pillow imports as 'PIL'
    }
    
    missing = []
    for package_name, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print("❌ Missing dependencies:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    return True


def check_files():
    """Check if required files exist."""
    project_root = Path(__file__).parent
    
    required_files = {
        'src/config.py': 'Configuration file',
        'src/gee_fetcher.py': 'GEE Fetcher module',
        'src/model_inference.py': 'Model Inference module',
        'src/health_assessment.py': 'Health Assessment module',
        'src/advisory_system.py': 'Advisory System module',
        'app/app.py': 'Main application',
    }
    
    optional_files = {
        'models/best_model_v4.pth': 'V4 Model weights',
        'models/best_model_v6_variable.pth': 'V6 Model weights',
        'credentials/gee_service_account.json': 'GEE Service Account',
    }
    
    print("\n📋 Checking required files...")
    all_present = True
    
    for file_path, description in required_files.items():
        full_path = project_root / file_path
        if full_path.exists():
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} (missing: {file_path})")
            all_present = False
    
    print("\n📋 Checking optional files...")
    for file_path, description in optional_files.items():
        full_path = project_root / file_path
        if full_path.exists():
            print(f"   ✅ {description}")
        else:
            print(f"   ⚠️  {description} (missing: {file_path})")
    
    return all_present


def main():
    """Main entry point."""
    print("=" * 60)
    print("🌾 AI-Driven Agricultural Field Monitoring System")
    print("=" * 60)
    
    # Check dependencies
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("   ✅ All dependencies installed")
    
    # Check files
    if not check_files():
        print("\n❌ Some required files are missing. Please check your setup.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🚀 Starting Streamlit application...")
    print("=" * 60)
    print("\n   Open your browser at: http://localhost:8501")
    print("   Press Ctrl+C to stop the server\n")
    
    # Get the path to app.py
    project_root = Path(__file__).parent
    app_path = project_root / "app" / "app.py"
    
    # Run Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped.")


if __name__ == "__main__":
    main()