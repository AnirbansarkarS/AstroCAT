import os
import csv
import json
import logging
import urllib.request
import numpy as np
import cv2
from pathlib import Path
from typing import Optional, Dict, Any

from astrocat.config import get_project
from astrocat.storage import save_subject, save_labels

logger = logging.getLogger("astrocat.ingest")

def _generate_synthetic_subject(subjects_dir: str, subject_id: str, is_pair: bool = True) -> Dict[str, str]:
    """Helper to generate local synthetic test images for offline or demo use."""
    os.makedirs(subjects_dir, exist_ok=True)
    ref_path = os.path.join(subjects_dir, f"{subject_id}_ref.png")
    
    # Create simple starfield image
    np.random.seed(int(subject_id.replace("sub_", "")) if subject_id.replace("sub_", "").isdigit() else 42)
    img = np.zeros((256, 256), dtype=np.uint8)
    for _ in range(20):
        cx, cy = np.random.randint(20, 236, size=2)
        cv2.circle(img, (cx, cy), np.random.randint(2, 6), 255, -1)
    
    cv2.imwrite(ref_path, img)
    
    moving_path = None
    if is_pair:
        moving_path = os.path.join(subjects_dir, f"{subject_id}_moving.png")
        moving_img = img.copy()
        # Add a moving object / blob to moving image for cv_diff
        if hash(subject_id) % 3 == 0:  # ~1/3 has a transient object
            cv2.circle(moving_img, (128, 128), 8, 255, -1)
        cv2.imwrite(moving_path, moving_img)

    return {"reference": ref_path, "moving": moving_path}

def ingest_subjects(project_slug: str, max_subjects: int = 200) -> int:
    """
    Ingest subjects for a project.
    Tries Panoptes API first; if unavailable or project_id is generic, generates local demo subjects.
    Returns count of ingested subjects.
    """
    proj_config = get_project(project_slug)
    db_path = proj_config["db_path"]
    subjects_dir = proj_config["subjects_dir"]
    project_id = proj_config.get("panoptes_project_id")
    is_pair = proj_config.get("model_type") == "cv_diff"
    
    count = 0
    try:
        from panoptes_client import Panoptes, Subject, Project
        Panoptes.connect()
        logger.info(f"Connected to Panoptes API for project {project_slug} (id={project_id})")
        
        subjects = Subject.where(project_id=project_id)
        for s in subjects:
            if count >= max_subjects:
                break
            
            subject_id = str(s.id)
            locations = s.locations
            if not locations:
                continue
            
            # Download reference image
            ref_url = list(locations[0].values())[0]
            ref_path = os.path.join(subjects_dir, f"{subject_id}_ref.jpg")
            if not os.path.exists(ref_path):
                urllib.request.urlretrieve(ref_url, ref_path)

            moving_path = None
            if is_pair and len(locations) > 1:
                moving_url = list(locations[1].values())[0]
                moving_path = os.path.join(subjects_dir, f"{subject_id}_moving.jpg")
                if not os.path.exists(moving_path):
                    urllib.request.urlretrieve(moving_url, moving_path)
            
            metadata = dict(s.metadata or {})
            save_subject(
                db_path=db_path,
                subject_id=subject_id,
                project_slug=project_slug,
                reference_image_path=ref_path,
                moving_image_path=moving_path,
                metadata=metadata
            )
            count += 1
            
    except Exception as e:
        logger.warning(f"Panoptes client fetch failed ({e}). Falling back to synthetic ingest for {project_slug}.")

    if count == 0:
        logger.info(f"Panoptes API returned 0 subjects. Ingesting synthetic subject batch for demo/testing...")
        for i in range(1, max_subjects + 1):
            subject_id = f"sub_{i:04d}"
            paths = _generate_synthetic_subject(subjects_dir, subject_id, is_pair=is_pair)
            save_subject(
                db_path=db_path,
                subject_id=subject_id,
                project_slug=project_slug,
                reference_image_path=paths["reference"],
                moving_image_path=paths["moving"],
                metadata={"synthetic": True, "index": i}
            )
            count += 1

    logger.info(f"Ingested {count} subjects for project '{project_slug}'.")
    return count


def ingest_aggregated_labels_from_csv(project_slug: str, csv_path: str) -> int:
    """Load pre-aggregated label CSV file into labels SQLite table."""
    proj_config = get_project(project_slug)
    db_path = proj_config["db_path"]
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Label CSV file not found: {csv_path}")

    count = 0
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject_id = row.get("subject_id")
            label = row.get("label")
            if not subject_id or label is None:
                continue
            consensus = float(row.get("consensus_score", 1.0))
            save_labels(
                db_path=db_path,
                subject_id=subject_id,
                label=label,
                consensus_score=consensus,
                metadata=dict(row)
            )
            count += 1
            
    logger.info(f"Ingested {count} labels from {csv_path}")
    return count
