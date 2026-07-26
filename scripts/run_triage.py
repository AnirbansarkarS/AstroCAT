#!/usr/bin/env python
import argparse
import sys
import os

# Ensure src/ is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from astrocat.triage import run_triage

def main():
    parser = argparse.ArgumentParser(description="AstroCAT Triage Pipeline CLI")
    parser.add_argument("--project", type=str, required=True, help="Project slug in projects.yaml")
    args = parser.parse_args()

    print(f"Running triage pipeline for project '{args.project}'...")
    count = run_triage(args.project)
    print(f"Finished triage scoring. Scored {count} new subjects.")

if __name__ == "__main__":
    main()
