# Track A — Authoritative Agricultural Data

This directory will hold all verified agricultural data for the SIH 2026
Fertilizer Recommendation System.

## Directory Structure

```
data/
├── raw/
│   ├── government/     # Punjab Agriculture Dept, data.gov.in, SHC portal data
│   ├── pau/            # Punjab Agricultural University publications & datasets
│   ├── icar/           # ICAR / AICRP-STCR experimental data
│   └── research/       # Peer-reviewed publications with field data
├── processed/          # Cleaned, validated datasets (output of ingestion scripts)
├── metadata/           # Dataset provenance JSON records
├── agronomy/           # (existing) biofertilizers.yaml
└── soil/               # (existing) district_averages.yaml
```

## Data Sources

Track A accepts data ONLY from:

1. **Punjab Agricultural University (PAU), Ludhiana**
   - STCR fertilizer-use research reports
   - Crop-specific nutrient response experiments
   - Recommended fertilizer packages

2. **ICAR / AICRP-STCR**
   - National soil test-crop response coordination network data
   - Published bulletins from ICAR-IISS (Bhopal)

3. **Punjab Agriculture Department**
   - District-level fertilizer recommendations
   - Soil Health Card survey data

4. **Government of India — Soil Health Card Portal**
   - soilhealth.dac.gov.in district-average datasets

5. **Government Open Data Platform**
   - data.gov.in agricultural datasets with documented methodology

6. **Peer-reviewed primary research**
   - Only with documented methodology, institution, and DOI

## Data Provenance Requirements

Every imported dataset MUST retain:

| Field | Required |
|-------|----------|
| `source` | Institution name |
| `source_url` | URL of original data |
| `publication` | Publication/report name |
| `publication_year` | Year |
| `retrieved_date` | Date of download |
| `license` | Data license |
| `checksum` | SHA-256 of raw file |
| `processing_script` | Script used to process |
| `verification_status` | `unverified` / `under_review` / `verified` |

Provenance records are stored as JSON files in `data/metadata/`.

## CRITICAL RULES

- **DO NOT overwrite raw files** — append `_v{N}` to new versions
- **DO NOT invent values** — all scientific data must trace to a source
- **DO NOT use random blogs, SEO sites, or uncited AI outputs**
- All STCR coefficients remain `null` until PAU/ICAR data is verified and ingested

## Current Status

| Dataset | Source | Status |
|---------|--------|--------|
| STCR coefficients | PAU Ludhiana | ⚠️ Pending acquisition |
| District soil averages | Punjab SHC Portal | ⚠️ Pending acquisition |
| Biofertilizer data | PAU Agronomy Dept | ⚠️ Pending acquisition |
| Fertilizer products | Punjab Agri Dept | ⚠️ Pending acquisition |
| Fertilizer prices | Government/market data | ⚠️ Pending acquisition |
