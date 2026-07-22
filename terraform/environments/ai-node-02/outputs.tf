output "ai_node_02" {
  description = "Planned B580 AI worker identity and placement."
  value = {
    name        = proxmox_virtual_environment_vm.ai_node_02.name
    vm_id       = proxmox_virtual_environment_vm.ai_node_02.vm_id
    node        = var.node_name
    pool        = var.pool_id
    mac_address = var.mac_address
    gpu_mapping = var.gpu_mapping
    os_storage  = var.os_datastore_id
  }
}
