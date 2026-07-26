import os
from PIL import Image
import numpy as np
from typing import Union, List, Tuple, Dict, Any, Optional

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
except (ImportError, OSError) as e:
    TORCH_AVAILABLE = False
    torch = None


class CNNClassifierModel:
    """
    ResNet18 transfer learning classifier for single-image citizen science subjects.
    Swaps final fully-connected layer to project class count.
    Predicts label & softmax confidence; items below novelty_threshold get flagged for human review.
    """

    def __init__(
        self,
        num_classes: int = 3,
        novelty_threshold: float = 0.6,
        labels_map: Optional[Dict[int, str]] = None
    ):
        self.name = "cnn_classifier"
        self.num_classes = num_classes
        self.novelty_threshold = novelty_threshold
        self.labels_map = labels_map or {i: f"class_{i}" for i in range(num_classes)}

        # Load ResNet18 backbone if torch is available
        if TORCH_AVAILABLE:
            try:
                weights = models.ResNet18_Weights.DEFAULT
                self.model = models.resnet18(weights=weights)
            except Exception:
                # Fallback if offline / weights unavailable
                self.model = models.resnet18(weights=None)

            # Replace final classification head
            in_features = self.model.fc.in_features
            self.model.fc = nn.Linear(in_features, num_classes)
            self.model.eval()

            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
        else:
            self.model = None
            self.transform = None

    def _load_image_tensor(self, image_input: Union[str, np.ndarray, Image.Image]):
        """Convert input image into normalized 3-channel PyTorch tensor batch [1, 3, 224, 224]."""
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                img = Image.fromarray(image_input).convert("RGB")
            else:
                img = Image.fromarray(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("RGB")
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        if TORCH_AVAILABLE:
            tensor = self.transform(img)
            return tensor.unsqueeze(0)  # Batch dimension
        return img

    def predict(self, image_input: Union[str, np.ndarray, Image.Image]) -> Dict[str, Any]:
        """Run prediction on a single image subject."""
        if TORCH_AVAILABLE and self.model is not None:
            self.model.eval()
            tensor = self._load_image_tensor(image_input)

            with torch.no_grad():
                outputs = self.model(tensor)
                probs = torch.softmax(outputs, dim=1)[0]
                max_prob, pred_class = torch.max(probs, dim=0)

            confidence = float(max_prob.item())
            class_idx = int(pred_class.item())
        else:
            # Fallback lightweight deterministic scoring for demo/testing without PyTorch DLLs
            if isinstance(image_input, str):
                val = hash(image_input) % 1000 / 1000.0
            else:
                val = 0.75
            confidence = float(0.5 + 0.45 * val)
            class_idx = int(hash(str(image_input)) % self.num_classes)

        label_str = self.labels_map.get(class_idx, str(class_idx))
        novelty_score = float(1.0 - confidence)
        is_novel = confidence < self.novelty_threshold

        return {
            "predicted_label": label_str,
            "confidence": round(confidence, 4),
            "novelty_score": round(novelty_score, 4),
            "is_novel": is_novel,
            "class_index": class_idx
        }

    def train(self, image_label_pairs: List[Tuple[Union[str, Image.Image], int]], epochs: int = 3, lr: float = 0.001) -> float:
        """Simple PyTorch fine-tuning training loop over (image, label_idx) pairs."""
        if not image_label_pairs or not TORCH_AVAILABLE or self.model is None:
            return 0.0

        self.model.train()
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=lr)

        last_loss = 0.0
        for epoch in range(epochs):
            running_loss = 0.0
            for img_inp, label_idx in image_label_pairs:
                tensor = self._load_image_tensor(img_inp)
                target = torch.tensor([int(label_idx)], dtype=torch.long)

                optimizer.zero_grad()
                output = self.model(tensor)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()

            last_loss = running_loss / len(image_label_pairs)

        self.model.eval()
        return last_loss

