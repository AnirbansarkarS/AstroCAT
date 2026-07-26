import pytest
import os
import tempfile
from astrocat.storage import (
    connect, save_subject, get_subject, save_labels, save_score,
    unscored_subjects, triage_queue
)

def test_storage_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_storage.db")

        # 1. Connect creates schema
        with connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
            assert "subjects" in tables
            assert "labels" in tables
            assert "scores" in tables

        # 2. Save & retrieve subject
        save_subject(
            db_path=db_path,
            subject_id="subj_001",
            project_slug="test-proj",
            reference_image_path="/path/to/ref.png",
            moving_image_path="/path/to/mov.png",
            metadata={"test_key": "test_val"}
        )
        subj = get_subject(db_path, "subj_001")
        assert subj is not None
        assert subj["id"] == "subj_001"
        assert subj["project_slug"] == "test-proj"
        assert subj["metadata"]["test_key"] == "test_val"

        # 3. Save labels & scores
        save_labels(db_path, "subj_001", "candidate", consensus_score=0.95)
        
        # Verify unscored filtering
        unscored = unscored_subjects(db_path, "test-proj", "cv_diff")
        assert len(unscored) == 1

        # Save score
        save_score(
            db_path=db_path,
            subject_id="subj_001",
            model_name="cv_diff",
            predicted_label="candidate",
            confidence=0.88,
            novelty_score=0.12,
            is_novel=False
        )

        # After scoring, unscored list should be empty
        unscored_after = unscored_subjects(db_path, "test-proj", "cv_diff")
        assert len(unscored_after) == 0

        # Queue check
        queue = triage_queue(db_path, "test-proj")
        assert len(queue) == 1
        assert queue[0]["subject_id"] == "subj_001"
        assert queue[0]["confidence"] == 0.88
