resource "proxmox_virtual_environment_vm" "ai_core_01" {
  name        = "ai-core-01"
  description = "CPU-only stable AI service plane. Managed by the ailab Terraform root."
  tags        = ["ailab", "core", "persistent", "services"]

  node_name = var.node_name
  vm_id     = var.vm_id
  pool_id   = var.pool_id

  started         = true
  on_boot         = true
  stop_on_destroy = false
  protection      = true

  bios          = "ovmf"
  machine       = "q35"
  scsi_hardware = "virtio-scsi-single"

  agent {
    enabled = true

    wait_for_ip {
      disabled = true
      ipv4     = true
    }
  }

  clone {
    vm_id        = var.template_vm_id
    node_name    = var.node_name
    datastore_id = var.os_datastore_id
    full         = true
    retries      = 3
  }

  cpu {
    cores = 8
    type  = "host"
  }

  memory {
    dedicated = 16384
    floating  = 0
  }

  efi_disk {
    datastore_id      = var.os_datastore_id
    type              = "4m"
    pre_enrolled_keys = true
  }

  disk {
    datastore_id = var.os_datastore_id
    interface    = "scsi0"
    size         = 100
    backup       = true
    discard      = "on"
    iothread     = true
    ssd          = true
  }

  initialization {
    datastore_id = var.os_datastore_id

    ip_config {
      ipv4 {
        address = var.ipv4_address
        gateway = var.ipv4_gateway
      }
    }

    user_account {
      username = "isaac"
      keys     = var.ssh_public_keys
    }
  }

  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    mac_address = var.mac_address
  }

  operating_system {
    type = "l26"
  }

  serial_device {}

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = var.pool_id == "ailab" && var.node_name == "cyberlab"
      error_message = "ai-core-01 must remain in the ailab pool on cyberlab."
    }

    precondition {
      condition     = var.os_datastore_id != "scenarios"
      error_message = "The stable AI service VM must not consume the cyberlab scenarios datastore."
    }
  }
}
