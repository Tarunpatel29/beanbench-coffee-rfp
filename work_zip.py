"""Package a clean project ZIP for a class submission."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).parent
OUTPUT = ROOT / "beanbench_submission.zip"
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_NAMES = {"beanbench.db", "beanbench_submission.zip", "secrets.toml"}

if __name__ == "__main__":
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name in SKIP_NAMES or any(part in SKIP_PARTS for part in path.parts):
                continue
            archive.write(path, path.relative_to(ROOT.parent))
    print(f"Created {OUTPUT}")
