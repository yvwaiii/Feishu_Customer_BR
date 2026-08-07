#!/usr/bin/env python3
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
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
minimum_skillhub = manifest["minimum_skillhub_version"]
if f"SkillHub 版本不得低于 `{minimum_skillhub}`" not in readme:
    errors.append("README SkillHub 最低版本未同步")
for relative in ("scripts/render-snapshot.py", "scripts/audit-snapshot.py"):
    content = (root / relative).read_text()
    version_match = re.search(r'^CONTENT_VERSION\s*=\s*"([^"]+)"', content, flags=re.M)
    if not version_match or version_match.group(1) != expected:
        errors.append(f"{relative} 内容版本未同步")

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

package_files = manifest.get("package_files", [])
if package_files != sorted(set(package_files)):
    errors.append("package_files 必须按字典序排列且不得重复")
package_set = set(package_files)
actual_files = set()
for path in root.rglob("*"):
    relative = path.relative_to(root)
    if ".git" in relative.parts:
        continue
    if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
        continue
    if path.name == ".DS_Store":
        continue
    if path.is_file():
        actual_files.add(relative.as_posix())

missing_allowlist = package_set - actual_files
unexpected_files = actual_files - package_set
for relative in sorted(missing_allowlist):
    errors.append(f"allowlist 文件不存在：{relative}")
for relative in sorted(unexpected_files):
    errors.append(f"文件未进入 package_files allowlist：{relative}")
for relative in package_files:
    path = root / relative
    if not path.is_file():
        continue
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o002:
        errors.append(f"allowlist 文件可被任意用户写入：{relative} ({oct(mode)})")
    if relative.startswith("scripts/") and not mode & 0o100:
        errors.append(f"allowlist 脚本不可执行：{relative} ({oct(mode)})")

contract = manifest.get("delivery_contract", {})
if contract.get("required_field_count") != 41:
    errors.append("delivery_contract.required_field_count 必须为 41")
if contract.get("meeting_required_field_count") != 9:
    errors.append("delivery_contract.meeting_required_field_count 必须为 9")
if contract.get("display_rounding") != "ROUND_HALF_UP_integer":
    errors.append("delivery_contract.display_rounding 必须为 ROUND_HALF_UP_integer")
field_result = subprocess.run(
    [sys.executable, str(root / "scripts/query-fields.py")],
    cwd=root,
    text=True,
    capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
)
if field_result.returncode != 0:
    errors.append(f"字段合同读取失败：{field_result.stderr}")
else:
    fields = json.loads(field_result.stdout)["required_fields"]
    meeting_fields = {
        "vc_dau", "vc_dau_penetration_rate", "vc_meeting_cnt",
        "join_meeting_ucnt", "vc_meeting_active_duration_pavg_val",
        "minutes_dau", "minutes_dau_penetration_rate", "vc_ai_dau",
        "vc_ai_minutes_dau_penetration_rate",
    }
    if len(fields) != 41:
        errors.append(f"实际必需字段数为 {len(fields)}，应为 41")
    if not meeting_fields.issubset(fields):
        errors.append("实际字段合同未完整包含会议九项")

for forbidden in [
    "npm install -g @customer360/lark-c360",
    "lark-cli whiteboard +create",
    "数值区只保留纯数字",
]:
    if forbidden in skill:
        errors.append(f"SKILL.md 包含过期规则：{forbidden}")

if not errors:
    package_script = root / "scripts/package-release.py"
    with tempfile.TemporaryDirectory() as temp_dir:
        first = Path(temp_dir) / "first.zip"
        second = Path(temp_dir) / "second.zip"
        for output in (first, second):
            result = subprocess.run(
                [sys.executable, str(package_script), "--output", str(output)],
                cwd=root,
                text=True,
                capture_output=True,
            )
            if result.returncode != 0:
                errors.append(f"确定性打包失败：{result.stderr or result.stdout}")
                break
        if errors:
            first_sha = second_sha = None
        else:
            first_sha = hashlib.sha256(first.read_bytes()).hexdigest()
            second_sha = hashlib.sha256(second.read_bytes()).hexdigest()
        if first_sha != second_sha:
            errors.append("相同输入生成的发布包不确定")

if errors:
    print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
    sys.exit(1)

print(json.dumps({
    "ok": True,
    "content_version": expected,
    "minimum_skillhub_version": minimum_skillhub,
    "required_files": len(manifest["required_files"]),
    "package_files": len(package_files),
    "deterministic_package": True,
}, ensure_ascii=False))
