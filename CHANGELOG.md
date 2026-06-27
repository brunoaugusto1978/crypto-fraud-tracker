# Changelog

## v3.4.0 - Real Intelligence Sources

### Added
- OFAC-derived local CSV importer for sanctioned wallet intelligence.
- Source importer package under `backend/app/layers/source_importers`.
- Example OFAC-derived CSV fixture under `feeds/ofac_derived.example.csv`.
- Tests for OFAC-derived normalization and deduplication.
- Documentation for real intelligence source import flow.

### Changed
- Generated OFAC-derived intelligence outputs are excluded from version control.


## v3.3.0 - Intelligence Feed Importers

### Added
- CSV/JSON intelligence feed importer for wallet risk data.
- Field alias normalization for common feed formats.
- Deduplication by address, asset, category and source.
- Example CSV feed under `feeds/input.example.csv`.
- Tests for CSV import, JSON import and record normalization.
- Documentation for intelligence feed importers.

### Changed
- Generated intelligence feed outputs are excluded from version control.


## v3.2.0 - Automatic Risk Enrichment

### Added
- File-based address intelligence provider configured by `ADDRESS_INTEL_FILE`.
- Example external watchlist feed under `backend/data/address_intelligence.example.json`.
- Automatic wallet classification using external/provider-backed intelligence.
- Tests for address enrichment and Blockstream provider integration.
- Documentation for automatic risk enrichment.

### Changed
- Unknown wallet intelligence now returns `risk_level=unknown` instead of assuming low risk.
- Known scam wallet rule now scores high-risk threshold.
- Backend Docker image now copies `backend/data` into `/app/data`.

### Security
- Reduces dependency on hardcoded wallet classifications.
- Preserves source, confidence and raw hash metadata from external intelligence matches.


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

