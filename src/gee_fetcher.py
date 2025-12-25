# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PAKISTAN CROP CLASSIFICATION SYSTEM - GEE FETCHER                         ║
# ║  Fetch Sentinel-2 satellite imagery from Google Earth Engine               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import ee
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

from config import GEEConfig, TemporalConfig, ModelConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GEEFetcher:
    """
    Fetches Sentinel-2 satellite imagery from Google Earth Engine.
    Handles authentication, cloud masking, and temporal compositing.
    """
    
    def __init__(self, service_account_key: str = None):
        """
        Initialize GEE Fetcher.
        
        Args:
            service_account_key: Path to service account JSON key file.
                                If None, uses default authentication.
        """
        self.service_account_key = service_account_key
        self.initialized = False
        self._initialize_ee()
    
    def _initialize_ee(self):
        """Initialize Earth Engine with service account credentials."""
        try:
            if self.service_account_key:
                # Service account authentication (production)
                with open(self.service_account_key) as f:
                    key_data = json.load(f)
                    service_account = key_data['client_email']
                
                credentials = ee.ServiceAccountCredentials(
                    service_account, 
                    self.service_account_key
                )
                ee.Initialize(credentials)
                logger.info(f"GEE initialized with service account: {service_account}")
            else:
                # Default authentication (development)
                ee.Initialize()
                logger.info("GEE initialized with default credentials")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize GEE: {str(e)}")
            self.initialized = False
            raise
    
    def _mask_clouds(self, image: ee.Image) -> ee.Image:
        """
        Mask clouds and cloud shadows from Sentinel-2 image.
        Uses SCL band for cloud masking.
        """
        # Scene Classification Layer (SCL) values:
        # 3: Cloud shadows, 7-10: Clouds
        scl = image.select('SCL')
        
        # Create mask (1 for clear, 0 for clouds)
        mask = (scl.neq(3)  # Cloud shadows
                .And(scl.neq(7))   # Cloud low probability
                .And(scl.neq(8))   # Cloud medium probability
                .And(scl.neq(9))   # Cloud high probability
                .And(scl.neq(10))) # Cirrus
        
        return image.updateMask(mask)
    
    def _get_date_range_for_month(self, year: int, month: int) -> Tuple[str, str]:
        """Get start and end date strings for a given month."""
        start_date = datetime(year, month, 1)
        
        # Get last day of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def _create_monthly_composite(self, 
                                   geometry: ee.Geometry,
                                   year: int, 
                                   month: int) -> Optional[ee.Image]:
        """
        Create a monthly median composite for the given location.
        
        Args:
            geometry: EE geometry for the location
            year: Year
            month: Month (1-12)
            
        Returns:
            ee.Image or None if no data available
        """
        start_date, end_date = self._get_date_range_for_month(year, month)
        
        # Filter collection
        collection = (ee.ImageCollection(GEEConfig.SENTINEL2_COLLECTION)
                     .filterBounds(geometry)
                     .filterDate(start_date, end_date)
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 
                                         GEEConfig.CLOUD_FILTER_PERCENT)))
        
        # Check if any images available
        count = collection.size().getInfo()
        
        if count == 0:
            logger.warning(f"No images found for {year}-{month:02d}")
            return None
        
        # Apply cloud masking and create median composite
        masked_collection = collection.map(self._mask_clouds)
        composite = masked_collection.median()
        
        # Select required bands
        composite = composite.select(GEEConfig.BANDS)
        
        logger.info(f"Created composite for {year}-{month:02d} from {count} images")
        return composite
    
    def _image_to_array(self, 
                        image: ee.Image, 
                        geometry: ee.Geometry) -> np.ndarray:
        """
        Convert EE image to numpy array.
        
        Args:
            image: EE Image with selected bands
            geometry: EE Geometry for the region
            
        Returns:
            numpy array of shape (bands, height, width)
        """
        # Get image as numpy array
        try:
            # Sample the region
            result = image.sampleRectangle(
                region=geometry,
                defaultValue=0
            )
            
            # Extract band arrays
            band_arrays = []
            for band in GEEConfig.BANDS:
                band_data = np.array(result.get(band).getInfo())
                band_arrays.append(band_data)
            
            # Stack bands: (bands, height, width)
            image_array = np.stack(band_arrays, axis=0)
            
            return image_array.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Failed to convert image to array: {str(e)}")
            # Return zeros if failed
            return np.zeros((len(GEEConfig.BANDS), 
                           ModelConfig.IMAGE_SIZE[0], 
                           ModelConfig.IMAGE_SIZE[1]), 
                          dtype=np.float32)
    
    def _get_season_months(self, query_date: datetime) -> Tuple[str, List[Tuple[int, int]]]:
        """
        Determine which crop season and months to fetch based on query date.
        
        Args:
            query_date: Date of the query
            
        Returns:
            Tuple of (season_name, list of (year, month) tuples)
        """
        month = query_date.month
        year = query_date.year
        
        # Determine season based on month
        if 5 <= month <= 11:
            # Rice season (Kharif)
            season = 'Rice'
            # Get all available months up to query date
            months_to_fetch = []
            for m in [5, 6, 8, 9, 10, 11]:  # Rice months (skip July)
                if m <= month:
                    months_to_fetch.append((year, m))
        else:
            # Wheat season (Rabi)
            season = 'Wheat'
            months_to_fetch = []
            
            # Wheat spans two years (Nov-Apr)
            if month >= 11:
                # Nov or Dec of current year
                wheat_year_start = year
            else:
                # Jan-Apr, wheat started previous year
                wheat_year_start = year - 1
            
            for m in [11, 12, 1, 2, 3, 4]:  # Wheat months
                if m >= 11:
                    m_year = wheat_year_start
                else:
                    m_year = wheat_year_start + 1
                
                # Check if this month is <= query date
                m_date = datetime(m_year, m, 1)
                if m_date <= query_date:
                    months_to_fetch.append((m_year, m))
        
        return season, months_to_fetch
    
    def fetch_temporal_data(self,
                           latitude: float,
                           longitude: float,
                           query_date: datetime = None) -> Dict:
        """
        Fetch temporal satellite data for a location.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            query_date: Date of query (default: today)
            
        Returns:
            Dictionary containing:
                - 'image': numpy array of shape (channels, height, width)
                - 'availability': list of 0/1 for each month
                - 'months_available': number of months with data
                - 'season': 'Rice' or 'Wheat'
                - 'growth_stage': current growth stage
                - 'metadata': additional information
        """
        if not self.initialized:
            raise RuntimeError("GEE not initialized. Check credentials.")
        
        if query_date is None:
            query_date = datetime.now()
        
        # Validate coordinates
        if not GEEConfig.is_in_punjab(latitude, longitude):
            logger.warning(f"Coordinates ({latitude}, {longitude}) outside Punjab region")
        
        # Create point geometry with buffer
        point = ee.Geometry.Point([longitude, latitude])
        region = point.buffer(GEEConfig.BUFFER_SIZE).bounds()
        
        # Determine season and months to fetch
        season, months_to_fetch = self._get_season_months(query_date)
        
        logger.info(f"Fetching {season} season data for ({latitude}, {longitude})")
        logger.info(f"Months to fetch: {months_to_fetch}")
        
        # Initialize output array (6 months × 4 bands × H × W)
        image_data = np.zeros((ModelConfig.NUM_CHANNELS, 
                              ModelConfig.IMAGE_SIZE[0], 
                              ModelConfig.IMAGE_SIZE[1]), 
                             dtype=np.float32)
        
        availability = [0] * ModelConfig.NUM_MONTHS
        
        # Map months to indices based on season
        if season == 'Rice':
            month_to_idx = {5: 0, 6: 1, 8: 2, 9: 3, 10: 4, 11: 5}  # May=0, Jun=1, Aug=2, etc.
        else:
            month_to_idx = {11: 0, 12: 1, 1: 2, 2: 3, 3: 4, 4: 5}  # Nov=0, Dec=1, Jan=2, etc.
        
        # Fetch data for each available month
        current_ndvi = None
        for year, month in months_to_fetch:
            try:
                # Create monthly composite
                composite = self._create_monthly_composite(region, year, month)
                
                if composite is None:
                    continue
                
                # Convert to array
                month_data = self._image_to_array(composite, region)
                
                # Resize to target size if needed
                if month_data.shape[1:] != ModelConfig.IMAGE_SIZE:
                    from PIL import Image
                    resized_bands = []
                    for b in range(month_data.shape[0]):
                        band_img = Image.fromarray(month_data[b])
                        band_img = band_img.resize(ModelConfig.IMAGE_SIZE, Image.BILINEAR)
                        resized_bands.append(np.array(band_img))
                    month_data = np.stack(resized_bands, axis=0)
                
                # Normalize
                month_data = month_data / 10000.0  # Sentinel-2 scaling
                month_data = np.clip(month_data, 0, 1)
                
                # Place in correct position
                month_idx = month_to_idx.get(month)
                if month_idx is not None:
                    start_ch = month_idx * ModelConfig.NUM_BANDS
                    end_ch = start_ch + ModelConfig.NUM_BANDS
                    image_data[start_ch:end_ch] = month_data
                    availability[month_idx] = 1
                
                # Calculate NDVI for current month
                if month == query_date.month:
                    nir = month_data[3]  # B8
                    red = month_data[2]  # B4
                    with np.errstate(divide='ignore', invalid='ignore'):
                        ndvi = (nir - red) / (nir + red + 1e-10)
                        current_ndvi = np.nanmean(ndvi)
                
                logger.info(f"Successfully fetched {year}-{month:02d}")
                
            except Exception as e:
                logger.error(f"Error fetching {year}-{month:02d}: {str(e)}")
                continue
        
        # Calculate current NDVI from latest available month if not set
        if current_ndvi is None and sum(availability) > 0:
            # Find latest available month
            for i in range(ModelConfig.NUM_MONTHS - 1, -1, -1):
                if availability[i] == 1:
                    start_ch = i * ModelConfig.NUM_BANDS
                    nir = image_data[start_ch + 3]  # B8
                    red = image_data[start_ch + 2]  # B4
                    with np.errstate(divide='ignore', invalid='ignore'):
                        ndvi = (nir - red) / (nir + red + 1e-10)
                        current_ndvi = float(np.nanmean(ndvi))
                    break
        
        # Get growth stage
        growth_stage = TemporalConfig.get_growth_stage(season, query_date.month)
        
        # Prepare result
        result = {
            'image': image_data,
            'availability': availability,
            'months_available': sum(availability),
            'season': season,
            'growth_stage': growth_stage,
            'current_ndvi': current_ndvi if current_ndvi is not None else 0.0,
            'metadata': {
                'latitude': latitude,
                'longitude': longitude,
                'query_date': query_date.strftime('%Y-%m-%d'),
                'months_fetched': months_to_fetch,
            }
        }
        
        logger.info(f"Fetch complete: {sum(availability)}/{ModelConfig.NUM_MONTHS} months available")
        
        return result
    
    def calculate_ndvi(self, 
                       latitude: float, 
                       longitude: float,
                       date: datetime = None) -> Dict:
        """
        Calculate current NDVI for a location (single date).
        
        Args:
            latitude: Latitude
            longitude: Longitude
            date: Date for NDVI calculation (default: today)
            
        Returns:
            Dictionary with NDVI statistics
        """
        if date is None:
            date = datetime.now()
        
        point = ee.Geometry.Point([longitude, latitude])
        region = point.buffer(GEEConfig.BUFFER_SIZE).bounds()
        
        # Get composite for current month
        composite = self._create_monthly_composite(region, date.year, date.month)
        
        if composite is None:
            # Try previous month
            prev_date = date - timedelta(days=30)
            composite = self._create_monthly_composite(region, prev_date.year, prev_date.month)
        
        if composite is None:
            return {
                'mean_ndvi': None,
                'min_ndvi': None,
                'max_ndvi': None,
                'error': 'No cloud-free imagery available'
            }
        
        # Calculate NDVI
        ndvi = composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Get statistics
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.minMax(), sharedInputs=True
            ),
            geometry=region,
            scale=GEEConfig.SCALE,
            maxPixels=1e9
        ).getInfo()
        
        return {
            'mean_ndvi': stats.get('NDVI_mean'),
            'min_ndvi': stats.get('NDVI_min'),
            'max_ndvi': stats.get('NDVI_max'),
            'date': date.strftime('%Y-%m-%d'),
        }


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def create_gee_fetcher(service_account_key: str = None) -> GEEFetcher:
    """
    Factory function to create GEE Fetcher instance.
    
    Args:
        service_account_key: Path to service account JSON key
        
    Returns:
        GEEFetcher instance
    """
    return GEEFetcher(service_account_key)


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with sample coordinates in Punjab
    print("Testing GEE Fetcher...")
    
    # This will use default auth (for testing)
    # In production, pass service account key
    fetcher = GEEFetcher()
    
    # Test location in Hafizabad, Punjab
    lat, lon = 31.5, 73.2
    
    print(f"\nFetching data for ({lat}, {lon})...")
    result = fetcher.fetch_temporal_data(lat, lon)
    
    print(f"\nResults:")
    print(f"  Season: {result['season']}")
    print(f"  Growth Stage: {result['growth_stage']}")
    print(f"  Months Available: {result['months_available']}/6")
    print(f"  Availability: {result['availability']}")
    print(f"  Current NDVI: {result['current_ndvi']:.3f}")
    print(f"  Image Shape: {result['image'].shape}")
