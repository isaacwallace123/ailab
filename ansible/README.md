# Ansible

Configuration management for AI lab guests after Terraform creates them.

The first automation slice is intentionally split:

- `playbooks/preflight.yml` is read-only and verifies Ubuntu 24.04, each host-specific GPU PCI ID,
  and the node-01 unformatted data disk without requiring one on node 02.
- `playbooks/bootstrap.yml` installs the baseline packages, enables the QEMU guest agent, hardens
  SSH, creates AI-owned directories, and enables UFW after adding the approved SSH source rules.
- `playbooks/site.yml` runs preflight and then bootstrap.
- `playbooks/gpu-kernel.yml` is a separate disruptive stage: it installs Ubuntu's supported HWE
  kernel, firmware, and diagnostics, reboots only when packages change, then requires `xe` and
  `/dev/dri/renderD128` before succeeding.
- `playbooks/intel-compute.yml` enables Intel's official graphics PPA, installs the OpenCL,
  Level Zero, and Vulkan baseline, then requires all three interfaces to see the assigned GPU. It does not
  install OMIX or an inference server; those remain benchmark candidates.
- `playbooks/llama-vulkan.yml` checks out a reviewed llama.cpp release, builds its Vulkan CLI,
  benchmark, and server binaries, downloads a checksum-pinned public smoke model, and requires
  prompt-processing and generation measurements on the exact assigned GPU. It does not expose a network
  service or select the production model.
- `playbooks/llama-vulkan-candidate.yml` requires that pinned runtime, downloads the reviewed Qwen3
  8B Q4_K_M candidate, and measures 512-token prompt processing, 4K prompt processing, and 128-token
  generation with flash attention and full GPU offload.
- `playbooks/litellm.yml` enables one persistent llama.cpp worker per GPU; deploys loopback-only
  PostgreSQL; reconciles pinned LiteLLM, seven scoped client identities, and tested fallback routing;
  deploys private SearXNG search, authenticated Docling document/OCR extraction, and the controlled
  public research gateway; then deploys pinned Open WebUI with its own database, virtual key, UFW
  rule, and closed signup.
  The accepted stable service plane defaults to `ai-core-01`.
- `playbooks/ai-core.yml` hardens VMID 9602, installs Docker Compose and host metrics, and validates
  the CPU-only guest contract.
- `playbooks/set-ai-core-address.yml` installs and verifies static `192.168.0.221/24` outside the
  router's `.100`-`.200` DHCP pool; `playbooks/trust-ai-core.yml` scopes both GPU workers to it.
- `playbooks/core-assistant.yml` deploys the copied Lab Status Assistant, pgvector data, approved
  source bundles, embedding cache, and private profile on core loopback port 18088.
- `playbooks/migrate-openwebui-state.yml` performs the explicitly confirmed, one-time state copy
  while preserving the old node-01 data for rollback.
- `playbooks/retire-ai-node-01-services.yml` stops, disables, and masks the legacy Open WebUI and
  LiteLLM units on node 01, closes their LAN ports, and leaves its model worker and rollback data intact.

The automation does not partition or format the data disk. That later play must use a guest-observed
stable disk ID and require an explicit destructive-operation flag.

## First Run

Run Ansible from WSL or another Linux control environment:

```bash
cd /mnt/c/Users/isaac/Desktop/ailab/ansible
cp inventory/production/hosts.example.yml inventory/production/hosts.yml
export AILAB_SSH_PRIVATE_KEY_PATH=/mnt/c/Users/isaac/.ssh/id_ed25519
export ANSIBLE_CONFIG=/mnt/c/Users/isaac/Desktop/ailab/ansible/ansible.cfg
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbooks/preflight.yml --check
ansible-playbook playbooks/site.yml
ansible-playbook playbooks/gpu-kernel.yml
ansible-playbook playbooks/intel-compute.yml
ansible-playbook playbooks/llama-vulkan.yml
ansible-playbook playbooks/llama-vulkan-candidate.yml
ansible-playbook -i inventory/production/hosts.yml playbooks/litellm.yml
ansible-playbook -i inventory/production/hosts.yml playbooks/ai-core.yml
ansible-playbook -i inventory/production/hosts.yml playbooks/core-assistant.yml
ansible-playbook -i inventory/production/hosts.yml playbooks/trust-ai-core.yml
ansible-playbook -i inventory/production/hosts.yml playbooks/retire-ai-node-01-services.yml
```

Refresh the ignored, allowlisted migration bundles before a deliberate assistant redeployment with
`scripts/package-core-assistant.ps1`. The script packages only reviewed source paths and copies the
database and embedding cache through the running workstation containers; it never packages `.env`
or `.private`.

The example inventory uses proposed `.210` and `.211` reservations; current leases are `.101` and
`.102`, so do not use the example addresses until reservations are active. SSH is initially restricted to
the workstation at `192.168.0.138/32` and the Proxmox `vmbr0` link-local address used by the guarded
bootstrap jump path. Update `inventory/production/group_vars/ai_nodes.yml` if either control address
changes.

Do not store vault passwords, private keys, or provider tokens here.
