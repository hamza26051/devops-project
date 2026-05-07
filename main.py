from fastapi import FastAPI, Body, Header, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import requests
import urllib.parse
import time
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from config import settings
from risk_engine import RiskScoringEngine
from fastapi.middleware.cors import CORSMiddleware

# ── Auth / Firebase ───────────────────────────────────────────────────
try:
    from jose import jwt, JWTError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None
    JWTError = Exception

try:
    from firebase_admin import auth as firebase_auth
    FIREBASE_AUTH_AVAILABLE = True
except ImportError:
    FIREBASE_AUTH_AVAILABLE = False
    firebase_auth = None

from firebase_service import (
    create_analysis_record,
    get_all_records,
    get_record,
    get_record_by_result_id,
    update_record,
    get_user_records,
    create_notification,
    get_user_notifications,
    mark_notification_read,
    get_unread_count,
)

# ── Admin JWT Config ────────────────────────────────────────────────
ADMIN_USERNAME = settings.ADMIN_USERNAME
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

def _create_admin_token() -> str:
    if not JWT_AVAILABLE:
        raise RuntimeError("python-jose not installed")
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": "admin", "role": "admin", "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)

def _verify_admin_token(token: str) -> Optional[dict]:
    if not JWT_AVAILABLE or not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "admin":
            return None
        return payload
    except (JWTError, Exception):
        return None

async def admin_auth_dependency(x_admin_token: str = Header(...)):
    payload = _verify_admin_token(x_admin_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    return payload

async def firebase_user_auth(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    if not FIREBASE_AUTH_AVAILABLE:
        return None
    id_token = authorization.split("Bearer ")[1]
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except Exception:
        return None

app = FastAPI()

# Add CORS middleware to allow frontend to fetch data
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8081",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No more in-memory store. We use Firestore exclusively for persistence.

# Initialize Risk Engine
risk_engine = RiskScoringEngine()

# ================== MASTODON CREDENTIALS ==================
MASTODON_INSTANCE = settings.MASTODON_INSTANCE
CLIENT_ID = settings.MASTODON_CLIENT_ID
CLIENT_SECRET = settings.MASTODON_CLIENT_SECRET
REDIRECT_URI = settings.MASTODON_REDIRECT_URI

# ================== HEALTH CHECK ==================
@app.get("/health")
def health_check():
    """Required by Docker HEALTHCHECK and load balancer liveness probes."""
    try:
        if risk_engine is None or not hasattr(risk_engine, "sent_pipe"):
            return JSONResponse(status_code=503, content={"status": "unhealthy", "reason": "Risk engine not initialized"})
        return {"status": "healthy", "mode": settings.MODEL_MODE, "env": settings.APP_ENV}
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "reason": str(exc)})


# ================== LOGIN PAGE ==================
@app.get("/login/mastodon", response_class=HTMLResponse)
def login_page():
    html = """
    <html>
    <head>
        <title>Login with Mastodon | VeriDrive</title>
        <style>
            :root {
                --ember: oklch(0.68 0.19 38);
                --background: #050505;
                --card: #0a0a0a;
            }
            body { 
                background: var(--background); 
                color: white; 
                font-family: 'Inter', -apple-system, sans-serif; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                height: 100vh; 
                margin: 0; 
                overflow: hidden;
            }
            /* Slideshow Simulation */
            .slideshow {
                position: fixed;
                inset: 0;
                z-index: -1;
            }
            .slide {
                position: absolute;
                inset: 0;
                background-size: cover;
                background-position: center;
                opacity: 0;
                animation: fade 15s infinite;
                filter: brightness(0.3) saturate(0.8);
            }
            .slide:nth-child(1) { background-image: url('https://images.unsplash.com/photo-1617788138017-80ad40651399?q=80&w=2070'); animation-delay: 0s; }
            .slide:nth-child(2) { background-image: url('https://images.unsplash.com/photo-1603584173870-7f3ca936a23f?q=80&w=2069'); animation-delay: 5s; }
            .slide:nth-child(3) { background-image: url('https://images.unsplash.com/photo-1552519507-da3b142c6e3d?q=80&w=2070'); animation-delay: 10s; }
            
            @keyframes fade {
                0%, 33% { opacity: 1; }
                40%, 100% { opacity: 0; }
            }

            .overlay {
                position: fixed;
                inset: 0;
                background: radial-gradient(circle at center, transparent 0%, var(--background) 100%);
                z-index: 0;
            }

            .card { 
                position: relative;
                z-index: 10;
                background: rgba(10, 10, 10, 0.8); 
                padding: 60px 40px; 
                border-radius: 32px; 
                text-align: center; 
                border: 1px solid rgba(255, 255, 255, 0.1); 
                backdrop-blur: 20px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                max-width: 400px;
                width: 90%;
            }
            
            .logo-mark {
                width: 48px;
                height: 48px;
                background: linear-gradient(135deg, var(--ember), #ff8700);
                border-radius: 12px;
                margin: 0 auto 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 0 20px var(--ember);
            }
            .logo-dot {
                width: 12px;
                height: 12px;
                background: white;
                border-radius: 50%;
            }

            h2 { 
                font-size: 32px; 
                margin: 0 0 12px; 
                font-weight: 800;
                letter-spacing: -0.02em;
            }
            p { 
                color: #a1a1aa; 
                margin-bottom: 40px; 
                font-size: 15px;
                line-height: 1.5;
            }
            
            .btn { 
                display: inline-flex;
                align-items: center;
                gap: 12px;
                background: linear-gradient(135deg, var(--ember), #ff8700); 
                border: none; 
                padding: 18px 36px; 
                color: white; 
                font-weight: 700; 
                border-radius: 100px; 
                cursor: pointer; 
                font-size: 16px; 
                text-decoration: none;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 10px 20px -5px var(--ember);
            }
            .btn:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 20px 30px -10px var(--ember);
            }
            .btn:active { transform: translateY(0); }
        </style>
    </head>
    <body>
        <div class="slideshow">
            <div class="slide"></div>
            <div class="slide"></div>
            <div class="slide"></div>
        </div>
        <div class="overlay"></div>
        
        <div class="card">
            <div class="logo-mark">
                <div class="logo-dot"></div>
            </div>
            <h2>Mastodon Access</h2>
            <p>Connect your profile to generate your AI-powered VeriDrive Risk Intelligence report.</p>
            <a href="/mastodon/start" class="btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                   <path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309-2.723.4-4.99 2.426-5.304 5.004-.314 2.578-.34 5.405-.34 5.405s.026 2.827.34 5.405c.314 2.578 2.581 4.61 5.304 5.004.453.067 1.308.309 5.288.309h.03c3.98 0 5.697-.242 6.15-.309 2.687-.394 4.954-2.426 5.304-5.004.314-2.578.34-5.405.34-5.405s-.026-2.827-.34-5.405zm-4.337 9.537c0 .542-.44.982-.982.982H6.464c-.542 0-.982-.44-.982-.982V6.464c0-.542.44-.982.982-.982h11.485c.542 0 .982.44.982.982v8.386z"/>
                </svg>
                Authorize with Mastodon
            </a>
        </div>
    </body>
    </html>
    """
    return html


@app.get("/mastodon/start")
def start_login():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read",
        "force_login": "true"
    }
    url = f"{MASTODON_INSTANCE}/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@app.get("/auth/mastodon/callback")
def callback(code: str, state: str = None):
    # Ensure redirect_uri matches EXACTLY what was sent in the first step
    token_resp = requests.post(
        f"{MASTODON_INSTANCE}/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "code": code,
            "scope": "read"
        }
    )
    
    if token_resp.status_code != 200:
        return JSONResponse({"error": f"Failed to get access token: {token_resp.text}"}, status_code=400)

    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return JSONResponse({"error": "No access token received"}, status_code=400)

    headers = {"Authorization": f"Bearer {access_token}"}

    # Get User Profile
    user_resp = requests.get(
        f"{MASTODON_INSTANCE}/api/v1/accounts/verify_credentials", 
        headers=headers
    )
    
    if user_resp.status_code != 200:
        return JSONResponse({"error": "Failed to fetch user profile"}, status_code=400)
    
    user = user_resp.json()

    # START ANALYSIS TIMER
    start_time = time.time()

    # Get User's Recent Posts (10 latest, excluding replies)
    posts_resp = requests.get(
        f"{MASTODON_INSTANCE}/api/v1/accounts/{user['id']}/statuses",
        headers=headers,
        params={
            "limit": 10, 
            "exclude_replies": "true",
            "exclude_reblogs": "false"
        }
    )
    
    raw_posts = posts_resp.json()
    posts_text = [p.get("content", "") for p in raw_posts]
    user_bio = user.get("note", "")

    # RUN RISK ANALYSIS
    analysis_result = risk_engine.analyze_user_profile(posts_text, bio=user_bio)
    
    if "error" in analysis_result:
        return JSONResponse({"error": analysis_result["error"]}, status_code=400)

    # Calculate Latency
    latency = analysis_result.get("engine_latency", "0s")

    # Account Age Calculation
    try:
        created_at = datetime.strptime(user.get("created_at"), "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        created_at = datetime.strptime(user.get("created_at").split('.')[0], "%Y-%m-%dT%H:%M:%S")
        
    account_age_days = (datetime.now() - created_at).days

    posts = []
    for p in raw_posts:
        clean_text = re.sub(r'<[^>]*>', '', p.get("content", ""))
        posts.append({
            "id": p.get("id"),
            "text": clean_text,
            "created_at": p.get("created_at"),
            "favourites": p.get("favourites_count"),
            "reblogs": p.get("reblogs_count"),
            "replies": p.get("replies_count"),
            "visibility": p.get("visibility"),
            "url": p.get("url")
        })

    # Determine status based on decision
    ai_decision = analysis_result["decision"]
    if ai_decision.startswith("APPROVE"):
        status = "AUTO_APPROVED"
    elif ai_decision.startswith("REJECT") or ai_decision.startswith("DECLINE"):
        status = "AUTO_DECLINED"
    else:
        status = "NEEDS_REVIEW"

    result_data = {
        "status": "success",
        "platform": "Mastodon",
        "analysis": {
            "decision": ai_decision,
            "risk_score": int(analysis_result["final_risk_score"] * 100),
            "confidence": f"{int(analysis_result['final_confidence'] * 100)}%",
            "latency": f"{latency}s",
            "reasons": analysis_result["reasons"],
            "status_color": analysis_result["status_color"]
        },
        "user": {
            "username": user.get("username"),
            "display_name": user.get("display_name"),
            "bio": re.sub(r'<[^>]*>', '', user.get("note", "")),
            "avatar": user.get("avatar"),
            "followers": user.get("followers_count"),
            "following": user.get("following_count"),
            "total_posts": user.get("statuses_count"),
            "account_age": f"{account_age_days}d",
            "ff_ratio": round(user.get("followers_count") / max(1, user.get("following_count")), 2)
        },
        "recent_posts": posts
    }

    result_id = str(uuid.uuid4())

    # Save to Firestore so Admins can review it and CT loop can use it!
    # We store the FULL result structure here so it can be reconstructed
    record_id = create_analysis_record({
        "user_id": f"mastodon-{user.get('id')}",
        "user_email": "anonymous@mastodon",
        "user_display_name": user.get("display_name") or user.get("username"),
        "source": "mastodon_auth",
        "posts": posts_text,
        "bio": user_bio,
        "ai_result": analysis_result,
        "status": status,
        "admin_review": None,
        "frontend_result_id": result_id,
        "full_result": result_data # Store the full object for easy reconstruction
    })
    
    if record_id:
        result_data["firestore_record_id"] = record_id

    # Direct redirect to frontend
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/analyze?id={result_id}")

@app.get("/get_analysis/{result_id}")
def get_analysis(result_id: str):
    # Fetch from Firestore (persistence)
    # This allows users to view results even if the server was restarted
    record = get_record_by_result_id(result_id)
    if record:
        # If we stored the full_result, use it!
        if "full_result" in record:
            res = record["full_result"]
            res["firestore_record_id"] = record.get("id")
            return res

        # Fallback reconstruction logic
        user_data = {
            "username": record.get("user_id", "").replace("mastodon-", ""),
            "display_name": record.get("user_display_name", "User"),
            "bio": record.get("bio", ""),
            "avatar": None, 
            "followers": None,
            "following": None,
            "total_posts": len(record.get("posts", [])),
            "account_age": None,
            "ff_ratio": None,
        }
        
        posts_data = []
        for i, text in enumerate(record.get("posts", [])):
            posts_data.append({
                "id": f"rec-{i}",
                "text": text,
            })
            
        return {
            "status": "success",
            "analysis": record.get("ai_result"),
            "user": user_data,
            "recent_posts": posts_data,
            "firestore_record_id": record.get("id")
        }
        
    return JSONResponse({"error": "Result not found"}, status_code=404)


# ══════════════════════════════════════════════════════════════════════
# MANUAL ENTRY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@app.post("/analyze/manual/text")
def analyze_manual_text(payload: dict = Body(...)):
    """Accept manual text posts (max 10) and optional bio for analysis."""
    posts = payload.get("posts", [])
    bio = payload.get("bio", "")

    if not isinstance(posts, list):
        return JSONResponse({"error": "posts must be an array"}, status_code=400)
    if len(posts) == 0:
        return JSONResponse({"error": "At least one post is required"}, status_code=400)
    if len(posts) > 10:
        posts = posts[:10]

    cleaned_posts = [p.strip() for p in posts if p.strip()]
    user_bio = bio.strip()

    # RUN RISK ANALYSIS
    analysis_result = risk_engine.analyze_user_profile(cleaned_posts, bio=user_bio)
    
    if "error" in analysis_result:
        return JSONResponse({"error": analysis_result["error"]}, status_code=400)

    latency = analysis_result.get("engine_latency", 0)

    posts_data = []
    for i, text in enumerate(cleaned_posts):
        posts_data.append({
            "id": f"manual-{i+1}",
            "text": text,
            "created_at": None,
            "favourites": None,
            "reblogs": None,
            "replies": None,
            "visibility": None,
            "url": None,
        })

    result_data = {
        "status": "success",
        "platform": "Manual",
        "mode": "text",
        "analysis": {
            "decision": analysis_result["decision"],
            "risk_score": int(analysis_result["final_risk_score"] * 100),
            "confidence": f"{int(analysis_result['final_confidence'] * 100)}%",
            "latency": f"{latency}s",
            "reasons": analysis_result["reasons"],
            "status_color": analysis_result["status_color"],
        },
        "user": {
            "username": "manual-user",
            "display_name": "Manual Entry",
            "bio": user_bio,
            "avatar": None,
            "followers": None,
            "following": None,
            "total_posts": len(cleaned_posts),
            "account_age": None,
            "ff_ratio": None,
        },
        "recent_posts": posts_data,
    }

    result_id = str(uuid.uuid4())
    
    # Pre-build full result for storage
    full_result = {
        "status": "success",
        "platform": "ManualEntry",
        "mode": "text",
        "analysis": result_data["analysis"],
        "user": {
            "username": "manual-entry",
            "display_name": "Manual Analysis",
            "bio": user_bio,
            "avatar": None,
            "followers": None,
            "following": None,
            "total_posts": len(cleaned_posts),
            "account_age": None,
            "ff_ratio": None,
        },
        "recent_posts": result_data["recent_posts"],
        "frontend_result_id": result_id
    }

    # Save to Firestore for persistence (MANDATORY)
    record_id = create_analysis_record({
        "user_id": "manual-user",
        "user_email": "manual@veridrive",
        "user_display_name": "Manual Entry",
        "source": "manual_text",
        "posts": cleaned_posts,
        "bio": user_bio,
        "ai_result": result_data["analysis"],
        "status": "MANUAL_ENTRY",
        "admin_review": None,
        "frontend_result_id": result_id,
        "full_result": full_result
    })
    
    return {"result_id": result_id}


# ══════════════════════════════════════════════════════════════════════
# AUTHENTICATED USER & ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

def _run_analysis_and_build_result(posts: List[str], bio: str = ""):
    cleaned_posts = [p.strip() for p in posts if p.strip()]
    user_bio = bio.strip()
    analysis_result = risk_engine.analyze_user_profile(cleaned_posts, bio=user_bio)
    
    if "error" in analysis_result:
        raise HTTPException(status_code=400, detail=analysis_result["error"])

    latency = analysis_result.get("engine_latency", 0)

    posts_data = []
    for i, text in enumerate(cleaned_posts):
        posts_data.append({
            "id": f"manual-{i+1}",
            "text": text,
            "created_at": None,
            "favourites": None,
            "reblogs": None,
            "replies": None,
            "visibility": None,
            "url": None,
        })

    ai_decision = analysis_result["decision"]
    if ai_decision.startswith("APPROVE"):
        status = "AUTO_APPROVED"
    elif ai_decision.startswith("REJECT") or ai_decision.startswith("DECLINE"):
        status = "AUTO_DECLINED"
    else:
        status = "NEEDS_REVIEW"

    return {
        "analysis": {
            "decision": ai_decision,
            "risk_score": int(analysis_result["final_risk_score"] * 100),
            "confidence": f"{int(analysis_result['final_confidence'] * 100)}%",
            "latency": f"{latency}s",
            "reasons": analysis_result["reasons"],
            "status_color": analysis_result["status_color"],
        },
        "recent_posts": posts_data,
        "status": status,
    }


# ── Admin Auth ──────────────────────────────────────────────────────

@app.post("/admin/login")
def admin_login(payload: dict = Body(...)):
    username = payload.get("username", "")
    password = payload.get("password", "")
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not JWT_AVAILABLE:
        raise HTTPException(status_code=500, detail="JWT library not available")
    token = _create_admin_token()
    return {"token": token, "role": "admin"}


@app.get("/admin/records")
def admin_get_records(_=Depends(admin_auth_dependency)):
    records = get_all_records()
    return {"records": records}


@app.post("/admin/records/{record_id}/decide")
def admin_decide(record_id: str, payload: dict = Body(...), _=Depends(admin_auth_dependency)):
    decision = payload.get("decision")
    notes = payload.get("notes", "")
    if decision not in ("APPROVE", "DECLINE"):
        raise HTTPException(status_code=400, detail="Decision must be APPROVE or DECLINE")

    record = get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    status = "ADMIN_APPROVED" if decision == "APPROVE" else "ADMIN_DECLINED"
    updated = update_record(record_id, {
        "status": status,
        "admin_review": {
            "decision": decision,
            "notes": notes,
            "reviewed_by": "admin",
            "reviewed_at": datetime.utcnow().isoformat(),
        },
    })
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update record")

    user_id = record.get("user_id")
    if user_id:
        msg = f"Your rental request has been {('approved' if decision == 'APPROVE' else 'declined')} by the admin."
        create_notification({
            "user_id": user_id,
            "record_id": record_id,
            "message": msg,
            "type": "ADMIN_DECISION",
            "decision": decision,
        })

    return {"success": True, "status": status}


@app.post("/admin/overrides")
def admin_submit_override(payload: dict = Body(...), _=Depends(admin_auth_dependency)):
    """Admin endpoint to submit a human override directly to Firestore."""
    from firebase_service import submit_human_override
    
    tweet = payload.get("tweet")
    label = payload.get("class") # 0=Hate, 1=Offensive, 2=Neither
    
    if tweet is None or label is None:
        raise HTTPException(status_code=400, detail="Missing tweet or class")
        
    override_id = submit_human_override({
        "tweet": tweet,
        "class": label,
        "source": "admin_manual"
    })
    
    if not override_id:
        raise HTTPException(status_code=500, detail="Failed to save override")
        
    return {"success": True, "override_id": override_id}


# ── User Analysis ───────────────────────────────────────────────────

@app.post("/user/analyze")
def user_analyze(payload: dict = Body(...), user=Depends(firebase_user_auth)):
    posts = payload.get("posts", [])
    bio = payload.get("bio", "")

    if not isinstance(posts, list):
        raise HTTPException(status_code=400, detail="posts must be an array")
    if len(posts) == 0:
        raise HTTPException(status_code=400, detail="At least one post is required")
    if len(posts) > 10:
        posts = posts[:10]

    result = _run_analysis_and_build_result(posts, bio)
    result_id = str(uuid.uuid4())

    # Build the full result object that the frontend expects
    full_result = {
        "status": "success",
        "platform": "UserSubmitted",
        "mode": "text",
        "analysis": result["analysis"],
        "user": {
            "username": user.get("name", user.get("email", "anonymous").split('@')[0]) if user else "anonymous",
            "display_name": user.get("name", user.get("email", "Anonymous")) if user else "Anonymous",
            "bio": bio.strip(),
            "avatar": None,
            "followers": None,
            "following": None,
            "total_posts": len(posts),
            "account_age": None,
            "ff_ratio": None,
        },
        "recent_posts": result["recent_posts"],
        "frontend_result_id": result_id
    }

    # Save to Firestore for persistence
    record_id = create_analysis_record({
        "user_id": user.get("uid") if user else "anonymous",
        "user_email": user.get("email", "") if user else "anonymous",
        "user_display_name": user.get("name", "") if user else "Anonymous",
        "source": "user_submitted",
        "posts": posts,
        "bio": bio.strip(),
        "ai_result": result["analysis"],
        "status": result["status"],
        "admin_review": None,
        "frontend_result_id": result_id,
        "full_result": full_result
    })
    
    if record_id:
        full_result["firestore_record_id"] = record_id

    return {"result_id": result_id, "status": result["status"]}


# ── User Records & Notifications ────────────────────────────────────

@app.get("/user/records")
def user_get_records(user=Depends(firebase_user_auth)):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    records = get_user_records(user["uid"])
    return {"records": records}


@app.get("/user/notifications")
def user_get_notifications(user=Depends(firebase_user_auth)):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    notifications = get_user_notifications(user["uid"])
    unread = get_unread_count(user["uid"])
    return {"notifications": notifications, "unread_count": unread}


@app.post("/user/notifications/{notification_id}/read")
def user_mark_read(notification_id: str, user=Depends(firebase_user_auth)):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    success = mark_notification_read(notification_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to mark as read")
    return {"success": True}
