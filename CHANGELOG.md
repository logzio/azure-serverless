# Changelog

All notable changes to the Logz.io Azure Serverless project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-05-08

### Added
- Implemented usage of previously defined utility functions:
  - `add_timestamp`: Now adds `@timestamp` field to logs based on the `time` field
  - `delete_empty_fields_of_log`: Removes empty or null fields from logs

### Fixed
- Addressed issue where unused utility functions were defined but not utilized

## [1.0.0] - Initial Release

### Added
- Initial implementation of Logz.io Shipper for Azure Functions
- EventHub trigger for processing logs
- Multi-threaded batch processing and sending capabilities
- Backup mechanism for failed log transmissions
- Application Insights integration for monitoring
- Environment variable configuration options