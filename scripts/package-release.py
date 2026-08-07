#!/usr/bin/env python3
import argparse
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath


FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ARCHIVE_ROOT = "customer-business-review"


def build_archive(root, output):
    manifest = json.loads((root / "release-manifest.json").read_text())
    files = manifest["package_files"]
    if files != sorted(set(files)):
        raise ValueError("package_files 必须排序且不得重复")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for relative in files:
            source = root / relative
            if not source.is_file():
                raise FileNotFoundError(f"allowlist 文件不存在：{relative}")
            archive_name = str(PurePosixPath(ARCHIVE_ROOT, relative))
            info = zipfile.ZipInfo(archive_name, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if relative.startswith("scripts/") else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.create_system = 3
            archive.writestr(info, source.read_bytes(), compresslevel=9)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    if root == output or root in output.parents:
        raise ValueError("发布包必须输出到仓库目录之外，避免污染 allowlist")
    build_archive(root, output)
    print(json.dumps({"ok": True, "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
