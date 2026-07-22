# ai-core-01 Terraform Root

This root owns the CPU-only stable service plane in the existing `ailab` Proxmox pool.

- VMID 9602 on `cyberlab`
- Ubuntu 24.04 cloud-init template 9000
- q35, OVMF, 8 host CPU cores, and fixed 16 GiB RAM
- 100 GiB backed-up OS disk on `local-lvm`; no dedicated data disk
- stable `vmbr0` MAC `BC:24:11:09:A0:47` and static `192.168.0.221/24`
- `onboot=1` and destruction protection enabled

Generate an ignored binary plan with `scripts/plan-ai-core-01.ps1`. Inspect the plan, then apply that
exact saved plan with `scripts/apply-ai-core-01.ps1`. Never commit Terraform state, plans, tokens, or
private SSH keys.
