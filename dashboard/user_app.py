import json
import os

import httpx
import pandas as pd
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


st.set_page_config(page_title="User Dashboard", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #fbfcf8; }
    section[data-testid="stSidebar"] { background: #063b36; }
    section[data-testid="stSidebar"] * { color: #f8fafc; }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border-left: 6px solid #16a34a;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 1px 8px rgba(6, 59, 54, 0.10);
    }
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "user_token" not in st.session_state:
    st.session_state.user_token = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""


def api_request(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.user_token:
        headers["Authorization"] = f"Bearer {st.session_state.user_token}"
    response = httpx.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=20, **kwargs)
    response.raise_for_status()
    return response.json()


def login_user(email: str, password: str) -> None:
    response = httpx.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    response.raise_for_status()
    st.session_state.user_token = response.json()["access_token"]
    me = api_request("GET", "/auth/me")
    st.session_state.user_email = me["email"]


def logout() -> None:
    st.session_state.user_token = ""
    st.session_state.user_email = ""
    st.rerun()


with st.sidebar:
    st.title("Jobs")
    if st.session_state.user_token:
        st.caption(st.session_state.user_email)
        page = st.radio("Pages", ["Dashboard", "Submit Job", "Job Details", "Account"])
    else:
        page = st.radio("Pages", ["Login", "Registration"])

if page == "Login":
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login", type="primary"):
        try:
            login_user(email, password)
            st.rerun()
        except Exception as exc:
            st.error(f"Login failed: {exc}")
    st.stop()

if page == "Registration":
    st.title("Registration")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Create account", type="primary"):
        try:
            httpx.post(
                f"{API_BASE_URL}/auth/register",
                json={"email": email, "password": password},
                timeout=20,
            ).raise_for_status()
            st.success("Account created. Open Login from the sidebar.")
        except Exception as exc:
            st.error(f"Registration failed: {exc}")
    st.stop()

if not st.session_state.user_token:
    st.stop()

if page == "Dashboard":
    st.title("My Job Dashboard")
    jobs = api_request("GET", "/jobs")
    total = len(jobs)
    completed = len([job for job in jobs if job["status"] == "COMPLETED"])
    running = len([job for job in jobs if job["status"] in {"ASSIGNED", "RUNNING", "RETRYING"}])
    failed = len([job for job in jobs if job["status"] in {"FAILED", "DEAD"}])

    cards = st.columns(4)
    cards[0].metric("My jobs", total)
    cards[1].metric("Completed", completed)
    cards[2].metric("Active", running)
    cards[3].metric("Needs attention", failed)

    if jobs:
        df = pd.DataFrame(jobs)
        left, right = st.columns([1, 2])
        with left:
            st.subheader("Status")
            st.bar_chart(df["status"].value_counts())
        with right:
            st.subheader("Recent activity")
            visible = ["id", "type", "status", "priority", "retry_count", "created_at"]
            st.dataframe(df[visible].head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No jobs yet. Submit your first job from the sidebar.")

elif page == "Submit Job":
    st.title("Submit Job")
    job_type = st.selectbox("Job type", ["resume_analysis", "pdf_summary", "email_send"])
    priority = st.select_slider(
        "Priority",
        options=[1, 2, 3],
        value=2,
        format_func=lambda value: {1: "High", 2: "Medium", 3: "Low"}[value],
    )
    max_retries = st.number_input("Max retries", min_value=0, max_value=10, value=3)

    payload = {}
    if job_type == "resume_analysis":
        st.subheader("Resume Analysis")
        resume_text = st.text_area("Resume text", height=220)
        file_path = st.text_input("Resume file path")
        payload = {"text": resume_text} if resume_text else {"file_path": file_path}
    elif job_type == "pdf_summary":
        st.subheader("PDF Summary")
        payload = {
            "file_path": st.text_input("PDF file path"),
            "max_length": st.number_input("Max summary length", min_value=50, max_value=1000, value=220),
        }
    elif job_type == "email_send":
        st.subheader("Email Send")
        payload = {
            "to": st.text_input("To"),
            "subject": st.text_input("Subject"),
            "body": st.text_area("Body", height=180),
        }

    with st.expander("Advanced JSON payload"):
        raw_payload = st.text_area("Payload", json.dumps(payload, indent=2), height=180)

    if st.button("Submit job", type="primary"):
        try:
            job = api_request(
                "POST",
                "/jobs",
                json={
                    "type": job_type,
                    "priority": priority,
                    "max_retries": max_retries,
                    "payload": json.loads(raw_payload),
                },
            )
            st.success(f"Job queued: {job['id']}")
        except Exception as exc:
            st.error(f"Job submission failed: {exc}")

elif page == "Job Details":
    st.title("Job Details")
    jobs = api_request("GET", "/jobs")
    if not jobs:
        st.info("No jobs available.")
        st.stop()

    df = pd.DataFrame(jobs)
    visible = ["id", "type", "status", "priority", "retry_count", "worker_id", "created_at"]
    st.dataframe(df[visible], use_container_width=True, hide_index=True)

    selected_job_id = st.selectbox("Select job", df["id"].tolist())
    selected = next(job for job in jobs if job["id"] == selected_job_id)

    actions = st.columns(3)
    if actions[0].button("Refresh"):
        st.rerun()
    if actions[1].button("Cancel queued job"):
        try:
            api_request("DELETE", f"/jobs/{selected_job_id}")
            st.success("Cancel request sent.")
            st.rerun()
        except Exception as exc:
            st.error(f"Cancel failed: {exc}")
    if actions[2].button("Retry failed job"):
        try:
            api_request("POST", f"/jobs/{selected_job_id}/retry")
            st.success("Retry request sent.")
            st.rerun()
        except Exception as exc:
            st.error(f"Retry failed: {exc}")

    st.subheader("Result")
    st.json(selected.get("result") or {})
    st.subheader("Lifecycle logs")
    try:
        logs = api_request("GET", f"/jobs/{selected_job_id}/logs")
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"Unable to load logs: {exc}")

elif page == "Account":
    st.title("Account")
    st.write(f"Signed in as **{st.session_state.user_email}**")
    if st.button("Logout", type="primary"):
        logout()
