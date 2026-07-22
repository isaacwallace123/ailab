# Terraform

Infrastructure-as-code for AI-owned Proxmox resources.

Expected ownership:

- existing Proxmox `ailab` resource pool as an external prerequisite
- `ai-node-01` VM definition under `environments/ai-node-01`
- `ai-node-02` B580 worker definition under `environments/ai-node-02`
- storage attachments
- network attachments
- DNS records if managed declaratively

Terraform should not manage homelab or cyberlab resources from this workspace unless there is a deliberate cross-lab module and a documented ADR.

The two roots manage VMID 9600 with the B50 and VMID 9601 with the B580. Both named mappings,
first-boot GPU gates, and recovery tests have passed. Boot-on-host remains disabled while permanent
addresses and service startup policy are decided. These roots must never use the read-only status
collector token for mutations.

Do not commit Terraform state, plans, or tfvars containing secrets.
