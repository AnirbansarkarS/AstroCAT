import pytest
import numpy as np
import cv2
import tempfile
import os
from astrocat.models import CVDiffModel, CNNClassifierModel

def test_cv_diff_model_prediction():
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_path = os.path.join(tmpdir, "ref.png")
        mov_path = os.path.join(tmpdir, "mov.png")

        # Synthetic image pair
        ref_img = np.zeros((256, 256), dtype=np.uint8)
        cv2.circle(ref_img, (50, 50), 5, 255, -1)
        cv2.imwrite(ref_path, ref_img)

        mov_img = ref_img.copy()
        # Add transient feature
        cv2.circle(mov_img, (128, 128), 10, 255, -1)
        cv2.imwrite(mov_path, mov_img)

        model = CVDiffModel(novelty_threshold=0.3)
        res = model.predict_pair(ref_path, mov_path)

        assert "predicted_label" in res
        assert "confidence" in res
        assert "novelty_score" in res
        assert "is_novel" in res
        assert isinstance(res["is_novel"], bool)

def test_cnn_classifier_model_prediction():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "sample.png")
        img = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        cv2.imwrite(img_path, img)

        model = CNNClassifierModel(num_classes=3, novelty_threshold=0.6)
        res = model.predict(img_path)

        assert "predicted_label" in res
        assert "confidence" in res
        assert 0.0 <= res["confidence"] <= 1.0
        assert "novelty_score" in res
        assert "is_novel" in res
