"""Write docs/openapi.json and a Postman collection generated from the live FastAPI schema.

Usage (from backend/): python -m scripts.export_api_docs
"""

import json
from pathlib import Path

from app.main import app

DOCS = Path(__file__).resolve().parents[2] / "docs"


def main() -> None:
    spec = app.openapi()
    DOCS.mkdir(exist_ok=True)
    (DOCS / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    folders: dict[str, list] = {}
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            query = [
                {"key": p["name"], "value": "", "disabled": True, "description": p.get("description", "")}
                for p in op.get("parameters", [])
                if p["in"] == "query"
            ]
            url_path = path.replace("{customer_id}", "{{customer_id}}")
            request = {
                "method": method.upper(),
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "url": {
                    "raw": "{{base_url}}" + url_path,
                    "host": ["{{base_url}}"],
                    "path": [s for s in url_path.split("/") if s],
                    "query": query,
                },
                "description": op.get("summary", ""),
            }
            if path == "/api/reviews/{customer_id}" and method == "patch":
                request["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(
                        {
                            "review_status": "UNDER_INVESTIGATION",
                            "review_notes": "Checking",
                            "updated_by": "Admin",
                        },
                        indent=2,
                    ),
                }
            if path == "/api/ml/predict":
                request["body"] = {"mode": "raw", "raw": json.dumps({"customer_id": "CUST0046"}, indent=2)}
            if path == "/api/data/import":
                request["header"] = []
                request["body"] = {
                    "mode": "formdata",
                    "formdata": [{"key": "file", "type": "file", "src": ""}],
                }
            tag = (op.get("tags") or ["other"])[0]
            folders.setdefault(tag, []).append({"name": f"{method.upper()} {path}", "request": request})

    collection = {
        "info": {
            "name": "Customer Return Risk Analyzer API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": "Generated from the FastAPI OpenAPI schema by scripts/export_api_docs.py",
        },
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000"},
            {"key": "customer_id", "value": "CUST0046"},
        ],
        "item": [{"name": tag, "item": items} for tag, items in folders.items()],
    }
    (DOCS / "api.postman_collection.json").write_text(json.dumps(collection, indent=2), encoding="utf-8")
    print(f"Wrote {DOCS / 'openapi.json'} and {DOCS / 'api.postman_collection.json'}")


if __name__ == "__main__":
    main()
