import pytest
from services.vision_service import calculate_waste_quantity
from schemas.report_schema import AiAnalysisResult, WasteQuantityEstimate

def test_plastic_waste_in_drain_quantity():
    # 70% plastic blockage in drain
    qty = calculate_waste_quantity(
        waste_type="plastic",
        blockage_percentage=70,
        estimated_waste_coverage=70,
        drain_detected=True,
        drainage_structure="open gutter"
    )
    
    # 2.88m³ * 0.70 = 2.02 m³
    assert qty["volume_m3"] == 2.02
    assert qty["density_kg_m3"] == 85.0
    # 2.02 * 85 = 171.7 kg
    assert qty["weight_kg"] == 171.7
    assert qty["weight_tons"] == 0.17
    # 171.7 / 25 = 7 bags
    assert qty["bags_count"] == 7
    # 2.02 / 0.8 = 3 tricycle trips
    assert qty["tricycle_trips"] == 3
    assert qty["cleanup_urgency"] == "URGENT"

def test_heavy_silt_blockage_quantity():
    # 85% silt sludge in drain
    qty = calculate_waste_quantity(
        waste_type="silt",
        blockage_percentage=85,
        estimated_waste_coverage=85,
        drain_detected=True,
        drainage_structure="box culvert"
    )
    
    # 2.88 * 0.85 = 2.45 m³
    assert qty["volume_m3"] == 2.45
    assert qty["density_kg_m3"] == 1450.0
    # 2.45 * 1450 = 3552.5 kg
    assert qty["weight_kg"] == 3552.5
    assert qty["weight_tons"] == 3.55
    # 3552.5 / 25 = 143 bags
    assert qty["bags_count"] == 143
    assert qty["tricycle_trips"] == 4
    assert qty["cleanup_urgency"] == "IMMEDIATE"

def test_open_ground_waste_quantity():
    # Trash on open ground, no drain
    qty = calculate_waste_quantity(
        waste_type="mixed",
        blockage_percentage=0,
        estimated_waste_coverage=50,
        drain_detected=False,
        drainage_structure="none"
    )
    
    # 2.10m³ * 0.50 = 1.05 m³
    assert qty["volume_m3"] == 1.05
    assert qty["density_kg_m3"] == 300.0
    # 1.05 * 300 = 315.0 kg
    assert qty["weight_kg"] == 315.0
    assert qty["bags_count"] == 13
    assert qty["tricycle_trips"] == 2
    assert qty["cleanup_urgency"] == "URGENT"

def test_zero_waste_clean_drain_quantity():
    # 0% blockage, clean drain
    qty = calculate_waste_quantity(
        waste_type="none",
        blockage_percentage=0,
        estimated_waste_coverage=0,
        drain_detected=True,
        drainage_structure="open gutter"
    )
    
    assert qty["volume_m3"] == 0.0
    assert qty["weight_kg"] == 0.0
    assert qty["bags_count"] == 0
    assert qty["tricycle_trips"] == 0
    assert qty["cleanup_urgency"] == "ROUTINE"

def test_ai_analysis_result_schema_compatibility():
    qty = calculate_waste_quantity(
        waste_type="plastic",
        blockage_percentage=50,
        estimated_waste_coverage=50,
        drain_detected=True
    )
    
    result = AiAnalysisResult(
        report_id="GL-TEST01",
        waste_detected=True,
        waste_type="plastic",
        blockage_percentage=50,
        waste_quantity=WasteQuantityEstimate(**qty),
        estimated_volume_m3=qty["volume_m3"],
        estimated_weight_kg=qty["weight_kg"],
        cleanup_bags_needed=qty["bags_count"],
        tricycle_trips_needed=qty["tricycle_trips"]
    )
    
    assert result.waste_quantity.volume_m3 == 1.44
    assert result.waste_quantity.weight_kg == 122.4
    assert result.cleanup_bags_needed == 5
    assert result.tricycle_trips_needed == 2
