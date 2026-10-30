import os
import pytest
import tempfile
from pathlib import Path
from starlette.requests import Request
from app.main import extract_client_ip, is_ip_trusted
from app.db.repository import DatabaseManager, DEFAULT_CONFIG


def make_mock_request(
    client_host: str = "127.0.0.1",
    headers: dict = None
) -> Request:
    """Helper to build a Starlette Request with specific client host and headers."""
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/health",
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_is_ip_trusted_helper():
    """Verify IP and CIDR matching for trusted proxies."""
    # Render internal networks
    assert is_ip_trusted("10.0.1.5", "render") is True
    assert is_ip_trusted("172.20.0.1", "render") is True
    assert is_ip_trusted("127.0.0.1", "render") is True
    assert is_ip_trusted("198.51.100.25", "render") is False

    # Explicit IP and CIDR
    assert is_ip_trusted("192.168.1.50", "192.168.1.0/24") is True
    assert is_ip_trusted("192.168.2.50", "192.168.1.0/24") is False
    assert is_ip_trusted("1.2.3.4", "1.2.3.4") is True
    assert is_ip_trusted("1.2.3.5", "1.2.3.4") is False

    # Wildcard
    assert is_ip_trusted("203.0.113.1", "*") is True


def test_direct_connection_untrusted_ignores_x_forwarded_for(monkeypatch):
    """When TRUSTED_PROXIES is not set, X-Forwarded-For must be ignored (fail-closed)."""
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    req = make_mock_request(
        client_host="198.51.100.25",
        headers={"x-forwarded-for": "1.2.3.4"}
    )
    # Must return immediate peer IP, ignoring spoofed header
    assert extract_client_ip(req) == "198.51.100.25"


def test_untrusted_peer_cannot_spoof_ip_when_trusted_proxies_configured(monkeypatch):
    """If client host is not in TRUSTED_PROXIES, forwarded headers are completely ignored."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.0/8,127.0.0.1")
    req = make_mock_request(
        client_host="203.0.113.5",  # Not in trusted list
        headers={"x-forwarded-for": "192.168.1.1"}
    )
    assert extract_client_ip(req) == "203.0.113.5"


def test_trusted_proxy_extracts_real_client_ip(monkeypatch):
    """When connection arrives from a trusted proxy, client IP is safely parsed."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.0/8")
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = make_mock_request(
        client_host="10.0.1.5",  # Trusted proxy host
        headers={"x-forwarded-for": "203.0.113.195"}
    )
    assert extract_client_ip(req) == "203.0.113.195"


def test_trusted_proxy_discards_client_spoofed_leftmost_hops(monkeypatch):
    """Traversing from right-to-left ensures client-supplied leftmost headers are discarded."""
    monkeypatch.setenv("TRUSTED_PROXIES", "render")
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    # Client sent X-Forwarded-For: 8.8.8.8, 9.9.9.9; Render proxy appended true IP 203.0.113.195
    req = make_mock_request(
        client_host="10.0.1.5",
        headers={"x-forwarded-for": "8.8.8.8, 9.9.9.9, 203.0.113.195"}
    )
    # The rightmost hop before Render is 203.0.113.195
    assert extract_client_ip(req) == "203.0.113.195"


def test_render_proxy_client_ip_preferred_when_trusted(monkeypatch):
    """Render-Proxy-Client-IP header is honored when connecting via a trusted proxy."""
    monkeypatch.setenv("TRUSTED_PROXIES", "render")
    req = make_mock_request(
        client_host="10.0.1.5",
        headers={
            "render-proxy-client-ip": "198.51.100.99",
            "x-forwarded-for": "8.8.8.8, 198.51.100.99"
        }
    )
    assert extract_client_ip(req) == "198.51.100.99"


def test_render_proxy_client_ip_ignored_when_peer_untrusted(monkeypatch):
    """Render-Proxy-Client-IP header is ignored if the peer host is untrusted."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.0/8")
    req = make_mock_request(
        client_host="192.168.1.100",  # Not trusted
        headers={"render-proxy-client-ip": "198.51.100.99"}
    )
    assert extract_client_ip(req) == "192.168.1.100"


def test_sqlite_wal_co_location():
    """Verify SQLite WAL mode is active and database operates in specified directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_wal.db"
        db = DatabaseManager(str(db_path))
        
        # Verify WAL mode is configured
        with db._get_connection() as conn:
            cursor = conn.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            assert mode.lower() == "wal"
            
        # Verify team persistence in the exact directory
        db.save_team("wal_team", DEFAULT_CONFIG, name="WAL Test")
        assert db_path.exists()
        retrieved = db.get_team("wal_team")
        assert retrieved is not None
        assert retrieved.captain == "V Kohli"


def test_sqlite_permission_error_handling(monkeypatch):
    """Verify that an unwritable path raises a clear RuntimeError."""
    # Attempt to write to a path where parent creation should fail
    unwritable_path = "/nonexistent_unwritable_directory_xyz/test.db"
    with pytest.raises(RuntimeError) as exc_info:
        DatabaseManager(unwritable_path)
    assert "Database directory creation failed" in str(exc_info.value)


from fastapi.testclient import TestClient
from app.main import app

test_client = TestClient(app)


def test_hsts_not_applied_on_spoofed_x_forwarded_proto_from_untrusted_peer(monkeypatch):
    """Direct HTTP request with spoofed X-Forwarded-Proto: https MUST NOT receive HSTS."""
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    res = test_client.get(
        "/api/health",
        headers={"x-forwarded-proto": "https"}
    )
    assert res.status_code == 200
    assert "Strict-Transport-Security" not in res.headers


def test_hsts_applied_when_direct_https():
    """Direct HTTPS connection (scheme=https) receives HSTS header."""
    https_client = TestClient(app, base_url="https://testserver")
    res = https_client.get("/api/health")
    assert res.status_code == 200
    assert "Strict-Transport-Security" in res.headers


def test_hsts_applied_from_trusted_proxy_with_forwarded_proto(monkeypatch):
    """When connecting through a trusted proxy with X-Forwarded-Proto: https, HSTS is applied."""
    # TestClient connects as 127.0.0.1 or testclient
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1,testclient")
    res = test_client.get(
        "/api/health",
        headers={"x-forwarded-proto": "https"}
    )
    assert res.status_code == 200
    assert "Strict-Transport-Security" in res.headers


def test_swagger_docs_csp_allows_cdn_and_inline_assets():
    """GET /docs must provide a CSP permitting Swagger UI assets from cdn.jsdelivr.net."""
    res = test_client.get("/docs")
    assert res.status_code == 200
    csp = res.headers.get("Content-Security-Policy", "")
    assert "cdn.jsdelivr.net" in csp
    assert "'unsafe-inline'" in csp
    assert "fastapi.tiangolo.com" in csp


def test_api_endpoints_retain_strict_csp():
    """Normal API endpoints (/api/*) must retain the strict default-src 'none' CSP."""
    res = test_client.get("/api/health")
    assert res.status_code == 200
    csp = res.headers.get("Content-Security-Policy", "")
    assert csp == "default-src 'none'; frame-ancestors 'none'"


def test_chunked_streaming_request_body_size_enforcement():
    """Oversized chunked/streamed body (> 100 KB) must be rejected with HTTP 413."""
    def chunk_generator():
        # Yield 6 chunks of 20 KB = 120 KB total
        for _ in range(6):
            yield b"x" * (20 * 1024)

    res = test_client.post(
        "/api/fantasy/scores/1",
        content=chunk_generator(),
        headers={"Transfer-Encoding": "chunked"}
    )
    assert res.status_code == 413
    assert "Payload too large" in res.json()["detail"]


def test_chunked_streaming_request_within_limit_succeeds():
    """Small chunked/streamed body (< 100 KB) is buffered and processed successfully."""
    valid_payload = b'{"selected_players":["V Kohli","JJ Bumrah","RG Sharma","HH Pandya","AR Patel","Arshdeep Singh","Q de Kock","H Klaasen","DA Miller","K Rabada","KA Maharaj"],"captain":"V Kohli","vice_captain":"JJ Bumrah"}'
    
    def small_chunk_generator():
        yield valid_payload[:50]
        yield valid_payload[50:]

    res = test_client.post(
        "/api/fantasy/scores/1",
        content=small_chunk_generator(),
        headers={"Transfer-Encoding": "chunked", "Content-Type": "application/json"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "player_scores" in data
    assert data["ball_delta"]["fantasy_team_total"] == 67.0

