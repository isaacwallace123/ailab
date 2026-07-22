# `ai-node-01` Discovery Gate

Do not start the GPU VM until these values are captured from the current `cyberlab` Proxmox node.
The stopped VM definition may be planned and created while runtime prerequisites remain gated.

## Required Facts

- Proxmox version, kernel, CPU topology, and currently available memory
- free and allocated bytes for `local-lvm`, `scenarios`, `secondary`, and `backupstore`
- block device models, stable IDs, filesystems, volume groups, and thin-pool utilization
- B50 and B580 PCI addresses, device/vendor IDs, bound drivers, and complete IOMMU groups
- whether Resizable BAR, Above 4G Decoding, VT-d, and IOMMU are active
- existing VM CPU and memory allocation, including expected cyberlab peak demand
- intended `vmbr0` address or DHCP reservation and inbound firewall allowlist
- backup target and recovery point objective for the AI VM configuration and durable data

Run `scripts/collect-ai-host-facts.sh` as root on the Proxmox host and review its output locally.
The script is read-only. Do not commit the raw output until hostnames, addresses, serials, and other
private fields have been reviewed.

## Initial Proposal To Validate

| Setting | Proposed value |
| :--- | :--- |
| VM | `ai-node-01` in pool `ailab` |
| OS | Ubuntu 24.04 LTS |
| CPU | 12 vCPU, host CPU type |
| Memory | 48 GB initial; reduced to 32 GiB after adding the second worker |
| OS disk | 80-120 GB on a storage target selected from current free-space evidence |
| Data disk | Separate 400-600 GB disk for models, databases, and caches if capacity allows |
| GPU | B50 first; B580 later assigned to separate `ai-node-02` after acceptance |
| Network | One NIC on `vmbr0`; no `vmbr90/91/93/94` attachment |
| Exposure | Internal only; host firewall and application authentication required |

## Recorded Capacity Snapshot

Observed through the read-only Proxmox API on 2026-07-18:

| Fact | Observed value |
| :--- | :--- |
| Proxmox | 9.2.4 on node `cyberlab` |
| CPU | 24 logical CPUs; approximately 0.3% used at observation time |
| Memory | 125.63 GiB total; approximately 20.11 GiB used |
| Root filesystem | 93.93 GiB total; approximately 19.5% used |
| Guests | 10 total, 5 running |
| `local-lvm` | approximately 691.4 GiB available |
| `scenarios` | approximately 884.7 GiB available; reserved for cyberlab scenarios |
| `secondary` | approximately 849.3 GiB available |
| `backupstore` | approximately 1.67 TiB available |

Current storage proposal: place a 100 GiB OS disk on `local-lvm` and a separate 500 GiB AI data
disk on `secondary`. This leaves substantially more headroom than placing both disks on `local-lvm`
and preserves `scenarios` for its existing cyberlab purpose. The data disk remains unformatted and
is visible in the guest as `/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1`; its backup and
filesystem policy must be approved before any destructive storage automation is enabled.

## Recorded GPU And IOMMU Evidence

Observed through the root-reviewed, read-only host collection on 2026-07-18:

| Device | PCI identity | IOMMU | Reset | Resizable BAR | Host driver |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Intel Arc B580 12 GB | `0000:03:00.0`, `8086:e20b` | isolated group 18 | present | 16 GiB active | `vfio-pci` |
| Intel Arc Pro B50 16 GB | `0000:0b:00.0`, `8086:e212` | isolated group 26 | present | 16 GiB active | `vfio-pci` |

VT-d is active with translated default domains, queued invalidation, and interrupt remapping. Each
GPU display function is the sole member of its IOMMU group. Their audio functions are separately
isolated at `0000:04:00.0` and `0000:0c:00.0`, so the AI VM does not need an audio function.

The kernel command line does not explicitly contain `intel_iommu=on`; the running Proxmox kernel
nevertheless proves that DMAR/IOMMU is enabled. Above-4G decoding was not printed directly, although
the active 16 GiB BARs strongly indicate firmware support. Confirm the firmware setting during the
next maintenance window rather than treating that inference as direct evidence.

The continuous `PVEAuditor` token cannot read `/nodes/cyberlab/hardware/pci` and was not broadened.
Raw PCI addresses belong only in Proxmox resource mappings. Terraform consumes the named
`ailab-intel-arc-pro-b50` and `ailab-intel-arc-b580` mappings.

## Plan-Only Terraform Status

`terraform/environments/ai-node-01` is initialized and validates with bpg/proxmox 0.111.1. It plans
VMID 9600, q35/OVMF, 12 host vCPUs, fixed 32 GiB RAM, a 100 GiB OS disk, a 500 GiB data disk, one
`vmbr0` NIC, and the named B50 mapping. Boot-on-host is disabled and Terraform destruction is
blocked; desired runtime state changed to running only after the reviewed acceptance boot passed.

The first live plan on 2026-07-18 was clean: one resource to add, zero to change, and zero to
destroy. The named `ailab-intel-arc-pro-b50` mapping passed its node check, and the dedicated
Terraform token could read all reviewed resources. The first apply was rejected before cloning
because Proxmox 9 requires `SDN.Use` at `/sdn/zones/localnetwork/vmbr0`. VMID 9600 remained absent
from both Terraform state and the subsequent Proxmox inventory snapshot.

Grant only that bridge permission to both the privilege-separated token and its backing user, then
regenerate the saved plan before retrying. A dedicated one-privilege role keeps network use separate
from the VM provisioning role:

```bash
pveum role add AILabNetworkUse --privs SDN.Use
pveum acl modify /sdn/zones/localnetwork/vmbr0 --user terraform-ailab@pve --role AILabNetworkUse
pveum acl modify /sdn/zones/localnetwork/vmbr0 --token 'terraform-ailab@pve!terraform' --role AILabNetworkUse
pveum user token permissions terraform-ailab@pve terraform
```

The bridge-scoped role and both privilege-separated ACL entries were added and verified. A fresh
plan remained one add, zero changes, and zero destroys. Terraform then created VMID 9600 on
2026-07-18 and a post-apply refresh reported no drift. The read-only inventory independently sees
`ai-node-01` stopped with 12 vCPUs and its original 48 GiB RAM allocation. It was later reduced to
32 GiB when `ai-node-02` was accepted. Its generated `vmbr0` MAC address is
`BC:24:11:09:A0:45`.

The host maintenance reboot and first guest boot are complete. The actual DHCP lease is
`192.168.0.101`; a permanent reservation has not been activated. Ansible uses the guest link-local
IPv6 address through a verified Proxmox SSH jump path.
The guest baseline is Ubuntu 24.04 on HWE kernel `7.0.0-28-generic`, with QEMU Guest Agent,
source-restricted UFW, hardened SSH, and a working Intel compute userspace.

## Exit Gate

The remaining discovery items are direct firmware confirmation of Above-4G decoding, a permanent
DHCP choice, and an approved backup/data policy. GPU passthrough and its reversible recovery path
have passed their initial host and guest gates.
