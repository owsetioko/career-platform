import pytest


@pytest.fixture(autouse=True)
def isolate_profile_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.PROFILE_CACHE_PATH", tmp_path / "public-profile.json"
    )
