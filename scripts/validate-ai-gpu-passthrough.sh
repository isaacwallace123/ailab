#!/usr/bin/env bash
set -euo pipefail

B50_PCI="0000:0b:00.0"
B50_DEVICE="8086:e212"
B50_MAPPING="ailab-intel-arc-pro-b50"
B50_VMID="9600"
B580_PCI="0000:03:00.0"
B580_DEVICE="8086:e20b"
B580_MAPPING="ailab-intel-arc-b580"
B580_VMID="9601"
NODE="cyberlab"
MODE="${1:---inspect}"

usage() {
  cat <<'EOF'
Usage: validate-ai-gpu-passthrough.sh [MODE]

  --inspect             Read-only inventory; VMs may be running.
  --preflight-b50       Require ai-node-01 stopped and B580 left on xe.
  --require-b50-vfio    Require ai-node-01 stopped, B50 on vfio-pci, B580 on xe.
  --preflight-both      Require both AI VMs stopped before enabling both GPUs.
  --require-both-vfio   Require both AI VMs stopped and both GPUs on vfio-pci.
EOF
}

driver_for() {
  local pci="$1"
  local driver_link="/sys/bus/pci/devices/${pci}/driver"
  if [[ -L "${driver_link}" ]]; then
    basename "$(readlink -f "${driver_link}")"
  else
    printf '%s\n' "unbound"
  fi
}

group_members() {
  local pci="$1"
  local group_link="/sys/bus/pci/devices/${pci}/iommu_group/devices"
  find "${group_link}" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort
}

mapping_is_valid() {
  local mapping="$1"
  pvesh get "/cluster/mapping/pci/${mapping}" --output-format json >/dev/null &&
    pvesh get /cluster/mapping/pci --check-node "${NODE}" --output-format json |
      grep -Fq "\"id\":\"${mapping}\""
}

vm_status() {
  local vmid="$1"
  if qm status "${vmid}" >/dev/null 2>&1; then
    qm status "${vmid}" | awk '{print $2}'
  else
    printf '%s\n' "absent"
  fi
}

require_vm_stopped_or_absent() {
  local vmid="$1"
  local status="$2"
  [[ "${status}" == "stopped" || "${status}" == "absent" ]] || {
    printf 'VM %s must be stopped; found %s.\n' "${vmid}" "${status}" >&2
    exit 1
  }
}

require_mapping_and_attachment() {
  local mapping="$1"
  local vmid="$2"
  mapping_is_valid "${mapping}" || {
    printf 'PCI mapping failed its node check: %s\n' "${mapping}" >&2
    exit 1
  }
  if qm status "${vmid}" >/dev/null 2>&1; then
    qm config "${vmid}" | grep -Eq "^hostpci0:.*mapping=${mapping}" || {
      printf 'VM %s does not use mapping %s.\n' "${vmid}" "${mapping}" >&2
      exit 1
    }
  fi
}

case "${MODE}" in
  --inspect|--preflight-b50|--require-b50-vfio|--preflight-both|--require-both-vfio) ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

for command in lspci pvesh qm; do
  command -v "${command}" >/dev/null || {
    printf 'Missing required command: %s\n' "${command}" >&2
    exit 1
  }
done

for pci in "${B50_PCI}" "${B580_PCI}"; do
  [[ -d "/sys/bus/pci/devices/${pci}" ]] || {
    printf 'Expected PCI device is missing: %s\n' "${pci}" >&2
    exit 1
  }
  [[ -e "/sys/bus/pci/devices/${pci}/reset" ]] || {
    printf 'PCI reset interface is missing: %s\n' "${pci}" >&2
    exit 1
  }
done

mapfile -t b50_group < <(group_members "${B50_PCI}")
mapfile -t b580_group < <(group_members "${B580_PCI}")
[[ "${#b50_group[@]}" -eq 1 && "${b50_group[0]}" == "${B50_PCI}" ]] || {
  printf 'B50 IOMMU group is no longer isolated: %s\n' "${b50_group[*]}" >&2
  exit 1
}
[[ "${#b580_group[@]}" -eq 1 && "${b580_group[0]}" == "${B580_PCI}" ]] || {
  printf 'B580 IOMMU group is no longer isolated: %s\n' "${b580_group[*]}" >&2
  exit 1
}

require_mapping_and_attachment "${B50_MAPPING}" "${B50_VMID}"
if [[ "${MODE}" == "--preflight-both" || "${MODE}" == "--require-both-vfio" ]]; then
  require_mapping_and_attachment "${B580_MAPPING}" "${B580_VMID}"
fi

b50_status="$(vm_status "${B50_VMID}")"
b580_status="$(vm_status "${B580_VMID}")"
b50_driver="$(driver_for "${B50_PCI}")"
b580_driver="$(driver_for "${B580_PCI}")"

if [[ "${MODE}" != "--inspect" ]]; then
  require_vm_stopped_or_absent "${B50_VMID}" "${b50_status}"
fi
if [[ "${MODE}" == "--preflight-both" || "${MODE}" == "--require-both-vfio" ]]; then
  require_vm_stopped_or_absent "${B580_VMID}" "${b580_status}"
fi

if [[ "${MODE}" == "--preflight-b50" || "${MODE}" == "--require-b50-vfio" ]]; then
  [[ "${b580_driver}" == "xe" ]] || {
    printf 'B580 must remain on xe in B50-only mode; found %s.\n' "${b580_driver}" >&2
    exit 1
  }
fi
if [[ "${MODE}" == "--require-b50-vfio" && "${b50_driver}" != "vfio-pci" ]]; then
  printf 'B50 must be bound to vfio-pci; found %s.\n' "${b50_driver}" >&2
  exit 1
fi
if [[ "${MODE}" == "--require-both-vfio" ]]; then
  for entry in "B50:${b50_driver}" "B580:${b580_driver}"; do
    gpu="${entry%%:*}"
    driver="${entry#*:}"
    [[ "${driver}" == "vfio-pci" ]] || {
      printf '%s must be bound to vfio-pci; found %s.\n' "${gpu}" "${driver}" >&2
      exit 1
    }
  done
fi

printf 'VM %s: %s\n' "${B50_VMID}" "${b50_status}"
printf 'VM %s: %s\n' "${B580_VMID}" "${b580_status}"
printf 'B50 %s (%s): driver=%s, isolated=yes, reset=yes\n' \
  "${B50_PCI}" "${B50_DEVICE}" "${b50_driver}"
printf 'B580 %s (%s): driver=%s, isolated=yes, reset=yes\n' \
  "${B580_PCI}" "${B580_DEVICE}" "${b580_driver}"
printf 'Mapping %s: valid on %s\n' "${B50_MAPPING}" "${NODE}"
if mapping_is_valid "${B580_MAPPING}" 2>/dev/null; then
  printf 'Mapping %s: valid on %s\n' "${B580_MAPPING}" "${NODE}"
else
  printf 'Mapping %s: absent (required for dual-GPU modes)\n' "${B580_MAPPING}"
fi
