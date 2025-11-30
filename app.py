import pathlib
import datetime as dt
import pandas as pd
import streamlit as st

# =============================
# DOCX (descrizioni funzioni)
# =============================

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# =============================
# CONFIG COLORI PER FUNZIONE
# =============================

FUNZIONE_COLORI = {
    "Area Vendita": "#1f77b4",
    "Merchandising": "#ff7f0e",
    "Ufficio Acquisti": "#2ca02c",
    "Ufficio Tecnico": "#d62728",
    "Ufficio IT": "#9467bd",
    "Affari Generali": "#8c564b",
    "Amministrazione-Tesoreria": "#e377c2",
    "Personale": "#7f7f7f",
    "Personale / HR": "#7f7f7f",
    "Logistica": "#17becf",
    "Marketing": "#bcbd22",
}


def badge_funzione(funzione: str) -> str:
    colore = FUNZIONE_COLORI.get(funzione, "#555")
    bg = f"{colore}20"
    html = f"""
    <span style="
        display:inline-block;
        padding:0.3rem 0.7rem;
        border-radius:999px;
        border:1px solid {colore};
        background-color:{bg};
        color:{colore};
        font-weight:600;
        font-size:0.9rem;
        margin-bottom:0.3rem;
    ">{funzione}</span>
    """
    return html


# =============================
# AUTENTICAZIONE SEMPLICE
# =============================

def check_password():
    """
    Semplice protezione con password.
    - In locale usa sempre DEFAULT_PASSWORD.
    - Su Streamlit Cloud puoi opzionalmente definire APP_PASSWORD nei secrets.
    """

    DEFAULT_PASSWORD = "demo2025"  # <--- Cambia qui se vuoi un'altra password

    def _password_ok():
        # di default usiamo la password hardcoded
        pwd_corretta = DEFAULT_PASSWORD

        # se esistono secrets e APP_PASSWORD è definita, la usiamo (senza far esplodere nulla)
        try:
            if "APP_PASSWORD" in st.secrets:
                pwd_corretta = st.secrets["APP_PASSWORD"]
        except Exception:
            # nessun secrets.toml o altro problema: ignoriamo e teniamo la default
            pwd_corretta = DEFAULT_PASSWORD

        if st.session_state.get("password_input", "") == pwd_corretta:
            st.session_state["auth_ok"] = True
            st.session_state["password_input"] = ""
        else:
            st.session_state["auth_ok"] = False

    if "auth_ok" not in st.session_state:
        st.session_state["auth_ok"] = False

    if not st.session_state["auth_ok"]:
        st.title("🔐 Accesso demo apertura negozio")
        st.write("Inserisci la password per visualizzare la demo.")

        st.text_input(
            "Password",
            type="password",
            key="password_input",
            on_change=_password_ok,
        )

        # Mostra errore solo se ha provato qualcosa ed è sbagliata
        if (
            st.session_state.get("password_input", "") == ""
            and st.session_state.get("auth_ok") is False
        ):
            # niente messaggio finché non prova
            pass
        elif st.session_state.get("auth_ok") is False:
            st.error("Password errata.")

        st.stop()


# =============================
# CARICAMENTO CSV
# =============================

def carica_prontuario(percorso_default="Prontuario_Funzioni.csv"):
    st.sidebar.subheader("📂 Sorgente dati")

    file_caricato = st.sidebar.file_uploader(
        "Carica Prontuario_Funzioni.csv",
        type=["csv"],
        help="Se non carichi nulla, userà il file locale nella cartella."
    )

    if file_caricato:
        df = pd.read_csv(file_caricato, sep=";")
    else:
        path = pathlib.Path(percorso_default)
        if not path.exists():
            st.error(f"File '{percorso_default}' non trovato.")
            st.stop()
        df = pd.read_csv(path, sep=";", encoding="utf-8")

    colonne = [
        "Funzione",
        "Operazione",
        "Tempistica_GG",
        "Tempistica_descrizione",
        "Di_cosa_ho_bisogno",
        "Da_chi",
        "Note",
    ]
    for c in colonne:
        if c not in df.columns:
            st.error(f"Manca la colonna '{c}' nel CSV.")
            st.stop()

    df["Tempistica_GG"] = pd.to_numeric(df["Tempistica_GG"], errors="coerce")
    return df


# =============================
# LETTURA DESCRIZIONI DOCX
# =============================

@st.cache_data
def carica_descrizioni_funzioni(docx_path="PRONTUARIO NUOVE APERTURE.docx"):
    descrizioni = {}
    info_msg = ""

    if not HAS_DOCX:
        return {}, "Modulo python-docx mancante (pip install python-docx)."

    path = pathlib.Path(docx_path)
    if not path.exists():
        return {}, f"File DOCX '{docx_path}' non trovato nella cartella."

    from docx import Document as DocxDocument
    doc = DocxDocument(path)

    paragraphs = doc.paragraphs
    n = len(paragraphs)
    i = 0

    while i < n:
        p = paragraphs[i]
        text = p.text.strip()

        if "Questo capitolo" in text:
            nome_funzione = text.split("Questo capitolo", 1)[0].strip(" :–-")
            blocco = [text]

            j = i + 1
            while j < n:
                t2 = paragraphs[j].text.strip()

                if "Questo capitolo" in t2 or "Schema Riassuntivo" in t2:
                    break

                if t2.strip():
                    blocco.append(t2)

                j += 1

            descrizioni[nome_funzione] = "\n\n".join(blocco)
            i = j
        else:
            i += 1

    return descrizioni, info_msg


def trova_descrizione_funzione(funzione: str, descrizioni: dict):
    if funzione in descrizioni:
        return funzione, descrizioni[funzione]

    for k in descrizioni.keys():
        if k.lower() in funzione.lower() or funzione.lower() in k.lower():
            return k, descrizioni[k]

    return None, None


# =============================
# VISTA: GIORNO PER GIORNO
# =============================

def mostra_attivita_per_giorno(df, giorno, query, descrizioni):

    df_g = df[df["Tempistica_GG"] == giorno]

    if query.strip():
        q = query.lower()
        df_g = df_g[
            df_g["Operazione"].str.lower().str.contains(q, na=False)
            | df_g["Note"].str.lower().str.contains(q, na=False)
            | df_g["Di_cosa_ho_bisogno"].str.lower().str.contains(q, na=False)
            | df_g["Funzione"].str.lower().str.contains(q, na=False)
        ]

    st.markdown(f"## 🗓️ Giorno {giorno}")

    if df_g.empty:
        st.info("Nessuna attività per questo giorno con i filtri attuali.")
        return

    for funzione in sorted(df_g["Funzione"].dropna().unique()):
        st.markdown("---")
        st.markdown(badge_funzione(funzione), unsafe_allow_html=True)
        st.markmarkdown = st.markdown  # (safe alias, in case)
        st.markdown("_Attività da svolgere oggi per questa funzione:_")

        df_f = df_g[df_g["Funzione"] == funzione].reset_index(drop=True)

        key_descr, _ = trova_descrizione_funzione(funzione, descrizioni)
        col_btn, _ = st.columns([1, 3])

        with col_btn:
            if key_descr:
                if st.button(
                    "📖 Descrizione completa funzione",
                    key=f"desc_{giorno}_{funzione}",
                ):
                    st.session_state["vista"] = "funzione"
                    st.session_state["funzione_dett"] = funzione
                    st.rerun()

        for idx, row in df_f.iterrows():
            st.markdown(f"#### ▶️ Passo {idx+1}: **{row['Operazione']}**")

            col1, col2 = st.columns(2)
            with col1:
                tgg = "—" if pd.isna(row["Tempistica_GG"]) else int(row["Tempistica_GG"])
                st.markdown(f"- **Giorno riferimento:** {tgg}")
                if isinstance(row["Tempistica_descrizione"], str) and row["Tempistica_descrizione"].strip():
                    st.markdown(f"- **Nota:** {row['Tempistica_descrizione']}")

            with col2:
                st.markdown(f"- **Da chi:** {row['Da_chi']}")

            st.markdown("**Cosa fare / Di cosa ho bisogno:**")
            if isinstance(row["Di_cosa_ho_bisogno"], str) and row["Di_cosa_ho_bisogno"].strip():
                st.write(row["Di_cosa_ho_bisogno"])
            else:
                st.write("_Nessuna informazione specifica._")

            if isinstance(row["Note"], str) and row["Note"].strip():
                st.markdown("**Note:**")
                st.write(row["Note"])


# =============================
# VISTA: ATTIVITÀ SENZA GIORNO
# =============================

def mostra_attivita_senza_giorni(df, query):

    df_na = df[df["Tempistica_GG"].isna()]

    if query.strip():
        q = query.lower()
        df_na = df_na[
            df_na["Operazione"].str.lower().str.contains(q, na=False)
            | df_na["Note"].str.lower().str.contains(q, na=False)
            | df_na["Di_cosa_ho_bisogno"].str.lower().str.contains(q, na=False)
            | df_na["Funzione"].str.lower().str.contains(q, na=False)
        ]

    if df_na.empty:
        return

    st.markdown("---")
    st.markdown("### 🧾 Attività senza giorno definito")

    for _, row in df_na.iterrows():
        st.markdown(f"#### 🔹 [{row['Funzione']}] {row['Operazione']}")
        if isinstance(row["Di_cosa_ho_bisogno"], str) and row["Di_cosa_ho_bisogno"].strip():
            st.write(row["Di_cosa_ho_bisogno"])
        if isinstance(row["Note"], str) and row["Note"].strip():
            st.write(f"**Note:** {row['Note']}")


# =============================
# VISTA: DETTAGLIO FUNZIONE
# =============================

def vista_dettaglio_funzione(funzione, descrizioni):
    st.markdown("## 📖 Dettaglio funzione")
    st.markdown(badge_funzione(funzione), unsafe_allow_html=True)
    st.markdown(f"### **{funzione}**")

    key_descr, testo = trova_descrizione_funzione(funzione, descrizioni)

    if not testo:
        st.warning("Nessuna descrizione trovata nel DOCX per questa funzione.")
    else:
        paragrafi = [p.strip() for p in testo.split("\n") if p.strip()]

        if paragrafi:
            intro = paragrafi[0]
            st.markdown(f"> {intro}")
            resto = paragrafi[1:]
        else:
            resto = []

        if resto:
            st.markdown("### Punti principali della funzione:")
            for p in resto:
                st.markdown(f"- {p}")
        else:
            st.info("Non ci sono ulteriori paragrafi strutturabili.")

        with st.expander("📜 Testo originale completo dal prontuario"):
            st.write(testo)

    st.markdown("---")
    if st.button("⬅ Torna alla guida giorno per giorno"):
        st.session_state["vista"] = "piano"
        st.rerun()


# =============================
# APP STREAMLIT
# =============================

def main():
    st.set_page_config(
        page_title="Prontuario Apertura Negozio",
        page_icon="📘",
        layout="wide",
    )

    # ---- password prima di tutto ----
    check_password()

    if "vista" not in st.session_state:
        st.session_state["vista"] = "piano"
    if "funzione_dett" not in st.session_state:
        st.session_state["funzione_dett"] = None

    st.title("📘 Prontuario Nuove Aperture – Timeline Giorno per Giorno")

    df = carica_prontuario()
    descrizioni, info_docx = carica_descrizioni_funzioni()

    if info_docx:
        st.sidebar.warning(info_docx)

    # Vista dettaglio funzione
    if st.session_state["vista"] == "funzione":
        vista_dettaglio_funzione(st.session_state["funzione_dett"], descrizioni)

        # Firma anche in questa vista
        st.markdown(
            """
            <style>
            .firma-bottom-right {
                position: fixed;
                bottom: 12px;
                right: 12px;
                font-size: 13px;
                color: #5a5a5a;
                padding: 6px 12px;
                border-radius: 6px;
                z-index: 99999;
                font-style: italic;
                font-weight: 500;
                background-color: rgba(255,255,255,0.8);
                backdrop-filter: blur(4px);
                box-shadow: 0px 0px 8px rgba(0,0,0,0.15);
            }
            </style>
            <div class="firma-bottom-right">
                Powered by Alessandro Camera | Project Demo
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # Vista principale
    st.caption("Seleziona un giorno e vedi, funzione per funzione, cosa deve essere fatto passo dopo passo.")

    st.sidebar.markdown("## 📅 Data apertura prevista")
    oggi = dt.date.today()
    data_apertura = st.sidebar.date_input("Data", value=oggi)

    giorni_mancanti = max(1, (data_apertura - oggi).days)

    df_num = df.dropna(subset=["Tempistica_GG"])
    if df_num.empty:
        st.error("Nel file non ci sono valori numerici in 'Tempistica_GG'.")
        st.stop()

    max_t = int(df_num["Tempistica_GG"].max())
    giorno_default = min(max(giorni_mancanti, 1), max_t)

    st.sidebar.markdown("## ⏱️ Giorno del piano")
    giorno = st.sidebar.slider("Giorno", 1, max_t, giorno_default)

    st.sidebar.markdown(f"**Mancano circa {giorni_mancanti} giorni all'apertura**")

    query = st.sidebar.text_input("🔎 Cerca nelle attività", "")

    mostra_attivita_per_giorno(df, giorno, query, descrizioni)
    mostra_attivita_senza_giorni(df, query)

    st.markdown("---")
    st.markdown("### 📊 Riepilogo")

    col1, col2, col3 = st.columns(3)
    col1.metric("Numero funzioni", df["Funzione"].nunique())
    col2.metric("Totale attività", len(df))
    col3.metric("Con giorni definiti", df_num.shape[0])

    # =============================
    # FIRMA IN BASSO A DESTRA
    # =============================
    st.markdown(
        """
        <style>
        .firma-bottom-right {
            position: fixed;
            bottom: 12px;
            right: 12px;
            font-size: 13px;
            color: #5a5a5a;
            padding: 6px 12px;
            border-radius: 6px;
            z-index: 99999;
            font-style: italic;
            font-weight: 500;
            background-color: rgba(255,255,255,0.8);
            backdrop-filter: blur(4px);
            box-shadow: 0px 0px 8px rgba(0,0,0,0.15);
        }
        </style>
        <div class="firma-bottom-right">
            Powered by Alessandro Camera | Project Demo
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
