variable "proxmox_endpoint" {
  description = "Proxmox API endpoint."
  type        = string

  validation {
    condition     = can(regex("^https://[^/]+:8006/?$", var.proxmox_endpoint))
    error_message = "proxmox_endpoint must be an HTTPS URL ending with port 8006."
  }
}

variable "proxmox_api_token" {
  description = "Dedicated AI lab Terraform token in user@realm!tokenid=secret form."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[^!]+![^=]+=.+$", var.proxmox_api_token))
    error_message = "proxmox_api_token must look like user@realm!tokenid=secret."
  }

  validation {
    condition     = !strcontains(var.proxmox_api_token, "replace-with-token-secret")
    error_message = "Replace the example Proxmox token before planning."
  }
}

variable "proxmox_insecure_tls" {
  description = "Allow the current self-signed Proxmox certificate."
  type        = bool
  default     = true
}

variable "node_name" {
  description = "Proxmox node hosting the first AI VM."
  type        = string
  default     = "cyberlab"

  validation {
    condition     = var.node_name == "cyberlab"
    error_message = "ai-node-01 must initially target the cyberlab Proxmox node."
  }
}

variable "pool_id" {
  description = "Existing AI-owned Proxmox resource pool."
  type        = string
  default     = "ailab"

  validation {
    condition     = var.pool_id == "ailab"
    error_message = "AI resources must remain in the ailab pool."
  }
}

variable "vm_id" {
  description = "Reserved VM ID for ai-node-01."
  type        = number
  default     = 9600

  validation {
    condition     = var.vm_id >= 9600 && var.vm_id <= 9699
    error_message = "AI lab VM IDs are reserved in the 9600-9699 range."
  }
}

variable "template_vm_id" {
  description = "Generic Ubuntu 24.04 cloud-init template on cyberlab."
  type        = number
  default     = 9000

  validation {
    condition     = var.template_vm_id == 9000
    error_message = "The first AI VM must use the reviewed generic template 9000."
  }
}

variable "os_datastore_id" {
  description = "Storage for the OS and cloud-init disks."
  type        = string
  default     = "local-lvm"

  validation {
    condition     = var.os_datastore_id == "local-lvm"
    error_message = "The reviewed OS datastore is local-lvm."
  }
}

variable "data_datastore_id" {
  description = "Storage for models, databases, and caches."
  type        = string
  default     = "secondary"

  validation {
    condition     = var.data_datastore_id == "secondary"
    error_message = "The reviewed AI data datastore is secondary."
  }
}

variable "gpu_mapping" {
  description = "Existing Proxmox PCI resource mapping for the Intel Arc Pro B50."
  type        = string
  default     = "ailab-intel-arc-pro-b50"

  validation {
    condition     = var.gpu_mapping == "ailab-intel-arc-pro-b50"
    error_message = "The first GPU mapping must be ailab-intel-arc-pro-b50."
  }
}

variable "mac_address" {
  description = "Stable MAC address for the ai-node-01 DHCP reservation."
  type        = string
  default     = "BC:24:11:09:A0:45"

  validation {
    condition     = can(regex("^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", var.mac_address))
    error_message = "mac_address must be a colon-separated 48-bit MAC address."
  }
}

variable "ssh_public_keys" {
  description = "SSH public keys injected for the non-root cloud-init user."
  type        = list(string)
  sensitive   = true

  validation {
    condition = length(var.ssh_public_keys) > 0 && alltrue([
      for key in var.ssh_public_keys :
      can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp[0-9]+|sk-ssh-ed25519@openssh\\.com|sk-ecdsa-sha2-nistp256@openssh\\.com) ", trimspace(key)))
    ])
    error_message = "At least one valid OpenSSH public key is required."
  }

  validation {
    condition     = alltrue([for key in var.ssh_public_keys : !strcontains(key, "exampleOnlyDoNotUse")])
    error_message = "Replace the example SSH key before planning."
  }
}
