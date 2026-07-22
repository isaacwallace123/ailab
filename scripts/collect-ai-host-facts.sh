#!/usr/bin/env bash
set -euo pipefail

section() {
  printf '\n## %s\n' "$1"
}

section "Collection metadata"
date --iso-8601=seconds
hostnamectl

section "Proxmox and kernel"
pveversion --verbose
uname -a
cat /proc/cmdline

section "CPU and memory"
lscpu
free -h

section "Proxmox storage"
pvesm status

section "Block devices"
lsblk --bytes --output NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL

section "LVM physical volumes"
pvs --units b --nosuffix --options pv_name,vg_name,pv_size,pv_free

section "LVM volume groups"
vgs --units b --nosuffix --options vg_name,vg_size,vg_free

section "LVM logical volumes and thin pools"
lvs --units b --nosuffix --options vg_name,lv_name,lv_size,data_percent,metadata_percent,lv_attr

section "Intel display devices and bound drivers"
lspci -Dnnk | awk '
  /^[0-9a-f]+:[0-9a-f]+:[0-9a-f]+\.[0-9].*(VGA|Display)/ {show=1}
  show {print}
  show && /^$/ {show=0}
'

section "IOMMU status"
dmesg | grep -Ei 'DMAR|IOMMU' || true

section "IOMMU groups"
if compgen -G '/sys/kernel/iommu_groups/*/devices/*' >/dev/null; then
  for device in /sys/kernel/iommu_groups/*/devices/*; do
    group=$(basename "$(dirname "$(dirname "$device")")")
    printf 'group=%s device=%s ' "$group" "$(basename "$device")"
    lspci -nns "$(basename "$device")"
  done
else
  printf 'No IOMMU groups are exposed.\n'
fi

section "Current guests"
qm list

section "Network bridges"
ip -brief address
bridge link

section "Proxmox firewall status"
pve-firewall status || true

