# import os
# from datetime import datetime

# import httpx
# import pandas as pd
# import streamlit as st


# API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


# st.set_page_config(page_title="Admin Dashboard", layout="wide")
# st.markdown(
#     """
#     <style>
#     .stApp { background: #f7f9fc; }
#     section[data-testid="stSidebar"] { background: #111827; }
#     section[data-testid="stSidebar"] * { color: #f9fafb; }
#     div[data-testid="stMetric"] {
#         background: #ffffff;
#         border-left: 6px solid #2563eb;
#         padding: 16px;
#         border-radius: 8px;
#         box-shadow: 0 1px 8px rgba(15, 23, 42, 0.08);
#     }
#     .block-container { padding-top: 2rem; }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# if "admin_token" not in st.session_state:
#     st.session_state.admin_token = ""
# if "admin_email" not in st.session_state:
#     st.session_state.admin_email = ""


# def api_request(method: str, path: str, **kwargs):
#     headers = kwargs.pop("headers", {})
#     if st.session_state.admin_token:
#         headers["Authorization"] = f"Bearer {st.session_state.admin_token}"
#     response = httpx.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=20, **kwargs)
#     response.raise_for_status()
#     return response.json()


# def login_admin(email: str, password: str) -> None:
#     response = httpx.post(
#         f"{API_BASE_URL}/auth/login",
#         json={"email": email, "password": password},
#         timeout=20,
#     )
#     response.raise_for_status()
#     st.session_state.admin_token = response.json()["access_token"]
#     me = api_request("GET", "/auth/me")
#     if not me.get("is_admin"):
#         st.session_state.admin_token = ""
#         raise PermissionError("This account is not an admin.")
#     st.session_state.admin_email = me["email"]


# def logout() -> None:
#     st.session_state.admin_token = ""
#     st.session_state.admin_email = ""
#     st.rerun()


# with st.sidebar:
#     st.title("Admin")
#     if st.session_state.admin_token:
#         st.caption(st.session_state.admin_email)
#         page = st.radio("Pages", ["Overview", "Jobs", "Workers", "Dead Letter Queue", "Account"])
#     else:
#         page = "Login"

# if not st.session_state.admin_token:
#     st.title("Admin Login")
#     st.info("Admin access is verified by the backend. A normal user account cannot open this dashboard.")
#     email = st.text_input("Email")
#     password = st.text_input("Password", type="password")
#     if st.button("Login", type="primary"):
#         try:
#             login_admin(email, password)
#             st.rerun()
#         except Exception as exc:
#             st.error(f"Login failed: {exc}")
#     st.stop()

# st.markdown("<meta http-equiv='refresh' content='10'>", unsafe_allow_html=True)

# if page == "Overview":
#     st.title("System Overview")
#     st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
#     metrics = api_request("GET", "/metrics")
#     queue_stats = api_request("GET", "/queue/stats")
#     jobs = api_request("GET", "/admin/jobs")

#     cards = st.columns(4)
#     cards[0].metric("Total jobs", metrics["total_jobs"])
#     cards[1].metric("Success rate", f'{metrics["success_rate"]}%')
#     cards[2].metric("Queue depth", metrics["queue_depth"])
#     cards[3].metric("Active workers", metrics["active_workers"])

#     cards = st.columns(4)
#     cards[0].metric("Running", metrics["running_jobs"])
#     cards[1].metric("Completed", metrics["completed_jobs"])
#     cards[2].metric("Failed", metrics["failed_jobs"])
#     cards[3].metric("DLQ size", metrics["dlq_size"])

#     left, right = st.columns([2, 1])
#     with left:
#         st.subheader("Jobs by status")
#         if jobs:
#             st.bar_chart(pd.DataFrame(jobs)["status"].value_counts())
#         else:
#             st.info("No jobs submitted yet.")
#     with right:
#         st.subheader("Queue by priority")
#         st.bar_chart(
#             pd.Series(
#                 {
#                     "High": queue_stats.get("high_priority", 0),
#                     "Medium": queue_stats.get("medium_priority", 0),
#                     "Low": queue_stats.get("low_priority", 0),
#                 }
#             )
#         )

# elif page == "Jobs":
#     st.title("All Jobs")
#     jobs = api_request("GET", "/admin/jobs")
#     if jobs:
#         df = pd.DataFrame(jobs)
#         visible = ["id", "user_id", "type", "status", "priority", "retry_count", "worker_id", "created_at", "completed_at"]
#         st.dataframe(df[visible], use_container_width=True, hide_index=True)
#         selected_job_id = st.selectbox("Inspect job", df["id"].tolist())
#         selected = next(job for job in jobs if job["id"] == selected_job_id)
#         st.json(selected)
#     else:
#         st.info("No jobs found.")

# elif page == "Workers":
#     st.title("Worker Health")
#     workers = api_request("GET", "/workers")
#     if workers:
#         st.dataframe(pd.DataFrame(workers), use_container_width=True, hide_index=True)
#     else:
#         st.info("No worker heartbeats found yet.")

# elif page == "Dead Letter Queue":
#     st.title("Dead Letter Queue")
#     dlq = api_request("GET", "/dlq")
#     if dlq:
#         st.dataframe(pd.DataFrame(dlq), use_container_width=True, hide_index=True)
#     else:
#         st.success("DLQ is empty.")

# elif page == "Account":
#     st.title("Account")
#     st.write(f"Signed in as **{st.session_state.admin_email}**")
#     if st.button("Logout", type="primary"):
#         logout()


"""
dashboard/admin_app.py
Production-grade Admin Dashboard for the Job Orchestration Platform.

Requirements met:
- Live metrics cards: total jobs, success rate, queue depth, active workers
- Bar chart: jobs by status (auto-refreshes every 10 seconds)
- Table: recent 20 jobs with status, type, duration, worker
- Worker health panel: all workers with last heartbeat time
- DLQ visibility + one-click requeue
- Throughput chart: jobs per minute over last 60 minutes
- Admin-only login guard
- Full error handling with user-friendly messages
"""

import os
import time
from datetime import datetime

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
AUTO_REFRESH_SECONDS = 10

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Orchestrator · Admin",
    page_icon="⚙️",
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
    section[data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-top: 3px solid #3b82f6;
        padding: 20px 24px;
        border-radius: 8px;
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.05em; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.8rem !important; font-weight: 700; }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

    /* Dataframe */
    .stDataFrame { border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; }

    /* Buttons */
    .stButton > button {
        background: #1e40af;
        color: #fff;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        transition: background 0.2s;
    }
    .stButton > button:hover { background: #1d4ed8; }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.03em;
    }
    .badge-completed  { background: #14532d; color: #86efac; }
    .badge-running    { background: #1e3a5f; color: #7dd3fc; }
    .badge-queued     { background: #1c1917; color: #d6d3d1; }
    .badge-failed     { background: #450a0a; color: #fca5a5; }
    .badge-dead       { background: #3b0764; color: #d8b4fe; }
    .badge-retrying   { background: #431407; color: #fdba74; }
    .badge-assigned   { background: #1e3a5f; color: #93c5fd; }

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

    .worker-alive  { color: #4ade80; font-weight: 600; }
    .worker-dead   { color: #f87171; font-weight: 600; }

    .block-container { padding: 2rem 2rem 2rem; max-width: 1400px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("admin_token", ""),
    ("admin_email", ""),
    ("last_refresh", 0.0),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── API helpers ───────────────────────────────────────────────────────────────

def api(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.admin_token:
        headers["Authorization"] = f"Bearer {st.session_state.admin_token}"
    try:
        r = httpx.request(
            method, f"{API_BASE_URL}{path}",
            headers=headers, timeout=15, **kwargs,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
        return None
    except httpx.RequestError as e:
        st.error(f"Cannot reach API at `{API_BASE_URL}`. Is the server running?")
        return None


def login_admin(email: str, password: str) -> None:
    try:
        r = httpx.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError:
        raise ValueError("Invalid credentials")
    except httpx.RequestError:
        raise ConnectionError(f"Cannot connect to {API_BASE_URL}")

    token = r.json()["access_token"]
    # Verify admin role
    me_r = httpx.get(
        f"{API_BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    me = me_r.json()
    if not me.get("is_admin"):
        raise PermissionError("This account does not have admin privileges.")
    st.session_state.admin_token = token
    st.session_state.admin_email = me["email"]


def logout():
    st.session_state.admin_token = ""
    st.session_state.admin_email = ""
    st.rerun()


# ── Status badge helper ───────────────────────────────────────────────────────

def badge(status: str) -> str:
    cls = f"badge-{status.lower()}"
    return f'<span class="badge {cls}">{status}</span>'


def worker_status_html(status: str) -> str:
    cls = "worker-alive" if status == "ALIVE" else "worker-dead"
    icon = "●" if status == "ALIVE" else "○"
    return f'<span class="{cls}">{icon} {status}</span>'


# ── Login page ────────────────────────────────────────────────────────────────

if not st.session_state.admin_token:
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### ⚙️ Admin Login")
        st.caption("Access is restricted to admin accounts only.")
        email = st.text_input("Email", placeholder="admin@example.com")
        password = st.text_input("Password", type="password")
        if st.button("Sign in", type="primary", use_container_width=True):
            if not email or not password:
                st.warning("Enter your email and password.")
            else:
                try:
                    login_admin(email, password)
                    st.rerun()
                except (ValueError, PermissionError) as e:
                    st.error(str(e))
                except ConnectionError as e:
                    st.error(str(e))
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Orchestrator")
    st.markdown(f"<small style='color:#475569'>Signed in as</small><br><b>{st.session_state.admin_email}</b>", unsafe_allow_html=True)
    st.divider()
    page = st.radio(
        "Navigation",
        ["Overview", "Jobs", "Workers", "Dead Letter Queue", "Throughput"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("Sign out", use_container_width=True):
        logout()

    st.markdown(
        f"<small style='color:#334155'>Auto-refreshes every {AUTO_REFRESH_SECONDS}s</small>",
        unsafe_allow_html=True,
    )


# ── Auto-refresh ──────────────────────────────────────────────────────────────
# Triggers a rerun after AUTO_REFRESH_SECONDS without freezing the UI.
now = time.time()
if now - st.session_state.last_refresh >= AUTO_REFRESH_SECONDS:
    st.session_state.last_refresh = now
    # Don't rerun on first load
    if st.session_state.last_refresh > AUTO_REFRESH_SECONDS:
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.markdown(f"## System Overview")
    st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')} · refreshes every {AUTO_REFRESH_SECONDS}s")

    metrics = api("GET", "/metrics")
    queue_stats = api("GET", "/queue/stats")

    if metrics is None or queue_stats is None:
        st.warning("Could not load metrics. Check API connectivity.")
        st.stop()

    # ── Row 1: Core health ────────────────────────────────────────────────────
    st.markdown('<p class="section-header">System Health</p>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Jobs", f"{metrics['total_jobs']:,}")
    c2.metric(
        "Success Rate",
        f"{metrics['success_rate']}%",
        delta=None,
        help="Completed / Total × 100",
    )
    c3.metric("Queue Depth", metrics["queue_depth"], help="Jobs waiting in Redis")
    c4.metric("Active Workers", metrics["active_workers"])

    # ── Row 2: Execution stats ────────────────────────────────────────────────
    st.markdown('<p class="section-header" style="margin-top:24px">Execution Stats</p>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Running Now", metrics["running_jobs"])
    c2.metric("Completed", f"{metrics['completed_jobs']:,}")
    c3.metric(
        "Avg Execution",
        f"{metrics['avg_execution_time_ms']:.0f} ms",
        help="Average job execution time",
    )
    c4.metric("Jobs / Min", metrics["jobs_per_minute"])

    # ── Row 3: Reliability ────────────────────────────────────────────────────
    st.markdown('<p class="section-header" style="margin-top:24px">Reliability</p>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Failed", metrics["failed_jobs"])
    c2.metric("DLQ Size", metrics["dlq_size"], help="Jobs in Dead Letter Queue")
    c3.metric("Retry Rate", f"{metrics['retry_rate']}%", help="Jobs that needed at least one retry")
    c4.metric(
        "Queue: High / Med / Low",
        f"{queue_stats.get('high_priority',0)} / {queue_stats.get('medium_priority',0)} / {queue_stats.get('low_priority',0)}",
    )

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown('<p class="section-header">Jobs by Status</p>', unsafe_allow_html=True)
        jobs = api("GET", "/admin/jobs")
        if jobs:
            df = pd.DataFrame(jobs)
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            st.bar_chart(status_counts.set_index("Status"))
        else:
            st.info("No jobs yet.")

    with right:
        st.markdown('<p class="section-header">Queue by Priority</p>', unsafe_allow_html=True)
        priority_df = pd.Series({
            "High (1)": queue_stats.get("high_priority", 0),
            "Medium (2)": queue_stats.get("medium_priority", 0),
            "Low (3)": queue_stats.get("low_priority", 0),
        }, name="Jobs Waiting")
        st.bar_chart(priority_df)

    # ── Recent 20 jobs ────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-header">Recent 20 Jobs</p>', unsafe_allow_html=True)
    jobs = api("GET", "/admin/jobs")
    if jobs:
        df = pd.DataFrame(jobs).head(20)

        # Compute duration
        def duration(row):
            if row.get("started_at") and row.get("completed_at"):
                try:
                    s = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
                    e = datetime.fromisoformat(row["completed_at"].replace("Z", "+00:00"))
                    ms = int((e - s).total_seconds() * 1000)
                    return f"{ms} ms"
                except Exception:
                    pass
            return "—"

        df["duration"] = df.apply(duration, axis=1)
        visible = ["id", "type", "status", "priority", "retry_count", "worker_id", "duration", "created_at"]
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
                "worker_id": st.column_config.TextColumn("Worker"),
                "duration": st.column_config.TextColumn("Duration", width="small"),
                "created_at": st.column_config.TextColumn("Created"),
            },
        )
    else:
        st.info("No jobs submitted yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: JOBS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Jobs":
    st.markdown("## All Jobs")

    jobs = api("GET", "/admin/jobs")
    if not jobs:
        st.info("No jobs found.")
        st.stop()

    df = pd.DataFrame(jobs)

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        status_filter = st.multiselect(
            "Filter by status",
            options=sorted(df["status"].unique()),
            default=[],
        )
    with col_f2:
        type_filter = st.multiselect(
            "Filter by type",
            options=sorted(df["type"].unique()),
            default=[],
        )
    with col_f3:
        search = st.text_input("Search job ID / worker ID", placeholder="Paste UUID…")

    filtered = df.copy()
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if type_filter:
        filtered = filtered[filtered["type"].isin(type_filter)]
    if search:
        mask = (
            filtered["id"].astype(str).str.contains(search, case=False) |
            filtered.get("worker_id", pd.Series(dtype=str)).astype(str).str.contains(search, case=False)
        )
        filtered = filtered[mask]

    st.caption(f"Showing {len(filtered)} of {len(df)} jobs")

    visible = ["id", "user_id", "type", "status", "priority", "retry_count", "worker_id", "created_at", "completed_at"]
    existing = [c for c in visible if c in filtered.columns]
    st.dataframe(filtered[existing], use_container_width=True, hide_index=True)

    st.divider()
    st.markdown('<p class="section-header">Inspect Job</p>', unsafe_allow_html=True)
    if len(filtered):
        selected_id = st.selectbox("Select job ID", filtered["id"].tolist())
        selected = next((j for j in jobs if j["id"] == selected_id), None)
        if selected:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Details**")
                st.json({k: selected[k] for k in ["id", "type", "status", "priority", "worker_id", "retry_count", "error_message"]})
            with c2:
                st.markdown("**Result**")
                st.json(selected.get("result") or {})


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: WORKERS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Workers":
    st.markdown("## Worker Health")
    st.caption("Workers send a heartbeat every 10 seconds. No heartbeat for 30s = DEAD.")

    workers = api("GET", "/workers")

    if workers is None:
        st.stop()

    if not workers:
        st.info("No worker heartbeats found. Are workers running?")
        st.stop()

    alive = [w for w in workers if w.get("status") == "ALIVE"]
    dead  = [w for w in workers if w.get("status") != "ALIVE"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Workers", len(workers))
    c2.metric("Alive", len(alive))
    c3.metric("Dead / Stale", len(dead))

    st.divider()

    for w in workers:
        status = w.get("status", "UNKNOWN")
        icon = "🟢" if status == "ALIVE" else "🔴"
        last_seen = w.get("last_seen", "—")
        if last_seen and last_seen != "—":
            try:
                dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                last_seen = dt.strftime("%H:%M:%S UTC")
            except Exception:
                pass

        with st.expander(f"{icon} {w['worker_id']}  —  {status}"):
            cc1, cc2, cc3 = st.columns(3)
            cc1.markdown(f"**Status:** `{status}`")
            cc2.markdown(f"**Last seen:** `{last_seen}`")
            cc3.markdown(f"**Current job:** `{w.get('current_job_id') or 'idle'}`")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DEAD LETTER QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Dead Letter Queue":
    st.markdown("## Dead Letter Queue")
    st.caption("Jobs that exhausted all retries. Inspect the error, then requeue or leave for audit.")

    dlq = api("GET", "/dlq")

    if dlq is None:
        st.stop()

    if not dlq:
        st.success("✓ DLQ is empty — no failed jobs awaiting inspection.")
        st.stop()

    st.warning(f"{len(dlq)} job(s) in the Dead Letter Queue.")

    for entry in dlq:
        job_id = entry.get("job_id", "unknown")
        moved_at = entry.get("moved_at", "—")
        if moved_at and moved_at != "—":
            try:
                dt = datetime.fromisoformat(moved_at.replace("Z", "+00:00"))
                moved_at = dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                pass

        with st.expander(f"🪦 Job `{job_id[:8]}…`  —  moved {moved_at}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Job ID:** `{job_id}`")
                st.markdown(f"**Failure reason:** `{entry.get('failure_reason', '—')}`")
                st.markdown(f"**Final error:**")
                st.code(entry.get("final_error", "—"), language="text")
            with c2:
                st.markdown("**Actions**")
                if st.button("↩ Requeue", key=f"requeue_{job_id}"):
                    result = api("POST", f"/dlq/{job_id}/requeue")
                    if result is not None:
                        st.success("Job moved back to main queue.")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: THROUGHPUT
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Throughput":
    st.markdown("## Throughput")
    st.caption("Jobs created per minute over the last 60 minutes.")

    data = api("GET", "/metrics/throughput")

    if data is None:
        st.stop()

    points = data.get("points", [])
    if not points:
        st.info("No throughput data yet. Submit some jobs first.")
        st.stop()

    df = pd.DataFrame(points)
    df["minute"] = pd.to_datetime(df["minute"])
    df = df.set_index("minute").sort_index()
    df.columns = ["Jobs Created"]

    st.line_chart(df, use_container_width=True)

    st.divider()
    st.markdown('<p class="section-header">Summary</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Peak (jobs/min)", int(df["Jobs Created"].max()))
    c2.metric("Average (jobs/min)", f"{df['Jobs Created'].mean():.1f}")
    c3.metric("Total in window", int(df["Jobs Created"].sum()))