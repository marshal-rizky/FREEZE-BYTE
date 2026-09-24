import json
import zipfile

from freezebyte import package_extension


def test_package_includes_runtime_files_and_excludes_tests(tmp_path):
    src = tmp_path / "extension"
    (src / "src").mkdir(parents=True)
    (src / "data").mkdir()
    (src / "test").mkdir()
    (src / "manifest.json").write_text(json.dumps({"version": "0.1.0"}), encoding="utf-8")
    (src / "src" / "content.js").write_text("//", encoding="utf-8")
    (src / "data" / "universe.json").write_text("{}", encoding="utf-8")
    (src / "test" / "harness.html").write_text("x", encoding="utf-8")

    out = package_extension.package(src, tmp_path / "dist")

    assert out.name == "freeze-byte-extension-0.1.0.zip"
    names = set(zipfile.ZipFile(out).namelist())
    assert names == {"manifest.json", "src/content.js", "data/universe.json"}
