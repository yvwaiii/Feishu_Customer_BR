#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
FCODE="${2:-}"
SOURCE="${3:-}"

if [[ -z "${FCODE}" || ! "${FCODE}" =~ ^[FL][A-Za-z0-9]+$ ]]; then
  echo "必须提供合法的主租户 F/L 码。" >&2
  exit 2
fi

if [[ -n "${AILY_WORKSPACE:-}" ]]; then
  ROOT="${AILY_WORKSPACE}"
elif [[ -d "${HOME}/.aily/workspace" ]]; then
  ROOT="${HOME}/.aily/workspace"
else
  ROOT="${HOME}/.cache"
fi

CACHE_DIR="${ROOT}/artifacts/customer-business-review/${FCODE}"
CACHE_FILE="${CACHE_DIR}/c360-data.md"

case "${ACTION}" in
  resolve)
    if [[ -n "${SOURCE}" && -r "${SOURCE}" ]]; then
      printf '%s\n' "${SOURCE}"
    elif [[ -r "${CACHE_FILE}" ]]; then
      printf '%s\n' "${CACHE_FILE}"
    else
      exit 1
    fi
    ;;
  save)
    if [[ -z "${SOURCE}" || ! -r "${SOURCE}" ]]; then
      echo "待保存的 C360 数据文件不可读。" >&2
      exit 3
    fi
    mkdir -p "${CACHE_DIR}"
    cp "${SOURCE}" "${CACHE_FILE}"
    printf '%s\n' "${CACHE_FILE}"
    ;;
  *)
    echo "用法：cache-c360-artifact.sh resolve|save <F/L码> [source]" >&2
    exit 2
    ;;
esac
