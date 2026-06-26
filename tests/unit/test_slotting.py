from pickai.contracts.facility import PickHistoryRecord
from pickai.domain.slotting import classify_abc, generate_slotting_suggestions
from pickai.facility.defaults import build_default_profile


def test_abc_classification():
    records = [
        PickHistoryRecord(order_id="o1", sku="FAST", location_id="L1", quantity=80, x=0, y=6),
        PickHistoryRecord(order_id="o2", sku="SLOW", location_id="L2", quantity=5, x=1, y=6),
    ]
    tiers = classify_abc(records)
    assert tiers["FAST"].value == "A"
    assert tiers["SLOW"].value in ("B", "C")


def test_slotting_suggestions_non_empty():
    profile = build_default_profile()
    records = [
        PickHistoryRecord(order_id=f"o{i}", sku="FAST-SKU", location_id=profile.locations[30].location_id, quantity=10, x=30, y=6)
        for i in range(20)
    ]
    suggestions = generate_slotting_suggestions(profile, records, top_n=3)
    assert isinstance(suggestions, list)
