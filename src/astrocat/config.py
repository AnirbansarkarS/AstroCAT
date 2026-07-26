import os
from pathlib import Path
import yaml

def get_repo_root() -> Path:
    """Return the absolute path of the repository root."""
    # src/astrocat/config.py -> parent x 3 is repo root
    return Path(__file__).resolve().parent.parent.parent

def load_projects_yaml() -> dict:
    """Load raw projects config from config/projects.yaml."""
    config_path = get_repo_root() / "config" / "projects.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_project(project_slug: str) -> dict:
    """
    Get resolved project configuration dict.
    Relative paths in config are converted to absolute paths anchored at repo root.
    """
    data = load_projects_yaml()
    projects = data.get("projects", {})
    if project_slug not in projects:
        available = list(projects.keys())
        raise KeyError(f"Project '{project_slug}' not found in projects.yaml. Available: {available}")
    
    proj_config = dict(projects[project_slug])
    proj_config["slug"] = project_slug
    repo_root = get_repo_root()

    # Resolve paths
    for key in ["data_dir", "db_path", "subjects_dir"]:
        if key in proj_config and proj_config[key]:
            abs_path = (repo_root / proj_config[key]).resolve()
            proj_config[key] = str(abs_path)
            # Ensure directories exist
            if key in ["data_dir", "subjects_dir"]:
                os.makedirs(abs_path, exist_ok=True)
            elif key == "db_path":
                os.makedirs(abs_path.parent, exist_ok=True)

    return proj_config
