import os
from datetime import datetime

import httpx
import pandas as pd
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f7f9fc; }
    section[data-testid="stSidebar"] { background: #111827; }
    section[data-testid="stSidebar"] * { color: #f9fafb; }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border-left: 6px solid #2563eb;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 1px 8px rgba(15, 23, 42, 0.08);
    }
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "admin_token" not in st.session_state:
    st.session_state.admin_token = ""
if "admin_email" not in st.session_state:
    st.session_state.admin_email = ""


def api_request(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.admin_token:
        headers["Authorization"] = f"Bearer {st.session_state.admin_token}"
    response = httpx.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=20, **kwargs)
    response.raise_for_status()
    return response.json()


def login_admin(email: str, password: str) -> None:
    response = httpx.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    response.raise_for_status()
    st.session_state.admin_token = response.json()["access_token"]
    me = api_request("GET", "/auth/me")
    if not me.get("is_admin"):
        st.session_state.admin_token = ""
        raise PermissionError("This account is not an admin.")
    st.session_state.admin_email = me["email"]


def logout() -> None:
    st.session_state.admin_token = ""
    st.session_state.admin_email = ""
    st.rerun()


with st.sidebar:
    st.title("Admin")
    if st.session_state.admin_token:
        st.caption(st.session_state.admin_email)
        page = st.radio("Pages", ["Overview", "Jobs", "Workers", "Dead Letter Queue", "Account"])
    else:
        page = "Login"

if not st.session_state.admin_token:
    st.title("Admin Login")
    st.info("Admin access is verified by the backend. A normal user account cannot open this dashboard.")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login", type="primary"):
        try:
            login_admin(email, password)
            st.rerun()
        except Exception as exc:
            st.error(f"Login failed: {exc}")
    st.stop()

st.markdown("<meta http-equiv='refresh' content='10'>", unsafe_allow_html=True)

if page == "Overview":
    st.title("System Overview")
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
    metrics = api_request("GET", "/metrics")
    queue_stats = api_request("GET", "/queue/stats")
    jobs = api_request("GET", "/admin/jobs")

    cards = st.columns(4)
    cards[0].metric("Total jobs", metrics["total_jobs"])
    cards[1].metric("Success rate", f'{metrics["success_rate"]}%')
    cards[2].metric("Queue depth", metrics["queue_depth"])
    cards[3].metric("Active workers", metrics["active_workers"])

    cards = st.columns(4)
    cards[0].metric("Running", metrics["running_jobs"])
    cards[1].metric("Completed", metrics["completed_jobs"])
    cards[2].metric("Failed", metrics["failed_jobs"])
    cards[3].metric("DLQ size", metrics["dlq_size"])

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Jobs by status")
        if jobs:
            st.bar_chart(pd.DataFrame(jobs)["status"].value_counts())
        else:
            st.info("No jobs submitted yet.")
    with right:
        st.subheader("Queue by priority")
        st.bar_chart(
            pd.Series(
                {
                    "High": queue_stats.get("high_priority", 0),
                    "Medium": queue_stats.get("medium_priority", 0),
                    "Low": queue_stats.get("low_priority", 0),
                }
            )
        )

elif page == "Jobs":
    st.title("All Jobs")
    jobs = api_request("GET", "/admin/jobs")
    if jobs:
        df = pd.DataFrame(jobs)
        visible = ["id", "user_id", "type", "status", "priority", "retry_count", "worker_id", "created_at", "completed_at"]
        st.dataframe(df[visible], use_container_width=True, hide_index=True)
        selected_job_id = st.selectbox("Inspect job", df["id"].tolist())
        selected = next(job for job in jobs if job["id"] == selected_job_id)
        st.json(selected)
    else:
        st.info("No jobs found.")

elif page == "Workers":
    st.title("Worker Health")
    workers = api_request("GET", "/workers")
    if workers:
        st.dataframe(pd.DataFrame(workers), use_container_width=True, hide_index=True)
    else:
        st.info("No worker heartbeats found yet.")

elif page == "Dead Letter Queue":
    st.title("Dead Letter Queue")
    dlq = api_request("GET", "/dlq")
    if dlq:
        st.dataframe(pd.DataFrame(dlq), use_container_width=True, hide_index=True)
    else:
        st.success("DLQ is empty.")

elif page == "Account":
    st.title("Account")
    st.write(f"Signed in as **{st.session_state.admin_email}**")
    if st.button("Logout", type="primary"):
        logout()
