"""Optional demo UI: streamlit run app.py"""

import streamlit as st

from core.config import ConfigError, Settings
from core.llm import GrokAPIError
from core.pipeline import run

st.set_page_config(page_title="Grok Bot : recherche de compte", page_icon="🔎")
st.title("Recherche de compte Grok Bot")
st.caption("Entreprises françaises Mid-Market : fiche compte, 3 cas d'usage, premier message.")

company = st.text_input("Nom de l'entreprise", placeholder="Qonto")
if st.button("Lancer la recherche", type="primary", disabled=not company.strip()):
    status = st.status("Recherche en cours...", expanded=True)
    try:
        report = run(company, Settings.from_env(), log=status.write)
    except (ConfigError, GrokAPIError, ValueError) as exc:
        status.update(label="Échec", state="error")
        st.error(str(exc))
    else:
        status.update(label="Terminé", state="complete", expanded=False)
        st.markdown(report)
        st.download_button("Télécharger le Markdown", report, file_name=f"{company.strip().lower()}.md")
