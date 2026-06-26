from pickai.contracts.facility import FacilityProfile
from pickai.facility.defaults import build_default_profile
from pickai.facility.store import FacilityStore


def test_default_profile_has_locations(tmp_path):
    profile = build_default_profile()
    assert profile.tenant_id == "default"
    assert len(profile.locations) >= 10
    assert len(profile.zones) == 3


def test_facility_store_save_load(tmp_path):
    store = FacilityStore(root=tmp_path)
    profile = build_default_profile(tenant_id="t1", facility_id="f1")
    store.save(profile)
    loaded = store.load(tenant_id="t1", facility_id="f1")
    assert loaded.facility_id == "f1"
    assert len(loaded.locations) == len(profile.locations)


def test_publish_increments_version(tmp_path):
    store = FacilityStore(root=tmp_path)
    profile = build_default_profile()
    profile.version = 1
    store.save(profile)
    published = store.publish(profile)
    assert published.version == 2
