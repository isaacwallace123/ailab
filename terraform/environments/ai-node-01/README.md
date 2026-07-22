# ai-node-01 Terraform Root

This root plans the first AI-owned VM in the existing `ailab` Proxmox resource pool. It deliberately
does not manage the pool, PCI resource mapping, Proxmox user, API token, physical bridge, or source
template. Those are reviewed host prerequisites.

Planned shape:

- VMID 9600 in pool `ailab` on node `cyberlab`
- generic Ubuntu 24.04 cloud-init template 9000
- q35 and OVMF
- 12 host CPU cores and fixed 32 GiB RAM
- 100 GiB OS disk on `local-lvm`
- 500 GiB data disk on `secondary`, excluded from default VM backups until its data policy is defined
- one `vmbr0` NIC using DHCP during initial bring-up
- Intel Arc Pro B50 through the named `ailab-intel-arc-pro-b50` PCI resource mapping
- running after the reviewed GPU acceptance boot, with boot-on-host still disabled
- destruction protection enabled

Do not plan until the named PCI mapping and a dedicated `terraform-ailab` token exist. Do not apply
until the plan has been reviewed and the VM's DHCP reservation, firewall allowlist, backup policy,
and GPU rollback procedure are recorded.

The mutation token is intentionally different from `ailab-status@pve!collector`. Put it in the
ignored root `.env` as `AILAB_TERRAFORM_PROXMOX_API_TOKEN`, set `AILAB_SSH_PUBLIC_KEY_PATH` to a
public `.pub` file, and generate the reviewed plan with:

```powershell
.\scripts\plan-ai-node-01.ps1
```

The wrapper produces an ignored binary plan under `artifacts/plans` and restores all temporary
`TF_VAR_*` environment variables. It has no apply mode.

```powershell
terraform init
terraform validate
```

`terraform.tfvars` is ignored. Never commit the API token or a private SSH key.
