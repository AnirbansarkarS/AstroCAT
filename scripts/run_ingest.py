#!/usr/bin/env python
import argparse
import sys
import os

# Ensure src/ is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from astrocat.ingest import ingest_subjects, ingest_aggregated_labels_from_csv

def main():
    parser = argparse.ArgumentParser(description="AstroCAT Ingest CLI")
    parser.add_argument("--project", type=str, required=True, help="Project slug in projects.yaml")
    parser.add_argument("--max-subjects", type=int, default=200, help="Max subjects to ingest")
    parser.add_argument("--labels-csv", type=str, default=None, help="Path to aggregated labels CSV")
    args = parser.parse_args()

    print(f"Ingesting subjects for project '{args.project}' (max: {args.max_subjects})...")
    sub_count = ingest_subjects(args.project, max_subjects=args.max_subjects)
    print(f"Ingested {sub_count} subjects.")

    if args.labels_csv:
        print(f"Ingesting labels from {args.labels_csv}...")
        lbl_count = ingest_aggregated_labels_from_csv(args.project, args.labels_csv)
        print(f"Ingested {lbl_count} labels.")

if __name__ == "__main__":
    main()
