#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://lf-ldic360.feishucdn.com/obj/ldi-c360/cli/lark-c360"
MANIFEST_URL="${BASE_URL}/manifest.json"

if command -v lark-c360 >/dev/null 2>&1; then
  command -v lark-c360
  exit 0
fi

if [[ -x "${AILY_WORKSPACE:-${HOME}/.aily/workspace}/bin/lark-c360" ]]; then
  printf '%s\n' "${AILY_WORKSPACE:-${HOME}/.aily/workspace}/bin/lark-c360"
  exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "缺少 npm，无法安装官方 lark-c360 npm 包。" >&2
  exit 2
fi

if [[ -n "${AILY_WORKSPACE:-}" ]]; then
  PREFIX="${AILY_WORKSPACE}"
elif [[ -d "${HOME}/.aily/workspace" || -d "${HOME}/.aily" ]]; then
  PREFIX="${HOME}/.aily/workspace"
else
  PREFIX="${LARK_C360_PREFIX:-${HOME}/.local/lark-c360}"
fi

mkdir -p "${PREFIX}" "${PREFIX}/bin"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

curl -fsSL "${MANIFEST_URL}" -o "${TMP_DIR}/manifest.json"

read -r ARCHIVE EXPECTED_SHA < <(
  node -e '
    const fs = require("fs");
    const m = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
    const p = m.npm_package;
    if (!p || !p.latest_archive || !p.latest_sha256) process.exit(2);
    process.stdout.write(`${p.latest_archive} ${p.latest_sha256}\n`);
  ' "${TMP_DIR}/manifest.json"
)

curl -fsSL "${BASE_URL}/latest/${ARCHIVE}" -o "${TMP_DIR}/${ARCHIVE}"

if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL_SHA="$(sha256sum "${TMP_DIR}/${ARCHIVE}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL_SHA="$(shasum -a 256 "${TMP_DIR}/${ARCHIVE}" | awk '{print $1}')"
else
  echo "缺少 sha256sum 或 shasum，无法校验安装包。" >&2
  exit 3
fi
if [[ "${ACTUAL_SHA}" != "${EXPECTED_SHA}" ]]; then
  echo "lark-c360 安装包 SHA256 校验失败。" >&2
  exit 3
fi

npm install -g "${TMP_DIR}/${ARCHIVE}" --prefix "${PREFIX}" --no-audit --no-fund >/dev/null

BIN="${PREFIX}/bin/lark-c360"
if [[ ! -x "${BIN}" ]]; then
  echo "lark-c360 安装完成但未找到可执行文件：${BIN}" >&2
  exit 4
fi

"${BIN}" --version >&2
"${BIN}" install-skills >/dev/null 2>&1 || true
printf '%s\n' "${BIN}"
