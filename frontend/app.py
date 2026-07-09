import sys
import os
import uuid

# Allow imports from the backend/ folder when running via `streamlit run frontend/app.py`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px

from backend.classifier import classify_request
from backend.remediation_engine import run_remediation
from backend.database import init_db, log_case, get_all_cases, get_summary_counts
from backend.models import IncomingRequest

st.set_page_config(
    page_title="AI Operations Copilot",
        layout="wide",
)

# ---- Custom Styling ----
st.markdown("""
<style>
    /* Overall page background */
    .stApp {
        background-color: #F8FAFC;
    }

    /* Hide default streamlit title styling since we use a custom banner */
    h1 { display: none; }

    /* Banner header */
    .app-banner {
        background: linear-gradient(135deg, #1E40AF 0%, #2563EB 40%, #7C3AED 100%);
        border-radius: 22px;
        padding: 38px 42px;
        margin-bottom: 24px;
        box-shadow: 0 12px 40px rgba(37, 99, 235, 0.25);
    }
    .app-banner h1 {
        display: block !important;
        color: white !important;
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0 0 2px 0;
        -webkit-text-fill-color: white !important;
        background: none !important;
        border: none !important;
    }
    .app-banner h2 {
        display: block !important;
        color: #DBEAFE !important;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 10px 0;
        border: none !important;
        padding: 0 !important;
    }
    .app-banner p {
        color: #E0E7FF;
        margin: 0 0 14px 0;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .status-pills span {
        display: inline-block;
        background-color: rgba(255,255,255,0.15);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
    }

    /* Section subheaders */
    h3 {
        border-left: 4px solid #2563EB;
        padding-left: 10px;
        margin-top: 1.5rem !important;
        color: #1E293B;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: white;
        padding: 6px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 10px 18px;
        font-weight: 600;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: white !important;
    }

    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid #E2E8F0;
        transition: all 0.15s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        border-color: #2563EB;
    }
    .stButton button[kind="primary"] {
        background-color: #2563EB;
        border: none;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #1D4ED8;
    }

    /* Card-like containers */
    .result-card {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 26px;
        margin-bottom: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.07);
        transition: 0.25s;
    }
    .result-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 18px 40px rgba(0,0,0,0.12);
    }
    .result-card h3 {
        margin-top: 0 !important;
    }

    /* Mini metric-style pills for classification summary */
    .mini-metric {
        display: inline-block;
        background: #F1F5F9;
        border-radius: 12px;
        padding: 10px 16px;
        margin: 4px 8px 4px 0;
        text-align: center;
        min-width: 110px;
    }
    .mini-metric .label {
        font-size: 0.72rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .mini-metric .value {
        font-size: 1.05rem;
        font-weight: 800;
        color: #0F172A;
    }

    /* Pipeline visual */
    .pipeline-step {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 6px;
        font-weight: 600;
        color: #1E293B;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .pipeline-arrow {
        text-align: center;
        color: #94A3B8;
        font-size: 0.9rem;
        margin: 2px 0;
    }

    /* Badge pills */
    .badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        color: white;
    }
    .badge-critical { background-color: #EF4444; }
    .badge-high { background-color: #F97316; }
    .badge-medium { background-color: #F59E0B; color: black; }
    .badge-low { background-color: #10B981; }

    .status-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        color: white;
        background-color: #7C3AED;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
</style>

<div class="app-banner">
    <h1>AI Operations Copilot</h1>
    <h2>Incoming Request Processing Workflow</h2>
    <p>AI-powered request classification, branch-specific remediation, audit logging and workflow automation.<br>Firstsource Agentic AI Engineer POC</p>
    <div class="status-pills">
        <span>AI Online</span>
        <span>Groq Llama 3.3 70B</span>
        <span>SQLite Connected</span>
        <span>Ready</span>
    </div>
</div>
""", unsafe_allow_html=True)

init_db()


tab1, tab2, tab3 = st.tabs(["🆕 Process a Request", "📊 Dashboard", "📜 Audit Log"])


# ---------------- TAB 1: Process a Request ----------------
with tab1:
    st.subheader("📥Submit an Incoming Request")

    channel = st.selectbox("Channel", ["Web_form", "Email", "Simulated_inbox"])

    if "request_text" not in st.session_state:
        st.session_state["request_text"] = ""

    sample_col1, sample_col2, sample_col3, sample_col4 = st.columns(4)
    with sample_col1:
        if st.button("Load Complaint sample"):
            st.session_state["request_text"] = "I've been charged twice this month for the same subscription and nobody is responding to my emails. Please fix this immediately."
    with sample_col2:
        if st.button("Load Enquiry sample"):
            st.session_state["request_text"] = "Hi, can you tell me what payment methods you accept and if you support international cards?"
    with sample_col3:
        if st.button("Load Service Request sample"):
            st.session_state["request_text"] = "I recently moved to a new address and need my billing address updated on my account."
    with sample_col4:
        if st.button("Load Urgent sample"):
            st.session_state["request_text"] = "This is the THIRD time I'm complaining about the same billing error. If this isn't fixed today I will be cancelling my contract and contacting my lawyer."

    raw_text = st.text_area(
        "Paste the request text here (or click a sample button above)",
        height=150,
        key="request_text",
    )

    process_btn = st.button("Analyze & Execute Workflow", type="primary")

    if process_btn:
        final_text = st.session_state["request_text"]
        if not final_text.strip():
            st.warning("Please enter or load a request first.")
        else:
            with st.spinner("AI is understanding the request and selecting the best remediation workflow..."):
                request_id = str(uuid.uuid4())[:8]
                incoming = IncomingRequest(request_id=request_id, raw_text=final_text, channel=channel)
                classification = classify_request(final_text)
                remediation = run_remediation(request_id, classification, final_text)
                log_case(final_text, classification, remediation)

            st.success(f"Request `{request_id}` processed successfully!")

            # Pipeline visual — shows the agentic flow the system just executed
            st.markdown("""
            <div class="pipeline-step">Request Received</div>
            <div class="pipeline-arrow">↓</div>
            <div class="pipeline-step">AI Intent Classification</div>
            <div class="pipeline-arrow">↓</div>
            <div class="pipeline-step">Workflow Branch Selected</div>
            <div class="pipeline-arrow">↓</div>
            <div class="pipeline-step">Draft Response Generated</div>
            <div class="pipeline-arrow">↓</div>
            <div class="pipeline-step">Audit Log Updated</div>
            <div class="pipeline-arrow">↓</div>
            <div class="pipeline-step">Completed</div>
            """, unsafe_allow_html=True)

            urgency_class = {
                "Critical": "badge-critical",
                "High": "badge-high",
                "Medium": "badge-medium",
                "Low": "badge-low",
            }.get(classification.urgency, "badge-low")

            # Quick-glance metric pills
            st.markdown(f"""
            <div style="margin: 16px 0;">
                <div class="mini-metric"><div class="label">Type</div><div class="value">{classification.request_type}</div></div>
                <div class="mini-metric"><div class="label">Urgency</div><div class="value">{classification.urgency}</div></div>
                <div class="mini-metric"><div class="label">Confidence</div><div class="value">{classification.confidence}</div></div>
                <div class="mini-metric"><div class="label">Sub-topic</div><div class="value">{classification.sub_topic}</div></div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="result-card">
                    <h3>🏷️ Classification</h3>
                    <p><b>Type:</b> {classification.request_type}</p>
                    <p><b>Urgency:</b> <span class="badge {urgency_class}">{classification.urgency}</span></p>
                    <p><b>Sub-topic:</b> {classification.sub_topic}</p>
                    <p><b>AI Confidence:</b> {classification.confidence}</p>
                    <p><b>Reasoning:</b> {classification.reasoning}</p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                steps_html = "".join([f"<li>{s}</li>" for s in remediation.steps_executed])
                st.markdown(f"""
                <div class="result-card">
                    <h3>Remediation Branch Executed</h3>
                    <ol>{steps_html}</ol>
                    <p><b>Routing Team:</b> {remediation.routing_team}</p>
                    <p><b>Follow-up:</b> {remediation.follow_up}</p>
                    <p><b>Status:</b> <span class="status-badge">{remediation.status}</span></p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("### ✉️ Generated Draft Response")
            st.text_area("Draft", value=remediation.draft_response, height=150, key="draft_out")

# ---------------- TAB 2: Dashboard ----------------
with tab2:
    st.subheader("Request Volume Summary")

    cases_all = get_all_cases()
    total = len(cases_all)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Requests", total)
    m2.metric("Critical / Escalated", sum(1 for c in cases_all if c["status"] in ["Escalated", "Human Review"]))
    m3.metric("Resolved", sum(1 for c in cases_all if c["status"] == "Resolved"))
    m4.metric("Pending", sum(1 for c in cases_all if c["status"] == "Pending"))

    summary = get_summary_counts()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**By Request Type**")
        if summary["by_type"]:
            df_type = pd.DataFrame(list(summary["by_type"].items()), columns=["Type", "Count"])
            fig_type = px.bar(df_type, x="Type", y="Count", color="Type", text="Count")
            fig_type.update_layout(template="plotly_white", height=380, showlegend=False, title="Request Distribution")
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("No requests processed yet.")

    with col2:
        st.markdown("**By Status**")
        if summary["by_status"]:
            df_status = pd.DataFrame(list(summary["by_status"].items()), columns=["Status", "Count"])
            fig_status = px.bar(df_status, x="Status", y="Count", color="Status", text="Count")
            fig_status.update_layout(template="plotly_white", height=380, showlegend=False, title="Status Breakdown")
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("No requests processed yet.")

    st.markdown("---")
    st.caption("Built for Firstsource Agentic AI Engineer POC | AI Operations Copilot | Powered by Groq Llama 3.3")

# ---------------- TAB 3: Audit Log ----------------
with tab3:
    st.subheader("Full Processing Log / Audit Trail")
    cases = get_all_cases()
    if cases:
        df = pd.DataFrame(cases)

        URGENCY_COLORS = {
            "Critical": "background-color: #ff4d4d; color: black;",
            "High": "background-color: #ffb3b3; color: black;",
            "Medium": "background-color: #ffe0b3; color: black;",
            "Low": "background-color: #fff5b3; color: black;",
        }

        def highlight_urgency(val):
            return URGENCY_COLORS.get(val, "")

        styled_df = (
            df.style
            .map(highlight_urgency, subset=["urgency"])
            .set_table_styles([
                {
                    "selector": "th",
                    "props": [
                        ("background-color", "#cfe8fc"),
                        ("color", "black"),
                        ("font-weight", "700"),
                        ("text-align", "left"),
                        ("padding", "8px"),
                    ],
                }
            ])
        )
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("No cases logged yet. Process a request in the first tab.")
