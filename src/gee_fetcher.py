# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PAKISTAN CROP CLASSIFICATION SYSTEM - GEE FETCHER                         ║
# ║  Fetch Sentinel-2 satellite imagery from Google Earth Engine               ║
# ║  Always outputs 24-channel tensor with zero-padding for missing months     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import ee
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

from config import GEEConfig, TemporalConfig, ModelConfig, DateConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GEEFetcher:
    """
    Fetches Sentinel-2 satellite imagery from Google Earth Engine.
    
    Key Design:
    -----------
    - ALWAYS outputs a 24-channel tensor (6 months × 4 bands)
    - Missing months are ZERO-PADDED
    - Returns availability mask indicating which months have data
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
        scl = image.select('SCL')
        
        # Create mask (1 for clear, 0 for clouds)
        mask = (scl.neq(3)      # Cloud shadows
                .And(scl.neq(7))   # Cloud low probability
                .And(scl.neq(8))   # Cloud medium probability
                .And(scl.neq(9))   # Cloud high probability
                .And(scl.neq(10))) # Cirrus
        
        return image.updateMask(mask)
    
    def _get_date_range_for_month(self, year: int, month: int) -> Tuple[str, str]:
        """Get start and end date strings for a given month."""
        start_date = datetime(year, month, 1)
        
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def _create_monthly_composite(self, 
                                   geometry: ee.Geometry,
                                   year: int, 
                                   month: int) -> Tuple[Optional[ee.Image], int]:
        """
        Create a monthly median composite for the given location.
        
        Args:
            geometry: EE geometry for the location
            year: Year
            month: Month (1-12)
            
        Returns:
            Tuple of (ee.Image or None, image_count)
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
            return None, 0
        
        # Apply cloud masking and create median composite
        masked_collection = collection.map(self._mask_clouds)
        composite = masked_collection.median()
        
        # Select required bands
        composite = composite.select(GEEConfig.BANDS)
        
        logger.info(f"Created composite for {year}-{month:02d} from {count} images")
        return composite, count
    
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
        try:
            result = image.sampleRectangle(
                region=geometry,
                defaultValue=0
            )
            
            band_arrays = []
            for band in GEEConfig.BANDS:
                band_data = np.array(result.get(band).getInfo())
                band_arrays.append(band_data)
            
            image_array = np.stack(band_arrays, axis=0)
            return image_array.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Failed to convert image to array: {str(e)}")
            return np.zeros((len(GEEConfig.BANDS), 
                           ModelConfig.IMAGE_SIZE[0], 
                           ModelConfig.IMAGE_SIZE[1]), 
                          dtype=np.float32)
    
    def _get_season_month_mapping(self, season: str) -> Dict[int, int]:
        """
        Get mapping from calendar month to slot index (0-5) for a season.
        
        Args:
            season: 'Rice' or 'Wheat'
            
        Returns:
            Dict mapping calendar month → slot index
        """
        if season == 'Rice':
            # Rice season: May(5), Jun(6), Jul(7), Aug(8), Sep(9), Oct(10)
            # Slot:         0       1       2       3       4       5
            return {5: 0, 6: 1, 7: 2, 8: 3, 9: 4, 10: 5}
        else:
            # Wheat season: Nov(11), Dec(12), Jan(1), Feb(2), Mar(3), Apr(4)
            # Slot:          0        1        2       3       4       5
            return {11: 0, 12: 1, 1: 2, 2: 3, 3: 4, 4: 5}
    
    def _get_months_to_fetch(self, query_date: datetime, season: str) -> List[Tuple[int, int, int]]:
        """
        Determine which months to fetch based on query date and season.
        
        Args:
            query_date: Date of the query
            season: 'Rice' or 'Wheat'
            
        Returns:
            List of (year, month, slot_index) tuples
        """
        month = query_date.month
        year = query_date.year
        
        month_to_slot = self._get_season_month_mapping(season)
        months_to_fetch = []
        
        if season == 'Rice':
            # Rice season: May to October (same year)
            season_months = [5, 6, 7, 8, 9, 10]
            for m in season_months:
                if m <= month:  # Only fetch months up to query date
                    slot = month_to_slot[m]
                    months_to_fetch.append((year, m, slot))
        else:
            # Wheat season: Nov-Dec (year N) + Jan-Apr (year N+1)
            # Determine the wheat season year
            if month >= 11:
                # Nov or Dec of current year - wheat season just started
                wheat_start_year = year
            else:
                # Jan-Apr, wheat started previous year
                wheat_start_year = year - 1
            
            season_months = [(wheat_start_year, 11), (wheat_start_year, 12),
                           (wheat_start_year + 1, 1), (wheat_start_year + 1, 2),
                           (wheat_start_year + 1, 3), (wheat_start_year + 1, 4)]
            
            for m_year, m in season_months:
                m_date = datetime(m_year, m, 15)  # Mid-month
                if m_date <= query_date:
                    slot = month_to_slot[m]
                    months_to_fetch.append((m_year, m, slot))
        
        return months_to_fetch
    
    def fetch_temporal_stack(self,
                             latitude: float,
                             longitude: float,
                             query_date: datetime = None) -> Dict:
        """
        Fetch temporal satellite data and create 24-channel stack.
        
        ALWAYS returns a 24-channel tensor regardless of data availability.
        Missing months are ZERO-PADDED.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            query_date: Date of query (default: today)
            
        Returns:
            Dictionary containing:
                - 'image_stack': numpy array of shape (24, H, W) - ALWAYS 24 channels
                - 'availability_mask': list of 6 integers [0 or 1] for each month slot
                - 'months_available': count of months with data
                - 'season': 'Rice' or 'Wheat'
                - 'growth_stage': current growth stage
                - 'current_ndvi': NDVI from latest available month
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
        
        # Determine season based on query month
        season = TemporalConfig.get_season_for_month(query_date.month)
        
        # Get months to fetch
        months_to_fetch = self._get_months_to_fetch(query_date, season)
        
        logger.info(f"Season: {season}")
        logger.info(f"Fetching months: {months_to_fetch}")
        
        # ═══════════════════════════════════════════════════════════════════
        # STACKER: Initialize 24-channel tensor with ZEROS
        # ═══════════════════════════════════════════════════════════════════
        image_stack = np.zeros(
            (ModelConfig.NUM_CHANNELS,  # 24
             ModelConfig.IMAGE_SIZE[0],  # 64
             ModelConfig.IMAGE_SIZE[1]), # 64
            dtype=np.float32
        )
        
        # Initialize availability mask with zeros (all months unavailable)
        availability_mask = [0] * ModelConfig.NUM_MONTHS  # [0, 0, 0, 0, 0, 0]
        
        # Track the latest NDVI
        current_ndvi = None
        latest_month_data = None
        
        # ═══════════════════════════════════════════════════════════════════
        # Fetch data for each month and place in correct slot
        # ═══════════════════════════════════════════════════════════════════
        for year, month, slot_idx in months_to_fetch:
            try:
                # Create monthly composite
                composite, img_count = self._create_monthly_composite(region, year, month)
                
                if composite is None or img_count == 0:
                    logger.warning(f"No data for {year}-{month:02d}, slot {slot_idx} remains zero-padded")
                    continue
                
                # Convert to array
                month_data = self._image_to_array(composite, region)
                
                # ═══════════════════════════════════════════════════════════
                # CRITICAL FIX: Validate data BEFORE marking as available
                # GEE might find images but all pixels get cloud-masked!
                # ═══════════════════════════════════════════════════════════
                data_max = np.max(month_data)
                data_sum = np.sum(month_data)
                
                if data_max == 0 or data_sum == 0:
                    logger.warning(f"⚠️  {year}-{month:02d}: Images found but extracted data is all zeros!")
                    logger.warning(f"   Likely cause: All pixels were cloud-masked or region has no valid data")
                    logger.warning(f"   Slot {slot_idx} remains zero-padded")
                    continue  # Skip this month - don't mark as available!
                
                logger.info(f"   {year}-{month:02d} raw data: min={np.min(month_data):.0f}, max={data_max:.0f}, mean={np.mean(month_data):.0f}")
                
                # Resize if needed
                if month_data.shape[1:] != ModelConfig.IMAGE_SIZE:
                    from PIL import Image
                    resized_bands = []
                    for b in range(month_data.shape[0]):
                        band_img = Image.fromarray(month_data[b])
                        band_img = band_img.resize(ModelConfig.IMAGE_SIZE, Image.BILINEAR)
                        resized_bands.append(np.array(band_img))
                    month_data = np.stack(resized_bands, axis=0)
                
                # Normalize (Sentinel-2 values are 0-10000)
                month_data = month_data / 10000.0
                month_data = np.clip(month_data, 0, 1)
                
                # Double-check after scaling
                if np.max(month_data) < 0.001:  # Near-zero threshold
                    logger.warning(f"⚠️  {year}-{month:02d}: Data near-zero after scaling - skipping")
                    continue
                
                logger.info(f"   {year}-{month:02d} scaled: min={np.min(month_data):.4f}, max={np.max(month_data):.4f}")
                
                # ═══════════════════════════════════════════════════════════
                # Place data in correct slot of the 24-channel stack
                # Slot 0: channels 0-3
                # Slot 1: channels 4-7
                # Slot 2: channels 8-11
                # etc.
                # ═══════════════════════════════════════════════════════════
                start_channel = slot_idx * ModelConfig.NUM_BANDS  # slot_idx * 4
                end_channel = start_channel + ModelConfig.NUM_BANDS
                
                image_stack[start_channel:end_channel] = month_data
                availability_mask[slot_idx] = 1  # Mark this slot as available
                
                # Store for NDVI calculation
                latest_month_data = month_data
                
                logger.info(f"✓ Slot {slot_idx} filled with {year}-{month:02d} data (channels {start_channel}-{end_channel-1})")
                
            except Exception as e:
                logger.error(f"Error fetching {year}-{month:02d}: {str(e)}")
                continue
        
        # ═══════════════════════════════════════════════════════════════════
        # Calculate NDVI from latest available month
        # ═══════════════════════════════════════════════════════════════════
        if latest_month_data is not None:
            nir = latest_month_data[3]  # B8
            red = latest_month_data[2]  # B4
            with np.errstate(divide='ignore', invalid='ignore'):
                ndvi = (nir - red) / (nir + red + 1e-10)
                current_ndvi = float(np.nanmean(ndvi))
        else:
            current_ndvi = 0.0
        
        # Get growth stage
        growth_stage = TemporalConfig.get_growth_stage(season, query_date.month)
        months_available = sum(availability_mask)
        
        # ═══════════════════════════════════════════════════════════════════
        # Prepare result
        # ═══════════════════════════════════════════════════════════════════
        result = {
            'image_stack': image_stack,  # ALWAYS shape (24, 64, 64)
            'availability_mask': availability_mask,  # e.g., [1, 1, 1, 0, 0, 0]
            'months_available': months_available,
            'season': season,
            'growth_stage': growth_stage,
            'current_ndvi': current_ndvi,
            'metadata': {
                'latitude': latitude,
                'longitude': longitude,
                'query_date': query_date.strftime('%Y-%m-%d'),
                'months_fetched': months_to_fetch,
                'stack_shape': image_stack.shape,
            }
        }
        
        logger.info(f"═══════════════════════════════════════════════════")
        logger.info(f"STACKER OUTPUT:")
        logger.info(f"  Stack shape: {image_stack.shape}")
        logger.info(f"  Availability mask: {availability_mask}")
        logger.info(f"  Months available: {months_available}/6")
        logger.info(f"  Season: {season}")
        logger.info(f"═══════════════════════════════════════════════════")
        
        return result
    
    # Alias for backward compatibility
    def fetch_temporal_data(self, latitude, longitude, query_date=None):
        """Alias for fetch_temporal_stack (backward compatibility)."""
        result = self.fetch_temporal_stack(latitude, longitude, query_date)
        # Map new key names to old ones for compatibility
        result['image'] = result['image_stack']
        result['availability'] = result['availability_mask']
        return result
    
    def calculate_ndvi(self, 
                       latitude: float, 
                       longitude: float,
                       date: datetime = None) -> Dict:
        """
        Calculate current NDVI for a location (single date).
        """
        if date is None:
            date = datetime.now()
        
        point = ee.Geometry.Point([longitude, latitude])
        region = point.buffer(GEEConfig.BUFFER_SIZE).bounds()
        
        composite, count = self._create_monthly_composite(region, date.year, date.month)
        
        if composite is None:
            prev_date = date - timedelta(days=30)
            composite, count = self._create_monthly_composite(region, prev_date.year, prev_date.month)
        
        if composite is None:
            return {
                'mean_ndvi': None,
                'min_ndvi': None,
                'max_ndvi': None,
                'error': 'No cloud-free imagery available'
            }
        
        ndvi = composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
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
    """Factory function to create GEE Fetcher instance."""
    return GEEFetcher(service_account_key)


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing GEE Fetcher (Stacker)...")
    print("=" * 60)
    
    fetcher = GEEFetcher()
    
    lat, lon = 31.5, 73.2
    
    print(f"\nFetching data for ({lat}, {lon})...")
    result = fetcher.fetch_temporal_stack(lat, lon)
    
    print(f"\n{'=' * 60}")
    print(f"STACKER OUTPUT:")
    print(f"{'=' * 60}")
    print(f"  Stack Shape: {result['image_stack'].shape}")
    print(f"  Availability Mask: {result['availability_mask']}")
    print(f"  Months Available: {result['months_available']}/6")
    print(f"  Season: {result['season']}")
    print(f"  Growth Stage: {result['growth_stage']}")
    print(f"  Current NDVI: {result['current_ndvi']:.3f}")
    print(f"{'=' * 60}")