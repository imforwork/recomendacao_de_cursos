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
    # 1. Agregação de Evasão (Mantida)
    ev_agg = (ev.groupby("COD_Base_de_Evasao")
                .agg(EVASAO_PAG=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="PAGANTE"].sum()),
                     EVASAO_BOLS=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="GRATUITO"].sum()))
                .reset_index())
    df = bd.merge(ev_agg, on="COD_Base_de_Evasao", how="left")

    # 2. Agregação de Concorrentes (Lógica DISTINCTCOUNT por Contexto)
    # Agrupamos por UNIDADE e CURSO para contar instituições únicas
    conc_agg = conc.groupby(["UNIDADE", "CURSO"])["INSTITUIÇÃO"].nunique().reset_index()
    conc_agg.columns = ["UNIDADE", "CURSO", "CONCORRENTES"]
    
    # Fazemos o merge baseado nas colunas dimensionais para garantir precisão
    df = df.merge(conc_agg, on=["UNIDADE", "CURSO"], how="left")

    if not vagas.empty:
        vagas_m = vagas.rename(columns={"VAGAS_2": "VAGAS_ULTIM"}).drop_duplicates(subset=["COD_VAGAS"])
        df = df.merge(vagas_m[["COD_VAGAS", "VAGAS_ULTIM"]], on="COD_VAGAS", how="left")
    
    if not bd.empty:
        col_map = {
            "CLASSIFICACAO": "CLASSIFICACAO", "CLASSIFICAÇÃO": "CLASSIFICACAO", "Classificação": "CLASSIFICACAO",
            "OFERTA_SENAI": "OFERTA_SENAI", "Oferta Senai": "OFERTA_SENAI", "OFERTA SENAI": "OFERTA_SENAI",
            "Esforço de Venda": "ESFORÇO DE VENDA", "ESFORÇO DE VENDA": "ESFORÇO DE VENDA"
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    # Tratamento de Nulos (Garante que cursos sem concorrentes cadastrados apareçam como 0)
    df["CONCORRENTES"] = df["CONCORRENTES"].fillna(0).astype(int)
    
    return df

# ─────────────────────────────────────────────
# FUNÇÃO DE CÁLCULO DE TENDÊNCIA
# ─────────────────────────────────────────────
def calcular_tendencia_linear(valores_num):
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
# 4. MOTOR DE CÁLCULO (MEDIDAS TEMPORAIS)
# ─────────────────────────────────────────────
def calcular_tendencia_linear(valores_num):
    x4, x3 = np.array([1, 2, 3, 4]), np.array([2, 3, 4])
    y = np.array(valores_num, dtype=float)
    def fit_slope(xi, yi):
        if sum(yi > 0) < 2: return None
        try: return np.polyfit(xi, yi, 1)[0]
        except: return None
    slope = fit_slope(x4, y)
    if slope is None: slope = fit_slope(x3, y[1:])
    if slope is None: return "S/ Param."
    if slope > 1: return "Alta"
    if slope > 0: return "Leve Alta"
    if slope < -1: return "Baixa"
    return "Leve Baixa"

def colorir_tendencia(val, tipo="crescimento"):
    if val == "S/ Param.": return val
    vde, vrm = "#28a745", "#dc3545"
    if tipo == "crescimento":
        cor = vde if "Alta" in val else (vrm if "Baixa" in val else "inherit")
    else: # Evasão: Alta é ruim (vermelho), Baixa é bom (verde)
        cor = vrm if "Alta" in val else (vde if "Baixa" in val else "inherit")
    return f'<b style="color:{cor}">{val}</b>'

def medidas_temporais(g):
    anos_ref = [2023, 2024, 2025, 2026]

    # Função auxiliar para obter listas numéricas puras (usada para tendências e strings)
    def obter_lista_num(condicao, coluna, is_sum=True):
        valores = []
        for ano in anos_ref:
            m_ano = (g["ANO"] == ano)
            if condicao: m_ano &= (g["CONDIÇÃO"] == condicao)
            sub = g.loc[m_ano, coluna]
            val = (sub.sum() if is_sum else sub.max()) if not sub.empty else 0
            valores.append(0 if pd.isna(val) else int(round(val)))
        return valores

    # Função para formatar a string "val | val | val" com as setas
    def formatar_string_temporal(valores_num):
        if sum(valores_num) == 0: return "-"
        res = []
        for i, atual in enumerate(valores_num):
            if atual == 0: res.append("-")
            else:
                if i > 0 and valores_num[i-1] > 0:
                    if atual > valores_num[i-1]: res.append(f"<span style='color: #28a745;'>🡅</span>{atual}")
                    elif atual < valores_num[i-1]: res.append(f"<span style='color: #dc3545;'>🡇</span>{atual}")
                    else: res.append(str(atual))
                else: res.append(str(atual))
        return " | ".join(res)

    # 1. Obter listas numéricas (Base para tudo)
    v_pag = obter_lista_num("PAGANTE", "Valor")
    v_bols = obter_lista_num("GRATUITO", "Valor")
    e_pag = obter_lista_num("PAGANTE", "EVASAO_PAG")
    e_bols = obter_lista_num("GRATUITO", "EVASAO_BOLS")
    vagas = obter_lista_num(None, "VAGAS_ULTIM", is_sum=False)
    turmas = obter_lista_num(None, "TURMA", is_sum=False)

    # 2. Gerar Taxas de Evasão (Lógica S/ Oferta / Cancelado)
    def gerar_serie_taxa_evasao(condicao, lista_evasao, lista_matricula, lista_vagas, lista_turmas):
        res_str = []
        for i in range(len(anos_ref)):
            if lista_vagas[i] == 0 and lista_turmas[i] == 0:
                res_str.append("S/ Oferta")
            elif lista_matricula[i] == 0:
                res_str.append("Cancelado")
            else:
                taxa = (lista_evasao[i] / lista_matricula[i]) * 100
                res_str.append(f"{int(round(taxa))}%")
        return " | ".join(res_str)

    return pd.Series({
        "MAT. PAG. (23-26)":  formatar_string_temporal(v_pag),
        "MAT. BOLS. (23-26)": formatar_string_temporal(v_bols),
        "EV. PAG. (23-26)":   formatar_string_temporal(e_pag),
        "EV. BOLS. (23-26)":  formatar_string_temporal(e_bols),
        "VAGAS (23-26)":      formatar_string_temporal(vagas),
        "TAXA EVASÃO PAG.":   gerar_serie_taxa_evasao("PAGANTE", e_pag, v_pag, vagas, turmas),
        "TAXA EVASÃO BOLS.":  gerar_serie_taxa_evasao("GRATUITO", e_bols, v_bols, vagas, turmas),
        "TEND. MAT. PAG.":    colorir_tendencia(calcular_tendencia_linear(v_pag), "crescimento"),
        "TEND. MAT. BOLS.":   colorir_tendencia(calcular_tendencia_linear(v_bols), "crescimento"),
        "TEND. EV. PAG.":     colorir_tendencia(calcular_tendencia_linear(e_pag), "evasao"),
        "TEND. EV. BOLS.":    colorir_tendencia(calcular_tendencia_linear(e_bols), "evasao"),
        "CONCORRENTES":       int(g["CONCORRENTES"].max() if "CONCORRENTES" in g.columns else 0)
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
# --- FUNÇÃO AUXILIAR PARA EXCEL ---
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Recomendacao')
    writer.close()
    processed_data = output.getvalue()
    return processed_data

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

total_conc = conc[
    (conc["UNIDADE"].isin(uni_sel)) & 
    (conc["CURSO"].isin(curso_sel))
]["INSTITUIÇÃO"].nunique()

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
render_kpi(ck2, "Evasão Pagante", at_metrics[2], ant_metrics[2], "#938D78FF", is_evasao=True)
render_kpi(ck3, "Taxa Evasão Pag.", at_metrics[4], ant_metrics[4], "#938D78FF", is_evasao=True, is_percent=True)
render_kpi(ck4, "Matrículas Bolsista", at_metrics[1], ant_metrics[1], "#004587")
render_kpi(ck5, "Evasão Bolsista", at_metrics[3], ant_metrics[3], "#938D78FF", is_evasao=True)
render_kpi(ck6, "Taxa Evasão Bols.", at_metrics[5], ant_metrics[5], "#938D78FF", is_evasao=True, is_percent=True)

with ck7:
    st.markdown(f"""
    <div class="kpi-box" style="border-left-color: #004587;">
        <div class="kpi-title">Cursos em Análise</div>
        <div class="kpi-value">{dff_tabela['CURSO'].nunique()}</div>
        <div class="kpi-delta">Portfólio Filtrado</div>
    </div>
    """, unsafe_allow_html=True)

## ─────────────────────────────────────────────
#  FILTROS DE TOPO E TABELA (MANTIDOS)
## ─────────────────────────────────────────────
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

## ─────────────────────────────────────────────
# SISTEMA DE CONTROLE NO MENU (CORRIGIDO)
## ─────────────────────────────────────────────
if 'ver_tendencias' not in st.session_state: st.session_state.ver_tendencias = True
if 'ver_tx_evasao' not in st.session_state: st.session_state.ver_tx_evasao = True

st.markdown('<div class="section-title">MENU DE VISUALIZAÇÃO</div>', unsafe_allow_html=True)
c_btn1, c_btn2 = st.columns([0.05, 0.03])

with c_btn1:
    label_tend = "OCULTAR TENDÊNCIAS" if st.session_state.ver_tendencias else "VER TENDÊNCIAS"
    if st.button(label_tend, use_container_width=True, key="btn_tendencia"):
        st.session_state.ver_tendencias = not st.session_state.ver_tendencias
        st.rerun()

with c_btn2:
    label_ev = "OCULTAR TAXA EVASÃO" if st.session_state.ver_tx_evasao else "VER TAXA EVASÃO"
    if st.button(label_ev, use_container_width=True, key="btn_evasao"):
        st.session_state.ver_tx_evasao = not st.session_state.ver_tx_evasao
        st.rerun()

## ─────────────────────────────────────────────
# RENDERIZAÇÃO DA TABELA (COM LÓGICA DE COLUNAS)
## ─────────────────────────────────────────────
if not dff_tabela.empty:
    # --- A. AGRUPAMENTO E PROCESSAMENTO ---
    # Define as colunas de agrupamento baseadas nas dimensões existentes
    g_cols = [c for c in ["CURSO", "MODALIDADE", "TURNO", "CLASSIFICACAO", "OFERTA_SENAI", "ESFORÇO DE VENDA"] if c in dff_tabela.columns]
    
    # Aplica a função de motor de cálculo
    tabela_resumo = dff_tabela.groupby(g_cols, dropna=False, as_index=False).apply(medidas_temporais).reset_index()
    
    # Limpa índices residuais do Pandas
    if "level_0" in tabela_resumo.columns: 
        tabela_resumo.drop(columns=["level_0"], inplace=True)

    # --- B. CSS PROFISSIONAL (SEM QUEBRA DE LINHA + CORES SENAI) ---
    st.markdown("""
        <style>
        .dashboard-container { overflow-x: auto; max-height: 650px; border: 1px solid #e0e0e0; border-radius: 8px; background: white; }
        .unified-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
        
        /* CABEÇALHO COM CORES SOLICITADAS */
        .unified-table th { 
            background: #004587 !important; /* Azul SENAI Principal */
            color: #ffffff !important;    
            position: sticky; 
            top: 0; 
            z-index: 10;
            padding: 12px 10px; 
            border-bottom: 2px solid #dee2e6; 
            white-space: nowrap !important;
            text-transform: uppercase;
            font-weight: 700;
        }
        
        /* CÉLULAS DE DADOS: PROIBIDO QUEBRA DE LINHA */
        .unified-table td { 
            padding: 10px 10px; 
            border-bottom: 1px solid #eee; 
            text-align: center; 
            color: #333;
            white-space: nowrap !important; 
            vertical-align: middle;
        }
        
        /* EXCEÇÃO: COLUNA CURSO (FIXA E COM QUEBRA) */
        .unified-table td:first-child, .unified-table th:first-child { 
            text-align: left !important; 
            min-width: 260px; 
            position: sticky; 
            left: 0; 
            background: white; 
            z-index: 5;
            white-space: normal !important; /* PERMITE QUEBRA APENAS NO CURSO */
        }
        
        /* Garante que o header do curso acompanhe a cor */
        /* Garante que o header da primeira coluna siga o padrão azul mas mantenha o z-index alto para o scroll */
        .unified-table th:first-child { background: #004587 !important; z-index: 11; color: white !important; }

        /* SEPARADORES VISUAIS (Borda Azul nas seções) */
        .sep-col { border-left: 3px solid #B1C9D9 !important; background: #f9f9f9; }
        
        .unified-table tr:hover { background-color: #f1f3f5; }
        .unified-table tr:hover td:first-child { background-color: #f1f3f5; }
        </style>
    """, unsafe_allow_html=True)

    # --- C. CONSTRUÇÃO DINÂMICA DA LISTA DE COLUNAS (LOGICA DOS BOTÕES) ---
    
    # 1. Colunas Dimensionais (Fixas)
    cols_estaticas = ["CURSO"] + [c for c in g_cols if c != "CURSO"] + ["CONCORRENTES"]
    
    # 2. Colunas Principais (Matrículas e Vagas)
    all_headers = cols_estaticas + ["VAGAS (23-26)", "MAT. PAG. (23-26)", "MAT. BOLS. (23-26)","EV. PAG. (23-26)", "EV. BOLS. (23-26)"]
    
    # 3. Bloco de Evasão (Condicional ao Botão)
    if st.session_state.get('ver_tx_evasao', True):
        all_headers += ["TAXA EVASÃO PAG.", "TAXA EVASÃO BOLS."]
        
    # 4. Bloco de Tendências (Condicional ao Botão)
    if st.session_state.get('ver_tendencias', True):
        all_headers += ["TEND. MAT. PAG.", "TEND. MAT. BOLS.", "TEND. EV. PAG.", "TEND. EV. BOLS."]

    # --- D. GERAÇÃO DO HTML FINAL ---
    html_str = '<div class="dashboard-container"><table class="unified-table"><thead><tr>'
    
    # Renderiza o Cabeçalho (Header)
    for h in all_headers:
        # Define onde colocar a borda de separação
        is_sep = h in ["EV. PAG. (23-26)", "TAXA EVASÃO PAG.", "TEND. MAT. PAG."]
        extra_class = ' class="sep-col"' if is_sep else ""
        html_str += f'<th{extra_class}>{h}</th>'
    
    html_str += '</tr></thead><tbody>'
    
    # Renderiza as Linhas de Dados (Rows)
    for _, row in tabela_resumo.iterrows():
        # Lógica Comercial: Destacar cursos com Classificação Alta e Concorrência Baixa (ajuste os termos conforme sua base)
        is_oportunidade = str(row.get("CLASSIFICACAO", "")).upper() in ["A", "ALTA", "ESTRATÉGICO"]
        row_style = ' style="background-color: #fff9e6;"' if is_oportunidade else ""
        
        html_str += f'<tr {row_style}>'
        for h in all_headers:
            val = row[h] if h in row else ""
            
            # Aplica a mesma classe de separador para as células
            is_sep = h in ["EV. PAG. (23-26)", "TAXA EVASÃO PAG.", "TEND. MAT. PAG."]
            extra_class = ' class="sep-col"' if is_sep else ""
            
            html_str += f'<td{extra_class}>{val}</td>'
        html_str += '</tr>'
    
    html_str += '</tbody></table></div>'
    
    # Exibe a tabela no Streamlit
    st.markdown(html_str, unsafe_allow_html=True)

else:
    st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")

