# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                                 GEE FETCHER                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import ee
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from PIL import Image as PILImage

from config import GEEConfig, TemporalConfig, ModelConfig, DateConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GEEFetcher:
    
    def __init__(self, service_account_key: str = None):
        self.service_account_key = service_account_key
        self.initialized = False
        self._initialize_ee()
    
    def _initialize_ee(self):
        """Initialize Earth Engine."""
        try:
            if self.service_account_key:
                with open(self.service_account_key) as f:
                    key_data = json.load(f)
                    service_account = key_data['client_email']
                
                credentials = ee.ServiceAccountCredentials(
                    service_account, 
                    self.service_account_key
                )
                ee.Initialize(credentials)
                logger.info(f"GEE initialized: {service_account}")
            else:
                ee.Initialize()
                logger.info("GEE initialized with default credentials")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize GEE: {str(e)}")
            raise
    
    def _mask_clouds(self, image: ee.Image) -> ee.Image:
        """
        Cloud masking using SCL band - LENIENT version.
        Only masks high-confidence clouds.
        """
        scl = image.select('SCL')
        
        # Only mask severe issues:
        # 3 = cloud shadows
        # 8 = cloud medium probability  
        # 9 = cloud high probability
        # 10 = cirrus
        mask = (scl.neq(3)
                .And(scl.neq(8))
                .And(scl.neq(9))
                .And(scl.neq(10)))
        
        return image.updateMask(mask)
    
    def _get_date_range_for_month(self, year: int, month: int) -> Tuple[str, str]:
        """Get start and end date for a month."""
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
        Create monthly composite with proper filtering.
        """
        start_date, end_date = self._get_date_range_for_month(year, month)
        
        # More lenient cloud filter
        collection = (ee.ImageCollection(GEEConfig.SENTINEL2_COLLECTION)
                     .filterBounds(geometry)
                     .filterDate(start_date, end_date)
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 90)))
        
        count = collection.size().getInfo()
        
        if count == 0:
            logger.warning(f"   No images for {year}-{month:02d}")
            return None, 0
        
        logger.info(f"   Found {count} images for {year}-{month:02d}")
        
        # Apply cloud masking
        masked_collection = collection.map(self._mask_clouds)
        composite = masked_collection.median()
        
        # Select required bands
        composite = composite.select(GEEConfig.BANDS)
        
        return composite, count
    
    def _image_to_array_proper(self, 
                                image: ee.Image, 
                                region: ee.Geometry) -> np.ndarray:
        try:
            # ═══════════════════════════════════════════════════════════════
            # METHOD 1: getRegion 
            # ═══════════════════════════════════════════════════════════════
            try:
                # Get region as a rectangle
                rect = region.bounds()
                
                sampled = image.sample(
                    region=rect,
                    scale=10,  # Sentinel-2 resolution
                    geometries=True,
                    numPixels=64 * 64  # Target number of pixels
                )
                
                sample_size = sampled.size().getInfo()
                
                if sample_size > 0:
                    logger.info(f"      Method 1 (sample): Got {sample_size} pixels")
                    
                    # Convert to list of features
                    features = sampled.toList(sample_size).getInfo()
                    
                    if features and len(features) > 0:
                        # Extract band values from features
                        band_data = {band: [] for band in GEEConfig.BANDS}
                        
                        for feature in features:
                            props = feature['properties']
                            for band in GEEConfig.BANDS:
                                if band in props and props[band] is not None:
                                    band_data[band].append(props[band])
                        
                        # Check if we got valid data
                        if all(len(band_data[band]) > 0 for band in GEEConfig.BANDS):
                            # Convert to 2D grid (approximate)
                            grid_size = int(np.sqrt(len(features)))
                            if grid_size == 0:
                                grid_size = 1
                            
                            arrays = []
                            for band in GEEConfig.BANDS:
                                values = np.array(band_data[band])
                                # Reshape to square grid
                                if len(values) >= grid_size * grid_size:
                                    grid = values[:grid_size * grid_size].reshape(grid_size, grid_size)
                                else:
                                    # Pad if necessary
                                    padded = np.pad(values, (0, grid_size * grid_size - len(values)), 
                                                  mode='constant', constant_values=0)
                                    grid = padded.reshape(grid_size, grid_size)
                                
                                arrays.append(grid)
                            
                            result = np.stack(arrays, axis=0)
                            
                            if np.max(result) > 0:
                                logger.info(f"      ✓ Method 1 SUCCESS: {result.shape}, max={np.max(result):.0f}")
                                return result
                
            except Exception as e:
                logger.warning(f"      Method 1 failed: {str(e)}")
            
            # ═══════════════════════════════════════════════════════════════
            # METHOD 2: sampleRectangle with proper geometry
            # ═══════════════════════════════════════════════════════════════
            try:
                
                bounds = region.bounds().getInfo()['coordinates'][0]
                
                
                rect_geom = ee.Geometry.Rectangle(
                    coords=[bounds[0], bounds[1], bounds[2], bounds[3]],
                    proj='EPSG:4326',
                    geodesic=False
                )
                
                
                result = image.sampleRectangle(
                    region=rect_geom,
                    defaultValue=0,
                    properties=[],
                )
                
                band_arrays = []
                for band in GEEConfig.BANDS:
                    band_data = np.array(result.get(band).getInfo())
                    band_arrays.append(band_data)
                
                result_array = np.stack(band_arrays, axis=0).astype(np.float32)
                
                if np.max(result_array) > 0:
                    logger.info(f"      ✓ Method 2 SUCCESS: {result_array.shape}, max={np.max(result_array):.0f}")
                    return result_array
                else:
                    logger.warning(f"      Method 2: Got zeros")
                    
            except Exception as e:
                logger.warning(f"      Method 2 failed: {str(e)}")
            
            # ═══════════════════════════════════════════════════════════════
            # METHOD 3: getThumbURL 
            # ═══════════════════════════════════════════════════════════════
            try:
                logger.info(f"      Trying Method 3 (getThumbURL)...")
                
                # Get thumbnail URL with proper visualization
                thumb_params = {
                    'region': region,
                    'dimensions': '64x64',
                    'format': 'png',
                    'bands': GEEConfig.BANDS,
                    'min': 0,
                    'max': 3000,  # Typical reflectance range
                }
                
                url = image.getThumbURL(thumb_params)
                
                import requests
                response = requests.get(url)
                
                if response.status_code == 200:
                    from io import BytesIO
                    img = PILImage.open(BytesIO(response.content))
                    img_array = np.array(img)
                    
                    
                    if len(img_array.shape) == 3:
                    
                        if img_array.shape[2] == 3:
                            logger.warning(f"      Method 3: Only got RGB from thumbnail")
                        else:
                            result_array = np.moveaxis(img_array[:, :, :4], 2, 0).astype(np.float32)
                            result_array = (result_array / 255.0) * 3000.0
                            
                            if np.max(result_array) > 0:
                                logger.info(f"      ✓ Method 3 SUCCESS: {result_array.shape}")
                                return result_array
                
            except Exception as e:
                logger.warning(f"      Method 3 failed: {str(e)}")
            
            # ═══════════════════════════════════════════════════════════════
            # All methods failed - return zeros
            # ═══════════════════════════════════════════════════════════════
            logger.error(f"      ❌ ALL METHODS FAILED - returning zeros")
            return np.zeros((len(GEEConfig.BANDS), 
                           ModelConfig.IMAGE_SIZE[0], 
                           ModelConfig.IMAGE_SIZE[1]), 
                          dtype=np.float32)
            
        except Exception as e:
            logger.error(f"      Fatal error in image_to_array: {str(e)}")
            return np.zeros((len(GEEConfig.BANDS), 
                           ModelConfig.IMAGE_SIZE[0], 
                           ModelConfig.IMAGE_SIZE[1]), 
                          dtype=np.float32)
    
    def _get_season_month_mapping(self, season: str) -> Dict[int, int]:
        """Get month to slot mapping."""
        if season == 'Rice':
            return {5: 0, 6: 1, 7: 2, 8: 3, 9: 4, 10: 5}
        else:
            return {11: 0, 12: 1, 1: 2, 2: 3, 3: 4, 4: 5}
    
    def _get_months_to_fetch(self, query_date: datetime, season: str) -> List[Tuple[int, int, int]]:
        """Determine which months to fetch."""
        month = query_date.month
        year = query_date.year
        
        month_to_slot = self._get_season_month_mapping(season)
        months_to_fetch = []
        
        if season == 'Rice':
            season_months = [5, 6, 7, 8, 9, 10]
            for m in season_months:
                if m <= month:
                    slot = month_to_slot[m]
                    months_to_fetch.append((year, m, slot))
        else:
            if month >= 11:
                wheat_start_year = year
            else:
                wheat_start_year = year - 1
            
            season_months = [(wheat_start_year, 11), (wheat_start_year, 12),
                           (wheat_start_year + 1, 1), (wheat_start_year + 1, 2),
                           (wheat_start_year + 1, 3), (wheat_start_year + 1, 4)]
            
            for m_year, m in season_months:
                m_date = datetime(m_year, m, 15)
                if m_date <= query_date:
                    slot = month_to_slot[m]
                    months_to_fetch.append((m_year, m, slot))
        
        return months_to_fetch
    
    def fetch_temporal_stack(self,
                             latitude: float,
                             longitude: float,
                             query_date: datetime = None) -> Dict:
        """
        Fetch temporal satellite data using proper GEE methods.
        """
        if not self.initialized:
            raise RuntimeError("GEE not initialized")
        
        if query_date is None:
            query_date = datetime.now()
        
        # Create geometry - LARGER buffer for better sampling
        point = ee.Geometry.Point([longitude, latitude])
        region = point.buffer(640).bounds()  # 640m = ~64 pixels at 10m resolution
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Location: ({latitude}, {longitude})")
        logger.info(f"Buffer: 640m")
        logger.info(f"Query date: {query_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*60}\n")
        
        # Determine season
        season = TemporalConfig.get_season_for_month(query_date.month)
        months_to_fetch = self._get_months_to_fetch(query_date, season)
        
        logger.info(f"Season: {season}")
        logger.info(f"Months to fetch: {len(months_to_fetch)}\n")
        
        # Initialize stack
        image_stack = np.zeros(
            (ModelConfig.NUM_CHANNELS, ModelConfig.IMAGE_SIZE[0], ModelConfig.IMAGE_SIZE[1]),
            dtype=np.float32
        )
        availability_mask = [0] * ModelConfig.NUM_MONTHS
        
        current_ndvi = None
        latest_month_data = None
        successful_months = []
        
        # Fetch each month
        for year, month, slot_idx in months_to_fetch:
            logger.info(f"{'─'*60}")
            logger.info(f"Fetching: {year}-{month:02d} (Slot {slot_idx})")
            logger.info(f"{'─'*60}")
            
            try:
                composite, img_count = self._create_monthly_composite(region, year, month)
                
                if composite is None or img_count == 0:
                    logger.warning(f"   ✗ No images available\n")
                    continue
                
                # Convert to array using proper method
                month_data = self._image_to_array_proper(composite, region)
                
                # Validate
                data_max = np.max(month_data)
                data_sum = np.sum(month_data)
                
                if data_max == 0 or data_sum == 0:
                    logger.warning(f"   ✗ Extracted data is all zeros\n")
                    continue
                
                logger.info(f"   Raw: min={np.min(month_data):.0f}, max={data_max:.0f}, mean={np.mean(month_data):.0f}")
                
                # Resize if needed
                if month_data.shape[1:] != ModelConfig.IMAGE_SIZE:
                    resized_bands = []
                    for b in range(month_data.shape[0]):
                        band_img = PILImage.fromarray(month_data[b])
                        band_img = band_img.resize(ModelConfig.IMAGE_SIZE, PILImage.BILINEAR)
                        resized_bands.append(np.array(band_img))
                    month_data = np.stack(resized_bands, axis=0)
                
                # Normalize
                month_data = month_data / 10000.0
                month_data = np.clip(month_data, 0, 1)
                
                # Final check
                if np.max(month_data) < 0.001:
                    logger.warning(f"   ✗ Data near-zero after scaling\n")
                    continue
                
                logger.info(f"   Scaled: min={np.min(month_data):.4f}, max={np.max(month_data):.4f}")
                
                # Place in stack
                start_channel = slot_idx * ModelConfig.NUM_BANDS
                end_channel = start_channel + ModelConfig.NUM_BANDS
                
                image_stack[start_channel:end_channel] = month_data
                availability_mask[slot_idx] = 1
                
                latest_month_data = month_data
                successful_months.append(f"{year}-{month:02d}")
                
                logger.info(f"   ✓✓✓ SUCCESS: Slot {slot_idx} filled (channels {start_channel}-{end_channel-1})\n")
                
            except Exception as e:
                logger.error(f"   ✗ Error: {str(e)}\n")
                continue
        
        # Calculate NDVI
        if latest_month_data is not None:
            nir = latest_month_data[3]
            red = latest_month_data[2]
            with np.errstate(divide='ignore', invalid='ignore'):
                ndvi = (nir - red) / (nir + red + 1e-10)
                current_ndvi = float(np.nanmean(ndvi))
        else:
            current_ndvi = 0.0
        
        growth_stage = TemporalConfig.get_growth_stage(season, query_date.month)
        months_available = sum(availability_mask)
        
        result = {
            'image_stack': image_stack,
            'availability_mask': availability_mask,
            'months_available': months_available,
            'season': season,
            'growth_stage': growth_stage,
            'current_ndvi': current_ndvi,
            'successful_months': successful_months,
            'metadata': {
                'latitude': latitude,
                'longitude': longitude,
                'query_date': query_date.strftime('%Y-%m-%d'),
                'stack_shape': image_stack.shape,
            }
        }
        
        logger.info(f"{'='*60}")
        logger.info(f"FINAL RESULT:")
        logger.info(f"{'='*60}")
        logger.info(f"  Months available: {months_available}/6")
        logger.info(f"  Availability: {availability_mask}")
        logger.info(f"  Successful: {', '.join(successful_months) if successful_months else 'None'}")
        logger.info(f"  NDVI: {current_ndvi:.3f}")
        logger.info(f"{'='*60}\n")
        
        return result
    
    # Backward compatibility
    def fetch_temporal_data(self, latitude, longitude, query_date=None):
        result = self.fetch_temporal_stack(latitude, longitude, query_date)
        result['image'] = result['image_stack']
        result['availability'] = result['availability_mask']
        return result


def create_gee_fetcher(service_account_key: str = None) -> GEEFetcher:
    return GEEFetcher(service_account_key)


if __name__ == "__main__":
    print("Testing GEE Fetcher (Proper Sampling Method)...")
    print("=" * 70)
    
    fetcher = GEEFetcher()
    
    # Test Sheikhupura
    lat, lon = 31.71818919, 74.03506432
    
    print(f"\nTesting: ({lat}, {lon})")
    result = fetcher.fetch_temporal_stack(lat, lon)
    
    print(f"\n{'='*70}")
    print(f"RESULT: {result['months_available']}/6 months")
    print(f"Successful: {', '.join(result['successful_months'])}")
    print(f"{'='*70}")