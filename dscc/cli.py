import os
import shutil
import sys
import yaml
from pathlib import Path

APPS_DIR = Path("apps")
TEMPLATE_APP_DIR = Path("template_app")
INDEX_FILE = APPS_DIR / "index.yaml"

class AppCLI:

    def create_app(self, name):
        """
        Create a new app by copying from template_app to apps/<name>.
        Also updates apps/index.yaml if it exists.
        """
        src = TEMPLATE_APP_DIR
        dest = APPS_DIR / name

        if not src.exists():
            print("❌ template_app directory does not exist.")
            sys.exit(1)

        if dest.exists():
            print(f"❌ App '{name}' already exists in apps/")
            sys.exit(1)

        shutil.copytree(src, dest)
        print(f"✅ Created new app at {dest}")

        # Update index
        self._update_index(name)

    def list_apps(self):
        """
        List all apps under the apps/ directory.
        """
        if not APPS_DIR.exists():
            print("📁 No apps directory found.")
            return

        apps = [d.name for d in APPS_DIR.iterdir() if d.is_dir() and d.name != 'template_app']
        if not apps:
            print("🪹 No apps found.")
            return

        print("📦 Available apps:")
        for app in sorted(apps):
            print(f" - {app}")

    def delete_app(self, name):
        """
        Delete an existing app from the apps/ directory.
        """
        target = APPS_DIR / name
        if not target.exists():
            print(f"❌ App '{name}' does not exist.")
            sys.exit(1)

        shutil.rmtree(target)
        print(f"🗑️ Deleted app '{name}' from apps/.")

        # Update index
        self._remove_from_index(name)

    def _update_index(self, name):
        """
        Append the app name to apps/index.yaml for tracking.
        """
        if not INDEX_FILE.exists():
            INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(INDEX_FILE, 'w') as f:
                yaml.dump({'apps': [name]}, f)
            return

        with open(INDEX_FILE, 'r') as f:
            index = yaml.safe_load(f) or {}

        index.setdefault('apps', [])
        if name not in index['apps']:
            index['apps'].append(name)

        with open(INDEX_FILE, 'w') as f:
            yaml.safe_dump(index, f)

    def _remove_from_index(self, name):
        """
        Remove the app name from apps/index.yaml.
        """
        if not INDEX_FILE.exists():
            return

        with open(INDEX_FILE, 'r') as f:
            index = yaml.safe_load(f) or {}

        if 'apps' in index and name in index['apps']:
            index['apps'].remove(name)

        with open(INDEX_FILE, 'w') as f:
            yaml.safe_dump(index, f)

def main():
    import fire
    fire.Fire(AppCLI)

if __name__ == "__main__":
    main()
