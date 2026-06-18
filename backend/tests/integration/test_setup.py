from httpx import AsyncClient


async def test_setup_happy_path_returns_access_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/setup",
        json={
            "household_name": "The MacLeods",
            "member_name": "Jason",
            "email": "jason@example.com",
            "password": "CorrectHorse123!",  # pragma: allowlist secret  # pragma: allowlist secret
        },
    )
    assert resp.status_code == 201
    assert "access_token" in resp.json()


async def test_setup_second_call_returns_409(client: AsyncClient) -> None:
    payload = {
        "household_name": "The MacLeods",
        "member_name": "Jason",
        "email": "jason@example.com",
        "password": "CorrectHorse123!",  # pragma: allowlist secret
    }
    first = await client.post("/api/v1/setup", json=payload)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/setup",
        json={
            "household_name": "Another Household",
            "member_name": "Someone",
            "email": "someone@example.com",
            "password": "CorrectHorse123!",  # pragma: allowlist secret  # pragma: allowlist secret
        },
    )
    assert second.status_code == 409


async def test_setup_status_reflects_completion(client: AsyncClient) -> None:
    before = await client.get("/api/v1/setup/status")
    assert before.json() == {"setup_complete": False}

    await client.post(
        "/api/v1/setup",
        json={
            "household_name": "The MacLeods",
            "member_name": "Jason",
            "email": "jason@example.com",
            "password": "CorrectHorse123!",  # pragma: allowlist secret  # pragma: allowlist secret
        },
    )

    after = await client.get("/api/v1/setup/status")
    assert after.json() == {"setup_complete": True}
