# Intel Arc B50 And B580 Passthrough Runbook

This runbook assigns the Arc Pro B50 (`8086:e212`, `0000:0b:00.0`) to `ai-node-01` and the Arc B580
(`8086:e20b`, `0000:03:00.0`) to `ai-node-02`. Both VMs must remain stopped throughout host
preparation. The installer retains a legacy B50-only mode, but the accepted policy binds both cards
to host `vfio-pci`.

Proxmox requires IOMMU support for PCI passthrough and recommends Q35 plus PCIe for GPU devices.
Those requirements are already present. The named mapping prevents Terraform from depending on the
raw host address.

## Pre-change Evidence

Run the repository's read-only validator as root on `cyberlab`:

```bash
bash scripts/validate-ai-gpu-passthrough.sh --preflight-both
```

Expected before enabling both: VMs 9600 and 9601 stopped, both GPUs isolated with reset support,
and both named mappings valid.

Do not continue without physical console access or another tested host-management path. Confirm
Above 4G Decoding remains enabled in firmware during the maintenance window.

## Bind Both GPUs

Before copying anything, verify the Proxmox SSH host key from its trusted local/web console:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

If the workstation reports a changed host key, compare the console fingerprint byte-for-byte with
the fingerprint shown by SSH. Remove the stale entry with `ssh-keygen -R 192.168.0.253` only after
they match, then reconnect normally and accept the verified replacement. Never use
`StrictHostKeyChecking=no` for this transition.

Copy both guarded host scripts to the Proxmox node and run the read-only mode first:

```bash
scp scripts/validate-ai-gpu-passthrough.sh \
  scripts/configure-ai-gpu-passthrough.sh root@192.168.0.253:/root/
ssh root@192.168.0.253 'bash /root/configure-ai-gpu-passthrough.sh --check'
```

The installer refuses to continue if the VM is running, either IOMMU group is no longer isolated,
the B580 is not on `xe`, the PCI mapping is invalid, or a target configuration file already exists
with different contents. Apply the configuration without rebooting:

```bash
ssh root@192.168.0.253 'bash /root/configure-ai-gpu-passthrough.sh --apply-both'
```

The guarded installer backs up matching pre-existing files under `/root`, writes the following two
narrowly scoped configurations, rebuilds every installed initramfs, and verifies that effective
`modprobe` ordering places `vfio-pci` before `xe` with both reviewed device IDs:

```bash
cat >/etc/modules-load.d/ailab-vfio.conf <<'EOF'
vfio
vfio_iommu_type1
vfio_pci
EOF

cat >/etc/modprobe.d/ailab-vfio.conf <<'EOF'
options vfio-pci ids=8086:e212,8086:e20b disable_vga=1
softdep xe pre: vfio-pci
EOF

update-initramfs -u -k all
```

These settings do not blacklist `xe`; guests still use `xe` after PCI assignment. Reboot the
Proxmox node only in an approved maintenance window, then run:

```bash
bash scripts/validate-ai-gpu-passthrough.sh --require-both-vfio
```

The required post-reboot state is B50=`vfio-pci`, B580=`vfio-pci`, and both AI VMs stopped. Do not
start either VM if any check fails.

The first host application and maintenance reboot completed on 2026-07-18. Both installed PVE
initramfs images were rebuilt, and strict post-reboot validation proved both GPUs on `vfio-pci`,
isolated groups, reset support, and valid mappings while both AI VMs remained stopped. The
two-node cluster returned quorate with no failed units and all required storage active.

The five guests that were running before the reboot were restored: `cyb-gw-01`,
`cyb-controller-01`, `cyb-access-01`, `cyb-atk-kali-01`, and `cyb-soc-01`. Kali VMID 9401 was
restored explicitly because it has `onboot=0`.

## Rollback

From the host console, leave VMs 9600 and 9601 stopped and use the guarded rollback. It refuses to remove files
without the AI lab ownership marker:

```bash
ssh root@192.168.0.253 'bash /root/configure-ai-gpu-passthrough.sh --rollback'
reboot
```

After reboot, the read-only validator should again report both GPUs on `xe`. If the host cannot boot
normally, use the bootloader's previous-kernel entry or a rescue environment to remove the same two
files and rebuild the initramfs.

## Guest Acceptance Gate

After the host passes `--require-both-vfio`, start each VM independently and run its Ansible
preflight. Node 01 must see `8086:e212` and its unformatted 500 GiB data disk; node 02 must see
`8086:e20b` and intentionally has no data disk. Stop and roll back if either GPU is missing or fails
to reset after a guest shutdown.

The first guest acceptance boot passed. QEMU exposes the B50 with its 16 GiB BAR; Ubuntu HWE kernel
`7.0.0-28-generic` binds `8086:e212` to `xe`; `/dev/dri/renderD128` exists; and Intel OpenCL,
Level Zero, and Vulkan all enumerate the card. A bounded `clpeak --compute-sp` run completed at
approximately 10.1-10.6 TFLOPS after warm-up. The first scalar measurement immediately after one
restart was lower, so these are acceptance-smoke results rather than a published benchmark. A
controlled guest shutdown returned the B50 cleanly to host `vfio-pci`; the VM then restarted in 11
seconds and passed preflight, OpenCL compute, Level Zero, and Vulkan checks again. The B580 later
passed the same guest stack and llama.cpp gates in node 02. Kernel 7.0 logs an unsupported
thermal-mailbox warning for B50 firmware at boot, but
no additional GPU warning or error appeared during the repeated compute tests; continue tracking it
under real inference workloads.

References:

- [Proxmox VE Administration Guide: PCI(e) Passthrough](https://pve.proxmox.com/pve-docs/pve-admin-guide.pdf)
- [Proxmox PCI resource mapping guidance](https://pve.proxmox.com/wiki/NVIDIA_vGPU_on_Proxmox_VE_7.x#Create_a_PCI_Resource_Mapping)
