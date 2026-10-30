import os
import time
from collections import defaultdict
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Load .env from backend directory or project root
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv()

from app.replay.engine import ReplayEngine
from app.ai.service import AIExplanationService
from app.api.routes import router, init_api_services
from app.scoring.ruleset import DEFAULT_RULESET

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

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Exempt health check and openapi docs from rate limiting
    if not request.url.path.startswith("/api/health") and not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi.json"):
        allowed, retry_after = limiter.check(client_ip, request.url.path)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again later."},
                headers={"Retry-After": str(retry_after)}
            )
    return await call_next(request)

# Defense-in-depth Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

    # HSTS only applied when request is over HTTPS (or x-forwarded-proto is https)
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    if is_https:
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

print(f"[BoundaryIQ] Initializing Replay Engine with: {match_data_file}")
replay_engine = ReplayEngine(str(match_data_file), ruleset=DEFAULT_RULESET)
ai_service = AIExplanationService()

# Initialize API router services
init_api_services(replay_engine, ai_service)

# Include API Router
app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Welcome to BoundaryIQ Cricket & Fantasy Engine API",
        "documentation": "/docs",
        "health": "/api/health"
    }
