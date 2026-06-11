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
    
    .page-title { font-family: 'Barlow Condensed', sans-serif; font-size: 2.2rem; font-weight: 700; color: #1a1a1a; letter-spacing: .02em; }
    .page-sub { font-size: .9rem; color: #666; margin-bottom: 1.5rem; }
    .section-title { font-family: 'Barlow Condensed', sans-serif; font-size: 1.2rem; font-weight: 600; text-transform: uppercase; color: #004587; margin: 1rem 0; border-left: 4px solid #004587; padding-left: 10px; }

    .kpi-box { background: white; padding: 15px; border-radius: 12px; border: 1px solid #E0E0E0; border-left: 5px solid #DDD; height: 100%; }
    .kpi-title { color: #666; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 5px; }
    .kpi-value { color: #1A1A1A; font-size: 1.6rem; font-weight: 800; }
    .kpi-delta { font-size: 0.75rem; margin-top: 5px; }

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
        "vagas": "dVagas.pkl"
    }
    data = {}
    for key, path in files.items():
        with open(path, "rb") as f:
            data[key] = pickle.load(f)
    return data["bd"], data["conc"], data["ev"], data["vagas"]

# ─────────────────────────────────────────────
# 3. PROCESSAMENTO E JOINS
# ─────────────────────────────────────────────
def process_data(bd, conc, ev, vagas):
    ev_agg = (ev.groupby("COD_Base_de_Evasao")
                .agg(EVASAO_PAG=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="PAGANTE"].sum()),
                     EVASAO_BOLS=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="GRATUITO"].sum()))
                .reset_index())
    df = bd.merge(ev_agg, on="COD_Base_de_Evasao", how="left")

    if not vagas.empty:
        vagas_m = vagas.rename(columns={"VAGAS_2": "VAGAS_ULTIM"}).drop_duplicates(subset=["COD_VAGAS"])
        df = df.merge(vagas_m[["COD_VAGAS", "VAGAS_ULTIM"]], on="COD_VAGAS", how="left")
    
    if not bd.empty:
        obs_clean = bd.copy()
        col_map = {
            next((c for c in ["CLASSIFICACAO", "CLASSIFICAÇÃO", "Classificação"] if c in bd.columns), "CLASSIFICACAO"): "CLASSIFICACAO",
            next((c for c in ["OFERTA_SENAI", "Oferta Senai", "OFERTA SENAI"] if c in bd.columns), "OFERTA_SENAI"): "OFERTA_SENAI"
        }
        obs_clean = obs_clean.rename(columns=col_map)
        obs_reduced = obs_clean[["COD_Observatorio", "CLASSIFICACAO", "OFERTA_SENAI"]].drop_duplicates(subset=["COD_Observatorio"])
        df = df.merge(obs_reduced, on="COD_Observatorio", how="left")

    # Join de Concorrentes (Mantenho para a tabela, mas usaremos a base bruta 'conc' para os Cards)
    conc_agg = conc.groupby("COD_Concorrentes")["INSTITUIÇÃO"].nunique().reset_index().rename(columns={"INSTITUIÇÃO": "QTD_CONCORRENTES"})
    df = df.merge(conc_agg, on="COD_Concorrentes", how="left")
    
    df["Valor"] = df["Valor"].fillna(0)
    for col in ["VAGAS_ULTIM", "TURMA", "QTD_CONCORRENTES", "EVASAO_PAG", "EVASAO_BOLS"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    return df

# ─────────────────────────────────────────────
# NOVO: FUNÇÃO DE CÁLCULO DE TENDÊNCIA (LÓGICA EXCEL)
# ─────────────────────────────────────────────
def calcular_tendencia_linear(valores_num):
    """
    Simula a lógica PROJ.LIN do Excel:
    Tenta 4 pontos (2023-2026), se falhar tenta os últimos 3.
    Retorna a classificação baseada no coeficiente angular (slope).
    """
    # X para 4 anos e 3 anos
    x4 = np.array([1, 2, 3, 4])
    x3 = np.array([2, 3, 4])
    y = np.array(valores_num, dtype=float)

    def fit_slope(xi, yi):
        # Filtra para garantir que temos dados significativos (evita erro de projeção com zeros)
        valid_mask = yi > 0
        if sum(valid_mask) < 2: return None
        try:
            slope, _ = np.polyfit(xi, yi, 1)
            return slope
        except: return None

    # Tenta 4 anos
    slope = fit_slope(x4, y)
    
    # Se erro/sem dados, tenta os últimos 3 anos
    if slope is None:
        slope = fit_slope(x3, y[1:])

    if slope is None: return "S/ Param."

    # Classificação conforme fórmula da imagem
    if slope > 1: return "Alta"
    if slope > 0: return "Leve Alta"
    if slope < -1: return "Baixa"
    return "Leve Baixa"

# ─────────────────────────────────────────────
# 4. MOTOR DE CÁLCULO (MEDIDAS TEMPORAIS ATUALIZADO)
# ─────────────────────────────────────────────
def medidas_temporais(g):
    anos_ref = [2023, 2024, 2025, 2026]
    
    def obter_valores_brutos(condicao, coluna, is_sum=True):
        valores = []
        for ano in anos_ref:
            mask = (g["ANO"] == ano)
            if condicao: mask &= (g["CONDIÇÃO"] == condicao)
            sub = g.loc[mask, coluna]
            res = (sub.sum() if is_sum else sub.max()) if not sub.empty else 0
            valores.append(0 if pd.isna(res) else int(round(float(res))))
        return valores

    def formatar_string_temporal(valores_num):
        if sum(valores_num) == 0: return "-"
        res_str = []
        for i, atual in enumerate(valores_num):
            if atual == 0: res_str.append("-")
            elif i > 0 and valores_num[i-1] > 0:
                if atual > valores_num[i-1]: res_str.append(f"🡅 {atual}")
                elif atual < valores_num[i-1]: res_str.append(f"🡇 {atual}")
                else: res_str.append(str(atual))
            else: res_str.append(str(atual))
        return " | ".join(res_str)

    # Coleta de dados brutos para Tendências
    v_mat_pag = obter_valores_brutos("PAGANTE", "Valor")
    v_mat_bols = obter_valores_brutos("GRATUITO", "Valor")
    v_ev_pag = obter_valores_brutos("PAGANTE", "EVASAO_PAG")
    v_ev_bols = obter_valores_brutos("GRATUITO", "EVASAO_BOLS")

    return pd.Series({
        "MAT. PAG. (23-26)":  formatar_string_temporal(v_mat_pag),
        "MAT. BOLS. (23-26)": formatar_string_temporal(v_mat_bols),
        "EV. PAG. (23-26)":   formatar_string_temporal(v_ev_pag),
        "EV. BOLS. (23-26)":  formatar_string_temporal(v_ev_bols),
        "TEND. MAT. PAG.":    calcular_tendencia_linear(v_mat_pag),
        "TEND. MAT. BOLS.":   calcular_tendencia_linear(v_mat_bols),
        "TEND. EV. PAG.":     calcular_tendencia_linear(v_ev_pag),
        "TEND. EV. BOLS.":    calcular_tendencia_linear(v_ev_bols),
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
        st.markdown("**📅 TEMPORAL**")
        # c1, c2 = st.columns(2)
        ano_sel = multiselect_all("ANO", sorted(df["ANO"].unique()), "f_ano")
        sem_sel = multiselect_all("SEMESTRE", sorted(df["SEMESTRE"].unique()), "f_sem")
        st.divider()
        st.markdown("**🌎 GEOGRÁFICO**")
        reg_sel = multiselect_all("REGIONAL", sorted(df["REGIONAL"].unique()), "f_reg")
        uni_sel = multiselect_all("UNIDADE", sorted(df[df["REGIONAL"].isin(reg_sel)]["UNIDADE"].unique()), "f_uni")
        st.divider()
        st.markdown("**📚 EDUCACIONAL**")
        mod_sel = multiselect_all("MODALIDADE", sorted(df["MODALIDADE"].unique()), "f_mod")
        tur_sel = multiselect_all("TURNO", sorted(df["TURNO"].unique()), "f_tur")
        curso_sel = multiselect_all("CURSO", sorted(df["CURSO"].unique()), "f_curso")
    return ano_sel, sem_sel, reg_sel, uni_sel, mod_sel, tur_sel, curso_sel

# ─────────────────────────────────────────────
# 6. EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────
apply_custom_styles()
bd, conc, ev, vagas = load_raw_data()
df = process_data(bd, conc, ev, vagas)

ano_sel, sem_sel, reg_sel, uni_sel, mod_sel, tur_sel, curso_sel = build_sidebar(df)

mask_base = (df["SEMESTRE"].isin(sem_sel) & df["UNIDADE"].isin(uni_sel) & 
             df["MODALIDADE"].isin(mod_sel) & df["TURNO"].isin(tur_sel) & df["CURSO"].isin(curso_sel))

dff_tabela = df[mask_base].copy()
dff_kpi = df[mask_base & df["ANO"].isin(ano_sel)].copy()

st.markdown('<div class="page-title">📊 INTELIGÊNCIA DE MERCADO</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">SENAI Bahia · Matriz de Recomendação de Cursos Técnicos</div>', unsafe_allow_html=True)

# --- BLOCO DE KPIs CORRIGIDO ---
st.markdown('<div class="section-title">Indicadores de Performance (Ano Selecionado)</div>', unsafe_allow_html=True)

def calc_kpis(current_df, full_df, ano_atual, mask_filtros, base_concorrentes):
    ano_ant = ano_atual - 1
    prev_df = full_df[(full_df["ANO"] == ano_ant) & mask_filtros]
    
    def get_metrics(dataframe):
        mp = dataframe[dataframe["CONDIÇÃO"] == "PAGANTE"]["Valor"].sum()
        mb = dataframe[dataframe["CONDIÇÃO"] == "GRATUITO"]["Valor"].sum()
        ep = dataframe[dataframe["CONDIÇÃO"] == "PAGANTE"]["EVASAO_PAG"].sum()
        eb = dataframe[dataframe["CONDIÇÃO"] == "GRATUITO"]["EVASAO_BOLS"].sum()
        tp = (ep / mp * 100) if mp > 0 else 0
        tb = (eb / mb * 100) if mb > 0 else 0
        return mp, mb, ep, eb, tp, tb

    at = get_metrics(current_df)
    ant = get_metrics(prev_df)
    
    # Correção Concorrentes: Contagem de Instituições únicas no contexto geográfico/curso filtrado
    # Filtramos a base bruta de concorrentes baseada nas unidades/cursos selecionados na sidebar
    # (Note: uni_sel e curso_sel vêm do escopo superior)
    total_conc = base_concorrentes[
        (base_concorrentes["UNIDADE"].isin(uni_sel)) & 
        (base_concorrentes["CURSO"].isin(curso_sel))
    ]["INSTITUIÇÃO"].nunique()
    
    return at, ant, total_conc

ult_ano = max(ano_sel) if ano_sel else 2025
(at_metrics, ant_metrics, total_conc) = calc_kpis(dff_kpi, df, ult_ano, mask_base, conc)

def render_kpi(col, label, val, ant, color, is_evasao=False, is_percent=False):
    if is_percent:
        delta = (val - ant) # Para taxas, o delta é a diferença de pontos percentuais
        val_str = f"{val:.1f}%"
    else:
        delta = ((val - ant)/ant*100) if ant > 0 else 0
        val_str = f"{int(val)}"
    
    seta = "▲" if delta >= 0 else "▼"
    cor_delta = ("#dc3545" if delta > 0 else "#28a745") if is_evasao else ("#28a745" if delta >= 0 else "#dc3545")
    label_delta = f"{delta:.1f}%" if not is_percent else f"{delta:+.1f} pp"
    
    with col:
        st.markdown(f"""
        <div class="kpi-box" style="border-left-color: {color};">
            <div class="kpi-title">{label}</div>
            <div class="kpi-value">{val_str}</div>
            <div class="kpi-delta"><span style="color:{cor_delta}">{seta} {label_delta}</span> vs {ult_ano-1}</div>
        </div>
        """, unsafe_allow_html=True)

# Layout de 7 colunas para comportar as novas taxas
ck1, ck2, ck3, ck4, ck5, ck6, ck7 = st.columns(7)
render_kpi(ck1, "Matrículas Pagante", at_metrics[0], ant_metrics[0], "#004587")
render_kpi(ck2, "Taxa Evasão Pag.", at_metrics[4], ant_metrics[4], "#69280D", is_evasao=True, is_percent=True)
render_kpi(ck3, "Evasão Pagante", at_metrics[2], ant_metrics[2], "#dc8d26", is_evasao=True)
render_kpi(ck4, "Matrículas Bolsista", at_metrics[1], ant_metrics[1], "#004587")
render_kpi(ck5, "Taxa Evasão Bols.", at_metrics[5], ant_metrics[5], "#69280D", is_evasao=True, is_percent=True)
render_kpi(ck6, "Evasão Bolsista", at_metrics[3], ant_metrics[3], "#dc8d26", is_evasao=True)
with ck7:
    st.markdown(f"""
    <div class="kpi-box" style="border-left-color: #00A199;">
        <div class="kpi-title">Concorrentes Diretos</div>
        <div class="kpi-value">{int(total_conc)}</div>
        <div class="kpi-delta">Instituições Únicas</div>
    </div>
    """, unsafe_allow_html=True)

# --- FILTROS DE TOPO E TABELA (MANTIDOS) ---
st.divider()
st.markdown('<div class="section-title">🔍 Detalhamento </div>', unsafe_allow_html=True)
ct1, ct2 = st.columns([0.5, 1])
with ct1:
    c_opts = sorted(df["CLASSIFICACAO"].dropna().unique()) if "CLASSIFICACAO" in df.columns else []
    c_sel = st.multiselect("🏷️ Preditiva (Observatório/PA): Classificação", c_opts, placeholder="Todas as Classificações")
with ct2:
    o_val = st.pills("🚀 Oferta SENAI Atual", options=["Sim", "Não"], selection_mode="single")

if c_sel: dff_tabela = dff_tabela[dff_tabela["CLASSIFICACAO"].isin(c_sel)]
if o_val: dff_tabela = dff_tabela[dff_tabela["OFERTA_SENAI"] == o_val]

# if not dff_tabela.empty:
#     g_cols = ["CURSO", "MODALIDADE", "TURNO"]
#     for c in ["CLASSIFICACAO", "OFERTA_SENAI"]:
#         if c in dff_tabela.columns: g_cols.append(c)
#     tabela_final = dff_tabela.groupby(g_cols, dropna=False, as_index=False).apply(medidas_temporais).reset_index()
#     if "level_0" in tabela_final.columns: tabela_final.drop(columns=["level_0"], inplace=True)
#     interactive_table(tabela_final, paging=False, scrollY="500px", scrollX=True, columnDefs=[{"className": "dt-center", "targets": "_all"}])
# else:
#     st.warning("Nenhum dado encontrado para os filtros selecionados.")

# ─────────────────────────────────────────────
# RENDERIZAÇÃO DAS TABELAS LADO A LADO
# ─────────────────────────────────────────────
if not dff_tabela.empty:
    g_cols = ["CURSO", "MODALIDADE", "TURNO"]
    for c in ["CLASSIFICACAO", "OFERTA_SENAI"]:
        if c in dff_tabela.columns: g_cols.append(c)
    
    tabela_resumo = dff_tabela.groupby(g_cols, dropna=False, as_index=False).apply(medidas_temporais).reset_index()
    if "level_0" in tabela_resumo.columns: tabela_resumo.drop(columns=["level_0"], inplace=True)

    col_principal, col_tendencia = st.columns([0.65, 0.35])

    with col_principal:
        st.markdown("**Séries Temporais (2023-2026)**")
        cols_p = g_cols + ["MAT. PAG. (23-26)", "MAT. BOLS. (23-26)", "EV. PAG. (23-26)", "EV. BOLS. (23-26)"]
        interactive_table(tabela_resumo[cols_p], paging=False, scrollY="500px", scrollX=True)

    with col_tendencia:
        st.markdown("**Tendências Projetadas**")
        cols_t = ["CURSO", "TEND. MAT. PAG.", "TEND. MAT. BOLS.", "TEND. EV. PAG.", "TEND. EV. BOLS."]
        interactive_table(tabela_resumo[cols_t], paging=False, scrollY="500px", scrollX=True)
else:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")