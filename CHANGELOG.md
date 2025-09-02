# Changelog

All notable changes to the Logz.io Azure Serverless project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.4]

### Added
- Support for custom Logz.io listener URLs in ARM template deployments
  - Added "CUSTOM" option to LogzioURL parameter dropdown
  - Added CustomLogzioURL parameter for specifying custom listener URLs
- Azure Key Vault integration for secure token storage
  - Added `UseKeyVaultForToken` parameter to enable Key Vault usage
  - Added `LogzioTokenSecretUri` parameter for specifying Key Vault secret URI
  - Added `KeyVaultResourceId` parameter for existing Key Vault resource ID
  - Function App now created with system-assigned managed identity
  - Automatic RBAC role assignment ("Key Vault Secrets User") on existing Key Vault
  - Support for versioned and versionless Key Vault secret references

## [0.0.3]

### Added
- Implemented usage of previously defined utility functions:
  - `add_timestamp`: Now adds `@timestamp` field to logs based on the `time` field
  - `delete_empty_fields_of_log`: Removes empty or null fields from logs
  - Enable running without app insights and a log analytics workspace (contributed by @athiedepayit)


### Fixed
- Addressed issue where unused utility functions were defined but not utilized

## [0.0.2] - Initial Release

### Added
- This new release introduces the ENV_FUNCTION_VERSION parameter into the ARM template and Terraform to allow dynamic configuration of the function app version.


## [0.0.1] - Initial Release

### Added
- Initial implementation of Logz.io Shipper for Azure Functions
- EventHub trigger for processing logs
- Multi-threaded batch processing and sending capabilities
- Backup mechanism for failed log transmissions
- Application Insights integration for monitoring
- Environment variable configuration options