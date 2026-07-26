import os
import argparse
from flask import Flask, render_template, request, send_file, abort
from astrocat.config import get_project
from astrocat.storage import triage_queue

def create_app(project_slug: str = "active-asteroids") -> Flask:
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.config["PROJECT_SLUG"] = project_slug

    @app.route("/")
    def index():
        slug = request.args.get("project", app.config["PROJECT_SLUG"])
        try:
            proj_config = get_project(slug)
            queue = triage_queue(proj_config["db_path"], slug)
            return render_template("index.html", project=proj_config, queue=queue)
        except Exception as e:
            return f"Error loading project '{slug}': {e}", 400

    @app.route("/image")
    def serve_image():
        path = request.args.get("path")
        if not path or not os.path.exists(path):
            abort(404, description="Image file not found")
        return send_file(path)

    return app

def main():
    parser = argparse.ArgumentParser(description="AstroCAT Triage Dashboard")
    parser.add_argument("--project", type=str, default="active-asteroids", help="Project slug (e.g. active-asteroids, galaxy-zoo)")
    parser.add_argument("--port", type=int, default=5000, help="Port to run dashboard server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    args = parser.parse_args()

    app = create_app(project_slug=args.project)
    print(f"Starting AstroCAT Dashboard for project '{args.project}' on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)

if __name__ == "__main__":
    main()
