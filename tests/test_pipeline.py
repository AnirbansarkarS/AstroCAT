import pytest
import os
import tempfile
import sqlite3
from unittest.mock import patch
from astrocat.config import get_project
from astrocat.ingest import ingest_subjects, _generate_synthetic_subject
from astrocat.storage import connect, triage_queue, get_subject
from astrocat.triage import run_triage

def test_five_stage_pipeline_end_to_end():
    """Verify that all 5 stages of the AstroCAT pipeline function together cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        subjects_dir = os.path.join(tmpdir, "subjects")
        db_path = os.path.join(tmpdir, "test_storage.db")

        # Mock project configuration
        mock_config = {
            "slug": "active-asteroids",
            "name": "Active Asteroids Test",
            "model_type": "cv_diff",
            "panoptes_project_id": "99999",
            "data_dir": tmpdir,
            "db_path": db_path,
            "subjects_dir": subjects_dir,
            "novelty_threshold": 0.3
        }

        with patch("astrocat.triage.get_project", return_value=mock_config), \
             patch("astrocat.ingest.get_project", return_value=mock_config):

            # Stage 1 & 2: Source & Ingest
            count = ingest_subjects("active-asteroids", max_subjects=5)
            assert count == 5

            # Stage 3: Storage Verification
            with connect(db_path) as conn:
                cur = conn.execute("SELECT count(*) FROM subjects;")
                assert cur.fetchone()[0] == 5

            # Stage 4: Triage Model Scoring
            scored_count = run_triage("active-asteroids")
            assert scored_count == 5

            # Stage 5: Review Queue Ordering Verification
            queue = triage_queue(db_path, "active-asteroids")
            assert len(queue) == 5

            # Assert sorting: is_novel DESC, confidence ASC
            for i in range(len(queue) - 1):
                curr_item = queue[i]
                next_item = queue[i + 1]
                if curr_item["is_novel"] == next_item["is_novel"]:
                    assert curr_item["confidence"] <= next_item["confidence"]
                else:
                    assert curr_item["is_novel"] > next_item["is_novel"]
