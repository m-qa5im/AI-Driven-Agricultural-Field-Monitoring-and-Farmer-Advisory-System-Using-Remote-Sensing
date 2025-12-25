# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PAKISTAN CROP CLASSIFICATION SYSTEM - MODEL INFERENCE                     ║
# ║  Hybrid V4 + V6 model inference for crop classification                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import numpy as np
from typing import Dict, Tuple, Optional
import logging
import os

from config import ModelConfig, PathConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL ARCHITECTURES
# ─────────────────────────────────────────────────────────────────────────────

class TemporalResNetV4(nn.Module):
    """
    V4 Model - ResNet34 for full 6-month temporal data.
    Best accuracy: 93.55%
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
    Handles variable number of input months (1-6).
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
        
        # Availability embedding
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
            nn.Linear(num_backbone_features + 64, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate / 2),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x: torch.Tensor, availability_mask: torch.Tensor) -> torch.Tensor:
        # Extract image features
        img_features = self.base(x)  # [batch, 512]
        
        # Embed availability information
        avail_features = self.availability_embed(availability_mask)  # [batch, 64]
        
        # Combine and classify
        combined = torch.cat([img_features, avail_features], dim=1)
        output = self.classifier(combined)
        
        return output


# ─────────────────────────────────────────────────────────────────────────────
# INFERENCE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class CropClassifier:
    """
    Hybrid crop classifier using V4 and V6 models.
    
    Strategy:
        - Use V4 when >= 5 months available (highest accuracy)
        - Use V6 when < 5 months available (handles partial data)
    """
    
    def __init__(self, 
                 v4_model_path: str = None,
                 v6_model_path: str = None,
                 device: str = None):
        """
        Initialize classifier.
        
        Args:
            v4_model_path: Path to V4 model weights
            v6_model_path: Path to V6 model weights
            device: 'cuda' or 'cpu' (auto-detect if None)
        """
        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        # Model paths
        self.v4_path = v4_model_path or PathConfig.V4_MODEL_PATH
        self.v6_path = v6_model_path or PathConfig.V6_MODEL_PATH
        
        # Initialize models
        self.model_v4 = None
        self.model_v6 = None
        
        # Load models
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
                
                logger.info(f"V4 model loaded from {self.v4_path}")
                logger.info(f"  Val F1: {checkpoint.get('val_f1', 'N/A')}")
                
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
                
                logger.info(f"V6 model loaded from {self.v6_path}")
                logger.info(f"  Val F1: {checkpoint.get('val_f1', 'N/A')}")
                
            except Exception as e:
                logger.error(f"Failed to load V6 model: {str(e)}")
                self.model_v6 = None
        else:
            logger.warning(f"V6 model not found at {self.v6_path}")
        
        # Check at least one model loaded
        if self.model_v4 is None and self.model_v6 is None:
            raise RuntimeError("No models loaded! Check model paths.")
    
    def _select_model(self, months_available: int) -> Tuple[nn.Module, str]:
        """
        Select appropriate model based on data availability.
        
        Args:
            months_available: Number of months with data
            
        Returns:
            Tuple of (model, model_name)
        """
        # Use V4 for full/near-full data
        if months_available >= ModelConfig.MIN_MONTHS_FOR_V4 and self.model_v4 is not None:
            return self.model_v4, 'V4'
        
        # Use V6 for partial data
        if self.model_v6 is not None:
            return self.model_v6, 'V6'
        
        # Fallback to V4 if V6 not available
        if self.model_v4 is not None:
            return self.model_v4, 'V4'
        
        raise RuntimeError("No suitable model available")
    
    def _apply_tta(self, image: torch.Tensor) -> list:
        """
        Generate Test-Time Augmentation variants.
        
        Args:
            image: Input tensor [1, C, H, W]
            
        Returns:
            List of augmented tensors
        """
        variants = [image]
        variants.append(torch.flip(image, dims=[-1]))  # Horizontal flip
        variants.append(torch.flip(image, dims=[-2]))  # Vertical flip
        variants.append(torch.rot90(image, k=1, dims=[-2, -1]))  # Rotate 90
        return variants
    
    def _get_confidence_level(self, confidence: float, months_available: int) -> str:
        """
        Determine confidence level based on probability and data availability.
        
        Args:
            confidence: Prediction confidence (0-1)
            months_available: Number of months with data
            
        Returns:
            Confidence level string
        """
        # Adjust threshold based on data availability
        if months_available >= 5:
            high_thresh = ModelConfig.HIGH_CONFIDENCE_THRESHOLD
            med_thresh = ModelConfig.MEDIUM_CONFIDENCE_THRESHOLD
        elif months_available >= 3:
            high_thresh = 0.90  # Higher threshold for partial data
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
                image: np.ndarray, 
                availability: list,
                use_tta: bool = True) -> Dict:
        """
        Predict crop type from satellite imagery.
        
        Args:
            image: numpy array of shape (channels, height, width)
            availability: list of 0/1 indicating available months
            use_tta: Whether to use Test-Time Augmentation
            
        Returns:
            Dictionary containing:
                - 'predicted_class': Class name
                - 'class_index': Class index
                - 'confidence': Prediction confidence
                - 'probabilities': Dict of class probabilities
                - 'confidence_level': 'high', 'medium', or 'low'
                - 'model_used': 'V4' or 'V6'
                - 'data_quality': Description of data quality
        """
        months_available = sum(availability)
        
        # Select model
        model, model_name = self._select_model(months_available)
        
        # Prepare input tensor
        image_tensor = torch.from_numpy(image).float().unsqueeze(0)  # Add batch dim
        image_tensor = image_tensor.to(self.device)
        
        # Prepare availability tensor (for V6)
        availability_tensor = torch.tensor(availability, dtype=torch.float32).unsqueeze(0)
        availability_tensor = availability_tensor.to(self.device)
        
        # Inference
        with torch.no_grad():
            if use_tta:
                # Apply TTA
                tta_variants = self._apply_tta(image_tensor)
                probs_sum = None
                
                for variant in tta_variants:
                    if model_name == 'V6':
                        output = model(variant, availability_tensor)
                    else:
                        output = model(variant)
                    
                    probs = F.softmax(output, dim=1)
                    if probs_sum is None:
                        probs_sum = probs
                    else:
                        probs_sum += probs
                
                avg_probs = probs_sum / len(tta_variants)
                
            else:
                # Single inference
                if model_name == 'V6':
                    output = model(image_tensor, availability_tensor)
                else:
                    output = model(image_tensor)
                
                avg_probs = F.softmax(output, dim=1)
        
        # Get prediction
        confidence, predicted_idx = torch.max(avg_probs, dim=1)
        confidence = confidence.item()
        predicted_idx = predicted_idx.item()
        predicted_class = ModelConfig.IDX_TO_CLASS[predicted_idx]
        
        # Get all probabilities
        probs_np = avg_probs.cpu().numpy()[0]
        probabilities = {
            ModelConfig.IDX_TO_CLASS[i]: float(probs_np[i]) 
            for i in range(ModelConfig.NUM_CLASSES)
        }
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(confidence, months_available)
        
        # Data quality description
        if months_available >= 5:
            data_quality = "Excellent - Full seasonal data available"
        elif months_available >= 4:
            data_quality = "Good - Most seasonal data available"
        elif months_available >= 3:
            data_quality = "Moderate - Partial seasonal data"
        else:
            data_quality = "Limited - Insufficient data for reliable classification"
        
        result = {
            'predicted_class': predicted_class,
            'class_index': predicted_idx,
            'confidence': confidence,
            'probabilities': probabilities,
            'confidence_level': confidence_level,
            'model_used': model_name,
            'months_available': months_available,
            'data_quality': data_quality,
        }
        
        logger.info(f"Prediction: {predicted_class} ({confidence:.1%}) using {model_name}")
        
        return result
    
    def is_ready(self) -> bool:
        """Check if at least one model is loaded and ready."""
        return self.model_v4 is not None or self.model_v6 is not None


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def create_classifier(v4_path: str = None, v6_path: str = None) -> CropClassifier:
    """
    Factory function to create CropClassifier instance.
    
    Args:
        v4_path: Path to V4 model
        v6_path: Path to V6 model
        
    Returns:
        CropClassifier instance
    """
    return CropClassifier(v4_model_path=v4_path, v6_model_path=v6_path)


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Crop Classifier...")
    
    # Create dummy data for testing
    dummy_image = np.random.rand(24, 64, 64).astype(np.float32)
    availability_full = [1, 1, 1, 1, 1, 1]  # 6 months
    availability_partial = [1, 1, 1, 0, 0, 0]  # 3 months
    
    try:
        # Initialize classifier (will fail without actual model files)
        classifier = CropClassifier()
        
        print("\nTest 1: Full data (6 months)")
        result = classifier.predict(dummy_image, availability_full)
        print(f"  Predicted: {result['predicted_class']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Model used: {result['model_used']}")
        
        print("\nTest 2: Partial data (3 months)")
        result = classifier.predict(dummy_image, availability_partial)
        print(f"  Predicted: {result['predicted_class']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Model used: {result['model_used']}")
        
    except Exception as e:
        print(f"\nTest skipped (model files not available): {str(e)}")
        print("This is expected if running without trained models.")
