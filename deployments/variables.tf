variable "failed_log_backup_container" {
  description = "The name of the blob container within the storage account."
  default     = "failedlogbackup"
}

variable "logzio_url" {
  description = "The Logz.io listener URL for your region."
  default     = "https://listener.logz.io:8071"
}

variable "logzio_token" {
  description = "Your Logz.io logs token."
  type        = string
  default     = ""  # Default empty, user must provide
}

variable "eventhub_namespace" {
  description = "Event Hub Namespace."
  default     = "LogzioLNS"
}

variable "eventhub_logs_name" {
  description = "Event Hub Logs Name."
  default     = "logzioeventhub"
}

variable "app_insights_name" {
  description = "App Insights name"
  default     = "logzioLInsight"
}
variable "log_analytics_workspace_name" {
  description = "Log Analytics Workspace Name"
  default     = "logzioWorkspace"
}

variable "thread_count" {
  description = "The number of threads to use, between 4 and 10."
  default     = 4
}

variable "buffer_size" {
  description = "The size of the log buffer. Minimum 50, maximum 500."
  default     = 100
}

variable "interval_time" {
  description = "The interval time for sending logs in milliseconds. Minimum 5000 (5 seconds), maximum 60000 (60 seconds)."
  default     = 10000
}

variable "max_tries" {
  description = "The maximum number of retries for the backoff mechanism."
  default     = 3
}

variable "log_type" {
  description = "The type of the logs being processed."
  default = "eventHub"
}

variable "resource_group_name" {
  default = "resources-terraform-test"
}

