import pickle
import warnings
import pandas as pd
import numpy as np
import streamlit as st
from itables.streamlit import interactive_table
from itables import show
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

.main { background: #f5f5f0; }
section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #ddd; }
section[data-testid="stSidebar"] * { color: #1a1a1a !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label { color: #555 !important; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .08em; }

.page-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2rem; font-weight: 700;
    color: #1a1a1a; letter-spacing: .04em;
    margin-bottom: .1rem;
}
.page-sub { font-size: .82rem; color: #777; margin-bottom: 1.4rem; }

/* Cards */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: .75rem; margin-bottom: 1.25rem; }
.kpi-card {
    background: #ffffff;
    border: 1px solid #ddd;
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
.kpi-label { font-size: .68rem; text-transform: uppercase; letter-spacing: .1em; color: #777; margin-bottom: .3rem; }
.kpi-value { font-family: 'Barlow Condensed', sans-serif; font-size: 2rem; font-weight: 700; color: #1a1a1a; line-height: 1; }
.kpi-delta { font-size: .72rem; margin-top: .25rem; color: #555; }

/* Table */
.styled-table-wrapper { border-radius: 8px; overflow: hidden; border: 1px solid #ddd; }
div[data-testid="stDataFrame"] { background: #f5f5f0; }

/* Badges por setor — cores extraídas do dashboard */
.badge-oport  { background:#e8f4e8; color:#1a4a2a; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }
.badge-risco  { background:#fdecea; color:#8b2e2e; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }
.badge-prov   { background:#eaf0fb; color:#1a3a6b; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }

/* Section titles — três variantes de setor */
.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem; font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .08em; margin: 1.2rem 0 .6rem;
    padding-left: .6rem;
}
.section-title.industria  { color: #b8962e; border-left: 3px solid #b8962e; }
.section-title.agro       { color: #8b4a2b; border-left: 3px solid #8b4a2b; }
.section-title.servico    { color: #1a4a4a; border-left: 3px solid #1a4a4a; }
.section-title.default    { color: #1a1a1a; border-left: 3px solid #e8826a; }
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

# 1. Evasão -> Já está agrupado por chave única (OK)
ev_agg = (ev.groupby("COD_Base_de_Evasao")
            .agg(EVASAO_PAG=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="PAGANTE"].sum()),
                 EVASAO_BOLS=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="GRATUITO"].sum()))
            .reset_index())
df = bd.merge(ev_agg, on="COD_Base_de_Evasao", how="left")

# 2. Vagas -> Garantir que COD_VAGAS seja único para não duplicar Valor
vagas_m = vagas[["COD_VAGAS", "VAGAS_2"]].rename(columns={"VAGAS_2": "VAGAS_ULTIM"}).drop_duplicates(subset=["COD_VAGAS"])
df = df.merge(vagas_m, on="COD_VAGAS", how="left")

# 3. Observatório -> Já possui drop_duplicates (OK)
obs_m = obs[["COD_Observatorio", "CLASSIFICAÇÃO", "Oferta Senai"]].drop_duplicates(subset=["COD_Observatorio"])
df = df.merge(obs_m, on="COD_Observatorio", how="left")

# 4. Concorrentes -> CÁLCULO PRÉVIO PARA EVITAR EXPLOSÃO DE LINHAS
# Agrupamos por chave e contamos as instituições únicas ANTES do merge
conc_agg = (conc.groupby("COD_Concorrentes")["INSTITUIÇÃO"]
               .nunique() 
               .reset_index()
               .rename(columns={"INSTITUIÇÃO": "QTD_CONCORRENTES"}))

# Agora o merge é 1 para 1 ou N para 1, sem duplicar as linhas da fato (bd)
df = df.merge(conc_agg, on="COD_Concorrentes", how="left")

def medidas(g):
    anos_ref = [2023, 2024, 2025, 2026]
    
    def gerar_serie_temporal(condicao, coluna, is_sum=True):
        valores_num = []
        for ano in anos_ref:
            # Filtro preciso por ano e condição
            m_ano = (g["ANO"] == ano)
            if condicao: 
                m_ano &= (g["CONDIÇÃO"] == condicao)
            
            sub = g.loc[m_ano, coluna]
            
            if sub.empty:
                val = 0
            else:
                # Agora o sum() será real, pois as linhas não estão duplicadas
                res = sub.sum() if is_sum else sub.max()
                val = 0 if pd.isna(res) else res
            
            valores_num.append(int(round(float(val))))
        
        if sum(valores_num) == 0: return "-"
        
        strings_finais = []
        for i, atual in enumerate(valores_num):
            if atual == 0:
                strings_finais.append("-")
            else:
                if i > 0:
                    anterior = valores_num[i-1]
                    if anterior > 0:
                        if atual > anterior:
                            strings_finais.append(f"🟢{atual}")
                        elif atual < anterior:
                            strings_finais.append(f"🔴{atual}")
                        else:
                            strings_finais.append(str(atual))
                    else:
                        strings_finais.append(str(atual))
                else:
                    strings_finais.append(str(atual))
        return " | ".join(strings_finais)

    # Pegamos o valor máximo da coluna de contagem de concorrentes do grupo
    conc_val = g["QTD_CONCORRENTES"].max() if "QTD_CONCORRENTES" in g.columns else 0
    conc_val = 0 if pd.isna(conc_val) else conc_val

    return pd.Series({
        "CONCORRENTES":             int(conc_val),
        "MAT. PAG. (23|24|25|26)":  gerar_serie_temporal("PAGANTE", "Valor"),
        "MAT. BOLS. (23|24|25|26)": gerar_serie_temporal("GRATUITO", "Valor"),
        "MAT. CANC. (23|24|25|26)": gerar_serie_temporal("CANCELADA", "Valor"),
        "EV. PAG. (23|24|25|26)":   gerar_serie_temporal("PAGANTE", "EVASAO_PAG"),
        "EV. BOLS. (23|24|25|26)":  gerar_serie_temporal("GRATUITO", "EVASAO_BOLS"),
        "VAGAS (23|24|25|26)":      gerar_serie_temporal(None, "VAGAS_ULTIM", False),
        "TURMAS (23|24|25|26)":     gerar_serie_temporal(None, "TURMA", False)
    })

# ─────────────────────────────────────────────
# SIDEBAR – FILTROS
# ─────────────────────────────────────────────
TODOS = "Todos"

def multiselect_com_todos(label, opcoes):
    """Selectbox que exibe 'Todos' + itens. Retorna lista com todos os itens se 'Todos' selecionado."""
    escolhas = st.multiselect(label, [TODOS] + list(opcoes), default=[TODOS])
    if TODOS in escolhas or not escolhas:
        return list(opcoes)
    return escolhas

with st.sidebar:
    st.markdown("### 🎛️ Centro de Comando")
    st.divider()

    # Bloco 1: Temporal
    st.markdown("**📅 TEMPORAL**")
    anos = sorted(df["ANO"].dropna().unique())
    ano_sel = multiselect_com_todos("Ano", anos)
    
    sems = sorted(df["SEMESTRE"].dropna().unique())
    sem_sel = multiselect_com_todos("Semestre", sems)
    st.divider()

    # Bloco 2: Operacional
    st.markdown("**⚙️ OPERACIONAL**")
    turnos = sorted(df["TURNO"].dropna().unique())
    tur_sel = multiselect_com_todos("Turno", turnos)
    
    modalidades = sorted(df["MODALIDADE"].dropna().unique())
    mod_sel = multiselect_com_todos("Modalidade", modalidades)
    st.divider()

    # Bloco 3: Geográfico
    st.markdown("**🌎 GEOGRÁFICO**")
    regionais = sorted(df["REGIONAL"].dropna().unique())
    reg_sel = multiselect_com_todos("Regional", regionais)
    
    unidades = sorted(df.loc[df["REGIONAL"].isin(reg_sel), "UNIDADE"].dropna().unique())
    uni_sel = multiselect_com_todos("Unidade", unidades)
    st.divider()

# ─────────────────────────────────────────────
# APLICAR FILTROS
# ─────────────────────────────────────────────

mask_tabela = (
    df["SEMESTRE"].isin(sem_sel) &
    df["UNIDADE"].isin(uni_sel) &
    df["MODALIDADE"].isin(mod_sel) &
    df["TURNO"].isin(tur_sel)
)

# Filtro que INCLUI o ANO (para os KPIs/Cards)
mask_kpi = mask_tabela & df["ANO"].isin(ano_sel)

# Dataframes distintos
dff_tabela = df[mask_tabela].copy() # Esse vai para a função medidas
dff_kpi = df[mask_kpi].copy()       # Esse vai para os totalizadores (Cards)

# ─────────────────────────────────────────────
# CABEÇALHO
# ─────────────────────────────────────────────
st.markdown('<div class="page-title">📊 RECOMENDAÇÃO DE CURSO</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">SENAI Bahia · Planejamento de Cursos Técnicos</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────
total_mat_pag  = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="PAGANTE","Valor"].sum()
total_mat_bols = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="GRATUITO","Valor"].sum()
total_ev_pag   = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="PAGANTE","EVASAO_PAG"].sum()
total_conc     = dff_kpi["CONCORRENTES"].max() if "CONCORRENTES" in dff_kpi.columns else 0
total_turmas   = dff_kpi["TURMA"].max()
total_cursos   = dff_kpi["CURSO"].nunique()
total_unidades = dff_kpi["UNIDADE"].nunique()
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

# Definimos as colunas de agrupamento (dimensões que não mudam)
group_cols = ["CURSO", "MODALIDADE", "TURNO"]
if "Esforço de Venda" in dff_tabela.columns: group_cols.append("Esforço de Venda")
if "Turmas Potenciais" in dff_tabela.columns: group_cols.append("Turmas Potenciais")
if "CLASSIFICAÇÃO" in dff_tabela.columns: group_cols.append("CLASSIFICAÇÃO")
if "OFERTA_SENAI" in dff_tabela.columns: group_cols.append("OFERTA_SENAI")

# Gerar a tabela aplicando a nova função de medidas
tabela = dff_tabela.groupby(group_cols, dropna=False, as_index=False).apply(medidas).reset_index()
tabela.rename(columns={"CLASSIFICACAO":"CLASSIFICAÇÃO", 
                    "Esforço de Venda":"ESFORÇO DE VENDA", 
                    "Turmas Potenciais":"TURMAS POTENCIAIS", 
                    "OFERTA_SENAI":"OFERTA SENAI"}, inplace=True)

# Limpeza de colunas duplicadas por causa do merge/apply
if "level_0" in tabela.columns: tabela = tabela.drop(columns=["level_0"])

st.markdown('<div class="section-title">Detalhamento Temporal por Curso / Unidade</div>', unsafe_allow_html=True)
st.caption("Valores exibidos na sequência: **2023 | 2024 | 2025 | 2026**")

# ─────────────────────────────────────────────
# FILTROS DE TOPO (CLASSIFICAÇÃO E OFERTA)
# ─────────────────────────────────────────────
st.markdown("#### 🔍Observatório/PA")
c_topo1, c_topo2 = st.columns([0.5, 1])

with c_topo1:
    class_opts = sorted(df["CLASSIFICACAO"].dropna().unique())
    class_sel = st.multiselect("🏷️  Preditiva: Classificação", class_opts, placeholder="Todas as Classificações")
    if not class_sel: class_sel = list(class_opts)

with c_topo2:
    # Flag Sim/Não (Se não selecionar nada, traz todos)
    of_val = st.pills(
        "🚀 Oferta SENAI", 
        options=["Sim", "Não"], 
        selection_mode="single"
    )
    of_opts = sorted(df["OFERTA_SENAI"].dropna().unique())
    of_sel = [of_val] if of_val else list(of_opts)

# Aplicação dos filtros finais antes do groupby
mask_tabela &= dff_tabela["CLASSIFICACAO"].isin(class_sel)
mask_tabela &= dff_tabela["OFERTA_SENAI"].isin(of_sel)

# Dataframe que será usado na função medidas
tabela_final = dff_tabela[mask_tabela].copy()
# Agora chame o groupby e a função medidas usando tabela_final...
tabela_exibicao = tabela_final.groupby(group_cols, dropna=False, as_index=False).apply(medidas).reset_index()

# Exibição com itables (interactive_table)
interactive_table(
    tabela_exibicao, # Resultado do apply(medidas)
    paging=False, 
    scrollY="600px", 
    scrollCollapse=True,
    scrollX=True,
    columnDefs=[{"className": "dt-center", "targets": "_all"}]
)
st.divider()
# ─────────────────────────────────────────────
# EXPORTAÇÃO
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">Exportação</div>', unsafe_allow_html=True)

# INSERI TABELA DE APROVEITAMENTO BOLSA
# AJUSTAR OS CARDS PARA EVASÃO PAGANTES E EVAÇÃO BOLSITA E MATRICULA PAGANTE E MATRIOCULA BOLSISTA
# # VER CALCULO DE VAGA DE BOLSISTA
# INSERIT TABELA DE TENDÊNCIA DE MATRICULAS
# TABELA DE RECOMENDAÇÃO E A TABELA DE VIABILIDADE DE TURMA