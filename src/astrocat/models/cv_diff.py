import cv2
import numpy as np
from typing import Union, Dict, Any
from astrocat.preprocess import standard_prep, align

class CVDiffModel:
    """
    Classical change / difference detection model for image pairs.
    Requires no training data. Predicts transient/moving object candidates by aligning frames,
    taking absolute difference, thresholding into blob masks, and scoring signal strength.
    """

    def __init__(self, novelty_threshold: float = 0.5):
        self.name = "cv_diff"
        self.novelty_threshold = novelty_threshold

    def predict_pair(
        self,
        reference_input: Union[str, np.ndarray],
        moving_input: Union[str, np.ndarray]
    ) -> Dict[str, Any]:
        """
        Process a (reference, moving) frame pair and return triage scores.
        """
        # 1. Preprocess frames
        ref = standard_prep(reference_input)
        mov = standard_prep(moving_input)

        # 2. Align moving frame to reference frame
        mov_aligned = align(ref, mov)

        # 3. Compute absolute difference image
        diff = cv2.absdiff(ref, mov_aligned)

        # 4. Threshold to binary blob mask
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        # 5. Find blob contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_area = 0.0
        total_area = 0.0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            total_area += area
            if area > max_area:
                max_area = area

        # 6. Calculate signal & confidence metric
        # Image area is 256x256 = 65536
        img_size = ref.shape[0] * ref.shape[1]
        area_ratio = max_area / img_size
        
        # Scale novelty score based on blob area ratio
        # A significant blob (> 50 px) gives higher novelty score
        novelty_score = float(np.clip(area_ratio * 500.0, 0.0, 1.0))
        
        # Confidence reflects how clear the candidate is
        confidence = float(np.clip(1.0 - (novelty_score if novelty_score > 0.5 else (0.5 - novelty_score)), 0.1, 0.99))
        
        is_novel = novelty_score >= self.novelty_threshold
        predicted_label = "transient_candidate" if is_novel else "background"

        return {
            "predicted_label": predicted_label,
            "confidence": round(confidence, 4),
            "novelty_score": round(novelty_score, 4),
            "is_novel": is_novel,
            "blob_max_area": float(max_area)
        }
