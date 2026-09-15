"""Tests for the randomized equipment fleet (api/equipment.py) — replaces
the previously hardcoded 20-item EQUIPMENT_IDS list."""

from api.equipment import _EQUIPMENT_PREFIX_RANGES, _generate_equipment_fleet
from etl.telemetry import _ASSET_TYPES_BY_PREFIX


def test_fleet_has_no_duplicate_ids():
    for _ in range(20):
        fleet = _generate_equipment_fleet()
        assert len(fleet) == len(set(fleet))


def test_fleet_covers_every_prefix_every_run():
    prefixes = {prefix for prefix, _ in _EQUIPMENT_PREFIX_RANGES}
    for _ in range(20):
        fleet = _generate_equipment_fleet()
        seen_prefixes = {equipment_id.split("-")[0] for equipment_id in fleet}
        assert seen_prefixes == prefixes


def test_fleet_maps_to_all_three_ml_asset_categories_every_run():
    """The model was trained on exactly PUMP / VALVE / LOADING_ARM — the
    generated fleet must always cover all three, not just probably."""
    for _ in range(20):
        fleet = _generate_equipment_fleet()
        categories = {_ASSET_TYPES_BY_PREFIX[equipment_id.split("-")[0]] for equipment_id in fleet}
        assert categories == {"PUMP", "VALVE", "LOADING_ARM"}


def test_arm_prefix_maps_directly_to_loading_arm():
    assert _ASSET_TYPES_BY_PREFIX["ARM"] == "LOADING_ARM"


def test_fleet_size_is_bounded():
    # 7 prefixes, 2-5 assets each.
    for _ in range(20):
        fleet = _generate_equipment_fleet()
        assert 14 <= len(fleet) <= 35
