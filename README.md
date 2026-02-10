# AI-Driven Agricultural Field Monitoring and Farmer Advisory System

An automated crop monitoring system using satellite imagery and deep learning to classify crops, assess health, and provide farming recommendations for Pakistani smallholder farmers.

## Overview

This system combines Sentinel-2 satellite imagery with ResNet34-based deep learning models to:
- Classify agricultural fields into wheat, rice, and other land cover
- Monitor crop health using vegetation indices (NDVI, EVI, SAVI)
- Generate crop-specific farming advisories
- Provide an accessible web interface for farmers and extension officers

## Features

- **Automated Crop Classification**: 93.55% accuracy on 6-month sequences, 89.25% with variable 1-6 month inputs
- **Health Monitoring**: Real-time vegetation index calculation and anomaly detection
- **Advisory Generation**: Crop-specific recommendations for irrigation, fertilization, and pest control
- **Google Earth Engine Integration**: Automated satellite data retrieval without user authentication
- **Web Dashboard**: Interactive visualization with bilingual support (English/Urdu)

## System Requirements

### Hardware
- CPU: Intel i5 or equivalent
- RAM: 8-16 GB minimum
- Storage: 250 GB
- GPU: Optional NVIDIA CUDA-compatible (for faster inference)

### Software
- Python 3.8+
- Ubuntu 20.04+ or Windows 10/11
- Modern web browser (Chrome 90+, Firefox 88+, Edge 90+)

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/m-qa5im/AI-Driven-Agricultural-Field-Monitoring-and-Farmer-Advisory-System-Using-Remote-Sensing.git
cd AI-Driven-Agricultural-Field-Monitoring-and-Farmer-Advisory-System-Using-Remote-Sensing
```

2. **Install dependencies**
```bash
pip install -r requirements.txt --break-system-packages
```

3. **Set up credentials**

   a. **Google Earth Engine Service Account**
   - Create a service account in Google Cloud Console
   - Download the JSON key file
   - Place it as `credentials/gee_service_account.json`

   b. **Gemini API Configuration**
   - Create a `.env` file in the `src/` folder
   - Add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Dataset

The model was trained on a Pakistan-specific dataset of 616 samples from Hafizabad and Sheikhupura districts in Punjab:
- **Wheat**: 200 samples (Rabi season: Nov-Apr)
- **Rice**: 216 samples (Kharif season: May-Oct)
- **Other**: 200 samples (mixed land cover)

**Dataset Access**: [Google Drive Link](https://drive.google.com/drive/folders/1NLR63mRqFqPJ9vHErCWDo6W8ahwF-PbB?usp=sharing)

Each sample contains 6-month temporal sequences of 4 spectral bands (Blue, Green, Red, Near-Infrared) from Sentinel-2 imagery.

## Usage

1. **Start the web application**
```bash
cd src
streamlit run app.py
```

2. **Access the dashboard**
   - Open browser at `http://localhost:8501`
   - Enter field coordinates (latitude, longitude)
   - Select temporal range
   - View classification results, health metrics, and advisories

3. **Export results**
   - Download classification maps (GeoTIFF)
   - Export health metrics (CSV)
   - Generate comprehensive reports (PDF)

## Model Information

### Available Models
- **V4 Model**: 93.55% accuracy, requires complete 6-month sequences
- **V6 Model**: 89.25% accuracy, supports variable 1-6 month inputs

The system automatically selects the appropriate model based on data availability.

### Performance
- **Accuracy**: >85% on all temporal configurations (4+ months)
- **Processing Time**: 5-7 minutes end-to-end per field (10 km²)
- **Supported Classes**: Wheat, Rice, Other

## Project Structure

```
├── src/                    # Source code
│   ├── app.py             # Streamlit web application
│   ├── .env               # Gemini API configuration (create this)
│   └── ...
├── credentials/           # Authentication files
│   └── gee_service_account.json  # GEE service account (add this)
├── models/               # Trained model weights
│   ├── V4/              # Fixed 6-month model
│   └── V6/              # Variable input model
└── requirements.txt     # Python dependencies
```

## Configuration Files Required

### 1. `.env` in `src/` folder
```
GEMINI_API_KEY=your_gemini_api_key_here
```
This enables the AI-powered advisory generation system.

### 2. `gee_service_account.json` in `credentials/` folder
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  ...
}
```
This enables automated Sentinel-2 imagery retrieval from Google Earth Engine.

## System Architecture

1. **Data Acquisition**: Google Earth Engine API retrieves Sentinel-2 imagery
2. **Preprocessing**: Cloud filtering, normalization, temporal stacking
3. **Classification**: ResNet34 model predicts crop type
4. **Health Monitoring**: Vegetation index calculation and anomaly detection
5. **Advisory Generation**: Rule-based recommendations using Gemini AI
6. **Presentation**: Streamlit dashboard with interactive visualizations

## Limitations

- Geographic scope limited to Punjab province training data
- Requires internet connection for satellite data retrieval
- Single-user local deployment (cloud scaling planned)
- Optical imagery only (affected by cloud cover)
- 3-class classification (no variety-level discrimination)

## Future Work

- Geographic expansion to other Pakistani provinces
- Multi-sensor fusion (Sentinel-1 SAR integration)
- Mobile application development
- Cloud deployment for multi-user support
- Yield prediction capabilities
- Regional language support (Punjabi, Sindhi, Pashto)

## Authors

- **Awais Ali** (BS-CSC-S22-18079)
- **Muhammad Qasim** (BS-CSC-S22-18047)

**Supervisor**: Dr. Maria Tariq  
**Institution**: Lahore Garrison University, Department of Computer Science  
**Session**: Spring 2022-2026

## License

This project is developed as a Final Year Project at Lahore Garrison University.

## Acknowledgments

- Dr. Maria Tariq for supervision and guidance
- Lahore Garrison University Computer Science Department
- European Space Agency for Sentinel-2 imagery
- Google Earth Engine platform

## Citation

If you use this system in your research, please cite:
```
Ali, A., & Qasim, M. (2026). AI-Driven Agricultural Field Monitoring and Farmer Advisory System 
Using Remote Sensing. Final Year Project, Lahore Garrison University.
```

## Contact

For questions or support, please open an issue on GitHub or contact the authors through the university.
