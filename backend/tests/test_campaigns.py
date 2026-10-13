import pytest


def payload(**changes):
    return {"title": "Seat belt awareness", "objective": "Encourage seat belt use", **changes}


def test_health_and_openapi(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "healthy"}
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths["/api/v1/campaigns"]) == {"get", "post"}
    assert set(paths["/api/v1/campaigns/{campaign_id}"]) == {"get", "patch", "delete"}


@pytest.mark.parametrize("language", ["arabic", "english", "both"])
def test_crud_lifecycle(client, language):
    response = client.post("/api/v1/campaigns", json=payload(language=language))
    assert response.status_code == 201
    campaign = response.json()
    campaign_id = campaign["id"]
    url = f"/api/v1/campaigns/{campaign_id}"
    assert campaign["status"] == "draft"
    assert campaign["domain"] == "traffic_safety"
    assert campaign["language"] == language
    assert campaign["created_at"]
    assert client.get(url).json() == campaign
    assert client.get("/api/v1/campaigns").json() == [campaign]
    response = client.patch(url, json={"title": "اربط حزام الأمان"})
    assert response.status_code == 200
    assert response.json()["title"] == "اربط حزام الأمان"
    assert response.json()["objective"] == campaign["objective"]
    assert response.json()["created_at"] == campaign["created_at"]
    # Preserve the existing no-op semantics for empty and null updates.
    assert client.patch(url, json={}).json() == response.json()
    assert client.patch(url, json={"title": None}).json() == response.json()
    deleted = client.delete(url)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(url).status_code == 404
    assert client.get("/api/v1/campaigns").json() == []


def test_pagination(client):
    ids = [client.post("/api/v1/campaigns", json=payload(title=str(i))).json()["id"] for i in range(3)]
    page = client.get("/api/v1/campaigns?skip=1&limit=1")
    assert page.status_code == 200
    assert [row["id"] for row in page.json()] == [ids[1]]
    assert [row["id"] for row in client.get("/api/v1/campaigns").json()] == ids[::-1]
    assert client.get("/api/v1/campaigns?skip=10").json() == []


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing_campaign(client, method):
    kwargs = {"json": {"title": "Updated"}} if method == "patch" else {}
    response = getattr(client, method)("/api/v1/campaigns/999999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Campaign not found"}


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101", "skip=abc"])
def test_invalid_pagination(client, query):
    assert client.get(f"/api/v1/campaigns?{query}").status_code == 422


@pytest.mark.parametrize("changes", [
    {"title": ""}, {"title": "x" * 256}, {"objective": ""},
    {"domain": ""}, {"domain": "x" * 101}, {"language": "french"},
])
def test_invalid_create(client, changes):
    assert client.post("/api/v1/campaigns", json=payload(**changes)).status_code == 422
    assert client.get("/api/v1/campaigns").json() == []


@pytest.mark.parametrize("changes", [{"title": ""}, {"language": "french"}, {"status": "published"}])
def test_invalid_update(client, changes):
    campaign = client.post("/api/v1/campaigns", json=payload()).json()
    url = f"/api/v1/campaigns/{campaign['id']}"
    assert client.patch(url, json=changes).status_code == 422
    assert client.get(url).json() == campaign


def test_required_fields_and_invalid_id(client):
    assert client.post("/api/v1/campaigns", json={}).status_code == 422
    assert client.get("/api/v1/campaigns/not-an-id").status_code == 422


@pytest.mark.parametrize("field", ["title", "domain", "objective"])
def test_whitespace_only_fields(client, field):
    assert client.post("/api/v1/campaigns", json=payload(**{field: " \t\n "})).status_code == 422
    campaign = client.post("/api/v1/campaigns", json=payload()).json()
    url = f"/api/v1/campaigns/{campaign['id']}"
    assert client.patch(url, json={field: " \t\n "}).status_code == 422
    assert client.get(url).json() == campaign


def test_trim_fields_and_preserve_arabic(client):
    response = client.post("/api/v1/campaigns", json=payload(
        title="  السلامة المرورية  ", objective="  Encourage safe driving  ",
    ))
    assert response.status_code == 201
    assert response.json()["title"] == "السلامة المرورية"
    assert response.json()["objective"] == "Encourage safe driving"
