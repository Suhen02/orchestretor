# import json
# import os

# import httpx
# import pandas as pd
# import streamlit as st


# API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


# st.set_page_config(page_title="User Dashboard", layout="wide")
# st.markdown(
#     """
#     <style>
#     .stApp { background: #fbfcf8; }
#     section[data-testid="stSidebar"] { background: #063b36; }
#     section[data-testid="stSidebar"] * { color: #f8fafc; }
#     div[data-testid="stMetric"] {
#         background: #ffffff;
#         border-left: 6px solid #16a34a;
#         padding: 16px;
#         border-radius: 8px;
#         box-shadow: 0 1px 8px rgba(6, 59, 54, 0.10);
#     }
#     .block-container { padding-top: 2rem; }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# if "user_token" not in st.session_state:
#     st.session_state.user_token = ""
# if "user_email" not in st.session_state:
#     st.session_state.user_email = ""


# def api_request(method: str, path: str, **kwargs):
#     headers = kwargs.pop("headers", {})
#     if st.session_state.user_token:
#         headers["Authorization"] = f"Bearer {st.session_state.user_token}"
#     response = httpx.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=20, **kwargs)
#     response.raise_for_status()
#     return response.json()


# def login_user(email: str, password: str) -> None:
#     response = httpx.post(
#         f"{API_BASE_URL}/auth/login",
#         json={"email": email, "password": password},
#         timeout=20,
#     )
#     response.raise_for_status()
#     st.session_state.user_token = response.json()["access_token"]
#     me = api_request("GET", "/auth/me")
#     st.session_state.user_email = me["email"]


# def logout() -> None:
#     st.session_state.user_token = ""
#     st.session_state.user_email = ""
#     st.rerun()


# with st.sidebar:
#     st.title("Jobs")
#     if st.session_state.user_token:
#         st.caption(st.session_state.user_email)
#         page = st.radio("Pages", ["Dashboard", "Submit Job", "Job Details", "Account"])
#     else:
#         page = st.radio("Pages", ["Login", "Registration"])

# if page == "Login":
#     st.title("Login")
#     email = st.text_input("Email")
#     password = st.text_input("Password", type="password")
#     if st.button("Login", type="primary"):
#         try:
#             login_user(email, password)
#             st.rerun()
#         except Exception as exc:
#             st.error(f"Login failed: {exc}")
#     st.stop()

# if page == "Registration":
#     st.title("Registration")
#     email = st.text_input("Email")
#     password = st.text_input("Password", type="password")
#     if st.button("Create account", type="primary"):
#         try:
#             httpx.post(
#                 f"{API_BASE_URL}/auth/register",
#                 json={"email": email, "password": password},
#                 timeout=20,
#             ).raise_for_status()
#             st.success("Account created. Open Login from the sidebar.")
#         except Exception as exc:
#             st.error(f"Registration failed: {exc}")
#     st.stop()

# if not st.session_state.user_token:
#     st.stop()

# if page == "Dashboard":
#     st.title("My Job Dashboard")
#     jobs = api_request("GET", "/jobs")
#     total = len(jobs)
#     completed = len([job for job in jobs if job["status"] == "COMPLETED"])
#     running = len([job for job in jobs if job["status"] in {"ASSIGNED", "RUNNING", "RETRYING"}])
#     failed = len([job for job in jobs if job["status"] in {"FAILED", "DEAD"}])

#     cards = st.columns(4)
#     cards[0].metric("My jobs", total)
#     cards[1].metric("Completed", completed)
#     cards[2].metric("Active", running)
#     cards[3].metric("Needs attention", failed)

#     if jobs:
#         df = pd.DataFrame(jobs)
#         left, right = st.columns([1, 2])
#         with left:
#             st.subheader("Status")
#             st.bar_chart(df["status"].value_counts())
#         with right:
#             st.subheader("Recent activity")
#             visible = ["id", "type", "status", "priority", "retry_count", "created_at"]
#             st.dataframe(df[visible].head(10), use_container_width=True, hide_index=True)
#     else:
#         st.info("No jobs yet. Submit your first job from the sidebar.")

# elif page == "Submit Job":
#     st.title("Submit Job")
#     job_type = st.selectbox("Job type", ["resume_analysis", "pdf_summary", "email_send"])
#     priority = st.select_slider(
#         "Priority",
#         options=[1, 2, 3],
#         value=2,
#         format_func=lambda value: {1: "High", 2: "Medium", 3: "Low"}[value],
#     )
#     max_retries = st.number_input("Max retries", min_value=0, max_value=10, value=3)

#     payload = {}
#     if job_type == "resume_analysis":
#         st.subheader("Resume Analysis")
#         resume_text = st.text_area("Resume text", height=220)
#         file_path = st.text_input("Resume file path")
#         payload = {"text": resume_text} if resume_text else {"file_path": file_path}
#     elif job_type == "pdf_summary":
#         st.subheader("PDF Summary")
#         payload = {
#             "file_path": st.text_input("PDF file path"),
#             "max_length": st.number_input("Max summary length", min_value=50, max_value=1000, value=220),
#         }
#     elif job_type == "email_send":
#         st.subheader("Email Send")
#         payload = {
#             "to": st.text_input("To"),
#             "subject": st.text_input("Subject"),
#             "body": st.text_area("Body", height=180),
#         }

#     with st.expander("Advanced JSON payload"):
#         raw_payload = st.text_area("Payload", json.dumps(payload, indent=2), height=180)

#     if st.button("Submit job", type="primary"):
#         try:
#             job = api_request(
#                 "POST",
#                 "/jobs",
#                 json={
#                     "type": job_type,
#                     "priority": priority,
#                     "max_retries": max_retries,
#                     "payload": json.loads(raw_payload),
#                 },
#             )
#             st.success(f"Job queued: {job['id']}")
#         except Exception as exc:
#             st.error(f"Job submission failed: {exc}")

# elif page == "Job Details":
#     st.title("Job Details")
#     jobs = api_request("GET", "/jobs")
#     if not jobs:
#         st.info("No jobs available.")
#         st.stop()

#     df = pd.DataFrame(jobs)
#     visible = ["id", "type", "status", "priority", "retry_count", "worker_id", "created_at"]
#     st.dataframe(df[visible], use_container_width=True, hide_index=True)

#     selected_job_id = st.selectbox("Select job", df["id"].tolist())
#     selected = next(job for job in jobs if job["id"] == selected_job_id)

#     actions = st.columns(3)
#     if actions[0].button("Refresh"):
#         st.rerun()
#     if actions[1].button("Cancel queued job"):
#         try:
#             api_request("DELETE", f"/jobs/{selected_job_id}")
#             st.success("Cancel request sent.")
#             st.rerun()
#         except Exception as exc:
#             st.error(f"Cancel failed: {exc}")
#     if actions[2].button("Retry failed job"):
#         try:
#             api_request("POST", f"/jobs/{selected_job_id}/retry")
#             st.success("Retry request sent.")
#             st.rerun()
#         except Exception as exc:
#             st.error(f"Retry failed: {exc}")

#     st.subheader("Result")
#     st.json(selected.get("result") or {})
#     st.subheader("Lifecycle logs")
#     try:
#         logs = api_request("GET", f"/jobs/{selected_job_id}/logs")
#         st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
#     except Exception as exc:
#         st.warning(f"Unable to load logs: {exc}")

# elif page == "Account":
#     st.title("Account")
#     st.write(f"Signed in as **{st.session_state.user_email}**")
#     if st.button("Logout", type="primary"):
#         logout()


"""
dashboard/user_app.py
Production-grade User Dashboard for the Job Orchestration Platform.

Features:
- Registration and login with clear validation feedback
- Job dashboard with per-status counts and auto-refresh
- Job submission form with type-specific payload builders + validation
- Job detail page: status, result, lifecycle logs, cancel/retry actions
- Clean empty states with actionable guidance
- Full error handling
"""

import json
import os
import time
from datetime import datetime

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
AUTO_REFRESH_SECONDS = 15

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Orchestrator · Jobs",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #0f1117; color: #e2e8f0; }

    section[data-testid="stSidebar"] {
        background: #0a0d14;
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] * { color: #94a3b8 !important; }

    div[data-testid="stMetric"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-top: 3px solid #10b981;
        padding: 18px 22px;
        border-radius: 8px;
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.05em; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.7rem !important; font-weight: 700; }

    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.15s;
    }
    .stButton > button[kind="primary"] { background: #059669; border: none; color: #fff; }
    .stButton > button[kind="primary"]:hover { background: #047857; }

    .stDataFrame { border: 1px solid #1e293b; border-radius: 8px; }

    .status-pill {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .pill-completed { background: #14532d; color: #86efac; }
    .pill-running   { background: #1e3a5f; color: #7dd3fc; }
    .pill-queued    { background: #292524; color: #d6d3d1; }
    .pill-failed    { background: #450a0a; color: #fca5a5; }
    .pill-dead      { background: #3b0764; color: #d8b4fe; }
    .pill-retrying  { background: #431407; color: #fdba74; }
    .pill-cancelled { background: #1c1917; color: #78716c; }
    .pill-assigned  { background: #1e3a5f; color: #93c5fd; }

    .section-header {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #475569;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1e293b;
    }
    .block-container { padding: 2rem 2rem 2rem; max-width: 1200px; }

    .empty-state {
        text-align: center;
        padding: 48px 24px;
        color: #475569;
    }
    .empty-state h3 { color: #64748b; font-size: 1.1rem; margin-bottom: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("user_token", ""),
    ("user_email", ""),
    ("last_refresh", 0.0),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── API helpers ───────────────────────────────────────────────────────────────

def api(method: str, path: str, silent: bool = False, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.user_token:
        headers["Authorization"] = f"Bearer {st.session_state.user_token}"
    try:
        r = httpx.request(
            method, f"{API_BASE_URL}{path}",
            headers=headers, timeout=15, **kwargs,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        if not silent:
            detail = e.response.json().get("detail", e.response.text) if e.response.headers.get("content-type", "").startswith("application/json") else e.response.text
            st.error(f"Error {e.response.status_code}: {detail}")
        return None
    except httpx.RequestError:
        if not silent:
            st.error(f"Cannot reach the API. Is the server running?")
        return None


def login_user(email: str, password: str) -> None:
    try:
        r = httpx.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", "Login failed") if "application/json" in e.response.headers.get("content-type", "") else "Invalid credentials"
        raise ValueError(detail)
    except httpx.RequestError:
        raise ConnectionError("Cannot reach the API.")

    st.session_state.user_token = r.json()["access_token"]
    me = httpx.get(
        f"{API_BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {st.session_state.user_token}"},
        timeout=15,
    ).json()
    st.session_state.user_email = me.get("email", email)


def register_user(email: str, password: str) -> None:
    try:
        r = httpx.post(
            f"{API_BASE_URL}/auth/register",
            json={"email": email, "password": password},
            timeout=15,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", "Registration failed") if "application/json" in e.response.headers.get("content-type", "") else "Registration failed"
        raise ValueError(detail)
    except httpx.RequestError:
        raise ConnectionError("Cannot reach the API.")


def logout():
    st.session_state.user_token = ""
    st.session_state.user_email = ""
    st.rerun()


def status_pill(status: str) -> str:
    cls = f"pill-{status.lower()}"
    return f'<span class="status-pill {cls}">{status}</span>'


# ── Unauthenticated pages ─────────────────────────────────────────────────────

if not st.session_state.user_token:
    with st.sidebar:
        st.markdown("### 🚀 Job Orchestrator")
        st.divider()
        auth_page = st.radio("", ["Login", "Create Account"], label_visibility="collapsed")

    if auth_page == "Login":
        col_l, col_c, col_r = st.columns([1, 1.2, 1])
        with col_c:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("### Sign in")
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            if st.button("Sign in", type="primary", use_container_width=True):
                if not email or not password:
                    st.warning("Enter your email and password.")
                else:
                    try:
                        login_user(email, password)
                        st.rerun()
                    except (ValueError, ConnectionError) as e:
                        st.error(str(e))

    else:
        col_l, col_c, col_r = st.columns([1, 1.2, 1])
        with col_c:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("### Create Account")
            email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_pass",
                                     help="Minimum 8 characters")
            confirm = st.text_input("Confirm password", type="password", key="reg_confirm")
            if st.button("Create account", type="primary", use_container_width=True):
                if not email or not password:
                    st.warning("Fill in all fields.")
                elif len(password) < 8:
                    st.warning("Password must be at least 8 characters.")
                elif password != confirm:
                    st.warning("Passwords do not match.")
                else:
                    try:
                        register_user(email, password)
                        st.success("Account created! Sign in from the sidebar.")
                    except (ValueError, ConnectionError) as e:
                        st.error(str(e))
    st.stop()


# ── Authenticated sidebar ─────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🚀 Job Orchestrator")
    st.markdown(
        f"<small style='color:#475569'>Signed in as</small><br><b>{st.session_state.user_email}</b>",
        unsafe_allow_html=True,
    )
    st.divider()
    page = st.radio(
        "Navigation",
        ["Dashboard", "Submit Job", "My Jobs", "Account"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("Sign out", use_container_width=True):
        logout()


# ── Auto-refresh (Dashboard page only) ───────────────────────────────────────
if page == "Dashboard":
    now = time.time()
    if now - st.session_state.last_refresh >= AUTO_REFRESH_SECONDS:
        st.session_state.last_refresh = now
        if st.session_state.last_refresh > AUTO_REFRESH_SECONDS:
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Dashboard":
    st.markdown("## My Dashboard")
    st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')} · refreshes every {AUTO_REFRESH_SECONDS}s")

    jobs = api("GET", "/jobs")
    if jobs is None:
        st.stop()

    total = len(jobs)

    if total == 0:
        st.markdown(
            """
            <div class="empty-state">
                <h3>No jobs yet</h3>
                <p>Submit your first job from <b>Submit Job</b> in the sidebar.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    # Counts by status
    by_status = pd.Series([j["status"] for j in jobs]).value_counts()
    completed = by_status.get("COMPLETED", 0)
    active = by_status.get("RUNNING", 0) + by_status.get("ASSIGNED", 0) + by_status.get("RETRYING", 0)
    queued = by_status.get("QUEUED", 0)
    needs_attention = by_status.get("FAILED", 0) + by_status.get("DEAD", 0)

    # ── Metrics row ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("Completed", completed)
    c3.metric("Active", active)
    c4.metric("Queued", queued)
    c5.metric("Needs Attention", needs_attention, delta=f"-{needs_attention}" if needs_attention else None, delta_color="inverse")

    st.divider()

    left, right = st.columns([2, 3])

    with left:
        st.markdown('<p class="section-header">Status Breakdown</p>', unsafe_allow_html=True)
        st.bar_chart(by_status)

        st.markdown('<p class="section-header" style="margin-top:16px">By Job Type</p>', unsafe_allow_html=True)
        type_counts = pd.Series([j["type"] for j in jobs]).value_counts()
        st.bar_chart(type_counts)

    with right:
        st.markdown('<p class="section-header">Recent Activity</p>', unsafe_allow_html=True)
        df = pd.DataFrame(jobs).head(15)
        visible = ["id", "type", "status", "priority", "retry_count", "created_at"]
        existing = [c for c in visible if c in df.columns]
        st.dataframe(
            df[existing],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.TextColumn("Job ID", width="medium"),
                "type": st.column_config.TextColumn("Type"),
                "status": st.column_config.TextColumn("Status"),
                "priority": st.column_config.NumberColumn("Pri", width="small"),
                "retry_count": st.column_config.NumberColumn("Retries", width="small"),
                "created_at": st.column_config.TextColumn("Created"),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SUBMIT JOB
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Submit Job":
    st.markdown("## Submit a Job")
    st.caption("Jobs are queued in Redis and picked up by the next available worker.")

    # ── Job type & config ─────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        job_type = st.selectbox(
            "Job type",
            ["resume_analysis", "pdf_summary", "email_send"],
            help="Selects which executor handles this job",
        )
    with c2:
        priority = st.select_slider(
            "Priority",
            options=[1, 2, 3],
            value=2,
            format_func=lambda v: {1: "🔴 High", 2: "🟡 Medium", 3: "🟢 Low"}[v],
        )
    with c3:
        max_retries = st.number_input(
            "Max retries",
            min_value=0, max_value=10, value=3,
            help="How many times to retry before moving to Dead Letter Queue",
        )

    st.divider()

    # ── Type-specific payload builder ─────────────────────────────────────────
    payload = {}
    valid = True

    if job_type == "resume_analysis":
        st.markdown("#### Resume Analysis")
        st.caption("Extracts skills, experience, education, and job titles from a resume.")
        input_mode = st.radio("Input mode", ["Paste text", "File path"], horizontal=True)
        if input_mode == "Paste text":
            text = st.text_area(
                "Resume text",
                height=220,
                placeholder="Paste the full resume text here…",
            )
            if text.strip():
                payload = {"text": text}
            else:
                valid = False
                st.caption("⚠ Paste resume text above.")
        else:
            path = st.text_input("File path", placeholder="/data/resume.txt")
            if path.strip():
                payload = {"file_path": path}
            else:
                valid = False
                st.caption("⚠ Enter a file path.")

    elif job_type == "pdf_summary":
        st.markdown("#### PDF Summary")
        st.caption("Extracts text from a PDF and generates a summary using an LLM.")
        file_path = st.text_input("PDF file path", placeholder="/data/document.pdf")
        max_length = st.slider("Summary max length (words)", 50, 1000, 220)
        if file_path.strip():
            payload = {"file_path": file_path, "max_length": max_length}
        else:
            valid = False
            st.caption("⚠ Enter the PDF file path.")

    elif job_type == "email_send":
        st.markdown("#### Email Send")
        st.caption("Sends an email via SMTP. Uses dry-run mode if SMTP is not configured.")
        to = st.text_input("To", placeholder="recipient@example.com")
        subject = st.text_input("Subject", placeholder="Hello from the orchestrator")
        body = st.text_area("Body", height=160, placeholder="Your message here…")
        if to.strip() and subject.strip() and body.strip():
            payload = {"to": to, "subject": subject, "body": body}
        else:
            valid = False
            if to or subject or body:
                st.caption("⚠ Fill in To, Subject, and Body.")

    # ── Advanced JSON override ────────────────────────────────────────────────
    with st.expander("Advanced — edit raw JSON payload"):
        raw = st.text_area(
            "Payload JSON",
            value=json.dumps(payload, indent=2),
            height=140,
            key="raw_payload",
        )
        try:
            payload = json.loads(raw)
            valid = bool(payload)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            valid = False

    # ── Submit ────────────────────────────────────────────────────────────────
    st.divider()
    col_btn, col_preview = st.columns([1, 3])
    with col_btn:
        submitted = st.button(
            "Submit job →",
            type="primary",
            disabled=not valid,
            use_container_width=True,
        )
    with col_preview:
        if payload:
            st.caption(f"Payload preview: `{json.dumps(payload)[:120]}…`" if len(json.dumps(payload)) > 120 else f"Payload: `{json.dumps(payload)}`")

    if submitted and valid:
        result = api("POST", "/jobs", json={
            "type": job_type,
            "priority": priority,
            "max_retries": int(max_retries),
            "payload": payload,
        })
        if result:
            st.success(f"✓ Job queued successfully!")
            c1, c2, c3 = st.columns(3)
            c1.metric("Job ID", str(result["id"])[:8] + "…")
            c2.metric("Status", result["status"])
            c3.metric("Priority", {1: "High", 2: "Medium", 3: "Low"}.get(result["priority"], str(result["priority"])))
            st.caption(f"Full ID: `{result['id']}`")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MY JOBS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "My Jobs":
    st.markdown("## My Jobs")

    jobs = api("GET", "/jobs")
    if jobs is None:
        st.stop()

    if not jobs:
        st.markdown(
            """
            <div class="empty-state">
                <h3>No jobs yet</h3>
                <p>Head to <b>Submit Job</b> to create your first job.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    # ── Filter bar ────────────────────────────────────────────────────────────
    df = pd.DataFrame(jobs)
    c1, c2 = st.columns(2)
    with c1:
        status_filter = st.multiselect(
            "Filter by status",
            options=sorted(df["status"].unique()),
            default=[],
        )
    with c2:
        type_filter = st.multiselect(
            "Filter by type",
            options=sorted(df["type"].unique()),
            default=[],
        )

    filtered = df.copy()
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if type_filter:
        filtered = filtered[filtered["type"].isin(type_filter)]

    st.caption(f"{len(filtered)} job(s)")

    visible = ["id", "type", "status", "priority", "retry_count", "worker_id", "created_at"]
    existing = [c for c in visible if c in filtered.columns]
    st.dataframe(filtered[existing], use_container_width=True, hide_index=True)

    st.divider()
    st.markdown('<p class="section-header">Job Details & Actions</p>', unsafe_allow_html=True)

    selected_id = st.selectbox("Select a job", filtered["id"].tolist() if len(filtered) else df["id"].tolist())
    selected = next((j for j in jobs if j["id"] == selected_id), None)

    if not selected:
        st.stop()

    # ── Status + actions row ──────────────────────────────────────────────────
    status = selected["status"]
    ca, cb, cc, cd = st.columns(4)
    ca.markdown(f"**Status:** `{status}`")
    cb.markdown(f"**Type:** `{selected['type']}`")
    cc.markdown(f"**Worker:** `{selected.get('worker_id') or 'unassigned'}`")
    cd.markdown(f"**Retries:** `{selected['retry_count']} / {selected['max_retries']}`")

    act1, act2, act3 = st.columns(3)

    with act1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    with act2:
        can_cancel = status == "QUEUED"
        if st.button(
            "✕ Cancel job",
            use_container_width=True,
            disabled=not can_cancel,
            help="Only QUEUED jobs can be cancelled" if not can_cancel else "Cancel this job",
        ):
            result = api("DELETE", f"/jobs/{selected_id}")
            if result is not None:
                st.success("Job cancelled.")
                st.rerun()

    with act3:
        can_retry = status in ("FAILED", "DEAD")
        if st.button(
            "↩ Retry job",
            use_container_width=True,
            disabled=not can_retry,
            help="Only FAILED or DEAD jobs can be retried" if not can_retry else "Requeue this job",
        ):
            result = api("POST", f"/jobs/{selected_id}/retry")
            if result is not None:
                st.success("Job re-queued.")
                st.rerun()

    # ── Error message ─────────────────────────────────────────────────────────
    if selected.get("error_message"):
        st.error(f"**Last error:** {selected['error_message']}")

    # ── Result ────────────────────────────────────────────────────────────────
    st.markdown('<p class="section-header" style="margin-top:20px">Result</p>', unsafe_allow_html=True)
    result = selected.get("result")
    if result:
        # Pretty-render known result shapes
        if selected["type"] == "resume_analysis" and "skills" in result:
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("Score", result.get("score", "—"))
            rc2.metric("Experience", f"{result.get('experience_years', 0)} yrs")
            rc3.metric("Skills found", len(result.get("skills", [])))
            if result.get("skills"):
                st.markdown("**Skills:** " + "  ·  ".join(f"`{s}`" for s in result["skills"]))
            if result.get("education"):
                st.markdown("**Education:** " + ", ".join(result["education"]))
        elif selected["type"] == "pdf_summary" and "summary" in result:
            rc1, rc2 = st.columns(2)
            rc1.metric("Pages", result.get("pages", "—"))
            rc2.metric("Word count", result.get("word_count", "—"))
            st.markdown("**Summary:**")
            st.info(result["summary"])
        elif selected["type"] == "email_send":
            rc1, rc2 = st.columns(2)
            rc1.metric("Delivered", "Yes" if result.get("delivered") else "Dry run")
            rc2.metric("Message ID", str(result.get("message_id", "—"))[:24] + "…")
        else:
            st.json(result)
    else:
        status_msg = {
            "QUEUED": "Waiting for a worker to pick up this job.",
            "ASSIGNED": "A worker has claimed this job and will start shortly.",
            "RUNNING": "Job is currently executing.",
            "RETRYING": "Job failed and is waiting to retry.",
            "FAILED": "Job failed. Click Retry to requeue.",
            "DEAD": "All retries exhausted. Click Retry to requeue from scratch.",
            "CANCELLED": "This job was cancelled.",
        }
        st.caption(status_msg.get(status, "No result yet."))

    # ── Lifecycle logs ────────────────────────────────────────────────────────
    st.markdown('<p class="section-header" style="margin-top:20px">Lifecycle Logs</p>', unsafe_allow_html=True)
    logs = api("GET", f"/jobs/{selected_id}/logs", silent=True)
    if logs:
        log_df = pd.DataFrame(logs)
        if "created_at" in log_df.columns:
            log_df["created_at"] = pd.to_datetime(log_df["created_at"]).dt.strftime("%H:%M:%S")
        visible_log = ["created_at", "event", "message"]
        existing_log = [c for c in visible_log if c in log_df.columns]
        st.dataframe(
            log_df[existing_log],
            use_container_width=True,
            hide_index=True,
            column_config={
                "created_at": st.column_config.TextColumn("Time", width="small"),
                "event": st.column_config.TextColumn("Event", width="medium"),
                "message": st.column_config.TextColumn("Message"),
            },
        )
    else:
        st.caption("No log entries yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ACCOUNT
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Account":
    st.markdown("## Account")
    st.markdown(f"**Email:** {st.session_state.user_email}")

    st.divider()
    st.markdown("### Token")
    st.caption("Your current session token (valid 24 hours):")
    token_preview = st.session_state.user_token
    st.code(token_preview[:40] + "…", language="text")

    st.divider()
    if st.button("Sign out", type="primary"):
        logout()
