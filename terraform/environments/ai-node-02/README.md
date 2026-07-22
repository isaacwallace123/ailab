# ai-node-02 Terraform Root

This root owns the B580-backed inference worker in the existing `ailab` Proxmox pool.

Planned shape:

- VMID 9601 in pool `ailab` on `cyberlab`
- Ubuntu 24.04 cloud-init template 9000
- q35, OVMF, 8 host CPU cores, and fixed 16 GiB RAM
- 100 GiB OS disk on `local-lvm`; no dedicated data disk initially
- stable `vmbr0` MAC `BC:24:11:09:A0:46`, using DHCP during bring-up
- Intel Arc B580 through `ailab-intel-arc-b580`
- running after successful B580 reset, kernel, compute, runtime, and API acceptance
- destruction protection enabled

Create and validate the named PCI mapping before planning. Generate an ignored binary plan with:

```powershell
.\scripts\plan-ai-node-02.ps1
```

The wrapper reads the mutation token and public SSH key from the ignored root `.env`. It has no
apply mode. Never commit Terraform state, a token, or a private SSH key.
