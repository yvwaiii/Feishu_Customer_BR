#!/usr/bin/env python3
import json
import re
import stat
import sys
from pathlib import Path


root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "release-manifest.json").read_text())
errors = []

skill = (root / "SKILL.md").read_text()
readme = (root / "README.md").read_text()
match = re.search(r'^version:\s*"([^"]+)"', skill, flags=re.M)
skill_version = match.group(1) if match else None
expected = manifest["content_version"]

if skill_version != expected:
    errors.append(f"SKILL.md 版本 {skill_version} != {expected}")
if f"当前版本：`{expected}`" not in readme:
    errors.append("README 版本未同步")

for relative in manifest["required_files"]:
    path = root / relative
    if not path.is_file():
        errors.append(f"缺少文件：{relative}")
        continue
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o002:
        errors.append(f"文件可被任意用户写入：{relative} ({oct(mode)})")
    if relative.startswith("scripts/") and not mode & 0o100:
        errors.append(f"脚本不可执行：{relative} ({oct(mode)})")

for forbidden in [
    "npm install -g @customer360/lark-c360",
    "lark-cli whiteboard +create",
    "数值区只保留纯数字",
]:
    if forbidden in skill:
        errors.append(f"SKILL.md 包含过期规则：{forbidden}")

if errors:
    print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
    sys.exit(1)

print(json.dumps({
    "ok": True,
    "content_version": expected,
    "minimum_skillhub_version": manifest["minimum_skillhub_version"],
    "required_files": len(manifest["required_files"]),
}, ensure_ascii=False))
