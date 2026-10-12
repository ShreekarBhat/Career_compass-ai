import app.tools.telegram_link as tl
from app.core.config import settings


def _auth(client):
    client.post("/auth/register", json={"email": "tg@example.com", "password": "password123", "full_name": "TG"})
    tok = client.post("/auth/login", data={"username": "tg@example.com", "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_one_click_link(client, monkeypatch):
    h = _auth(client)
    monkeypatch.setattr(settings, "telegram_bot_token", "123:ABC")
    sent, captured = [], {}
    monkeypatch.setattr(tl, "send_telegram", lambda chat, text: sent.append((chat, text)) or True)

    def fake_call(method, **params):
        if method == "getMe":
            return {"username": "cc_test_bot"}
        if method == "getUpdates":
            return [{"update_id": 7, "message": {"chat": {"id": 4242, "type": "private"},
                                                   "text": f"/start {captured['code']}"}}]
    monkeypatch.setattr(tl, "_call", fake_call)
    tl._state.update(offset=None, username=None)

    r = client.post("/notifications/telegram/link", headers=h)
    assert r.status_code == 200
    link = r.json()["link"]
    assert link.startswith("https://t.me/cc_test_bot?start=")
    captured["code"] = link.split("start=")[1]

    assert client.get("/notifications/telegram/status", headers=h).json() == {"linked": True}
    assert sent and sent[0][0] == "4242"
    # code is single-use
    assert tl.process_updates.__name__ == "process_updates"


def test_link_requires_bot_token(client, monkeypatch):
    h = _auth(client)
    monkeypatch.setattr(settings, "telegram_bot_token", "")
    assert client.post("/notifications/telegram/link", headers=h).status_code == 503
