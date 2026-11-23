"""Optional demo UI: streamlit run app.py"""

import streamlit as st

from core.config import ConfigError, Settings
from core.llm import GrokAPIError
from core.pipeline import run

st.set_page_config(page_title="Grok Bot account research", page_icon="🔎")
st.title("Grok Bot account research")
st.caption("French Mid-Market companies: account brief, 3 use cases, first outreach message.")

company = st.text_input("Company name", placeholder="Qonto")
if st.button("Run research", type="primary", disabled=not company.strip()):
    status = st.status("Researching...", expanded=True)
    try:
        report = run(company, Settings.from_env(), log=status.write)
    except (ConfigError, GrokAPIError, ValueError) as exc:
        status.update(label="Failed", state="error")
        st.error(str(exc))
    else:
        status.update(label="Done", state="complete", expanded=False)
        st.markdown(report)
        st.download_button("Download Markdown", report, file_name=f"{company.strip().lower()}.md")
