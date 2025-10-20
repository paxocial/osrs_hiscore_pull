from pathlib import Path

from core.mode_cache import ModeCache


def test_mode_cache_round_trip(tmp_path: Path) -> None:
    cache_path = tmp_path / "mode_cache.json"
    cache = ModeCache(cache_path)

    assert cache.get("PlayerOne") is None

    cache.update("PlayerOne", "hardcore")
    cache.persist()

    new_cache = ModeCache(cache_path)
    assert new_cache.get("PlayerOne") == "hardcore"

    new_cache.update("PlayerOne", "main")
    new_cache.persist()

    final_cache = ModeCache(cache_path)
    assert final_cache.get("PlayerOne") == "main"
