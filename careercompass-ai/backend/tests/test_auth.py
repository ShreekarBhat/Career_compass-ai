import uuid


def test_refresh_tokens_rotate_and_logout(client):
    email = f"refresh{uuid.uuid4().hex[:8]}@example.com"
    response = client.post("/auth/register", json={
        "email": email,
        "password": "supersecret1",
        "full_name": "Refresh Test",
    })
    assert response.status_code == 201
    tokens = response.json()
    assert tokens["expires_in"] == 15 * 60
    assert tokens["refresh_expires_in"] == 30 * 24 * 60 * 60

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    next_tokens = refreshed.json()
    assert next_tokens["access_token"] != tokens["access_token"]
    assert next_tokens["refresh_token"] != tokens["refresh_token"]

    replay = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    rejected_after_reuse = client.post("/auth/refresh", json={
        "refresh_token": next_tokens["refresh_token"],
    })
    assert rejected_after_reuse.status_code == 401


def test_logout_revokes_refresh_token(client):
    email = f"logout{uuid.uuid4().hex[:8]}@example.com"
    response = client.post("/auth/register", json={
        "email": email,
        "password": "supersecret1",
        "full_name": "Logout Test",
    })
    refresh_token = response.json()["refresh_token"]

    logout = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200
    assert logout.json() == {"revoked": True}

    refreshed = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 401
