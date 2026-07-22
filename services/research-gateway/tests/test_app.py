from ailab_research_gateway.app import Settings, create_app, normalize_search_results
from fastapi.testclient import TestClient


def test_fetch_route_requires_api_key() -> None:
    settings = Settings(api_key="g" * 48, docling_api_key="d" * 48)
    with TestClient(create_app(settings)) as client:
        response = client.post("/v1/fetch", json={"url": "https://example.com/"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_search_route_requires_api_key() -> None:
    settings = Settings(api_key="g" * 48, docling_api_key="d" * 48)
    with TestClient(create_app(settings)) as client:
        response = client.post("/v1/search", json={"query": "AAPL stock quote"})
    assert response.status_code == 401


def test_search_results_are_bounded_and_normalized() -> None:
    body = {
        "results": [
            {
                "title": "Example quote",
                "url": "https://example.com/quote",
                "content": "Timestamped market page",
                "engines": ["brave", "google"],
                "score": 1.25,
            },
            {"title": "Unsafe", "url": "javascript:alert(1)"},
        ]
    }
    results = normalize_search_results(body, 8)
    assert len(results) == 1
    assert results[0].engines == ["brave", "google"]
    assert results[0].snippet == "Timestamped market page"
