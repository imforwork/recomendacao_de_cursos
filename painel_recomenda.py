import pickle
import warnings
import pandas as pd
import numpy as np
import streamlit as st
from itables.streamlit import interactive_table
from io import BytesIO

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 1. CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Recomendação de Curso | SENAI Bahia",
    layout="wide",
    initial_sidebar_state="expanded",
)

def apply_custom_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }
    .main { background: #f8f9fa; }
    
    /* Títulos */
    .page-title { font-family: 'Barlow Condensed', sans-serif; font-size: 2.2rem; font-weight: 700; color: #1a1a1a; letter-spacing: .02em; }
    .page-sub { font-size: .9rem; color: #666; margin-bottom: 1.5rem; }
    .section-title { font-family: 'Barlow Condensed', sans-serif; font-size: 1.2rem; font-weight: 600; text-transform: uppercase; color: #004587; margin: 1rem 0; border-left: 4px solid #004587; padding-left: 10px; }

    /* Cards KPI */
    .kpi-box { background: white; padding: 15px; border-radius: 12px; border: 1px solid #E0E0E0; border-left: 5px solid #DDD; }
    .kpi-title { color: #666; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 5px; }
    .kpi-value { color: #1A1A1A; font-size: 1.6rem; font-weight: 800; }
    .kpi-delta { font-size: 0.75rem; margin-top: 5px; }

    /* Filtros Sidebar */
    section[data-testid="stSidebar"] { background: #ffffff; }
    div[data-baseweb="select"] > div:focus-within { border-color: #004587 !important; }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. CARREGAMENTO DE DADOS
# ─────────────────────────────────────────────
@st.cache_data
def load_raw_data():
    files = {
        "bd": "BD_Plan_Curso_Tecnico.pkl",
        "conc": "Base_Concorrentes.pkl",
        "ev": "Base_de_Evasao.pkl",
        "vagas": "dVagas.pkl",
        "obs": "Observatorio_2.pkl"
    }
    data = {}
    for key, path in files.items():
        with open(path, "rb") as f:
            data[key] = pickle.load(f)
    return data["bd"], data["conc"], data["ev"], data["vagas"], data["obs"]

# ─────────────────────────────────────────────
# 3. PROCESSAMENTO E JOINS (ETL)
# ─────────────────────────────────────────────
def process_data(bd, conc, ev, vagas, obs):
    # --- A. Evasão ---
    ev_agg = (ev.groupby("COD_Base_de_Evasao")
                .agg(EVASAO_PAG=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="PAGANTE"].sum()),
                     EVASAO_BOLS=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="GRATUITO"].sum()))
                .reset_index())
    df = bd.merge(ev_agg, on="COD_Base_de_Evasao", how="left")

    # --- B. Vagas ---
    if not vagas.empty:
        vagas_m = vagas.rename(columns={"VAGAS_2": "VAGAS_ULTIM"}).drop_duplicates(subset=["COD_VAGAS"])
        df = df.merge(vagas_m[["COD_VAGAS", "VAGAS_ULTIM"]], on="COD_VAGAS", how="left")
    
    # --- C. Observatório (Classificação e Oferta) ---
    if not obs.empty:
        # Padronização de nomes de colunas do Observatório
        obs_clean = obs.copy()
        col_map = {
            next((c for c in ["CLASSIFICACAO", "CLASSIFICAÇÃO", "Classificação"] if c in obs.columns), "CLASSIFICACAO"): "CLASSIFICACAO",
            next((c for c in ["OFERTA_SENAI", "Oferta Senai", "OFERTA SENAI"] if c in obs.columns), "OFERTA_SENAI"): "OFERTA_SENAI"
        }
        obs_clean = obs_clean.rename(columns=col_map)
        obs_reduced = obs_clean[["COD_Observatorio", "CLASSIFICACAO", "OFERTA_SENAI"]].drop_duplicates(subset=["COD_Observatorio"])
        df = df.merge(obs_reduced, on="COD_Observatorio", how="left")

    # --- D. Concorrentes ---
    conc_agg = conc.groupby("COD_Concorrentes")["INSTITUIÇÃO"].nunique().reset_index().rename(columns={"INSTITUIÇÃO": "QTD_CONCORRENTES"})
    df = df.merge(conc_agg, on="COD_Concorrentes", how="left")
    
    # Preenchimento de nulos básicos
    df["Valor"] = df["Valor"].fillna(0)
    for col in ["VAGAS_ULTIM", "TURMA", "QTD_CONCORRENTES", "EVASAO_PAG", "EVASAO_BOLS"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)
            
    return df

# ─────────────────────────────────────────────
# 4. MOTOR DE CÁLCULO (MEDIDAS TEMPORAIS)
# ─────────────────────────────────────────────
def medidas_temporais(g):
    anos_ref = [2023, 2024, 2025, 2026]
    
    def gerar_serie_temporal(condicao, coluna, is_sum=True):
        valores_num = []
        for ano in anos_ref:
            mask = (g["ANO"] == ano)
            if condicao: mask &= (g["CONDIÇÃO"] == condicao)
            
            sub = g.loc[mask, coluna]
            res = (sub.sum() if is_sum else sub.max()) if not sub.empty else 0
            val = 0 if pd.isna(res) else int(round(float(res)))
            valores_num.append(val)
        
        if sum(valores_num) == 0: return "-"
        
        # Lógica de ícones de tendência
        res_str = []
        for i, atual in enumerate(valores_num):
            if atual == 0: res_str.append("-")
            elif i > 0 and valores_num[i-1] > 0:
                if atual > valores_num[i-1]: res_str.append(f"🟢{atual}")
                elif atual < valores_num[i-1]: res_str.append(f"🔴{atual}")
                else: res_str.append(str(atual))
            else: res_str.append(str(atual))
        return " | ".join(res_str)

    return pd.Series({
        "MAT. PAG. (23-26)":  gerar_serie_temporal("PAGANTE", "Valor"),
        "MAT. BOLS. (23-26)": gerar_serie_temporal("GRATUITO", "Valor"),
        "MAT. CANC. (23-26)": gerar_serie_temporal("CANCELADA", "Valor"),
        "VAGAS (23-26)":      gerar_serie_temporal(None, "VAGAS_ULTIM", False),
        "TURMAS (23-26)":     gerar_serie_temporal(None, "TURMA", False),
        "CONCORRENTES":       int(g["QTD_CONCORRENTES"].max()) if "QTD_CONCORRENTES" in g.columns else 0
    })

# ─────────────────────────────────────────────
# 5. INTERFACE SIDEBAR (FILTROS)
# ─────────────────────────────────────────────
def build_sidebar(df):
    with st.sidebar:
        st.markdown("### ✦ CENTRO DE COMANDO")
        st.divider()

        def multiselect_all(label, options, key):
            sel = st.multiselect(label, ["Selecionar Todos"] + list(options), key=key)
            if "Selecionar Todos" in sel or not sel: return list(options)
            return sel

        # Agrupamento Temporal
        st.markdown("**📅 TEMPORAL**")
        c1, c2 = st.columns(2)
        with c1: ano_sel = multiselect_all("ANO", sorted(df["ANO"].unique()), "f_ano")
        with c2: sem_sel = multiselect_all("SEM.", sorted(df["SEMESTRE"].unique()), "f_sem")
        
        st.divider()
        # Agrupamento Geográfico
        st.markdown("**🌎 GEOGRÁFICO**")
        reg_sel = multiselect_all("REGIONAL", sorted(df["REGIONAL"].unique()), "f_reg")
        uni_sel = multiselect_all("UNIDADE", sorted(df[df["REGIONAL"].isin(reg_sel)]["UNIDADE"].unique()), "f_uni")
        
        st.divider()
        # Agrupamento Educacional
        st.markdown("**📚 EDUCACIONAL**")
        mod_sel = multiselect_all("MODALIDADE", sorted(df["MODALIDADE"].unique()), "f_mod")
        tur_sel = multiselect_all("TURNO", sorted(df["TURNO"].unique()), "f_tur")
        curso_sel = multiselect_all("CURSO", sorted(df["CURSO"].unique()), "f_curso")
        
    return ano_sel, sem_sel, reg_sel, uni_sel, mod_sel, tur_sel, curso_sel

# ─────────────────────────────────────────────
# 6. EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────
apply_custom_styles()
bd, conc, ev, vagas, obs = load_raw_data()
df = process_data(bd, conc, ev, vagas, obs)

# Sidebar e Filtros
ano_sel, sem_sel, reg_sel, uni_sel, mod_sel, tur_sel, curso_sel = build_sidebar(df)

# Criação das Máscaras
mask_base = (df["SEMESTRE"].isin(sem_sel) & df["UNIDADE"].isin(uni_sel) & 
             df["MODALIDADE"].isin(mod_sel) & df["TURNO"].isin(tur_sel) & df["CURSO"].isin(curso_sel))

dff_tabela = df[mask_base].copy()
dff_kpi = df[mask_base & df["ANO"].isin(ano_sel)].copy()

# --- HEADER ---
st.markdown('<div class="page-title">📊 INTELIGÊNCIA DE MERCADO</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">SENAI Bahia · Matriz de Recomendação de Cursos Técnicos</div>', unsafe_allow_html=True)

# --- BLOCO DE KPIs ---
st.markdown('<div class="section-title">Indicadores de Performance (Ano Selecionado)</div>', unsafe_allow_html=True)

def calc_kpis(current_df, full_df, ano_atual, mask_filtros):
    ano_ant = ano_atual - 1
    prev_df = full_df[(full_df["ANO"] == ano_ant) & mask_filtros]
    
    def get_v(dataframe, cond): return dataframe[dataframe["CONDIÇÃO"] == cond]["Valor"].sum()
    
    # Matrículas
    m_pag = get_v(current_df, "PAGANTE"); m_pag_ant = get_v(prev_df, "PAGANTE")
    m_bols = get_v(current_df, "GRATUITO"); m_bols_ant = get_v(prev_df, "GRATUITO")
    
    # Evasão
    e_pag = current_df[current_df["CONDIÇÃO"] == "PAGANTE"]["EVASAO_PAG"].sum()
    e_pag_ant = prev_df[prev_df["CONDIÇÃO"] == "PAGANTE"]["EVASAO_PAG"].sum()
    
    return (m_pag, m_pag_ant), (m_bols, m_bols_ant), (e_pag, e_pag_ant)

# Cálculo dos Deltas e Exibição
ult_ano = max(ano_sel) if ano_sel else 2025
(mp, mp_a), (mb, mb_a), (ep, ep_a) = calc_kpis(dff_kpi, df, ult_ano, mask_base)

def render_kpi(col, label, val, ant, color, is_evasao=False):
    delta = ((val - ant)/ant*100) if ant > 0 else 0
    seta = "▲" if delta >= 0 else "▼"
    # Se for evasão, subir é ruim (vermelho)
    cor_delta = ("#dc3545" if delta > 0 else "#28a745") if is_evasao else ("#28a745" if delta >= 0 else "#dc3545")
    
    with col:
        st.markdown(f"""
        <div class="kpi-box" style="border-left-color: {color};">
            <div class="kpi-title">{label}</div>
            <div class="kpi-value">{int(val)}</div>
            <div class="kpi-delta"><span style="color:{cor_delta}">{seta} {delta:.1f}%</span> vs {ult_ano-1}</div>
        </div>
        """, unsafe_allow_html=True)

ck1, ck2, ck3, ck4 = st.columns(4)
render_kpi(ck1, "Matrículas Pagante", mp, mp_a, "#004587")
render_kpi(ck2, "Matrículas Bolsista", mb, mb_a, "#004587")
render_kpi(ck3, "Evasão Pagante", ep, ep_a, "#dc8d26", is_evasao=True)
with ck4:
    total_conc = dff_kpi["QTD_CONCORRENTES"].sum() if "QTD_CONCORRENTES" in dff_kpi.columns else 0
    st.markdown(f"""<div class="kpi-box" style="border-left-color: #00A199;"><div class="kpi-title">Concorrentes Diretos</div><div class="kpi-value">{int(total_conc)}</div><div class="kpi-delta">Mapeamento Atual</div></div>""", unsafe_allow_html=True)

# --- FILTROS DE TOPO (OBSERVATÓRIO) ---
st.divider()
st.markdown('<div class="section-title">🔍 Refinar Detalhamento (Observatório/PA)</div>', unsafe_allow_html=True)
ct1, ct2 = st.columns([2, 1])
with ct1:
    c_opts = sorted(df["CLASSIFICACAO"].dropna().unique()) if "CLASSIFICACAO" in df.columns else []
    c_sel = st.multiselect("🏷️ Classificação Preditiva", c_opts, placeholder="Todas as Classificações")
with ct2:
    o_val = st.pills("🚀 Oferta SENAI Atual", options=["Sim", "Não"], selection_mode="single")

# Aplicação Final e Tabela
if c_sel: dff_tabela = dff_tabela[dff_tabela["CLASSIFICACAO"].isin(c_sel)]
if o_val: dff_tabela = dff_tabela[dff_tabela["OFERTA_SENAI"] == o_val]

if not dff_tabela.empty:
    g_cols = ["CURSO", "MODALIDADE", "TURNO"]
    for c in ["CLASSIFICACAO", "OFERTA_SENAI"]:
        if c in dff_tabela.columns: g_cols.append(c)
        
    tabela_final = dff_tabela.groupby(g_cols, dropna=False, as_index=False).apply(medidas_temporais).reset_index()
    if "level_0" in tabela_final.columns: tabela_final.drop(columns=["level_0"], inplace=True)
    
    interactive_table(tabela_final, paging=False, scrollY="500px", scrollX=True, columnDefs=[{"className": "dt-center", "targets": "_all"}])
else:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")