import pytest
from pathlib import Path
from astrocat.config import get_project, get_repo_root

def test_get_project_active_asteroids():
    config = get_project("active-asteroids")
    assert config["slug"] == "active-asteroids"
    assert config["model_type"] == "cv_diff"
    assert Path(config["data_dir"]).is_absolute()
    assert Path(config["db_path"]).is_absolute()
    assert Path(config["subjects_dir"]).is_absolute()

def test_get_project_invalid():
    with pytest.raises(KeyError):
        get_project("non-existent-project")
