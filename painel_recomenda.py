import pickle
import warnings
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Recomendação de Curso | SENAI Bahia",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }

.main { background: #0d1117; }
section[data-testid="stSidebar"] { background: #111827; border-right: 1px solid #1f2937; }
section[data-testid="stSidebar"] * { color: #d1d5db !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label { color: #9ca3af !important; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .08em; }

.page-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2rem; font-weight: 700;
    color: #f9fafb; letter-spacing: .04em;
    margin-bottom: .1rem;
}
.page-sub { font-size: .82rem; color: #6b7280; margin-bottom: 1.4rem; }

/* Cards */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: .75rem; margin-bottom: 1.25rem; }
.kpi-card {
    background: #161d2b;
    border: 1px solid #1e2d42;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    position: relative; overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute; top:0; left:0;
    width: 3px; height: 100%;
    background: var(--accent);
}
.kpi-label { font-size: .68rem; text-transform: uppercase; letter-spacing: .1em; color: #6b7280; margin-bottom: .3rem; }
.kpi-value { font-family: 'Barlow Condensed', sans-serif; font-size: 2rem; font-weight: 700; color: #f3f4f6; line-height: 1; }
.kpi-delta { font-size: .72rem; margin-top: .25rem; color: #9ca3af; }

/* Table */
.styled-table-wrapper { border-radius: 8px; overflow: hidden; border: 1px solid #1e2d42; }
div[data-testid="stDataFrame"] { background: #0d1117; }

.badge-oport  { background:#064e3b; color:#6ee7b7; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }
.badge-risco  { background:#7f1d1d; color:#fca5a5; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }
.badge-prov   { background:#1e3a5f; color:#93c5fd; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }

.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem; font-weight: 600;
    color: #e5e7eb; text-transform: uppercase;
    letter-spacing: .08em; margin: 1.2rem 0 .6rem;
    border-left: 3px solid #2563eb; padding-left: .6rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    with open("BD_Plan_Curso_Tecnico.pkl","rb") as f: bd = pickle.load(f)
    with open("Base_Concorrentes.pkl","rb") as f: conc = pickle.load(f)
    with open("Base_de_Evasao.pkl","rb") as f: ev = pickle.load(f)
    with open("dVagas.pkl","rb") as f: vagas = pickle.load(f)
    with open("dCLASSIFICACAO.pkl","rb") as f: classif = pickle.load(f)
    with open("dOFERTA_SENAI.pkl","rb") as f: oferta = pickle.load(f)
    with open("Observatorio_2.pkl","rb") as f: obs = pickle.load(f)
    return bd, conc, ev, vagas, classif, oferta, obs

bd, conc, ev, vagas, classif, oferta, obs = load_data()

# ─────────────────────────────────────────────
# JOINS
# ─────────────────────────────────────────────
# Evasão → BD
ev_agg = (ev.groupby("COD_Base_de_Evasao")
            .agg(EVASAO_PAG=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="PAGANTE"].sum()),
                 EVASAO_BOLS=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="GRATUITO"].sum()))
            .reset_index())

df = bd.merge(ev_agg, on="COD_Base_de_Evasao", how="left")

# Vagas → BD
vagas_m = vagas[["COD_VAGAS","VAGAS_2"]].rename(columns={"VAGAS_2":"VAGAS_ULTIM"})
df = df.merge(vagas_m, on="COD_VAGAS", how="left")

# Observatório → CLASSIFICAÇÃO / Oferta Senai
if "CLASSIFICAÇÃO" not in df.columns and "CLASSIFICAÇÃO" in obs.columns:
    obs_m = obs[["COD_Observatorio","CLASSIFICAÇÃO"]].drop_duplicates()
    df = df.merge(obs_m, on="COD_Observatorio", how="left")
if "Oferta Senai" not in df.columns and "Oferta Senai" in obs.columns:
    obs_o = obs[["COD_Observatorio","Oferta Senai"]].drop_duplicates()
    if "Oferta Senai" not in df.columns:
        df = df.merge(obs_o, on="COD_Observatorio", how="left")

# Concorrentes → QTD_CONCORRENTES
conc_agg = (conc.groupby("COD_Concorrentes")["INSTITUIÇÃO"]
               .nunique().reset_index()
               .rename(columns={"INSTITUIÇÃO":"QTD_CONCORRENTES"}))
df = df.merge(conc_agg, on="COD_Concorrentes", how="left")

# ─────────────────────────────────────────────
# MEDIDAS (equivalentes DAX)
# ─────────────────────────────────────────────
def medidas(g):
    mat_pag  = g.loc[g["CONDIÇÃO"]=="PAGANTE","Valor"].sum()
    mat_bols = g.loc[g["CONDIÇÃO"]=="GRATUITO","Valor"].sum()
    mat_canc = g.loc[g["CONDIÇÃO"]=="CANCELADA","Valor"].sum()
    ev_pag   = g.loc[g["CONDIÇÃO"]=="PAGANTE","EVASAO_PAG"].sum()
    ev_bols  = g.loc[g["CONDIÇÃO"]=="GRATUITO","EVASAO_BOLS"].sum()
    vagas_   = g["VAGAS_ULTIM"].max()
    turma_   = g["TURMA"].max()
    conc_    = g["QTD_CONCORRENTES"].max() if "QTD_CONCORRENTES" in g.columns else np.nan

    mat_pag_aj  = 0 if (mat_pag==0 and mat_canc>0) else mat_pag
    mat_bols_aj = 0 if (mat_bols==0 and mat_canc>0) else mat_bols
    mat_pag_tr  = np.nan if mat_pag==0 else mat_pag

    ev_pag_pos = g.loc[(g["CONDIÇÃO"]=="PAGANTE") & (g["EVASAO_PAG"]>0),"EVASAO_PAG"]
    ev_pag_med = ev_pag_pos.mean() if len(ev_pag_pos) else np.nan

    return pd.Series({
        "MAT. PAG.":       mat_pag,
        "MAT. BOLS.":      mat_bols,
        "MAT. CANC.":      mat_canc,
        "EV. PAG.":        ev_pag,
        "EV. BOLS.":       ev_bols,
        "VAGAS":           vagas_,
        "TURMA":           turma_,
        "QTD_CONCORRENTES":conc_,
        "MAT.PAG_AJUST":   mat_pag_aj,
        "MAT.BOLS_AJUST":  mat_bols_aj,
        "MAT.PAG_TRAT":    mat_pag_tr,
        "EV.PAG.MÉDIO":    ev_pag_med,
    })

# ─────────────────────────────────────────────
# SIDEBAR – FILTROS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ Filtros")

    anos = sorted(df["ANO"].dropna().unique().tolist())
    ano_sel = st.multiselect("Ano", anos, default=anos)

    sems = sorted(df["SEMESTRE"].dropna().unique().tolist())
    sem_sel = st.multiselect("Semestre", sems, default=sems)

    regionais = sorted(df["REGIONAL"].dropna().unique().tolist())
    reg_sel = st.multiselect("Regional", regionais, default=regionais)

    unidades = sorted(df.loc[df["REGIONAL"].isin(reg_sel),"UNIDADE"].dropna().unique())
    uni_sel = st.multiselect("Unidade", unidades, default=list(unidades))

    modalidades = sorted(df["MODALIDADE"].dropna().unique())
    mod_sel = st.multiselect("Modalidade", modalidades, default=list(modalidades))

    turnos = sorted(df["TURNO"].dropna().unique())
    tur_sel = st.multiselect("Turno", turnos, default=list(turnos))

    if "CLASSIFICAÇÃO" in df.columns:
        class_opts = sorted(df["CLASSIFICAÇÃO"].dropna().unique())
        class_sel = st.multiselect("Classificação", class_opts, default=list(class_opts))
    else:
        class_sel = []

    if "Oferta Senai" in df.columns:
        of_opts = sorted(df["Oferta Senai"].dropna().unique())
        of_sel = st.multiselect("Oferta SENAI", of_opts, default=list(of_opts))
    else:
        of_sel = []

# ─────────────────────────────────────────────
# APLICAR FILTROS
# ─────────────────────────────────────────────
mask = (
    df["ANO"].isin(ano_sel) &
    df["SEMESTRE"].isin(sem_sel) &
    df["UNIDADE"].isin(uni_sel) &
    df["MODALIDADE"].isin(mod_sel) &
    df["TURNO"].isin(tur_sel)
)
if class_sel and "CLASSIFICAÇÃO" in df.columns:
    mask &= df["CLASSIFICAÇÃO"].isin(class_sel)
if of_sel and "Oferta Senai" in df.columns:
    mask &= df["Oferta Senai"].isin(of_sel)

dff = df[mask].copy()

# ─────────────────────────────────────────────
# CABEÇALHO
# ─────────────────────────────────────────────
st.markdown('<div class="page-title">📊 RECOMENDAÇÃO DE CURSO</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">SENAI Bahia · Planejamento de Cursos Técnicos</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────
total_mat_pag  = dff.loc[dff["CONDIÇÃO"]=="PAGANTE","Valor"].sum()
total_mat_bols = dff.loc[dff["CONDIÇÃO"]=="GRATUITO","Valor"].sum()
total_ev_pag   = dff.loc[dff["CONDIÇÃO"]=="PAGANTE","EVASAO_PAG"].sum()
total_conc     = dff["QTD_CONCORRENTES"].max() if "QTD_CONCORRENTES" in dff.columns else 0
total_turmas   = dff["TURMA"].max()
total_cursos   = dff["CURSO"].nunique()
total_unidades = dff["UNIDADE"].nunique()
taxa_ev = (total_ev_pag / total_mat_pag * 100) if total_mat_pag > 0 else 0

c1,c2,c3,c4,c5,c6 = st.columns(6)
cards = [
    (c1, "Matrículas Pagantes", f"{int(total_mat_pag):,}".replace(",","."), "#2563eb"),
    (c2, "Matrículas Bolsistas", f"{int(total_mat_bols):,}".replace(",","."), "#7c3aed"),
    (c3, "Evasão Pagante", f"{int(total_ev_pag):,}".replace(",","."), "#dc2626"),
    (c4, "Taxa de Evasão", f"{taxa_ev:.1f}%", "#d97706"),
    (c5, "Cursos Ativos", str(total_cursos), "#059669"),
    (c6, "Unidades", str(total_unidades), "#0891b2"),
]
for col, label, val, accent in cards:
    with col:
        st.markdown(f"""
        <div class="kpi-card" style="--accent:{accent}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{val}</div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABELA PRINCIPAL
# ─────────────────────────────────────────────
group_cols = ["ANO","SEMESTRE","UNIDADE","CURSO","MODALIDADE","TURNO"]
if "CLASSIFICAÇÃO" in dff.columns: group_cols.append("CLASSIFICAÇÃO")
if "Oferta Senai"  in dff.columns: group_cols.append("Oferta Senai")
if "QTD_CONCORRENTES" in dff.columns: group_cols.append("QTD_CONCORRENTES")

tabela = dff.groupby(group_cols, dropna=False).apply(medidas).reset_index()

# Remover coluna duplicada se QTD_CONCORRENTES veio do groupby
if "QTD_CONCORRENTES" in group_cols and "QTD_CONCORRENTES" in tabela.columns:
    tabela = tabela.drop(columns=["QTD_CONCORRENTES_y"], errors="ignore")
    tabela = tabela.rename(columns={"QTD_CONCORRENTES_x":"QTD_CONCORRENTES"}, errors="ignore")

st.markdown('<div class="section-title">Detalhamento por Curso / Unidade</div>', unsafe_allow_html=True)

# Formatação numérica
int_cols = ["MAT. PAG.","MAT. BOLS.","MAT. CANC.","EV. PAG.","EV. BOLS.","VAGAS","TURMA","MAT.PAG_AJUST","MAT.BOLS_AJUST"]
for c in int_cols:
    if c in tabela.columns:
        tabela[c] = tabela[c].fillna(0).astype(int)

st.dataframe(
    tabela,
    use_container_width=True,
    height=520,
    column_config={
        "ANO":           st.column_config.NumberColumn("Ano",    format="%d"),
        "SEMESTRE":      st.column_config.NumberColumn("Sem.",   format="%d"),
        "MAT. PAG.":     st.column_config.NumberColumn("Mat. Pag."),
        "MAT. BOLS.":    st.column_config.NumberColumn("Mat. Bols."),
        "MAT. CANC.":    st.column_config.NumberColumn("Mat. Canc."),
        "EV. PAG.":      st.column_config.NumberColumn("Ev. Pag."),
        "EV. BOLS.":     st.column_config.NumberColumn("Ev. Bols."),
        "VAGAS":         st.column_config.NumberColumn("Vagas"),
        "TURMA":         st.column_config.NumberColumn("Turma"),
        "EV.PAG.MÉDIO":  st.column_config.NumberColumn("Ev.Méd.Pag.", format="%.1f"),
        "MAT.PAG_TRAT":  st.column_config.NumberColumn("Mat.Pag.Trat."),
        "QTD_CONCORRENTES": st.column_config.NumberColumn("Concorrentes"),
    }
)

# ─────────────────────────────────────────────
# EXPORTAÇÃO
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">Exportação</div>', unsafe_allow_html=True)

col_xl, col_csv, _ = st.columns([1,1,4])

@st.cache_data
def to_excel(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Recomendacao")
    return buf.getvalue()

@st.cache_data
def to_csv(df):
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")

with col_xl:
    st.download_button(
        "⬇️ Exportar Excel",
        data=to_excel(tabela),
        file_name="recomendacao_curso.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with col_csv:
    st.download_button(
        "⬇️ Exportar CSV",
        data=to_csv(tabela),
        file_name="recomendacao_curso.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(f"🔎 {len(tabela):,} linhas exibidas · Filtro aplicado sobre {len(dff):,} registros")