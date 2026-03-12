import asyncio
from app.core.a2a import a2a


def test_registration_poll_loop_disabled(monkeypatch):
    monkeypatch.setattr(a2a.settings, "REGISTRY_POLL_ENABLED", False)
    asyncio.run(a2a.registration_poll_loop("http://localhost:9501"))


def test_registration_poll_loop_reregisters_when_missing(monkeypatch):
    called = {"register": 0}

    async def fake_is_registered(_):
        await asyncio.sleep(0)
        return False

    async def fake_register(_):
        await asyncio.sleep(0)
        called["register"] += 1
        raise asyncio.CancelledError

    monkeypatch.setattr(a2a.settings, "REGISTRY_POLL_ENABLED", True)
    monkeypatch.setattr(a2a.settings, "REGISTRY_POLL_INTERVAL_S", 60.0)
    monkeypatch.setattr(a2a, "is_registered_in_registry", fake_is_registered)
    monkeypatch.setattr(a2a, "register_with_registry", fake_register)

    try:
        asyncio.run(a2a.registration_poll_loop("http://localhost:9501"))
    except asyncio.CancelledError:
        pass

    assert called["register"] == 1
