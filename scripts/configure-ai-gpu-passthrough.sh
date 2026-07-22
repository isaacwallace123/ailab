#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---check}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR="${SCRIPT_DIR}/validate-ai-gpu-passthrough.sh"
MODULES_FILE="/etc/modules-load.d/ailab-vfio.conf"
MODPROBE_FILE="/etc/modprobe.d/ailab-vfio.conf"
MANAGED_MARKER="# Managed by ailab configure-ai-gpu-passthrough.sh"

usage() {
  cat <<'EOF'
Usage: configure-ai-gpu-passthrough.sh [MODE]

  --check       Read-only inventory and managed-file report.
  --apply       Install the legacy B50-only VFIO policy.
  --apply-both  Install the B50+B580 VFIO policy and rebuild initramfs.
  --rollback    Remove only this script's managed files and rebuild initramfs.

Apply modes require affected AI VMs to be stopped. This script never reboots the host or starts VMs.
EOF
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    printf 'Run this command as root on the Proxmox host.\n' >&2
    exit 1
  fi
}

require_validator() {
  [[ -f "${VALIDATOR}" ]] || {
    printf 'Missing sibling validator: %s\n' "${VALIDATOR}" >&2
    exit 1
  }
}

report_files() {
  for path in "${MODULES_FILE}" "${MODPROBE_FILE}"; do
    if [[ -e "${path}" ]]; then
      printf '%s: present\n' "${path}"
    else
      printf '%s: absent\n' "${path}"
    fi
  done
}

write_expected_files() {
  local temporary_directory="$1"
  local device_ids="$2"
  cat >"${temporary_directory}/modules-load.conf" <<EOF
${MANAGED_MARKER}
vfio
vfio_iommu_type1
vfio_pci
EOF
  cat >"${temporary_directory}/modprobe.conf" <<EOF
${MANAGED_MARKER}
options vfio-pci ids=${device_ids} disable_vga=1
softdep xe pre: vfio-pci
EOF
}

refuse_unmanaged_file() {
  local target="$1"
  local expected="$2"
  if [[ -e "${target}" ]] && ! cmp -s "${target}" "${expected}" && \
    ! grep -Fxq "${MANAGED_MARKER}" "${target}"; then
    printf 'Refusing to overwrite an existing unmanaged file: %s\n' "${target}" >&2
    exit 1
  fi
}

verify_effective_policy() {
  local device_ids="$1"
  local modprobe_configuration
  local dependencies
  local vfio_line
  local xe_line

  modprobe_configuration="$(modprobe -c)"
  grep -Fxq "options vfio_pci ids=${device_ids} disable_vga=1" <<<"${modprobe_configuration}"
  grep -Fxq 'softdep xe pre: vfio-pci' <<<"${modprobe_configuration}"

  dependencies="$(modprobe --show-depends xe)"
  vfio_line="$(printf '%s\n' "${dependencies}" | nl -ba | awk '/vfio-pci\.ko/ {print $1; exit}')"
  xe_line="$(printf '%s\n' "${dependencies}" | nl -ba | awk '/\/xe\.ko/ {print $1; exit}')"
  if [[ -z "${vfio_line}" || -z "${xe_line}" || "${vfio_line}" -ge "${xe_line}" ]]; then
    printf 'Effective module policy does not order vfio-pci before xe.\n' >&2
    exit 1
  fi
}

apply_configuration() {
  local target="$1"
  local device_ids
  local preflight_mode
  local post_reboot_mode
  if [[ "${target}" == "both" ]]; then
    device_ids="8086:e212,8086:e20b"
    preflight_mode="--preflight-both"
    post_reboot_mode="--require-both-vfio"
  else
    device_ids="8086:e212"
    preflight_mode="--preflight-b50"
    post_reboot_mode="--require-b50-vfio"
  fi

  require_root
  require_validator
  bash "${VALIDATOR}" "${preflight_mode}"

  local temporary_directory
  temporary_directory="$(mktemp -d)"
  trap 'rm -rf -- "${temporary_directory}"' RETURN
  write_expected_files "${temporary_directory}" "${device_ids}"
  refuse_unmanaged_file "${MODULES_FILE}" "${temporary_directory}/modules-load.conf"
  refuse_unmanaged_file "${MODPROBE_FILE}" "${temporary_directory}/modprobe.conf"

  local backup_directory
  backup_directory="/root/ailab-vfio-backup-$(date -u +%Y%m%dT%H%M%SZ)"
  install -d -m 0700 "${backup_directory}"
  for path in "${MODULES_FILE}" "${MODPROBE_FILE}"; do
    if [[ -e "${path}" ]]; then
      cp -a -- "${path}" "${backup_directory}/"
    fi
  done
  printf '%s\n' \
    "Applied by ${0} at $(date -u --iso-8601=seconds)" \
    "Host: $(hostname --fqdn 2>/dev/null || hostname)" \
    "Device IDs: ${device_ids}" \
    "Files: ${MODULES_FILE} ${MODPROBE_FILE}" >"${backup_directory}/MANIFEST.txt"

  install -m 0644 "${temporary_directory}/modules-load.conf" "${MODULES_FILE}"
  install -m 0644 "${temporary_directory}/modprobe.conf" "${MODPROBE_FILE}"
  update-initramfs -u -k all
  verify_effective_policy "${device_ids}"

  printf 'VFIO policy installed for %s. Backup: %s\n' "${target}" "${backup_directory}"
  printf 'The host was NOT rebooted. After the maintenance reboot, run:\n'
  printf '  bash %q %q\n' "${VALIDATOR}" "${post_reboot_mode}"
}

rollback_configuration() {
  require_root
  for path in "${MODULES_FILE}" "${MODPROBE_FILE}"; do
    if [[ -e "${path}" ]] && ! grep -Fxq "${MANAGED_MARKER}" "${path}"; then
      printf 'Refusing to remove an unmanaged file: %s\n' "${path}" >&2
      exit 1
    fi
  done

  rm -f -- "${MODULES_FILE}" "${MODPROBE_FILE}"
  update-initramfs -u -k all
  printf 'AI lab VFIO files removed and initramfs rebuilt. The host was NOT rebooted.\n'
}

case "${MODE}" in
  --check)
    require_validator
    bash "${VALIDATOR}" --inspect
    report_files
    ;;
  --apply)
    apply_configuration b50
    ;;
  --apply-both)
    apply_configuration both
    ;;
  --rollback)
    rollback_configuration
    ;;
  --help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
