from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

app = Flask(__name__)

DATA_FILE = Path("registry_data.json")
ALLOWED_PROVIDERS = {"aws", "gcs", "azure", "datalabs", "other"}
DEFAULT_PROVIDER = "aws"
DEFAULT_VERSION = "1.0"
CONTACT_PATTERN = re.compile(
    r"^(?:<(?P<email_only>[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)>|(?P<name>[^<>\n]+)\s<(?P<email_named>[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)>)$"
)

DEFAULT_REGISTRY_DOCUMENT: dict[str, Any] = {
    "version": "1.0",
    "modificationDate": "2022-01-01T00:00:00Z",
    "registry": [
        {
            "endpoint": "s3://gov-nasa-hdrl-data1/",
            "name": "GSFC HelioCloud Set 1",
            "provider": "aws",
            "region": "us-east-1",
            "contact": "HelioCloud Team <heliocloud@example.org>",
        }
    ],
}

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dataset Registry</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 2rem auto;
      max-width: 960px;
      padding: 0 1rem;
      line-height: 1.5;
    }
    h1, h2 { margin-bottom: 0.5rem; }
    .card {
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 1rem;
      background: #fafafa;
    }
    label {
      display: block;
      font-weight: 600;
      margin-top: 0.75rem;
    }
    input, select {
      width: 100%;
      padding: 0.65rem;
      margin-top: 0.25rem;
      box-sizing: border-box;
    }
    button {
      margin-top: 1rem;
      padding: 0.75rem 1rem;
      cursor: pointer;
    }
    code, pre {
      background: #f4f4f4;
      border-radius: 6px;
    }
    pre {
      padding: 1rem;
      overflow-x: auto;
    }
    .grid {
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }
    .muted { color: #666; }
    .error {
      color: #8b0000;
      font-weight: 600;
    }
  </style>
</head>
<body>
  <h1>Dataset Registry</h1>
  <p class="muted">This Flask app serves registry JSON matching the requested schema and provides a minimal form for editing it.</p>

  {% if error %}
    <p class="error">{{ error }}</p>
  {% endif %}

  <div class="card">
    <h2>Add registry entry</h2>
    <form method="post" action="{{ url_for('add_registry_entry_from_form') }}">
      <div class="grid">
        <div>
          <label for="endpoint">Endpoint</label>
          <input id="endpoint" name="endpoint" placeholder="s3://my-bucket/" value="{{ form_data.endpoint }}" required>
        </div>
        <div>
          <label for="name">Dataset name</label>
          <input id="name" name="name" placeholder="My dataset" value="{{ form_data.name }}" required>
        </div>
        <div>
          <label for="provider">Provider</label>
          <select id="provider" name="provider">
            {% for provider in providers %}
              <option value="{{ provider }}" {% if provider == form_data.provider %}selected{% endif %}>{{ provider }}</option>
            {% endfor %}
          </select>
        </div>
        <div>
          <label for="region">Region</label>
          <input id="region" name="region" placeholder="us-east-1" value="{{ form_data.region }}" required>
        </div>
        <div>
          <label for="contact">Contact</label>
          <input id="contact" name="contact" placeholder="Name <email@example.org> or <email@example.org>" value="{{ form_data.contact }}" required>
        </div>
      </div>
      <button type="submit">Add entry</button>
    </form>
  </div>

  <div class="card">
    <h2>Current JSON</h2>
    <p><strong>JSON endpoint:</strong> <a href="{{ url_for('get_registry') }}">{{ url_for('get_registry') }}</a></p>
    <pre>{{ registry_json }}</pre>
  </div>
</body>
</html>
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_registry_document() -> dict[str, Any]:
    if not DATA_FILE.exists():
        save_registry_document(deepcopy(DEFAULT_REGISTRY_DOCUMENT))

    with DATA_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    validate_registry_document(data)
    return data


def save_registry_document(data: dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def validate_contact(contact: Any) -> None:
    if not isinstance(contact, str) or not CONTACT_PATTERN.fullmatch(contact.strip()):
        raise ValueError("contact must be in the form '<email>' or 'Name <email>'")


def validate_registry_entry(entry: dict[str, Any]) -> dict[str, str]:
    required_fields = {"endpoint", "name", "provider", "region", "contact"}
    missing = required_fields - set(entry.keys())
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"registry entry is missing required field(s): {missing_str}")

    normalized = {
        "endpoint": str(entry["endpoint"]).strip(),
        "name": str(entry["name"]).strip(),
        "provider": str(entry.get("provider", DEFAULT_PROVIDER)).strip().lower(),
        "region": str(entry["region"]).strip(),
        "contact": str(entry["contact"]).strip(),
    }

    if not normalized["endpoint"]:
        raise ValueError("endpoint must not be empty")
    if not normalized["name"]:
        raise ValueError("name must not be empty")
    if not normalized["region"]:
        raise ValueError("region must not be empty")
    if normalized["provider"] not in ALLOWED_PROVIDERS:
        allowed = ", ".join(sorted(ALLOWED_PROVIDERS))
        raise ValueError(f"provider must be one of: {allowed}")

    validate_contact(normalized["contact"])
    return normalized


def validate_registry_document(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("registry document must be an object")

    if str(data.get("version")) != DEFAULT_VERSION:
        raise ValueError("version must be '1.0'")

    registry = data.get("registry")
    if not isinstance(registry, list):
        raise ValueError("registry must be a list")

    for entry in registry:
        if not isinstance(entry, dict):
            raise ValueError("each registry entry must be an object")
        validate_registry_entry(entry)


def append_registry_entry(entry: dict[str, Any]) -> dict[str, Any]:
    document = load_registry_document()
    normalized_entry = validate_registry_entry(entry)
    document["registry"].append(normalized_entry)
    document["modificationDate"] = utc_now_iso()
    save_registry_document(document)
    return document


@app.route("/", methods=["GET"])
def index() -> str:
    document = load_registry_document()
    return render_template_string(
        HTML_TEMPLATE,
        registry_json=json.dumps(document, indent=4),
        providers=sorted(ALLOWED_PROVIDERS),
        default_provider=DEFAULT_PROVIDER,
        error=None,
        form_data={
            "endpoint": "",
            "name": "",
            "provider": DEFAULT_PROVIDER,
            "region": "",
            "contact": "",
        },
    )


@app.route("/registry", methods=["GET"])
def get_registry():
    return jsonify(load_registry_document())


@app.route("/registry", methods=["POST"])
def add_registry_entry_api():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    try:
        document = append_registry_entry(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(document), 201


@app.route("/add", methods=["POST"])
def add_registry_entry_from_form():
    entry = {
        "endpoint": request.form.get("endpoint", ""),
        "name": request.form.get("name", ""),
        "provider": request.form.get("provider", DEFAULT_PROVIDER),
        "region": request.form.get("region", ""),
        "contact": request.form.get("contact", ""),
    }

    try:
        append_registry_entry(entry)
    except ValueError as exc:
        document = load_registry_document()
        return (
            render_template_string(
                HTML_TEMPLATE,
                registry_json=json.dumps(document, indent=4),
                providers=sorted(ALLOWED_PROVIDERS),
                default_provider=DEFAULT_PROVIDER,
                error=str(exc),
                form_data=entry,
            ),
            400,
        )

    return redirect(url_for("index"))


if __name__ == "__main__":
    load_registry_document()
    app.run(host="0.0.0.0", port=5000, debug=True)
