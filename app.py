"""
Flask server for the Bug Report Analyzer UI.

Serves the static frontend and exposes POST /api/analyze, which runs the
LangGraph pipeline and streams one JSON line per completed node so the UI
can show live progress.

Run:  python app.py   ->   http://127.0.0.1:5000
"""

import json
import os

from flask import Flask, Response, jsonify, request, send_from_directory

from bug_analyzer import build_graph

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Frontend files can live in ./static, ./templates, or next to app.py.
SEARCH_DIRS = [os.path.join(BASE_DIR, d) for d in ("static", "templates")] + [BASE_DIR]

app = Flask(__name__, static_folder=None)
graph = build_graph()


def find_file(filename):
    """Return the first search directory that contains `filename`, or None."""
    for directory in SEARCH_DIRS:
        if os.path.isfile(os.path.join(directory, filename)):
            return directory
    return None


@app.get("/")
def index():
    directory = find_file("index.html")
    if directory is None:
        return "index.html not found. Looked in: " + ", ".join(SEARCH_DIRS), 404
    return send_from_directory(directory, "index.html")


@app.get("/static/<path:filename>")
def assets(filename):
    directory = find_file(filename)
    if directory is None:
        return f"{filename} not found. Looked in: " + ", ".join(SEARCH_DIRS), 404
    return send_from_directory(directory, filename)


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    description = (payload.get("bug_description") or "").strip()

    if len(description) < 15:
        return jsonify(error="Add a bit more detail (at least a sentence) so the analysis is useful."), 400
    if len(description) > 5000:
        return jsonify(error="That description is too long. Keep it under 5,000 characters."), 400

    def stream():
        try:
            for update in graph.stream({"bug_description": description}, stream_mode="updates"):
                for node, data in update.items():
                    yield json.dumps({"node": node, "data": data}) + "\n"
        except Exception as exc:  # surface model/API errors to the UI
            yield json.dumps({"error": str(exc)}) + "\n"

    return Response(stream(), mimetype="application/x-ndjson")


if __name__ == "__main__":
    print("Serving UI files from:", find_file("index.html"))
    app.run(debug=True, port=5000)