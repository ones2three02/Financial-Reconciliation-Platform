#!/usr/bin/env bash
set -euo pipefail

variant="${1:-}"
case "$variant" in
  core|apex|signal) ;;
  *)
    echo "用法: $0 core|apex|signal" >&2
    exit 2
    ;;
esac

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
source_dir="$script_dir/variants/$variant/tauri"
tauri_icons="$repo_root/frontend/src-tauri/icons"
frontend_icon="$repo_root/frontend/src/assets/icon-source.png"
backup_dir="$script_dir/backups/$(date +%Y%m%d-%H%M%S)-$variant"

required=(
  32x32.png
  128x128.png
  128x128@2x.png
  icon-source.png
  icon.png
  icon.icns
  icon.ico
)

for file in "${required[@]}"; do
  if [[ ! -f "$source_dir/$file" ]]; then
    echo "图标包不完整，缺少: $source_dir/$file" >&2
    exit 1
  fi
done

mkdir -p "$backup_dir/tauri"
for target in "$tauri_icons"/*; do
  [[ -f "$target" ]] || continue
  file="$(basename "$target")"
  if [[ -f "$source_dir/$file" ]]; then
    cp "$target" "$backup_dir/tauri/$file"
    cp "$source_dir/$file" "$target"
  fi
done

if [[ -f "$frontend_icon" ]]; then
  cp "$frontend_icon" "$backup_dir/frontend-icon-source.png"
fi
cp "$source_dir/icon-source.png" "$frontend_icon"

web_favicon="$repo_root/frontend/public/favicon.svg"
if [[ -f "$web_favicon" ]]; then
  cp "$web_favicon" "$backup_dir/favicon.svg"
fi
cp "$script_dir/variants/$variant/app-icon.svg" "$web_favicon"

echo "桌面端与 Web 图标已切换为 ${variant}；原图标备份在: $backup_dir"
