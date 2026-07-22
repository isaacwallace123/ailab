output "ai_core_01" {
  description = "Stable AI service VM identity and placement."
  value = {
    name        = proxmox_virtual_environment_vm.ai_core_01.name
    vm_id       = proxmox_virtual_environment_vm.ai_core_01.vm_id
    node        = var.node_name
    pool        = var.pool_id
    mac_address = var.mac_address
    os_storage  = var.os_datastore_id
    on_boot     = proxmox_virtual_environment_vm.ai_core_01.on_boot
  }
}
