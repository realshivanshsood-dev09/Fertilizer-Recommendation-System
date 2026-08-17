# Track B — ML Training Data Architecture

This directory holds all machine learning data for the SIH 2026
Fertilizer Recommendation System.

## Architecture Overview

The ML pipeline is a **correction/residual model** on top of the STCR agronomic baseline:

```
Raw field-trial data
    ↓ validation + cleaning
    ↓ normalization
    ↓ feature engineering
    ↓ STCR baseline calculation
    ↓ define correction/residual target = observed_dose − stcr_baseline
    ↓ train XGBoost
    ↓ k-fold cross-validation
    ↓ compare vs. STCR baseline alone
    ↓ error analysis + SHAP
    ↓ model registry
    ↓ FastAPI inference
```

**The ML model must NOT replace STCR.**
If the model does not demonstrably improve over the STCR baseline, STCR is the production recommendation.

## Directory Structure

```
ml/
├── data/
│   ├── raw/            # Original field trial datasets (never modified after download)
│   ├── interim/        # Partially processed (imputation, outlier flags)
│   └── processed/      # Feature-ready datasets for training
├── features/           # Feature engineering outputs and schemas
├── training/           # Training scripts (train.py already present)
├── evaluation/         # Evaluation reports, CV results, comparison vs. STCR
├── models/             # Serialized model artifacts (.pkl, .json)
├── explainability/     # SHAP values, feature importance outputs
└── registry/           # Model version metadata JSON files
```

## Training Data Requirements

Training data must come from real field experiments, NOT synthetic records.

Preferred sources:
- PAU field experiments (Ludhiana)
- ICAR/AICRP-STCR network experiments
- Government agricultural trial datasets
- Peer-reviewed field trials with documented methodology

**FORBIDDEN**: Synthetic agricultural training records, random Kaggle datasets
without documented provenance, or datasets without soil + fertilizer + yield variables.

## Expected Feature Set

Each training record should ideally contain:

| Feature | Description |
|---------|-------------|
| `soil_n_kg_per_ha` | Available N (alkaline KMnO4) |
| `soil_p_kg_per_ha` | Available P₂O₅ (Olsen's) |
| `soil_k_kg_per_ha` | Available K₂O (ammonium acetate) |
| `ph` | Soil pH (1:2 water) |
| `organic_carbon_pct` | OC% (Walkley-Black) |
| `crop` | wheat / rice / cotton |
| `season` | rabi / kharif |
| `district` | Location |
| `year` | Experimental year |
| `irrigation` | Irrigation type |
| `fertilizer_n_applied` | N dose applied (kg/ha) |
| `fertilizer_p2o5_applied` | P₂O₅ dose applied (kg/ha) |
| `fertilizer_k2o_applied` | K₂O dose applied (kg/ha) |
| `observed_yield_mg_per_ha` | Measured grain yield |
| `stcr_baseline_n` | STCR-calculated N dose |
| `stcr_baseline_p2o5` | STCR-calculated P dose |
| `stcr_baseline_k2o` | STCR-calculated K dose |
| `correction_n` | Target: applied − stcr_baseline (N) |
| `correction_p` | Target: applied − stcr_baseline (P) |
| `correction_k` | Target: applied − stcr_baseline (K) |

## Current Status

- Training data: ⚠️ **Not acquired** — awaiting Track A data acquisition
- Model training: ⚠️ **Not started** — requires verified training dataset
- Model registry: ✅ **Schema ready** (ModelVersion table in database)
- Feature schema: ⚠️ **Pending** — will be defined when data is available
