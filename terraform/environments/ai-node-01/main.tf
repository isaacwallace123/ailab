resource "proxmox_virtual_environment_vm" "ai_node_01" {
  name        = "ai-node-01"
  description = "Primary AI lab runtime host. Managed by the ailab Terraform root."
  tags        = ["ailab", "gpu", "intel-arc", "persistent"]

  node_name = var.node_name
  vm_id     = var.vm_id
  pool_id   = var.pool_id

  started         = true
  on_boot         = false
  stop_on_destroy = false

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
    cores = 12
    type  = "host"
  }

  memory {
    dedicated = 32768
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
    discard      = "on"
    iothread     = true
    ssd          = true
  }

  disk {
    datastore_id = var.data_datastore_id
    interface    = "scsi1"
    size         = 500
    discard      = "on"
    iothread     = true
    ssd          = true
    backup       = false
  }

  initialization {
    datastore_id = var.os_datastore_id

    ip_config {
      ipv4 {
        address = "dhcp"
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

  hostpci {
    device  = "hostpci0"
    mapping = var.gpu_mapping
    pcie    = true
    rombar  = true
    xvga    = false
  }

  operating_system {
    type = "l26"
  }

  serial_device {}

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = var.pool_id == "ailab" && var.node_name == "cyberlab"
      error_message = "ai-node-01 must remain in the ailab pool on cyberlab."
    }

    precondition {
      condition     = var.os_datastore_id != "scenarios" && var.data_datastore_id != "scenarios"
      error_message = "AI disks must not consume the cyberlab scenarios datastore."
    }
  }
}
