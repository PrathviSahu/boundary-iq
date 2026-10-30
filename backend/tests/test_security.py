import pytest
from fastapi.testclient import TestClient
from app.main import app, limiter

@pytest.fixture
def client():
    return TestClient(app)

def test_security_headers_present(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("Permissions-Policy") == "geolocation=(), camera=(), microphone=()"
    assert headers.get("Content-Security-Policy") == "default-src 'none'; frame-ancestors 'none'"

def test_hsts_applied_only_on_https(client):
    # Standard HTTP request: no HSTS header
    http_res = client.get("/api/health")
    assert "Strict-Transport-Security" not in http_res.headers

    # HTTPS proxy request: HSTS header must be present
    https_res = client.get("/api/health", headers={"x-forwarded-proto": "https"})
    assert https_res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

def test_cors_allows_whitelisted_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"

def test_cors_rejects_unauthorized_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-phishing-site.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    # Unauthorized origin must NOT be reflected
    assert res.headers.get("access-control-allow-origin") != "https://malicious-phishing-site.com"
    assert res.headers.get("access-control-allow-origin") != "*"

def test_cors_allows_project_scoped_preview_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://boundary-iq-preview-123.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") == "https://boundary-iq-preview-123.vercel.app"

def test_cors_rejects_unrelated_vercel_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://some-other-project.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") != "https://some-other-project.vercel.app"
    assert res.headers.get("access-control-allow-origin") != "*"

def test_explanation_endpoint_caching(client):
    # First call
    res1 = client.get("/api/matches/ind_sa_t20wc_2024_final/explain/24")
    assert res1.status_code == 200
    data1 = res1.json()

    # Second call should immediately retrieve from cache
    res2 = client.get("/api/matches/ind_sa_t20wc_2024_final/explain/24")
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1["delivery_index"] == data2["delivery_index"]
    assert data1["headline"] == data2["headline"]
    assert data1["what_happened"] == data2["what_happened"]

def test_rate_limiter_enforcement(client):
    # Temporarily set lower limit for testing
    original_limit = limiter.explain_limit
    limiter.explain_limit = 5
    limiter.explain_requests.clear()

    try:
        # First 5 calls pass
        for i in range(5):
            res = client.get(f"/api/matches/ind_sa_t20wc_2024_final/explain/{i}")
            assert res.status_code == 200

        # 6th call should be rejected with 429
        res_blocked = client.get("/api/matches/ind_sa_t20wc_2024_final/explain/5")
        assert res_blocked.status_code == 429
        assert "Retry-After" in res_blocked.headers
        assert "Too many requests" in res_blocked.json()["detail"]
    finally:
        # Restore original limit
        limiter.explain_limit = original_limit
        limiter.explain_requests.clear()

