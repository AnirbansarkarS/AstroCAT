import logging
from typing import Dict, Any

from astrocat.config import get_project
from astrocat.storage import unscored_subjects, save_score
from astrocat.models import CVDiffModel, CNNClassifierModel

logger = logging.getLogger("astrocat.triage")

def instantiate_model(proj_config: Dict[str, Any]):
    """Instantiate model based on project configuration."""
    model_type = proj_config.get("model_type")
    threshold = proj_config.get("novelty_threshold", 0.5)

    if model_type == "cv_diff":
        return CVDiffModel(novelty_threshold=threshold)
    elif model_type == "cnn_classifier":
        num_classes = proj_config.get("num_classes", 3)
        labels_map = proj_config.get("labels_map", {})
        # Ensure integer keys in labels_map
        int_labels_map = {int(k): str(v) for k, v in labels_map.items()} if labels_map else None
        return CNNClassifierModel(
            num_classes=num_classes,
            novelty_threshold=threshold,
            labels_map=int_labels_map
        )
    else:
        raise ValueError(f"Unknown model_type '{model_type}' for project '{proj_config.get('slug')}'")

def run_triage(project_slug: str) -> int:
    """
    Run triage scoring on all unscored subjects for a project.
    Incremental execution: skips subjects already scored by this model.
    """
    proj_config = get_project(project_slug)
    db_path = proj_config["db_path"]
    model = instantiate_model(proj_config)

    subjects = unscored_subjects(db_path, project_slug, model.name)
    logger.info(f"Found {len(subjects)} unscored subjects for project '{project_slug}' using model '{model.name}'")

    count = 0
    for subj in subjects:
        subj_id = subj["id"]
        ref_path = subj["reference_image_path"]
        moving_path = subj.get("moving_image_path")

        if model.name == "cv_diff":
            if not moving_path:
                # Fallback if moving image is missing for cv_diff
                moving_path = ref_path
            pred = model.predict_pair(ref_path, moving_path)
        else:
            pred = model.predict(ref_path)

        save_score(
            db_path=db_path,
            subject_id=subj_id,
            model_name=model.name,
            predicted_label=pred["predicted_label"],
            confidence=pred["confidence"],
            novelty_score=pred["novelty_score"],
            is_novel=pred["is_novel"]
        )
        count += 1

    logger.info(f"Successfully triaged {count} subjects for project '{project_slug}'")
    return count
