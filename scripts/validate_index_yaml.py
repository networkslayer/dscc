import yaml
from pathlib import Path

def validate_and_fix_index():
    index_path = Path("apps/index.yaml")
    apps_dir = Path("apps")

    existing_apps = [
        app.name for app in apps_dir.iterdir()
        if app.is_dir() and (app / "base" / "config").exists()
    ]

    if not index_path.exists():
        print("❌ index.yaml not found. Creating a new one.")
        data = {"apps": existing_apps}
    else:
        with open(index_path, "r") as f:
            data = yaml.safe_load(f) or {}

        # Update to only include real apps
        data["apps"] = [app for app in data.get("apps", []) if app in existing_apps]

        # Add missing ones
        for app in existing_apps:
            if app not in data["apps"]:
                data["apps"].append(app)

    with open(index_path, "w") as f:
        yaml.dump(data, f, sort_keys=False)

    print(f"✅ index.yaml updated with {len(data['apps'])} apps.")

if __name__ == "__main__":
    validate_and_fix_index()
