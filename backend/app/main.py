import os
import time
import logging
import ipaddress
from collections import defaultdict
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("boundary_iq")

BASE_DIR = Path(__file__).resolve().parent.parent
# Load .env from backend directory or project root
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv()

from app.replay.engine import ReplayEngine
from app.ai.service import AIExplanationService
from app.api.routes import router, init_api_services
from app.scoring.ruleset import DEFAULT_RULESET
from app.db.repository import DatabaseManager

app = FastAPI(
    title="BoundaryIQ API",
    description="Cricket & Fantasy Sports Companion: Deterministic Scoring & Grounded AI Explanations",
    version="1.0.0"
)

# Hardened CORS: Explicit origin whitelist to disallow wildcard-with-credentials vulnerability
# Production origins must be explicitly passed via ALLOWED_ORIGINS (e.g. ALLOWED_ORIGINS="https://boundary-iq.vercel.app")
# Narrowly-scoped preview regex: ONLY allows boundary-iq project deployments on Vercel
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if allowed_origins_env:
    raw_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]
    allowed_origins = [o for o in raw_origins if o != "*"]
    if not allowed_origins:
        allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
else:
    # Safe local development origins only - no assumed production domains
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

# Narrowly scoped preview origin regex: strictly matches boundary-iq or boundaryiq project deployments
# Broad *.vercel.app is explicitly rejected.
allowed_origin_regex_env = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip()
if allowed_origin_regex_env:
    if allowed_origin_regex_env.lower() in ("none", "false", "0"):
        allowed_origin_regex = None
    else:
        allowed_origin_regex = allowed_origin_regex_env
else:
    # Default to strictly project-scoped preview matching
    allowed_origin_regex = r"^https:\/\/boundary-?iq(-[a-zA-Z0-9_-]+)?\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Sliding Window Rate Limiter
class SlidingWindowRateLimiter:
    def __init__(self, general_limit: int = 120, explain_limit: int = 30):
        self.general_limit = general_limit
        self.explain_limit = explain_limit
        self.general_requests = defaultdict(list)
        self.explain_requests = defaultdict(list)

    def check(self, client_ip: str, path: str) -> tuple[bool, int]:
        now = time.time()
        window = 60.0
        is_explain = "/explain" in path
        limit = self.explain_limit if is_explain else self.general_limit
        records = self.explain_requests[client_ip] if is_explain else self.general_requests[client_ip]

        cutoff = now - window
        records[:] = [ts for ts in records if ts > cutoff]

        if len(records) >= limit:
            retry_after = int(window - (now - records[0])) if records else 60
            return False, max(1, retry_after)

        records.append(now)
        return True, 0

limiter = SlidingWindowRateLimiter(
    general_limit=int(os.getenv("RATE_LIMIT_GENERAL", "120")),
    explain_limit=int(os.getenv("RATE_LIMIT_EXPLAIN", "30"))
)

# Trusted reverse proxy networks
RENDER_INTERNAL_NETWORKS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.1", "::1"]

def is_ip_trusted(client_host: str, trusted_config: str) -> bool:
    """Check whether a peer client IP is an authorized reverse proxy."""
    if not client_host or not trusted_config:
        return False

    normalized = trusted_config.lower().strip()
    if normalized == "*":
        return True

    trusted_entries = [e.strip() for e in trusted_config.split(",") if e.strip()]
    if "render" in trusted_entries:
        trusted_entries.remove("render")
        trusted_entries.extend(RENDER_INTERNAL_NETWORKS)

    # Allow exact string match for hostnames (e.g. "localhost", "testclient")
    if client_host in trusted_entries:
        return True

    try:
        ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False

    for entry in trusted_entries:
        try:
            if "/" in entry:
                if ip in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if ip == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue
    return False

def extract_client_ip(request: Request) -> str:
    """
    Safely extract the client IP address.

    Security Guarantee:
    1. Direct requests (untrusted peers) NEVER trust X-Forwarded-For or Render headers (prevents IP spoofing).
    2. Only requests originating from configured TRUSTED_PROXIES (e.g. Render edge proxy) may supply forwarded headers.
    3. Traverses X-Forwarded-For from right to left based on TRUSTED_PROXY_COUNT, discarding client-injected leftmost values.
    4. Render-Proxy-Client-IP is respected only when connecting through a trusted proxy.
    """
    peer_ip = request.client.host if request.client else "127.0.0.1"
    trusted_proxies_cfg = os.getenv("TRUSTED_PROXIES", "").strip()

    # Fail-closed: If trusted proxies are not configured or peer is not trusted, use peer_ip directly.
    if not trusted_proxies_cfg or not is_ip_trusted(peer_ip, trusted_proxies_cfg):
        return peer_ip

    # Peer is a trusted reverse proxy:
    # Check Render-Proxy-Client-IP first (Render's canonical client IP header)
    render_client_ip = request.headers.get("render-proxy-client-ip")
    if render_client_ip:
        render_client_ip = render_client_ip.strip()
        try:
            ipaddress.ip_address(render_client_ip)
            return render_client_ip
        except ValueError:
            pass

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer_ip

    raw_ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
    if not raw_ips:
        return peer_ip

    # Safe right-to-left traversal:
    # A single reverse proxy tier (Render) appends the true client IP to the end.
    # Therefore, ips[-1] is the client that connected to Render, while ips[0] is client-supplied and untrusted.
    try:
        proxy_count = max(1, int(os.getenv("TRUSTED_PROXY_COUNT", "1")))
    except ValueError:
        proxy_count = 1

    hop_index = max(0, len(raw_ips) - proxy_count)
    selected_ip = raw_ips[hop_index]

    try:
        ipaddress.ip_address(selected_ip)
        return selected_ip
    except ValueError:
        return peer_ip

MAX_REQUEST_BODY_SIZE = 100 * 1024  # 100 KB

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Enforce 100 KB request body limit (Content-Length header & chunked streaming)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload too large. Maximum request size is 100 KB."}
                )
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header."}
            )
    elif request.method in ("POST", "PUT", "PATCH"):
        # Guard chunked transfer encoding or missing content-length by incrementally reading stream
        chunks = []
        bytes_read = 0
        async for chunk in request.stream():
            bytes_read += len(chunk)
            if bytes_read > MAX_REQUEST_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload too large. Maximum request size is 100 KB."}
                )
            chunks.append(chunk)
        request._body = b"".join(chunks)

    # Secure proxy-safe IP extraction
    client_ip = extract_client_ip(request)

    # Exempt health, readiness, and openapi docs from rate limiting
    exempt_paths = ("/api/health", "/api/ready", "/docs", "/redoc", "/openapi.json")
    if not any(request.url.path.startswith(p) for p in exempt_paths):
        allowed, retry_after = limiter.check(client_ip, request.url.path)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again later."},
                headers={"Retry-After": str(retry_after)}
            )
    return await call_next(request)

# Global Unhandled Error Handler to prevent stack trace leakage in production
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# Defense-in-depth Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    # Narrowly scoped CSP: allow CDN assets for Swagger / Redoc UI; default-src 'none' for API
    req_path = request.url.path
    if req_path in ("/docs", "/redoc", "/openapi.json"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

    # HSTS only applied when request is genuinely over HTTPS
    # (Direct TLS or verified X-Forwarded-Proto from an authenticated trusted proxy)
    peer_ip = request.client.host if request.client else "127.0.0.1"
    trusted_proxies_cfg = os.getenv("TRUSTED_PROXIES", "").strip()
    is_direct_https = request.url.scheme == "https"
    is_trusted_proxy_https = (
        bool(trusted_proxies_cfg)
        and is_ip_trusted(peer_ip, trusted_proxies_cfg)
        and request.headers.get("x-forwarded-proto") == "https"
    )
    if is_direct_https or is_trusted_proxy_https:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# Locate Cricsheet JSON Match File
BASE_DIR = Path(__file__).resolve().parent.parent
POSSIBLE_PATHS = [
    BASE_DIR / "data" / "ind_sa_t20wc_2024_final.json",
    BASE_DIR.parent / "data" / "ind_sa_t20wc_2024_final.json",
    BASE_DIR / "data" / "match_1298150.json",
    BASE_DIR.parent / "data" / "match_1298150.json",
]

match_data_file = None
for p in POSSIBLE_PATHS:
    if p.exists():
        match_data_file = p
        break

if not match_data_file:
    raise FileNotFoundError(
        "Cricsheet match file 'data/ind_sa_t20wc_2024_final.json' not found."
    )

logger.info(f"Initializing Replay Engine with match data: {match_data_file}")
replay_engine = ReplayEngine(str(match_data_file), ruleset=DEFAULT_RULESET)
ai_service = AIExplanationService()
db_manager = DatabaseManager()

# Initialize API router services with persistent DB
init_api_services(replay_engine, ai_service, db_manager)

# Include API Router
app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Welcome to BoundaryIQ Cricket & Fantasy Engine API",
        "documentation": "/docs",
        "health": "/api/health"
    }
