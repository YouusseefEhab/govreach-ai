import pytest


def payload(**changes):
    return {"title": "Seat belt awareness", "objective": "Encourage seat belt use", **changes}


def marketing_payload(**changes):
    return {
        "campaign_type": "marketing",
        "title": "  Spring offers  ",
        "objective": "  Increase orders  ",
        "business_name": "  Cairo Bakery  ",
        "offer_summary": "  Weekend pastry box  ",
        "target_audience": "  Local families  ",
        **changes,
    }


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
    assert set(campaign) == {"id", "title", "domain", "objective", "language", "status", "created_at"}
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


def test_marketing_create_list_and_detail(client):
    legacy = client.post("/api/v1/campaigns", json=payload()).json()
    response = client.post("/api/v1/campaigns", json=marketing_payload(
        domain="traffic_safety",
        language="arabic",
        budget={"amount": "1500.5", "currency": "EGP"},
        channels=["social", "email", "search", "website", "print"],
        brief="  Mention pickup.  ",
    ))
    assert response.status_code == 201, response.text
    campaign = response.json()
    assert campaign == {
        "id": campaign["id"],
        "created_at": campaign["created_at"],
        "campaign_type": "marketing",
        "domain": "marketing",
        "title": "Spring offers",
        "objective": "Increase orders",
        "business_name": "Cairo Bakery",
        "offer_summary": "Weekend pastry box",
        "target_audience": "Local families",
        "language": "arabic",
        "status": "draft",
        "budget": {"amount": "1500.50", "currency": "EGP"},
        "channels": ["social", "email", "search", "website", "print"],
        "brief": "Mention pickup.",
    }
    assert client.get(f"/api/v1/campaigns/{campaign['id']}").json() == campaign
    assert client.get("/api/v1/campaigns").json() == [campaign, legacy]
    assert client.get("/api/v1/campaigns?skip=1&limit=1").json() == [legacy]


def test_marketing_patch_preserves_omitted_fields_and_clears_optional_fields(client):
    response = client.post("/api/v1/campaigns", json=marketing_payload())
    assert response.status_code == 201, response.text
    campaign = response.json()
    assert campaign["budget"] is None
    assert campaign["channels"] == []
    assert campaign["brief"] is None
    assert campaign["language"] == "both"
    url = f"/api/v1/campaigns/{campaign['id']}"

    changes = {
        "business_name": "  Cairo Bakes  ",
        "target_audience": "  University students  ",
        "budget": {"amount": "0", "currency": "USD"},
        "channels": ["social"],
        "brief": "  Mention pickup.  ",
    }
    response = client.patch(url, json=changes)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated == {
        **campaign,
        "business_name": "Cairo Bakes",
        "target_audience": "University students",
        "budget": {"amount": "0.00", "currency": "USD"},
        "channels": ["social"],
        "brief": "Mention pickup.",
    }
    assert client.patch(url, json={}).json() == updated
    assert client.patch(url, json={"campaign_type": "marketing", "domain": "marketing"}).json() == updated
    response = client.patch(url, json={"budget": None, "channels": None, "brief": None})
    assert response.status_code == 200, response.text
    assert response.json() == {**updated, "budget": None, "channels": None, "brief": None}
    assert client.get(url).json() == response.json()


def test_domain_marketing_without_opt_in_remains_legacy(client):
    response = client.post("/api/v1/campaigns", json=payload(
        domain="marketing", objective="x" * 2001, business_name=123,
    ))
    assert response.status_code == 201, response.text
    campaign = response.json()
    assert campaign["domain"] == "marketing"
    assert "campaign_type" not in campaign
    assert "business_name" not in campaign
    url = f"/api/v1/campaigns/{campaign['id']}"
    assert client.patch(url, json={
        "campaign_type": None, "objective": None, "budget": {}, "channels": ["unknown"],
    }).json() == campaign
    assert client.patch(url, json={"campaign_type": "marketing"}).status_code == 422
    assert client.get(url).json() == campaign
    assert client.patch(url, json={"domain": "traffic_safety"}).json() == {
        **campaign, "domain": "traffic_safety",
    }


@pytest.mark.parametrize("field", ["business_name", "offer_summary", "target_audience", "title", "objective"])
def test_marketing_requires_nonblank_values_on_create_and_patch(client, field):
    data = marketing_payload()
    del data[field]
    assert client.post("/api/v1/campaigns", json=data).status_code == 422
    assert client.post("/api/v1/campaigns", json={**data, field: " \t "}).status_code == 422

    campaign = client.post("/api/v1/campaigns", json=marketing_payload()).json()
    url = f"/api/v1/campaigns/{campaign['id']}"
    assert client.patch(url, json={field: None}).status_code == 422
    assert client.get(url).json() == campaign


@pytest.mark.parametrize("changes", [
    {"campaign_type": "other"},
    {"business_name": "x" * 121},
    {"offer_summary": "x" * 1001},
    {"target_audience": "x" * 301},
    {"objective": "x" * 2001},
    {"brief": "x" * 3001},
    {"channels": ["social", "social"]},
    {"channels": ["radio"]},
    {"channels": "social"},
    {"budget": {"amount": "-0.01", "currency": "EGP"}},
    {"budget": {"amount": "1000000000000.00", "currency": "EGP"}},
    {"budget": {"amount": "0.001", "currency": "EGP"}},
    {"budget": {"amount": "1.000", "currency": "EGP"}},
    {"budget": {"amount": "NaN", "currency": "EGP"}},
    {"budget": {"amount": "1e2", "currency": "EGP"}},
    {"budget": {"amount": 1.25, "currency": "EGP"}},
    {"budget": {"amount": 0, "currency": "EGP"}},
    {"budget": {"amount": "1", "currency": "EUR"}},
    {"budget": {"amount": "1"}},
])
def test_marketing_rejects_invalid_create_and_patch(client, changes):
    assert client.post("/api/v1/campaigns", json=marketing_payload(**changes)).status_code == 422
    campaign = client.post("/api/v1/campaigns", json=marketing_payload()).json()
    url = f"/api/v1/campaigns/{campaign['id']}"
    response = client.patch(url, json={"title": "Do not save", **changes})
    assert response.status_code == 422, response.text
    assert client.get(url).json() == campaign


@pytest.mark.parametrize("changes", [
    {"campaign_type": None},
    {"domain": "traffic_safety"},
    {"domain": None},
    {"status": "published"},
    {"status": None},
])
def test_marketing_patch_preserves_type_domain_and_draft_status(client, changes):
    campaign = client.post("/api/v1/campaigns", json=marketing_payload()).json()
    url = f"/api/v1/campaigns/{campaign['id']}"
    assert client.patch(url, json=changes).status_code == 422
    assert client.get(url).json() == campaign
