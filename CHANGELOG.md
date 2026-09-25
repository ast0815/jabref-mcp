# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-09-25

### Added

- Refresh configured `.bib` files after JabRef or another client changes them, so read tools see saved updates without an MCP restart. Only changed files are reparsed.

### Fixed

- Accept bare full-month values such as `month = July` instead of failing the entire library with an undefined-string error.
- Preserve non-standard entry types such as `@Electronic` when loading libraries.
- Report other undefined BibTeX strings with the affected file and value instead of an opaque parser error.

### Changed

- Clarify that `add_entry` reports dispatch to JabRef, which may still require acceptance, saving, and verification after the command returns.
- Make the example OpenCode configuration run this checkout against the in-repository sample library without machine-specific paths.
- Expand configuration, attachment, cache-refresh, and release documentation in the README and repository contributor guidance.

[Unreleased]: https://github.com/ast0815/jabref-mcp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ast0815/jabref-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ast0815/jabref-mcp/releases/tag/v0.1.0
