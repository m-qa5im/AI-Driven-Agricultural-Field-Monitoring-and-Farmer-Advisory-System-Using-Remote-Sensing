# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PAKISTAN CROP CLASSIFICATION SYSTEM - MODEL INFERENCE                     ║
# ║  Logic Controller (Brain) - Decides V4 vs V6 based on data availability   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import numpy as np
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import logging
import os

from config import ModelConfig, PathConfig, TemporalConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL ARCHITECTURES
# ─────────────────────────────────────────────────────────────────────────────

class TemporalResNetV4(nn.Module):
    """
    V4 Model - ResNet34 for full 6-month temporal data.
    
    Input: 24-channel tensor (6 months × 4 bands)
    Output: 3 class probabilities (Rice, Wheat, Other)
    
    Best accuracy: 93.55%
    Use when: >= 5 months of data available
    """
    
    def __init__(self, num_classes: int = 3, in_channels: int = 24, dropout_rate: float = 0.4):
        super().__init__()
        
        self.base = models.resnet34(weights=None)
        
        # Modify first conv for 24 channels
        self.base.conv1 = nn.Conv2d(
            in_channels, 64,
            kernel_size=7, stride=2, padding=3, bias=False
        )
        
        # Classifier head
        num_features = self.base.fc.in_features
        self.base.fc = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(num_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate / 2),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base(x)


class VariableInputResNetV6(nn.Module):
    """
    V6 Model - ResNet34 with availability mask awareness.
    
    Input: 
        - 24-channel tensor (6 months × 4 bands) with zero-padding
        - 6-element availability mask [1, 1, 1, 0, 0, 0]
    Output: 3 class probabilities (Rice, Wheat, Other)
    
    Accuracy: 89.25%
    Use when: < 5 months of data available
    """
    
    def __init__(self, num_classes: int = 3, in_channels: int = 24, 
                 num_months: int = 6, dropout_rate: float = 0.4):
        super().__init__()
        
        self.num_months = num_months
        
        # Base ResNet34
        self.base = models.resnet34(weights=None)
        
        # Modify first conv for 24 channels
        self.base.conv1 = nn.Conv2d(
            in_channels, 64,
            kernel_size=7, stride=2, padding=3, bias=False
        )
        
        # Get backbone output features
        num_backbone_features = self.base.fc.in_features  # 512
        
        # Availability embedding - learns to weight importance of each month
        self.availability_embed = nn.Sequential(
            nn.Linear(num_months, 32),
            nn.ReLU(inplace=True),
            nn.Linear(32, 64),
            nn.ReLU(inplace=True)
        )
        
        # Remove original FC
        self.base.fc = nn.Identity()
        
        # Combined classifier
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(num_backbone_features + 64, 512),  # 512 + 64 = 576
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate / 2),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x: torch.Tensor, availability_mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Image tensor [batch, 24, H, W]
            availability_mask: Binary mask [batch, 6] indicating available months
        """
        # Extract image features
        img_features = self.base(x)  # [batch, 512]
        
        # Embed availability information
        avail_features = self.availability_embed(availability_mask)  # [batch, 64]
        
        # Combine and classify
        combined = torch.cat([img_features, avail_features], dim=1)  # [batch, 576]
        output = self.classifier(combined)
        
        return output


# ─────────────────────────────────────────────────────────────────────────────
# SEASON VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

class SeasonValidator:
    """Validates crop predictions against current season."""
    
    @staticmethod
    def validate_prediction(predicted_class: str, 
                           probabilities: Dict[str, float],
                           month: int) -> Dict:
        """
        Validate and potentially adjust prediction based on season.
        
        Rule:
        - Rice season (May-Oct): Can classify Rice or Other (NOT Wheat)
        - Wheat season (Nov-Apr): Can classify Wheat or Other (NOT Rice)
        """
        valid_crops = TemporalConfig.get_valid_crops_for_season(month)
        season_info = TemporalConfig.get_season_info(month)
        
        is_valid, reason = TemporalConfig.is_crop_valid_for_season(predicted_class, month)
        
        result = {
            'original_prediction': predicted_class,
            'is_seasonally_valid': is_valid,
            'season': season_info['name'],
            'valid_crops': valid_crops,
            'validation_message': reason,
        }
        
        if is_valid:
            result['final_prediction'] = predicted_class
            result['was_adjusted'] = False
            result['adjustment_reason'] = None
        else:
            # Find highest probability valid crop
            valid_probs = {
                crop: prob for crop, prob in probabilities.items() 
                if crop in valid_crops
            }
            
            if valid_probs:
                adjusted_class = max(valid_probs, key=valid_probs.get)
                adjusted_confidence = valid_probs[adjusted_class]
                
                result['final_prediction'] = adjusted_class
                result['was_adjusted'] = True
                result['adjustment_reason'] = (
                    f"'{predicted_class}' invalid for {season_info['name']} season. "
                    f"Adjusted to '{adjusted_class}' ({adjusted_confidence:.1%})"
                )
                result['adjusted_confidence'] = adjusted_confidence
            else:
                result['final_prediction'] = 'Other'
                result['was_adjusted'] = True
                result['adjustment_reason'] = "Defaulting to 'Other'"
        
        return result


# ─────────────────────────────────────────────────────────────────────────────
# LOGIC CONTROLLER (BRAIN)
# ─────────────────────────────────────────────────────────────────────────────

class CropClassifier:
    """
    Logic Controller (Brain) - Decides which model to use.
    
    Decision Rule:
    ══════════════════════════════════════════════════════════════
    │ Months Available │ Model │ Input                          │
    ══════════════════════════════════════════════════════════════
    │     >= 5         │  V4   │ 24-channel stack only          │
    │     < 5          │  V6   │ 24-channel stack + mask        │
    ══════════════════════════════════════════════════════════════
    """
    
    # Threshold for switching between models
    MIN_MONTHS_FOR_V4 = 5
    
    def __init__(self, 
                 v4_model_path: str = None,
                 v6_model_path: str = None,
                 device: str = None,
                 enable_season_validation: bool = True):
        """
        Initialize classifier.
        
        Args:
            v4_model_path: Path to V4 model weights
            v6_model_path: Path to V6 model weights
            device: 'cuda' or 'cpu' (auto-detect if None)
            enable_season_validation: Whether to validate predictions against season
        """
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        self.v4_path = v4_model_path or PathConfig.V4_MODEL_PATH
        self.v6_path = v6_model_path or PathConfig.V6_MODEL_PATH
        
        self.enable_season_validation = enable_season_validation
        self.season_validator = SeasonValidator()
        
        self.model_v4 = None
        self.model_v6 = None
        
        self._load_models()
    
    def _load_models(self):
        """Load both V4 and V6 models."""
        
        # Load V4 model
        if os.path.exists(self.v4_path):
            try:
                self.model_v4 = TemporalResNetV4(
                    num_classes=ModelConfig.NUM_CLASSES,
                    in_channels=ModelConfig.NUM_CHANNELS
                )
                
                checkpoint = torch.load(self.v4_path, map_location=self.device)
                self.model_v4.load_state_dict(checkpoint['model_state_dict'])
                self.model_v4 = self.model_v4.to(self.device)
                self.model_v4.eval()
                
                logger.info(f"✓ V4 model loaded from {self.v4_path}")
                
            except Exception as e:
                logger.error(f"Failed to load V4 model: {str(e)}")
                self.model_v4 = None
        else:
            logger.warning(f"V4 model not found at {self.v4_path}")
        
        # Load V6 model
        if os.path.exists(self.v6_path):
            try:
                self.model_v6 = VariableInputResNetV6(
                    num_classes=ModelConfig.NUM_CLASSES,
                    in_channels=ModelConfig.NUM_CHANNELS,
                    num_months=ModelConfig.NUM_MONTHS
                )
                
                checkpoint = torch.load(self.v6_path, map_location=self.device)
                self.model_v6.load_state_dict(checkpoint['model_state_dict'])
                self.model_v6 = self.model_v6.to(self.device)
                self.model_v6.eval()
                
                logger.info(f"✓ V6 model loaded from {self.v6_path}")
                
            except Exception as e:
                logger.error(f"Failed to load V6 model: {str(e)}")
                self.model_v6 = None
        else:
            logger.warning(f"V6 model not found at {self.v6_path}")
        
        if self.model_v4 is None and self.model_v6 is None:
            raise RuntimeError("No models loaded! Check model paths.")
    
    def _apply_tta(self, image: torch.Tensor) -> list:
        """Generate Test-Time Augmentation variants."""
        variants = [image]
        variants.append(torch.flip(image, dims=[-1]))  # Horizontal flip
        variants.append(torch.flip(image, dims=[-2]))  # Vertical flip
        variants.append(torch.rot90(image, k=1, dims=[-2, -1]))  # Rotate 90
        return variants
    
    def _get_confidence_level(self, confidence: float, months_available: int) -> str:
        """Determine confidence level."""
        if months_available >= 5:
            high_thresh = ModelConfig.HIGH_CONFIDENCE_THRESHOLD
            med_thresh = ModelConfig.MEDIUM_CONFIDENCE_THRESHOLD
        elif months_available >= 3:
            high_thresh = 0.90
            med_thresh = 0.75
        else:
            high_thresh = 0.95
            med_thresh = 0.80
        
        if confidence >= high_thresh:
            return 'high'
        elif confidence >= med_thresh:
            return 'medium'
        else:
            return 'low'
    
    
    def predict(self, 
                image_stack: np.ndarray = None, 
                availability_mask: List[int] = None,
                analysis_date: datetime = None,
                use_tta: bool = True,
                **kwargs) -> Dict:
        """
        Predict crop type using Logic Controller decision.
        
        ═══════════════════════════════════════════════════════════════════
        LOGIC CONTROLLER DECISION:
        ═══════════════════════════════════════════════════════════════════
        │ count = sum(availability_mask)                                  │
        │                                                                 │
        │ if count >= 5:                                                  │
        │     model = V4                                                  │
        │     input = image_stack only                                    │
        │                                                                 │
        │ if count < 5:                                                   │
        │     model = V6                                                  │
        │     input = image_stack + availability_mask                     │
        ═══════════════════════════════════════════════════════════════════
        
        Args:
            image_stack: numpy array of shape (24, H, W) - zero-padded
            availability_mask: list of 6 integers [0 or 1]
            analysis_date: Date of analysis (for season validation)
            use_tta: Whether to use Test-Time Augmentation
            
        Returns:
            Prediction results dictionary
        """
        # Backward compatibility
        if image_stack is None:
            image_stack = kwargs.get('image')
        if availability_mask is None:
            availability_mask = kwargs.get('availability')
            
        months_available = sum(availability_mask)
        
        if analysis_date is None:
            analysis_date = datetime.now()
        analysis_month = analysis_date.month
        
        # ═══════════════════════════════════════════════════════════════════
        # LOGIC CONTROLLER: Select model based on months available
        # ═══════════════════════════════════════════════════════════════════
        if months_available >= self.MIN_MONTHS_FOR_V4 and self.model_v4 is not None:
            model = self.model_v4
            model_name = 'V4'
            use_mask = False
            logger.info(f"BRAIN: {months_available} months >= {self.MIN_MONTHS_FOR_V4} → Using V4")
        elif self.model_v6 is not None:
            model = self.model_v6
            model_name = 'V6'
            use_mask = True
            logger.info(f"BRAIN: {months_available} months < {self.MIN_MONTHS_FOR_V4} → Using V6 with mask")
        elif self.model_v4 is not None:
            model = self.model_v4
            model_name = 'V4'
            use_mask = False
            logger.warning("BRAIN: V6 unavailable, falling back to V4")
        else:
            raise RuntimeError("No suitable model available")
        
        # ═══════════════════════════════════════════════════════════════════
        # Prepare input tensors
        # ═══════════════════════════════════════════════════════════════════
        image_tensor = torch.from_numpy(image_stack).float().unsqueeze(0)  # [1, 24, H, W]
        image_tensor = image_tensor.to(self.device)
        
        if use_mask:
            mask_tensor = torch.tensor(availability_mask, dtype=torch.float32).unsqueeze(0)  # [1, 6]
            mask_tensor = mask_tensor.to(self.device)
        
        # ═══════════════════════════════════════════════════════════════════
        # Inference
        # ═══════════════════════════════════════════════════════════════════
        with torch.no_grad():
            if use_tta:
                tta_variants = self._apply_tta(image_tensor)
                probs_sum = None
                
                for variant in tta_variants:
                    if use_mask:
                        output = model(variant, mask_tensor)
                    else:
                        output = model(variant)
                    
                    probs = F.softmax(output, dim=1)
                    if probs_sum is None:
                        probs_sum = probs
                    else:
                        probs_sum += probs
                
                avg_probs = probs_sum / len(tta_variants)
            else:
                if use_mask:
                    output = model(image_tensor, mask_tensor)
                else:
                    output = model(image_tensor)
                
                avg_probs = F.softmax(output, dim=1)
        
        # ═══════════════════════════════════════════════════════════════════
        # Get predictions
        # ═══════════════════════════════════════════════════════════════════
        confidence, predicted_idx = torch.max(avg_probs, dim=1)
        confidence = confidence.item()
        predicted_idx = predicted_idx.item()
        raw_prediction = ModelConfig.IDX_TO_CLASS[predicted_idx]
        
        probs_np = avg_probs.cpu().numpy()[0]
        probabilities = {
            ModelConfig.IDX_TO_CLASS[i]: float(probs_np[i]) 
            for i in range(ModelConfig.NUM_CLASSES)
        }
        
        # ═══════════════════════════════════════════════════════════════════
        # Season validation
        # ═══════════════════════════════════════════════════════════════════
        if self.enable_season_validation:
            validation_result = self.season_validator.validate_prediction(
                raw_prediction, probabilities, analysis_month
            )
            final_prediction = validation_result['final_prediction']
            
            if validation_result['was_adjusted']:
                confidence = validation_result.get('adjusted_confidence', probabilities.get(final_prediction, confidence))
        else:
            validation_result = {
                'is_seasonally_valid': True,
                'was_adjusted': False,
                'validation_message': 'Season validation disabled'
            }
            final_prediction = raw_prediction
        
        # Confidence level
        confidence_level = self._get_confidence_level(confidence, months_available)
        
        # Data quality
        if months_available >= 5:
            data_quality = "Excellent - Full seasonal data"
        elif months_available >= 4:
            data_quality = "Good - Most seasonal data"
        elif months_available >= 3:
            data_quality = "Moderate - Partial data"
        else:
            data_quality = "Limited - Insufficient for reliable classification"
        
        # ═══════════════════════════════════════════════════════════════════
        # Result
        # ═══════════════════════════════════════════════════════════════════
        result = {
            'predicted_class': final_prediction,
            'raw_prediction': raw_prediction,
            'class_index': ModelConfig.CLASS_TO_IDX[final_prediction],
            'confidence': confidence,
            'probabilities': probabilities,
            'confidence_level': confidence_level,
            'model_used': model_name,
            'months_available': months_available,
            'availability_mask': availability_mask,
            'data_quality': data_quality,
            'analysis_month': analysis_month,
            'season_validation': validation_result,
        }
        
        logger.info(f"═══════════════════════════════════════════════════")
        logger.info(f"PREDICTION RESULT:")
        logger.info(f"  Model: {model_name}")
        logger.info(f"  Mask used: {use_mask}")
        logger.info(f"  Raw prediction: {raw_prediction}")
        logger.info(f"  Final prediction: {final_prediction}")
        logger.info(f"  Confidence: {confidence:.1%}")
        logger.info(f"═══════════════════════════════════════════════════")
        
        return result
    
    def is_ready(self) -> bool:
        """Check if at least one model is loaded."""
        return self.model_v4 is not None or self.model_v6 is not None


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def create_classifier(v4_path: str = None, 
                      v6_path: str = None,
                      enable_season_validation: bool = True) -> CropClassifier:
    """Factory function to create CropClassifier."""
    return CropClassifier(
        v4_model_path=v4_path, 
        v6_model_path=v6_path,
        enable_season_validation=enable_season_validation
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING LOGIC CONTROLLER (BRAIN)")
    print("=" * 70)
    
    # Test case 1: Full data (6 months)
    print("\n[TEST 1] Full data - 6 months available")
    image_stack = np.random.rand(24, 64, 64).astype(np.float32)
    mask_full = [1, 1, 1, 1, 1, 1]
    print(f"  Availability mask: {mask_full}")
    print(f"  Expected: V4 model (>= 5 months)")
    
    # Test case 2: Partial data (3 months)
    print("\n[TEST 2] Partial data - 3 months available")
    mask_partial = [1, 1, 1, 0, 0, 0]
    print(f"  Availability mask: {mask_partial}")
    print(f"  Expected: V6 model (< 5 months)")
    
    # Test case 3: Edge case (5 months)
    print("\n[TEST 3] Edge case - 5 months available")
    mask_edge = [1, 1, 1, 1, 1, 0]
    print(f"  Availability mask: {mask_edge}")
    print(f"  Expected: V4 model (>= 5 months)")
    
    # Test case 4: Minimal data (1 month)
    print("\n[TEST 4] Minimal data - 1 month available")
    mask_minimal = [1, 0, 0, 0, 0, 0]
    print(f"  Availability mask: {mask_minimal}")
    print(f"  Expected: V6 model (< 5 months)")
    
    print("\n" + "=" * 70)
    print("Test with actual models...")
    print("=" * 70)
    
    try:
        classifier = CropClassifier(enable_season_validation=True)
        
        result = classifier.predict(image_stack, mask_full)
        print(f"\nFull data result:")
        print(f"  Model used: {result['model_used']}")
        print(f"  Prediction: {result['predicted_class']}")
        print(f"  Confidence: {result['confidence']:.1%}")
        
        result = classifier.predict(image_stack, mask_partial)
        print(f"\nPartial data result:")
        print(f"  Model used: {result['model_used']}")
        print(f"  Prediction: {result['predicted_class']}")
        print(f"  Confidence: {result['confidence']:.1%}")
        
    except Exception as e:
        print(f"\nModel test skipped: {str(e)}")
"""

---

## Summary

| Component | Responsibility |
|-----------|----------------|
| **Stacker (gee_fetcher.py)** | ALWAYS outputs 24-channel tensor with zero-padding |
| **Brain (model_inference.py)** | Decides V4 (≥5 months) or V6 (<5 months) |

### Decision Flow
```
Input: Coordinates + Date
         │
         ▼
┌─────────────────────────────────────────┐
│           STACKER                        │
│  • Fetch available months                │
│  • Create 24-channel tensor              │
│  • Zero-pad missing slots                │
│  • Generate availability mask            │
│                                          │
│  Output: [24, 64, 64] + [1,1,1,0,0,0]   │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│            BRAIN                         │
│  count = sum(availability_mask)          │
│                                          │
│  if count >= 5:                          │
│      V4(image_stack)                     │
│  else:                                   │
│      V6(image_stack, mask)               │
└─────────────────────────────────────────┘
         │
         ▼
   Final Prediction
   """