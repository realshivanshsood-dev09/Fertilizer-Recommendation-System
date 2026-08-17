# Science Status — Fertilizer Recommendation System
## SIH 2026 | Malwa Region, Punjab

> Last updated: 2026-08-17
> This document is the authoritative record of what is real, what is placeholder,
> and exactly what data and information are still needed before the system can
> produce real recommendations.

---

## 1. What is Real (Phase 1)

| Component | Status | Notes |
|---|---|---|
| Project architecture | ✅ Real | Two-layer STCR + ML design |
| Domain enums (districts, crops, seasons) | ✅ Real | Correct administrative categories |
| Crop-season validity matrix | ✅ Real | Wheat=Rabi, Rice/Cotton=Kharif |
| API request/response schema | ✅ Real | Pydantic validated |
| Soil-source provenance tracking | ✅ Real | Carries through to response |
| Pipeline orchestration | ✅ Real | All 10 steps wired |
| STCR formula *structure* | ✅ Real | Formula: `(a×T − b×S) / FUE` |
| ML feature interface | ✅ Real | Feature vector defined |
| Unit tests | ✅ Real | Passing |

---

## 2. STCR Data Required

### 2.1 What We Need

For each crop (Wheat, Rice, Cotton) × each nutrient (N, P, K):

| Parameter | Description | Unit |
|---|---|---|
| `a` | Nutrient requirement per unit target yield | kg nutrient / Mg grain yield |
| `b` | Soil test calibration coefficient (slope) | dimensionless |
| `target_yield` | Realistic attainable yield for Malwa | Mg / ha |
| `FUE` | Fertilizer Use Efficiency | fraction (0–1) |

> [!CAUTION]
> Do NOT use generic national STCR values as proxies for Malwa.
> STCR coefficients are soil-series and agro-ecology specific.
> Values from other regions will produce incorrect recommendations.

### 2.2 Where to Get These Values

1. **PAU Ludhiana** — Punjab Agricultural University has conducted STCR trials
   in the Malwa agro-ecological zone. Contact: Soil Science Department, PAU.
   - Publication: *"Fertilizer Use Research in Punjab"* (PAU, periodic bulletins)
   - STCR project data from the soil fertility mapping programme

2. **ICAR-IISS Bhopal** — Indian Institute of Soil Science publishes STCR
   norms for major crops in alluvial soils.
   - Publication: *"STCR Approach for Balanced Fertilization"* (ICAR-IISS)

3. **Punjab Agriculture Department** — Soil Health Card portal data and
   district fertilizer response field trials.

### 2.3 Data Gaps to Fill in `agronomy/stcr/stcr_coefficients.yaml`

- [ ] Wheat × N: `a`, `b`, `target_yield`, `FUE`
- [ ] Wheat × P: `a`, `b`, `target_yield`, `FUE`
- [ ] Wheat × K: `a`, `b`, `target_yield`, `FUE`
- [ ] Rice × N: `a`, `b`, `target_yield`, `FUE`
- [ ] Rice × P: `a`, `b`, `target_yield`, `FUE`
- [ ] Rice × K: `a`, `b`, `target_yield`, `FUE`
- [ ] Cotton × N: `a`, `b`, `target_yield`, `FUE`
- [ ] Cotton × P: `a`, `b`, `target_yield`, `FUE`
- [ ] Cotton × K: `a`, `b`, `target_yield`, `FUE`

---

## 3. ML Training Data Required

### 3.1 What We Need

A validated dataset where each record contains:

| Field | Description |
|---|---|
| `crop` | wheat / rice / cotton |
| `district` | One of the 5 Malwa districts |
| `season` | rabi / kharif |
| `soil_N` | Available N (kg/ha) from soil test |
| `soil_P` | Available P₂O₅ (kg/ha) from soil test |
| `soil_K` | Available K₂O (kg/ha) from soil test |
| `soil_pH` | pH at time of soil test |
| `soil_OC` | Organic carbon (%) |
| `irrigation` | Irrigation type |
| `actual_N_applied` | Fertilizer N actually applied (kg/ha) |
| `actual_P_applied` | Fertilizer P₂O₅ actually applied (kg/ha) |
| `actual_K_applied` | Fertilizer K₂O actually applied (kg/ha) |
| `yield_Mg_per_ha` | Actual crop yield observed |
| **`correction_N`** | **Target: actual_N − STCR_N** |
| **`correction_P`** | **Target: actual_P − STCR_P** |
| **`correction_K`** | **Target: actual_K − STCR_K** |

> [!IMPORTANT]
> The ML model predicts **correction residuals** (actual − STCR baseline),
> NOT absolute fertilizer doses. The STCR baseline must be computed first.

### 3.2 Minimum Dataset Size

- Recommended: ≥500 records per crop per district
- Minimum for meaningful training: ≥100 records per crop

### 3.3 Potential Data Sources

- Punjab Agriculture Department field trial records
- Soil Health Card + yield follow-up surveys
- NABARD / ATMA farmer survey data
- PAU agronomic trial publications

### 3.4 Before Training

- [ ] Dataset with schema above is available
- [ ] Target variable definition is validated by an agronomist
- [ ] Train/val/test split strategy defined
- [ ] Cross-validation scheme defined (ideally district-stratified)
- [ ] Baseline performance of STCR-only is measured
- [ ] Model must beat STCR-only to justify ML layer

---

## 4. Fertilizer Product Translation Data Required

- [ ] List of commercial fertilizer products available in Malwa (Urea, DAP, MOP, SSP, etc.)
- [ ] Nutrient percentage per product (N%, P₂O₅%, K₂O%)
- [ ] Current market prices per product (INR/50kg bag)
- [ ] Seasonal price variations
- [ ] Government subsidy rates (current MSP for subsidised fertilizers)

Source: Punjab Agri. Department fertilizer price notifications, local mandi data.

---

## 5. Biofertilizer Data Required

For each crop:
- [ ] Recommended bio-inoculant species / strains
- [ ] Application method (seed treatment / soil application)
- [ ] Application timing (at sowing / transplanting)
- [ ] Product availability in Malwa districts

Source: PAU crop production guide (*Kheti Sandesh*), PAU Ludhiana extension.

---

## 6. District Soil Profile Averages Required

For each of the 5 districts (Bathinda, Mansa, Muktsar, Moga, Faridkot):
- [ ] Mean available N (kg/ha) — from Soil Health Card survey
- [ ] Mean available P₂O₅ (kg/ha)
- [ ] Mean available K₂O (kg/ha)
- [ ] Mean pH
- [ ] Mean organic carbon (%)
- [ ] Sample size / year of survey

Source: Punjab SHC portal (soilhealth.dac.gov.in), PAU soil survey reports.

---

## 7. Information Required Before Implementing STCR Equations

The STCR computation in `backend/app/services/stcr_service.py` is structurally
correct but will only produce real doses when ALL of the following are available:

1. ✅ Formula structure — already implemented: `Dose = (a × T − b × S) / FUE`
2. ❌ Coefficient `a` per crop × nutrient
3. ❌ Coefficient `b` per crop × nutrient  
4. ❌ Target yield `T` per crop (Malwa-specific attainable yield)
5. ❌ Fertilizer Use Efficiency `FUE` per crop × nutrient
6. ❌ Soil test value units confirmed (kg/ha vs ppm — check PAU lab method)
7. ❌ Calibration method confirmed (Walkley-Black for OC, alkaline KMnO₄ for N, etc.)
8. ❌ Agronomist review of the formula implementation

> [!WARNING]
> Do not populate coefficients from internet sources without agronomist validation.
> Incorrect STCR coefficients produce incorrect recommendations. This is an
> agronomic safety issue, not just a data quality issue.

---

## 8. Application Timing Data Required

- [ ] Wheat: N split schedule (e.g., % at sowing, % at first irrigation, % at tillering)
- [ ] Rice: N split schedule (transplanting, tillering, panicle initiation)
- [ ] Cotton: N split schedule

Source: PAU crop production guides.

---

## 9. Weather Data Integration (Future)

Currently not integrated. Future ML features may include:
- [ ] Historical rainfall (district-level, seasonal)
- [ ] Temperature extremes
- [ ] IMD forecast data API

Source: IMD (imd.gov.in) district weather data.
