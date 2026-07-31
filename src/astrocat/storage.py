import sqlite3
import json
import os
from contextlib import contextmanager
from typing import Generator, List, Dict, Any, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS subjects (
    id TEXT PRIMARY KEY,
    project_slug TEXT NOT NULL,
    reference_image_path TEXT NOT NULL,
    moving_image_path TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    label TEXT NOT NULL,
    consensus_score REAL DEFAULT 1.0,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    predicted_label TEXT NOT NULL,
    confidence REAL NOT NULL,
    novelty_score REAL DEFAULT 0.0,
    is_novel INTEGER DEFAULT 0,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subjects_project ON subjects(project_slug);
CREATE INDEX IF NOT EXISTS idx_scores_subject_model ON scores(subject_id, model_name);
CREATE INDEX IF NOT EXISTS idx_scores_triage ON scores(is_novel, confidence);
"""

@contextmanager
def connect(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite DB connection with automatic schema init."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Initialize schema
    with conn:
        conn.executescript(SCHEMA_SQL)
    
    try:
        yield conn
    finally:
        conn.close()

def save_subject(
    db_path: str,
    subject_id: str,
    project_slug: str,
    reference_image_path: str,
    moving_image_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Save or update a subject record."""
    metadata_json = json.dumps(metadata) if metadata else None
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO subjects (id, project_slug, reference_image_path, moving_image_path, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                project_slug=excluded.project_slug,
                reference_image_path=excluded.reference_image_path,
                moving_image_path=excluded.moving_image_path,
                metadata_json=excluded.metadata_json;
            """,
            (subject_id, project_slug, reference_image_path, moving_image_path, metadata_json)
        )
        conn.commit()

def get_subject(db_path: str, subject_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single subject by ID."""
    with connect(db_path) as conn:
        cursor = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        row = cursor.fetchone()
        if row:
            res = dict(row)
            res["metadata"] = json.loads(res["metadata_json"]) if res.get("metadata_json") else {}
            return res
        return None

def save_labels(
    db_path: str,
    subject_id: str,
    label: str,
    consensus_score: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Insert aggregated label record."""
    metadata_json = json.dumps(metadata) if metadata else None
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO labels (subject_id, label, consensus_score, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            (subject_id, str(label), consensus_score, metadata_json)
        )
        conn.commit()

def save_score(
    db_path: str,
    subject_id: str,
    model_name: str,
    predicted_label: str,
    confidence: float,
    novelty_score: float = 0.0,
    is_novel: bool = False
) -> None:
    """Save model prediction score."""
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO scores (subject_id, model_name, predicted_label, confidence, novelty_score, is_novel)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (subject_id, model_name, str(predicted_label), float(confidence), float(novelty_score), 1 if is_novel else 0)
        )
        conn.commit()


def unscored_subjects(db_path: str, project_slug: str, model_name: str) -> List[Dict[str, Any]]:
    """Return subjects for a project that haven't been scored by model_name yet."""
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT s.* FROM subjects s
            LEFT JOIN scores sc ON s.id = sc.subject_id AND sc.model_name = ?
            WHERE s.project_slug = ? AND sc.id IS NULL
            ORDER BY s.created_at ASC
            """,
            (model_name, project_slug)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["metadata"] = json.loads(item["metadata_json"]) if item.get("metadata_json") else {}
            results.append(item)
        return results

def triage_queue(db_path: str, project_slug: str) -> List[Dict[str, Any]]:
    """
    Get triage queue ordered by:
    1. Novel / low-confidence flagged items first (is_novel DESC)
    2. Ascending confidence (lowest confidence first)
    """
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT 
                s.id as subject_id,
                s.project_slug,
                s.reference_image_path,
                s.moving_image_path,
                s.metadata_json,
                sc.model_name,
                sc.predicted_label,
                sc.confidence,
                sc.novelty_score,
                sc.is_novel,
                sc.scored_at
            FROM subjects s
            INNER JOIN scores sc ON s.id = sc.subject_id
            WHERE s.project_slug = ?
            ORDER BY sc.is_novel DESC, sc.confidence ASC
            """,
            (project_slug,)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["metadata"] = json.loads(item["metadata_json"]) if item.get("metadata_json") else {}
            results.append(item)
        return results
