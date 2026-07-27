#!/usr/bin/env python
"""
Run the full AstroCAT 5-stage pipeline end-to-end:
1. Zooniverse (Source)
2. Ingest (Fetch subjects & labels)
3. Storage (SQLite persistence)
4. Triage Model (Score subjects with cv_diff or cnn_classifier)
5. Review Queue (Display ranked queue summary & launch web dashboard)
"""
import argparse
import sys
import os

# Ensure src/ is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from astrocat.config import get_project
from astrocat.ingest import ingest_subjects, ingest_aggregated_labels_from_csv
from astrocat.triage import run_triage
from astrocat.storage import triage_queue

def main():
    parser = argparse.ArgumentParser(description="AstroCAT End-to-End 5-Stage Pipeline CLI")
    parser.add_argument("--project", type=str, required=True, help="Project slug in projects.yaml (e.g. active-asteroids, galaxy-zoo)")
    parser.add_argument("--max-subjects", type=int, default=50, help="Max subjects to ingest")
    parser.add_argument("--labels-csv", type=str, default=None, help="Path to optional aggregated labels CSV")
    parser.add_argument("--serve", action="store_true", help="Launch the review dashboard web server after triage")
    parser.add_argument("--port", type=int, default=5000, help="Dashboard web server port")
    args = parser.parse_args()

    print("=" * 60)
    print("🐱 AstroCAT 5-Stage Triage Pipeline")
    print("=" * 60)

    # 1. Zooniverse Source Config
    proj_config = get_project(args.project)
    print(f"\n[Stage 1: Source] Configured project '{proj_config['name']}' (Model: {proj_config['model_type']})")

    # 2. Ingest
    print(f"\n[Stage 2: Ingest] Fetching batch from Zooniverse API (max {args.max_subjects})...")
    ingest_count = ingest_subjects(args.project, max_subjects=args.max_subjects)
    if args.labels_csv:
        lbl_count = ingest_aggregated_labels_from_csv(args.project, args.labels_csv)
        print(f"  └ Ingested {lbl_count} aggregated human vote labels from {args.labels_csv}")
    print(f"  └ Total ingested subjects: {ingest_count}")

    # 3 & 4. Storage & Triage Model
    print(f"\n[Stage 3 & 4: Storage & Triage Model] Scoring unscored subjects...")
    scored_count = run_triage(args.project)
    print(f"  └ Scored {scored_count} new subjects in database: {proj_config['db_path']}")

    # 5. Review Queue
    queue = triage_queue(proj_config["db_path"], args.project)
    novel_count = sum(1 for item in queue if item.get("is_novel"))
    print(f"\n[Stage 5: Review Queue] Priority Queue Summary:")
    print(f"  └ Total Queue Items : {len(queue)}")
    print(f"  └ Novel/Flagged Items: {novel_count}")

    if queue:
        print("\nTop Priority Items in Queue:")
        for idx, item in enumerate(queue[:5], 1):
            flag = "⚡ NOVEL" if item['is_novel'] else "STANDARD"
            print(f"  {idx}. ID: #{item['subject_id']:<10} | Pred: {item['predicted_label']:<20} | Conf: {item['confidence']*100:.1f}% | Novelty: {item['novelty_score']:.3f} [{flag}]")

    if args.serve:
        print(f"\n🚀 Launching Review Dashboard at http://127.0.0.1:{args.port} ...")
        from astrocat.dashboard.app import create_app
        app = create_app(project_slug=args.project)
        app.run(host="127.0.0.1", port=args.port, debug=False)

if __name__ == "__main__":
    main()
