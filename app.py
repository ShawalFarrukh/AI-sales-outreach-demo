import json
import csv
import io
import streamlit as st

from test_api import ask_ai

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="AI tool Demo",
    page_icon="⚡",
    layout="centered",
)

st.title("⚡AI – Ops & Sales Assistant")
st.caption("Turn company notes into opportunity insights and ready-to-send outreach emails.")

# -------------------------------------------------
# Sender (shared for both modes)
# -------------------------------------------------
st.subheader("Sender (your outreach identity)")
sender_company = st.text_input("Sender company", value="Northeast co.")
sender_service = st.text_input(
    "What you offer",
    value="automation + AI tools (dashboards, CRM workflows, outreach automation)",
)
sender_tone = st.selectbox(
    "Tone",
    ["professional, concise, helpful", "friendly and direct", "formal"],
    index=0,
)

st.divider()

# -------------------------------------------------
# Mode selector
# -------------------------------------------------
mode = st.radio("Mode", ["Single company", "Batch (CSV)"], horizontal=True)
st.divider()

# -------------------------------------------------
# SINGLE MODE
# -------------------------------------------------
if mode == "Single company":
    company_name = st.text_input("Company name", value="Acme Logistics")
    industry = st.text_input("Industry", value="Logistics")
    notes = st.text_area(
        "Notes / pain points",
        value="Manual follow-ups, Excel-based tracking",
        height=120,
    )

    if st.button("Generate Insight"):
        with st.spinner("Analyzing..."):
            raw = ask_ai(
                company_name,
                industry,
                notes,
                sender_company=sender_company,
                sender_service=sender_service,
                sender_tone=sender_tone,
            )
            data = json.loads(raw)

        st.success("Analysis complete")

        st.subheader("Category")
        st.write(data["category"])

        st.subheader("Opportunity Summary")
        st.write(data["opportunity_summary"])

        st.subheader("Draft Email")

        st.text_input(
            "Subject",
            value=data["email_subject"],
            key="email_subject_display",
        )

        st.text_area(
            "Body",
            value=data["email_body"],
            height=260,
            key="email_body_display",
        )

        import streamlit.components.v1 as components
        safe_body = (data["email_body"] or "").replace("`", "\\`")

        components.html(
            f"""
            <style>
                .copy-btn {{
                    background-color: #262730;
                    color: #fafafa;
                    border: 1px solid #3c3f4a;
                    border-radius: 6px;
                    padding: 8px 14px;
                    font-size: 14px;
                    cursor: pointer;
               }}

               .copy-btn:hover {{
                   background-color: #323443;
               }}
           </style>

           <button
               class="copy-btn"
               onclick="navigator.clipboard.writeText(`{safe_body}`)"
           >
               📋 Copy email body
           </button>
           """,
           height=55,
     )


# -------------------------------------------------
# BATCH MODE
# -------------------------------------------------
else:
    st.markdown("CSV must include these columns:")
    st.code("company_name,industry,notes", language="text")

    tab_upload, tab_paste = st.tabs(["Upload CSV", "Paste CSV"])

    uploaded = None
    pasted = None

    with tab_upload:
        uploaded = st.file_uploader("Upload CSV", type=["csv"])

    with tab_paste:
        st.caption("Paste CSV rows including the header row.")
        pasted = st.text_area(
            "CSV input",
            height=220,
            placeholder=(
                "company_name,industry,notes\n"
                "Acme Logistics,Logistics,\"Manual follow-ups, Excel-based tracking\"\n"
                "BetaSoft,SaaS,\"No CRM, outbound heavy\""
            ),
        )

    max_rows = st.number_input(
        "Max rows to process (safety)",
        min_value=1,
        max_value=50,
        value=10,
    )

    # Decide input source -> get raw CSV text
    csv_text = None
    if uploaded is not None:
        csv_text = uploaded.read().decode("utf-8-sig")  # strips BOM if present
    elif pasted and pasted.strip():
        csv_text = pasted.strip()

    if csv_text and st.button("Run Batch"):
        # Read CSV
        reader = csv.DictReader(io.StringIO(csv_text))

        if not reader.fieldnames:
            st.error("Could not read CSV headers. Make sure the first row is the header row.")
            st.stop()

        # Normalize headers (fixes spaces/case issues)
        normalized_fieldnames = [h.strip().lower() for h in reader.fieldnames]
        reader.fieldnames = normalized_fieldnames

        # Validate required columns
        required_cols = {"company_name", "industry", "notes"}
        missing = required_cols - set(reader.fieldnames)
        if missing:
            st.error(f"Missing required column(s): {', '.join(sorted(missing))}")
            st.stop()

        # Read rows (normalize values)
        rows = []
        for r in reader:
            clean = {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
            if any(clean.get(c, "") for c in required_cols):  # skip totally empty lines
                rows.append(clean)

        rows = rows[:max_rows]

        if not rows:
            st.error("No rows found in CSV (after header).")
            st.stop()

        results = []

        with st.spinner("Processing batch..."):
            for row in rows:
                raw = ask_ai(
                    row.get("company_name", ""),
                    row.get("industry", ""),
                    row.get("notes", ""),
                    sender_company=sender_company,
                    sender_service=sender_service,
                    sender_tone=sender_tone,
                )
                data = json.loads(raw)

                results.append(
                    {
                        "company_name": row.get("company_name", ""),
                        "industry": row.get("industry", ""),
                        "category": data["category"],
                        "opportunity_summary": data["opportunity_summary"],
                        "email_subject": data["email_subject"],
                        "email_body": data["email_body"],
                    }
                )

        st.success(f"Processed {len(results)} companies")

        st.subheader("Results")
        st.dataframe(results, use_container_width=True)

        # Export CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

        st.download_button(
            "Download results as CSV",
            data=output.getvalue(),
            file_name="ai_results.csv",
            mime="text/csv",
        )
