"""Builds lambda-deployment.zip outside the backend directory for AWS Lambda."""
import os
import zipfile

def build():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    backend = os.path.join(root, "backend")
    zip_path = os.path.join(root, "lambda-deployment.zip")

    if os.path.exists(zip_path):
        os.remove(zip_path)

    site_packages = os.path.join(backend, ".venv", "Lib", "site-packages")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add functions/
        for r, dirs, files in os.walk(os.path.join(backend, "functions")):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if not file.endswith(".pyc"):
                    fp = os.path.join(r, file)
                    arcname = os.path.relpath(fp, backend)
                    zf.write(fp, arcname)

        # Add shared/ (including sources.json)
        for r, dirs, files in os.walk(os.path.join(backend, "shared")):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if not file.endswith(".pyc"):
                    fp = os.path.join(r, file)
                    arcname = os.path.relpath(fp, backend)
                    zf.write(fp, arcname)

        # Add pure-python packages (tzdata, dotenv)
        if os.path.exists(site_packages):
            for pkg in ["tzdata", "dotenv"]:
                pdir = os.path.join(site_packages, pkg)
                if os.path.exists(pdir):
                    for r, dirs, files in os.walk(pdir):
                        dirs[:] = [d for d in dirs if d != "__pycache__"]
                        for file in files:
                            if not file.endswith(".pyc"):
                                fp = os.path.join(r, file)
                                arcname = os.path.relpath(fp, site_packages)
                                zf.write(fp, arcname)

    size_kb = round(os.path.getsize(zip_path) / 1024, 2)
    print(f"Created: {zip_path} ({size_kb} KB)")

if __name__ == "__main__":
    build()

