# Changelog

## v3.1.0 - AML Investigation Hardening

### Added
- Evidence records with raw payload hash, source metadata and collected_by.
- Initial AML typologies for fan-in/fan-out, mixer exposure, exchange cash-out candidate and layering/peel-chain candidate.
- Ownership metadata for investigations.
- Additional tests for AML hardening.

### Changed
- Investigation flow now uses provider transaction data instead of synthetic transactions.
- Blockstream transaction handling now preserves UTXO inputs, outputs and transfers.
- HTML report generation now escapes dynamic content.
- Bitcoin wallet normalization preserves Base58 case.

### Security
- Sensitive endpoints now require authentication.
- Queue status endpoint requires admin role.
- Production environment fails safe when configured with mock intelligence provider.

