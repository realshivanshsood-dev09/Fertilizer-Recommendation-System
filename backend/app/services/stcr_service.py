"""
STCR Baseline Service
=====================
Computes the agronomic fertilizer baseline using Soil Test Crop Response (STCR)
methodology published by Punjab Agricultural University (PAU) and ICAR.

Verified Datasets in Live Engine:
  - Wheat: DS-ICAR-PAU-WHEAT-STCR-2022 (Singh, Mavi & Saini 2022, Indian J. Agric. Sci.)
      NPK:
        FN = 3.78*T - 0.96*SN
        FP2O5 = 1.54*T - 0.23*SP2O5
        FK2O = 0.95*T - 0.09*SK2O
      Rice-residue 6 t/ha:
        FN = 3.78*T - 0.96*SN - 0.77*RRN
        FP2O5 = 1.54*T - 0.23*SP2O5 - 0.30*RRP2O5
        FK2O = 0.95*T - 0.10*SK2O - 0.12*RRK2O

  - Rice: DS-ICAR-PAU-RICE-TYE-INM-2021 (Singh, Mavi & Saini 2021, Indian J. Agric. Sci.)
      Target-yield equation:
        FN = 3.02*T - 0.63*SN
        FP2O5 = 1.78*T - 8.37*SP
        FK2O = 2.75*T - 1.39*SK
      Provenance status: verified_application_probable_calibration.

  - Cotton:
      Unpopulated / placeholder awaiting authoritative PAU/ICAR calibration.

Dose Clipping:
  All final nutrient doses are clipped to >= 0.0 (negative fertilizer requirements
  are never returned).
"""

from __future__ import annotations

import structlog
from typing import List, Optional

from app.core.constants import Crop, District, Season
from app.core.data_loader import STCRCoefficients, load_stcr_coefficients
from app.schemas.response import CalculationStep, STCRBaseline
from app.services.soil_resolution import SoilProfile

log = structlog.get_logger(__name__)

_stcr_data: STCRCoefficients = load_stcr_coefficients()


class STCRService:
    """
    Computes STCR fertilizer baseline doses using verified Track A equations.
    """

    def __init__(self, stcr_coefficients: Optional[STCRCoefficients] = None) -> None:
        self._coeffs = stcr_coefficients or _stcr_data

    def compute(
        self,
        crop: Crop,
        district: District,
        season: Season,
        soil: SoilProfile,
        target_yield_q_ha: Optional[float] = None,
        rice_residue_incorporated: bool = False,
        rice_residue_rrn: Optional[float] = None,
        rice_residue_rrp2o5: Optional[float] = None,
        rice_residue_rrk2o: Optional[float] = None,
    ) -> STCRBaseline:
        log.info(
            "stcr_compute_start",
            crop=crop.value,
            district=district.value,
            soil_source=soil.source.value,
            target_yield_q_ha=target_yield_q_ha,
            residue=rice_residue_incorporated,
        )

        # 1. Reject impossible negative inputs
        if soil.nitrogen is not None and soil.nitrogen < 0:
            raise ValueError(f"Soil Nitrogen cannot be negative: {soil.nitrogen}")
        if soil.phosphorus is not None and soil.phosphorus < 0:
            raise ValueError(f"Soil Phosphorus cannot be negative: {soil.phosphorus}")
        if soil.potassium is not None and soil.potassium < 0:
            raise ValueError(f"Soil Potassium cannot be negative: {soil.potassium}")
        if target_yield_q_ha is not None and target_yield_q_ha <= 0:
            raise ValueError(f"Target yield must be strictly positive (q/ha): {target_yield_q_ha}")

        # 2. Check completeness of soil data
        if not soil.is_complete_for_stcr():
            log.warning(
                "stcr_skipped_incomplete_soil",
                reason=f"Soil source '{soil.source.value}' did not provide complete N/P/K measurements.",
            )
            return STCRBaseline(
                N_kg_per_ha=None,
                P2O5_kg_per_ha=None,
                K2O_kg_per_ha=None,
                target_yield_q_ha=target_yield_q_ha,
                equation_version="SKIPPED",
                data_source="STCR skipped — soil N/P/K not available",
                calculation_steps=[],
                is_placeholder=True,
                notes=(
                    f"Soil source '{soil.source.value}' did not provide complete N/P/K. "
                    "STCR baseline cannot be computed safely without measured soil nutrients."
                ),
            )

        sn = float(soil.nitrogen)  # type: ignore[arg-type]
        sp = float(soil.phosphorus)  # type: ignore[arg-type]
        sk = float(soil.potassium)  # type: ignore[arg-type]

        # 3. WHEAT STCR (Singh, Mavi & Saini 2022)
        if crop == Crop.WHEAT:
            t = float(target_yield_q_ha) if target_yield_q_ha is not None else 50.0

            n_coeff = self._coeffs.get_nutrient_coefficients("wheat", "N")
            p_coeff = self._coeffs.get_nutrient_coefficients("wheat", "P")
            k_coeff = self._coeffs.get_nutrient_coefficients("wheat", "K")

            a_n = n_coeff.get("a", 3.78) or 3.78
            b_n = n_coeff.get("b", 0.96) or 0.96

            a_p = p_coeff.get("a", 1.54) or 1.54
            b_p = p_coeff.get("b", 0.23) or 0.23

            a_k = k_coeff.get("a", 0.95) or 0.95
            b_k = k_coeff.get("b", 0.09) or 0.09

            steps: List[CalculationStep] = []

            if rice_residue_incorporated:
                c_rn = n_coeff.get("c_residue", 0.77) or 0.77
                c_rp = p_coeff.get("c_residue", 0.30) or 0.30
                c_rk = k_coeff.get("c_residue", 0.12) or 0.12
                b_k_res = k_coeff.get("b_with_residue", 0.10) or 0.10

                rrn = float(rice_residue_rrn) if rice_residue_rrn is not None else 0.0
                rrp = float(rice_residue_rrp2o5) if rice_residue_rrp2o5 is not None else 0.0
                rrk = float(rice_residue_rrk2o) if rice_residue_rrk2o is not None else 0.0

                raw_n = a_n * t - b_n * sn - c_rn * rrn
                raw_p = a_p * t - b_p * sp - c_rp * rrp
                raw_k = a_k * t - b_k_res * sk - c_rk * rrk

                eq_ver = "STCR-PAU-2022-WHEAT-RESIDUE"
                notes = f"STCR wheat prescription (T={t} q/ha) with 6 t/ha rice residue on alluvial soil."

                fn = max(0.0, round(raw_n, 2))
                fp = max(0.0, round(raw_p, 2))
                fk = max(0.0, round(raw_k, 2))

                steps.append(CalculationStep(
                    nutrient="N",
                    equation_formula=f"FN = {a_n}*T - {b_n}*SN - {c_rn}*RRN",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sn,
                    raw_calculated_dose=round(raw_n, 2),
                    final_clipped_dose=fn,
                    step_explanation=f"{a_n}×{t} - {b_n}×{sn} - {c_rn}×{rrn} = {raw_n:.2f} kg N/ha",
                ))
                steps.append(CalculationStep(
                    nutrient="P2O5",
                    equation_formula=f"FP2O5 = {a_p}*T - {b_p}*SP2O5 - {c_rp}*RRP2O5",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sp,
                    raw_calculated_dose=round(raw_p, 2),
                    final_clipped_dose=fp,
                    step_explanation=f"{a_p}×{t} - {b_p}×{sp} - {c_rp}×{rrp} = {raw_p:.2f} kg P2O5/ha",
                ))
                steps.append(CalculationStep(
                    nutrient="K2O",
                    equation_formula=f"FK2O = {a_k}*T - {b_k_res}*SK2O - {c_rk}*RRK2O",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sk,
                    raw_calculated_dose=round(raw_k, 2),
                    final_clipped_dose=fk,
                    step_explanation=f"{a_k}×{t} - {b_k_res}×{sk} - {c_rk}×{rrk} = {raw_k:.2f} kg K2O/ha",
                ))
            else:
                raw_n = a_n * t - b_n * sn
                raw_p = a_p * t - b_p * sp
                raw_k = a_k * t - b_k * sk

                eq_ver = "STCR-PAU-2022-WHEAT-NPK"
                notes = f"STCR wheat prescription (T={t} q/ha) on alluvial soil (Singh et al., 2022)."

                fn = max(0.0, round(raw_n, 2))
                fp = max(0.0, round(raw_p, 2))
                fk = max(0.0, round(raw_k, 2))

                steps.append(CalculationStep(
                    nutrient="N",
                    equation_formula=f"FN = {a_n}*T - {b_n}*SN",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sn,
                    raw_calculated_dose=round(raw_n, 2),
                    final_clipped_dose=fn,
                    step_explanation=f"{a_n} × {t} - {b_n} × {sn} = {a_n*t:.2f} - {b_n*sn:.2f} = {raw_n:.2f} kg N/ha",
                ))
                steps.append(CalculationStep(
                    nutrient="P2O5",
                    equation_formula=f"FP2O5 = {a_p}*T - {b_p}*SP2O5",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sp,
                    raw_calculated_dose=round(raw_p, 2),
                    final_clipped_dose=fp,
                    step_explanation=f"{a_p} × {t} - {b_p} × {sp} = {a_p*t:.2f} - {b_p*sp:.2f} = {raw_p:.2f} kg P2O5/ha",
                ))
                steps.append(CalculationStep(
                    nutrient="K2O",
                    equation_formula=f"FK2O = {a_k}*T - {b_k}*SK2O",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sk,
                    raw_calculated_dose=round(raw_k, 2),
                    final_clipped_dose=fk,
                    step_explanation=f"{a_k} × {t} - {b_k} × {sk} = {a_k*t:.2f} - {b_k*sk:.2f} = {raw_k:.2f} kg K2O/ha",
                ))

            return STCRBaseline(
                N_kg_per_ha=fn,
                P2O5_kg_per_ha=fp,
                K2O_kg_per_ha=fk,
                target_yield_q_ha=t,
                equation_version=eq_ver,
                data_source="DS-ICAR-PAU-WHEAT-STCR-2022 (PAU Ludhiana)",
                dataset_id="DS-ICAR-PAU-WHEAT-STCR-2022",
                source_id="SRC-ICAR-PAU-WHEAT-STCR-2022",
                provenance_status="verified",
                calculation_steps=steps,
                is_placeholder=False,
                notes=notes,
            )

        # 4. RICE STCR (Singh, Mavi & Saini 2021)
        if crop == Crop.RICE:
            t = float(target_yield_q_ha) if target_yield_q_ha is not None else 70.0

            n_coeff = self._coeffs.get_nutrient_coefficients("rice", "N")
            p_coeff = self._coeffs.get_nutrient_coefficients("rice", "P")
            k_coeff = self._coeffs.get_nutrient_coefficients("rice", "K")

            a_n = n_coeff.get("a", 3.02) or 3.02
            b_n = n_coeff.get("b", 0.63) or 0.63

            a_p = p_coeff.get("a", 1.78) or 1.78
            b_p = p_coeff.get("b", 8.37) or 8.37

            a_k = k_coeff.get("a", 2.75) or 2.75
            b_k = k_coeff.get("b", 1.39) or 1.39

            raw_n = a_n * t - b_n * sn
            raw_p = a_p * t - b_p * sp
            raw_k = a_k * t - b_k * sk

            fn = max(0.0, round(raw_n, 2))
            fp = max(0.0, round(raw_p, 2))
            fk = max(0.0, round(raw_k, 2))

            steps = [
                CalculationStep(
                    nutrient="N",
                    equation_formula=f"FN = {a_n}*T - {b_n}*SN",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sn,
                    raw_calculated_dose=round(raw_n, 2),
                    final_clipped_dose=fn,
                    step_explanation=f"{a_n} × {t} - {b_n} × {sn} = {a_n*t:.2f} - {b_n*sn:.2f} = {raw_n:.2f} kg N/ha",
                ),
                CalculationStep(
                    nutrient="P2O5",
                    equation_formula=f"FP2O5 = {a_p}*T - {b_p}*SP",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sp,
                    raw_calculated_dose=round(raw_p, 2),
                    final_clipped_dose=fp,
                    step_explanation=f"{a_p} × {t} - {b_p} × {sp} = {a_p*t:.2f} - {b_p*sp:.2f} = {raw_p:.2f} kg P2O5/ha",
                ),
                CalculationStep(
                    nutrient="K2O",
                    equation_formula=f"FK2O = {a_k}*T - {b_k}*SK",
                    target_yield_q_ha=t,
                    soil_value_kg_ha=sk,
                    raw_calculated_dose=round(raw_k, 2),
                    final_clipped_dose=fk,
                    step_explanation=f"{a_k} × {t} - {b_k} × {sk} = {a_k*t:.2f} - {b_k*sk:.2f} = {raw_k:.2f} kg K2O/ha",
                ),
            ]

            return STCRBaseline(
                N_kg_per_ha=fn,
                P2O5_kg_per_ha=fp,
                K2O_kg_per_ha=fk,
                target_yield_q_ha=t,
                equation_version="STCR-PAU-2021-RICE-TYE",
                data_source="DS-ICAR-PAU-RICE-TYE-INM-2021 (PAU Gurdaspur)",
                dataset_id="DS-ICAR-PAU-RICE-TYE-INM-2021",
                source_id="SRC-ICAR-PAU-RICE-TYE-INM-2021",
                provenance_status="verified_application_probable_calibration",
                calculation_steps=steps,
                is_placeholder=False,
                notes=(
                    f"STCR rice target-yield prescription (T={t} q/ha). "
                    "Calibration derivation pending physical archival acquisition."
                ),
            )

        # 5. COTTON / OTHER (Unpopulated coefficients)
        return STCRBaseline(
            N_kg_per_ha=None,
            P2O5_kg_per_ha=None,
            K2O_kg_per_ha=None,
            target_yield_q_ha=target_yield_q_ha,
            equation_version="PLACEHOLDER",
            data_source="PAU/ICAR cotton STCR coefficients pending",
            dataset_id=None,
            source_id=None,
            provenance_status="unverified",
            calculation_steps=[],
            is_placeholder=True,
            notes=(
                f"STCR coefficients for {crop.value} in Malwa are not yet available. "
                "All numerical doses are None until real PAU/ICAR values are provided."
            ),
        )
