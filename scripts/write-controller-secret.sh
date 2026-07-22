#!/usr/bin/env bash
set -euo pipefail

name="${1:-}"
if [[ ! "$name" =~ ^[a-z0-9][a-z0-9/-]{1,95}$ ]] || [[ "$name" == /* ]] || [[ "$name" == *..* ]]; then
  echo 'Invalid controller secret name.' >&2
  exit 2
fi

secret_dir="${AILAB_CONTROLLER_SECRET_DIR:-$HOME/.config/ailab}"
target_dir="$secret_dir/$(dirname "$name")"
mkdir -p "$target_dir"
chmod 700 "$secret_dir" "$target_dir"
umask 077
base_name="$(basename "$name")"
temporary="$(mktemp "$target_dir/.${base_name}.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
tr -d '\r\n' > "$temporary"
if [[ ! -s "$temporary" ]]; then
  echo 'Refusing to install an empty controller secret.' >&2
  exit 3
fi
chmod 600 "$temporary"
mv "$temporary" "$secret_dir/$name"
trap - EXIT
