import yaml
import os
import json
from pathlib import Path

OUTPUT_FILE = "frontend/static/detections.json"

def build_index():
    apps_dir = Path("apps")
    results = []

    for app_dir in apps_dir.iterdir():
        config_dir = app_dir / "base" / "config"
        if not config_dir.exists():
            continue

        for yaml_file in config_dir.glob("*.yaml"):
            with open(yaml_file, "r") as f:
                try:
                    data = yaml.safe_load(f)
                    results.append({
                        "app": app_dir.name,
                        "name": data.get("name", ""),
                        "description": data.get("description", ""),
                        "source": data.get("source", ""),
                        "sourcetype": data.get("sourcetype", ""),
                        "platform": data.get("platform", "")
                    })
                except yaml.YAMLError as e:
                    print(f"⚠️ Error parsing {yaml_file}: {e}")

    Path("frontend/static").mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as out:
        json.dump(results, out, indent=2)
    print(f"✅ Built detection index with {len(results)} items.")

if __name__ == "__main__":
    build_index()
