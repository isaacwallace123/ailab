output "ai_node_01" {
  description = "Planned AI VM identity and placement."
  value = {
    name         = proxmox_virtual_environment_vm.ai_node_01.name
    vm_id        = proxmox_virtual_environment_vm.ai_node_01.vm_id
    node         = var.node_name
    pool         = var.pool_id
    mac_address  = var.mac_address
    gpu_mapping  = var.gpu_mapping
    os_storage   = var.os_datastore_id
    data_storage = var.data_datastore_id
  }
}
