from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "deliverables"
ZIP_PATH = OUTPUT_DIR / "agent-qualityops-mvp.zip"
DELIVERY_NOTE = OUTPUT_DIR / "Agent-QualityOps-交付说明.md"
PORTFOLIO_PAGE = OUTPUT_DIR / "Agent-QualityOps-作品集.html"
VIDEO_DESIGN = OUTPUT_DIR / "Agent-QualityOps-演示视频设计.md"

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    "work",
    "deliverables",
}
EXCLUDED_SUFFIXES = {".pyc", ".db", ".tsbuildinfo", ".log"}
EXCLUDED_NAMES = {"vite.config.js", "vite.config.d.ts"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES or ".db-" in path.name or path.name in EXCLUDED_NAMES:
        return False
    if relative.as_posix().startswith("video/round3/audio/"):
        return False
    if relative.as_posix() == "video/round3/agent-qualityops-narration-mix.wav":
        return False
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return False
    return True


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and included(path):
                archive.write(path, Path("agent-qualityops") / path.relative_to(ROOT))

    shutil.copyfile(ROOT / "README.md", DELIVERY_NOTE)
    shutil.copyfile(ROOT / "portfolio" / "index.html", PORTFOLIO_PAGE)
    shutil.copyfile(ROOT / "docs" / "DEMO_VIDEO_DESIGN.md", VIDEO_DESIGN)
    print(ZIP_PATH)
    print(DELIVERY_NOTE)
    print(PORTFOLIO_PAGE)
    print(VIDEO_DESIGN)


if __name__ == "__main__":
    main()
