"""extension/ -> dist/freeze-byte-extension-<versi>.zip untuk GitHub Release
dan Chrome Web Store. Folder test/ tidak ikut.

    python -m freezebyte.package_extension
"""
import json
import zipfile
from pathlib import Path

from freezebyte import config

EXCLUDED_DIRS = {"test"}


def package(src: Path, out_dir: Path) -> Path:
    version = json.loads((src / "manifest.json").read_text(encoding="utf-8"))["version"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"freeze-byte-extension-{version}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(src.rglob("*")):
            relative = path.relative_to(src)
            if path.is_dir() or relative.parts[0] in EXCLUDED_DIRS:
                continue
            archive.write(path, relative.as_posix())
    return out


if __name__ == "__main__":
    print(package(config.ROOT / "extension", config.ROOT / "dist"))
