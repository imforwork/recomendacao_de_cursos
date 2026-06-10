# import pickle
# import warnings
# import pandas as pd
# import numpy as np
# import streamlit as st
# from itables.streamlit import interactive_table
# from itables import show
# from io import BytesIO

# warnings.filterwarnings("ignore")

# # ─────────────────────────────────────────────
# # CONFIG
# # ─────────────────────────────────────────────
# st.set_page_config(
#     page_title="Recomendação de Curso | SENAI Bahia",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # ─────────────────────────────────────────────
# # ESTILOS
# # ─────────────────────────────────────────────
# st.markdown("""
# <style>
# @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@300;400;500&display=swap');

# html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }

# .main { background: #f5f5f0; }
# section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #ddd; }
# section[data-testid="stSidebar"] * { color: #1a1a1a !important; }
# section[data-testid="stSidebar"] .stSelectbox label,
# section[data-testid="stSidebar"] .stMultiSelect label { color: #555 !important; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .08em; }

# .page-title {
#     font-family: 'Barlow Condensed', sans-serif;
#     font-size: 2rem; font-weight: 700;
#     color: #1a1a1a; letter-spacing: .04em;
#     margin-bottom: .1rem;
# }
# .page-sub { font-size: .82rem; color: #777; margin-bottom: 1.4rem; }

# /* Cards */
# .kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: .75rem; margin-bottom: 1.25rem; }
# .kpi-card {
#     background: #ffffff;
#     border: 1px solid #ddd;
#     border-radius: 10px;
#     padding: 1rem 1.2rem;
#     position: relative; overflow: hidden;
# }
# .kpi-card::before {
#     content: '';
#     position: absolute; top:0; left:0;
#     width: 3px; height: 100%;
#     background: var(--accent);
# }
# .kpi-label { font-size: .68rem; text-transform: uppercase; letter-spacing: .1em; color: #777; margin-bottom: .3rem; }
# .kpi-value { font-family: 'Barlow Condensed', sans-serif; font-size: 2rem; font-weight: 700; color: #1a1a1a; line-height: 1; }
# .kpi-delta { font-size: .72rem; margin-top: .25rem; color: #555; }

# /* Table */
# .styled-table-wrapper { border-radius: 8px; overflow: hidden; border: 1px solid #ddd; }
# div[data-testid="stDataFrame"] { background: #f5f5f0; }

# /* Badges por setor — cores extraídas do dashboard */
# .badge-oport  { background:#e8f4e8; color:#1a4a2a; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }
# .badge-risco  { background:#fdecea; color:#8b2e2e; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }
# .badge-prov   { background:#eaf0fb; color:#1a3a6b; padding:2px 8px; border-radius:4px; font-size:.7rem; font-weight:600; }

# /* Section titles — três variantes de setor */
# .section-title {
#     font-family: 'Barlow Condensed', sans-serif;
#     font-size: 1.1rem; font-weight: 600;
#     text-transform: uppercase;
#     letter-spacing: .08em; margin: 1.2rem 0 .6rem;
#     padding-left: .6rem;
# }
# .section-title.industria  { color: #b8962e; border-left: 3px solid #b8962e; }
# .section-title.agro       { color: #8b4a2b; border-left: 3px solid #8b4a2b; }
# .section-title.servico    { color: #1a4a4a; border-left: 3px solid #1a4a4a; }
# .section-title.default    { color: #1a1a1a; border-left: 3px solid #e8826a; }
# </style>
# """, unsafe_allow_html=True)

# # ─────────────────────────────────────────────
# # LOAD DATA
# # ─────────────────────────────────────────────
# @st.cache_data
# def load_data():
#     with open("BD_Plan_Curso_Tecnico.pkl","rb") as f: bd = pickle.load(f)
#     with open("Base_Concorrentes.pkl","rb") as f: conc = pickle.load(f)
#     with open("Base_de_Evasao.pkl","rb") as f: ev = pickle.load(f)
#     with open("dVagas.pkl","rb") as f: vagas = pickle.load(f)
#     with open("dCLASSIFICACAO.pkl","rb") as f: classif = pickle.load(f)
#     with open("dOFERTA_SENAI.pkl","rb") as f: oferta = pickle.load(f)
#     # with open("Observatorio_2.pkl","rb") as f: obs = pickle.load(f)
#     return bd, conc, ev, vagas, classif, oferta

# bd, conc, ev, vagas, classif, oferta = load_data()

# # ─────────────────────────────────────────────
# # JOINS
# # ─────────────────────────────────────────────

# # 1. Evasão -> Já está agrupado por chave única (OK) obs
# ev_agg = (ev.groupby("COD_Base_de_Evasao")
#             .agg(EVASAO_PAG=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="PAGANTE"].sum()),
#                  EVASAO_BOLS=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="GRATUITO"].sum()))
#             .reset_index())
# df = bd.merge(ev_agg, on="COD_Base_de_Evasao", how="left")

# # 2. Vagas -> Garantir que COD_VAGAS seja único para não duplicar Valor

# # vagas_m = vagas[["COD_VAGAS", "VAGAS_2"]].rename(columns={"VAGAS_2": "VAGAS_ULTIM"}).drop_duplicates(subset=["COD_VAGAS"])
# # df = df.merge(vagas_m, on="COD_VAGAS", how="left")

# # ─────────────────────────────────────────────
# # CORREÇÃO DO JOIN DE VAGAS
# # ─────────────────────────────────────────────
# if not vagas.empty:
#     # 1. Limpeza rigorosa da tabela de vagas
#     vagas_m = vagas.copy()
    
#     # Garantir que as colunas de composição da chave não tenham espaços
#     for c in ["COD_VAGAS", "VAGAS_2"]:
#         if c in vagas_m.columns:
#             vagas_m[c] = vagas_m[c].astype(str).str.strip()
    
#     # Renomear para o padrão usado na função medidas
#     vagas_m = vagas_m.rename(columns={"VAGAS_2": "VAGAS_ULTIM"})
    
#     # Manter apenas a última definição de vaga por chave (evitar duplicação)
#     vagas_m = vagas_m.drop_duplicates(subset=["COD_VAGAS"])
    
#     # 2. Limpeza da chave na tabela principal antes do merge
#     df["COD_VAGAS"] = df["COD_VAGAS"].astype(str).str.strip()
    
#     # 3. Executar o Merge
#     df = df.merge(vagas_m[["COD_VAGAS", "VAGAS_ULTIM"]], on="COD_VAGAS", how="left")
    
#     # 4. Preencher NaNs com 0 para a função medidas não falhar
#     df["VAGAS_ULTIM"] = pd.to_numeric(df["VAGAS_ULTIM"], errors='coerce').fillna(0)


# # 3. Observatório -> Tratamento Defensivo de Colunas e Chaves
# if not bd.empty:
#     # Identifica os nomes reais das colunas (com ou sem acento/underscore)
#     cols_bd = bd.columns.tolist()
    
#     # 1. Recuperar ou Criar COD_Observatorio
#     if "COD_Observatorio" not in cols_bd:
#         # Se foi removida, recriamos usando UNIDADE_2 + CURSO (conforme lógica do PQ)
#         if "UNIDADE_2" in cols_bd and "CURSO" in cols_bd:
#             bd["COD_Observatorio"] = bd["UNIDADE_2"].astype(str) + bd["CURSO"].astype(str)
#         elif "UNIDADE_2" in cols_bd and "Catálogo - Curso Técnico" in cols_bd:
#             bd["COD_Observatorio"] = bd["UNIDADE_2"].astype(str) + bd["Catálogo - Curso Técnico"].astype(str)

#     # 2. Mapear Classificação e Oferta (variantes comuns)
#     col_class = next((c for c in ["CLASSIFICACAO", "CLASSIFICAÇÃO", "Classificação"] if c in cols_bd), None)
#     col_oferta = next((c for c in ["OFERTA_SENAI", "Oferta Senai", "OFERTA SENAI"] if c in cols_bd), None)

#     # # 3. Preparar tabela para merge com nomes padronizados
#     cols_selecao = ["COD_Observatorio"] # obs
#     renomear = {}
    
#     if col_class: 
#         cols_selecao.append(col_class)
#         renomear[col_class] = "CLASSIFICAÇÃO"
#     if col_oferta: 
#         cols_selecao.append(col_oferta)
#         renomear[col_oferta] = "Oferta Senai"

# # 3. Observatório -> Padronização Forçada
# if not bd.empty:
#     cols_bd = bd.columns.tolist()
    
#     # Busca variações de nome para Classificação e Oferta
#     col_class_orig = next((c for c in ["CLASSIFICAÇÃO", "CLASSIFICACAO", "Classificação"] if c in cols_bd), None)
#     col_oferta_orig = next((c for c in ["Oferta Senai", "OFERTA_SENAI", "OFERTA SENAI"] if c in cols_bd), None)

#     if col_class_orig:
#         obs_m = bd[["COD_Observatorio", col_class_orig]].drop_duplicates(subset=["COD_Observatorio"])
#         df = df.merge(obs_m, on="COD_Observatorio", how="left").rename(columns={col_class_orig: "CLASSIFICACAO"})

#     if col_oferta_orig:
#         obs_o = bd[["COD_Observatorio", col_oferta_orig]].drop_duplicates(subset=["COD_Observatorio"])
#         df = df.merge(obs_o, on="COD_Observatorio", how="left").rename(columns={col_oferta_orig: "OFERTA_SENAI"})

#     # Executa o merge apenas com o que foi encontrado
#     obs_m = bd[cols_selecao].drop_duplicates(subset=["COD_Observatorio"]).rename(columns=renomear)
#     df = df.merge(obs_m, on="COD_Observatorio", how="left")

# # 4. Concorrentes -> CÁLCULO PRÉVIO PARA EVITAR EXPLOSÃO DE LINHAS
# # Agrupamos por chave e contamos as instituições únicas ANTES do merge
# conc_agg = (conc.groupby("COD_Concorrentes")["INSTITUIÇÃO"]
#                .nunique() 
#                .reset_index()
#                .rename(columns={"INSTITUIÇÃO": "QTD_CONCORRENTES"}))

# # Agora o merge é 1 para 1 ou N para 1, sem duplicar as linhas da fato (bd)
# df = df.merge(conc_agg, on="COD_Concorrentes", how="left")

# def medidas(g):
#     anos_ref = [2023, 2024, 2025, 2026]
    
#     def gerar_serie_temporal(condicao, coluna, is_sum=True):
#         valores_num = []
#         for ano in anos_ref:
#             m_ano = (g["ANO"] == ano)
#             # Se houver condição (PAGANTE/GRATUITO), aplica o filtro
#             if condicao: 
#                 m_ano &= (g["CONDIÇÃO"] == condicao)
            
#             # Aqui estava o erro: 'coluna' deve ser o nome da coluna no DF (ex: 'Valor' ou 'VAGAS_ULTIM')
#             sub = g.loc[m_ano, coluna]
            
#             if sub.empty:
#                 val = 0
#             else:
#                 res = sub.sum() if is_sum else sub.max()
#                 val = 0 if pd.isna(res) else res
            
#             valores_num.append(int(round(float(val))))
        
#         if sum(valores_num) == 0:
#             return "-"
        
#         strings_finais = []
#         for i, atual in enumerate(valores_num):
#             if atual == 0:
#                 strings_finais.append("-")
#             else:
#                 if i > 0:
#                     anterior = valores_num[i-1]
#                     if anterior > 0:
#                         if atual > anterior:
#                             strings_finais.append(f" 🡅 {atual}")
#                         elif atual < anterior:
#                             strings_finais.append(f" 🡇 {atual}")
#                         else:
#                             strings_finais.append(str(atual))
#                     else:
#                         strings_finais.append(str(atual))
#                 else:
#                     strings_finais.append(str(atual))
#         return " | ".join(strings_finais)

#     # Pegamos o valor máximo da coluna de contagem de concorrentes do grupo
#     conc_val = g["QTD_CONCORRENTES"].max() if "QTD_CONCORRENTES" in g.columns else 0
#     conc_val = 0 if pd.isna(conc_val) else conc_val
   
#     return pd.Series({
#         "CONCORRENTES":             int(conc_val),
#         "MAT. PAG.":  gerar_serie_temporal("PAGANTE", "Valor"),
#         "MAT. BOLS.": gerar_serie_temporal("GRATUITO", "Valor"),
#         "MAT. CANC.": gerar_serie_temporal("CANCELADA", "Valor"),
#         "EV. PAG.":   gerar_serie_temporal("PAGANTE", "EVASAO_PAG"),
#         "EV. BOLS.":  gerar_serie_temporal("GRATUITO", "EVASAO_BOLS"),
#         "VAGAS":      gerar_serie_temporal(None, "VAGAS_ULTIM", is_sum=False),
#         "TURMAS":     gerar_serie_temporal(None, "TURMA", is_sum=False)
#     })

# # ─────────────────────────────────────────────
# # SIDEBAR – FILTROS
# # ─────────────────────────────────────────────
# TODOS = "Todos"

# # ─────────────────────────────────────────────
# # ESTILO CUSTOMIZADO (Borda e Dropdown)
# # ─────────────────────────────────────────────
# st.markdown("""
# <style>
#     /* Estilização da borda de foco do multiselect (igual à foto) */
#     div[data-baseweb="select"] > div:focus-within {
#         border-color: #ff4b4b !important;
#         box-shadow: 0 0 0 1px #ff4b4b !important;
#     }
#     /* Ajuste de fonte e placeholder */
#     .stMultiSelect div[data-baseweb="select"] {
#         border-radius: 8px;
#     }
# </style>
# """, unsafe_allow_html=True)

# def multiselect_com_seletor(label, opcoes, placeholder):
#     """
#     Cria um multiselect que inclui 'Select all' no topo.
#     """
#     opcoes_list = list(opcoes)
#     # Adiciona "Select all" como primeira opção
#     selecionados = st.multiselect(
#         label, 
#         options=["Select all"] + opcoes_list, 
#         placeholder=placeholder
#     )
    
#     # Lógica: Se "Select all" for clicado ou nada for selecionado, retorna todas as opções
#     if "Select all" in selecionados or not selecionados:
#         return opcoes_list
#     return selecionados

# with st.sidebar:
#     st.markdown("### ✦ FILTROS")
#     st.divider()

#     # Bloco 1: Temporal
#     st.markdown("**📅 TEMPORAL**")
#     ano_sel = multiselect_com_seletor(
#         "ANO", 
#         sorted(df["ANO"].dropna().unique()), 
#         "Todos os Anos"
#     )
#     sem_sel = multiselect_com_seletor(
#         "SEMESTRE", 
#         sorted(df["SEMESTRE"].dropna().unique()), 
#         "Todos os Semestres"
#     )
#     st.divider()

#     # Bloco 3: Geográfico
#     st.markdown("**🌎 GEOGRÁFICO**")
#     reg_sel = multiselect_com_seletor(
#         "REGIONAL", 
#         sorted(df["REGIONAL"].dropna().unique()), 
#         "Todas as Regionais"
#     )
#     uni_sel = multiselect_com_seletor(
#         "UNIDADE", 
#         sorted(df.loc[df["REGIONAL"].isin(reg_sel), "UNIDADE"].dropna().unique()), 
#         "Todas as Unidades"
#     )
#     st.divider()
    
#     # Bloco 2: Operacional
#     st.markdown("**📚 EDUCACIONAL**")
#     tur_sel = multiselect_com_seletor(
#         "TURNO", 
#         sorted(df["TURNO"].dropna().unique()), 
#         "Todos os Turnos")
    
#     mod_sel = multiselect_com_seletor(
#         "MODALIDADE", 
#         sorted(df["MODALIDADE"].dropna().unique()), 
#         "Todas as Modalidades"
#     )

#     curso_sel = multiselect_com_seletor(
#         "CURSO", 
#         sorted(df["CURSO"].dropna().unique()), 
#         "Todas os Cursos"
#     )
#     st.divider()

# # ─────────────────────────────────────────────
# # APLICAR FILTROS
# # ─────────────────────────────────────────────

# mask_tabela = (
#     df["SEMESTRE"].isin(sem_sel) &
#     df["UNIDADE"].isin(uni_sel) &
#     df["MODALIDADE"].isin(mod_sel) &
#     df["TURNO"].isin(tur_sel) &
#     df["CURSO"].isin(curso_sel)
# )

# # Filtro que INCLUI o ANO (para os KPIs/Cards)
# mask_kpi = mask_tabela & df["ANO"].isin(ano_sel)

# # Dataframes distintos
# dff_tabela = df[mask_tabela].copy() # Esse vai para a função medidas
# dff_kpi = df[mask_kpi].copy()       # Esse vai para os totalizadores (Cards)

# # ─────────────────────────────────────────────
# # CABEÇALHO
# # ─────────────────────────────────────────────
# st.markdown('<div class="page-title">📊 RECOMENDAÇÃO DE CURSO</div>', unsafe_allow_html=True)
# st.markdown('<div class="page-sub">SENAI Bahia · Planejamento de Cursos Técnicos</div>', unsafe_allow_html=True)

# # ─────────────────────────────────────────────
# #  KPI CARDS
# # ─────────────────────────────────────────────

# # Identificar o ano de referência (último selecionado) e o ano imediatamente anterior
# ano_atual = max(ano_sel) if ano_sel else 2025
# ano_anterior = ano_atual - 1

# # Filtrar base para o ano anterior (mantendo os mesmos filtros de regional/unidade/semestre)
# mask_prev = mask_tabela & (df["ANO"] == ano_anterior)
# dff_prev = df[mask_prev]

# # Métricas Ano Atual (dff_kpi já é o ano atual filtrado)
# total_mat_pag  = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="PAGANTE","Valor"].sum()
# total_mat_bols = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="GRATUITO","Valor"].sum()
# total_ev_pag   = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="PAGANTE","EVASAO_PAG"].sum()
# total_ev_bols  = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="GRATUITO","EVASAO_BOLS"].sum()
# # Concorrentes: Usamos nunique na base filtrada por regional/unidade
# total_conc = dff_kpi["INSTITUIÇÃO"].nunique() if "INSTITUIÇÃO" in dff_kpi.columns else 0

# # Taxas Atuais (Corrigidas)
# taxa_ev_pag = (total_ev_pag / total_mat_pag * 100) if total_mat_pag > 0 else 0
# taxa_ev_bols = (total_ev_bols / total_mat_bols * 100) if total_mat_bols > 0 else 0

# # Métricas Ano Anterior (Para o Delta)
# prev_mat_pag = dff_prev.loc[dff_prev["CONDIÇÃO"]=="PAGANTE","Valor"].sum()
# prev_mat_bols = dff_prev.loc[dff_prev["CONDIÇÃO"]=="GRATUITO","Valor"].sum()

# # ─────────────────────────────────────────────
# # LÓGICA DE MÉTRICAS E DELTAS (RETIFICADA)
# # ─────────────────────────────────────────────

# # 1. Definir o Ano Base para Comparação
# # Se "Todos" estiver selecionado, pegamos o maior ano disponível (ex: 2026)
# ultimo_ano_sel = max(ano_sel) if ano_sel else df["ANO"].max()
# ano_anterior = ultimo_ano_sel - 1

# # 2. Filtrar dados para o cálculo do Delta (Respeitando os outros filtros da sidebar)
# # Filtramos a base ORIGINAL (df) com os filtros operacionais, mas isolando os anos
# dff_ano_atual = df[(df["ANO"] == ultimo_ano_sel) & mask_tabela]
# dff_ano_prev  = df[(df["ANO"] == ano_anterior) & mask_tabela]

# def get_mat(dataframe, cond):
#     return dataframe.loc[dataframe["CONDIÇÃO"] == cond, "Valor"].sum()

# # Valores para os Cards (Baseados na seleção atual dff_kpi)
# mat_pag_total = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="PAGANTE", "Valor"].sum()
# mat_bols_total = dff_kpi.loc[dff_kpi["CONDIÇÃO"]=="GRATUITO", "Valor"].sum()

# # Valores para o Cálculo do Delta (Comparando Ano Atual vs Anterior)
# val_pag_atual = get_mat(dff_ano_atual, "PAGANTE")
# val_pag_prev  = get_mat(dff_ano_prev, "PAGANTE")
# val_bols_atual = get_mat(dff_ano_atual, "GRATUITO")
# val_bols_prev  = get_mat(dff_ano_prev, "GRATUITO")

# # 3. Cálculo de Concorrentes (Somatório de Instituições Únicas)
# # Garantimos que a contagem ignore duplicatas de anos/turnos no set filtrado
# if "INSTITUIÇÃO" in dff_kpi.columns:
#     total_conc = dff_kpi["INSTITUIÇÃO"].nunique()
# else:
#     # Fallback caso a coluna tenha sido renomeada no merge
#     total_conc = dff_kpi["QTD_CONCORRENTES"].max() if "QTD_CONCORRENTES" in dff_kpi.columns else 0

# # Definir anos para comparação
# ultimo_ano = max(ano_sel) if ano_sel else df["ANO"].max()
# ano_ant = ultimo_ano - 1

# # Dataframes auxiliares (Respeitando filtros operacionais da sidebar)
# dff_at = df[(df["ANO"] == ultimo_ano) & mask_tabela]
# dff_ant = df[(df["ANO"] == ano_ant) & mask_tabela]

# def get_metrics(dataframe):
#     m_pag = dataframe.loc[dataframe["CONDIÇÃO"] == "PAGANTE", "Valor"].sum()
#     m_bols = dataframe.loc[dataframe["CONDIÇÃO"] == "GRATUITO", "Valor"].sum()
#     e_pag = dataframe.loc[dataframe["CONDIÇÃO"] == "PAGANTE", "EVASAO_PAG"].sum()
#     e_bols = dataframe.loc[dataframe["CONDIÇÃO"] == "GRATUITO", "EVASAO_BOLS"].sum()
    
#     t_pag = (e_pag / m_pag * 100) if m_pag > 0 else 0
#     t_bols = (e_bols / m_bols * 100) if m_bols > 0 else 0
    
#     return m_pag, m_bols, e_pag, e_bols, t_pag, t_bols

# # Calcular valores Atuais e Anteriores
# at_mp, at_mb, at_ep, at_eb, at_tp, at_tb = get_metrics(dff_at)
# ant_mp, ant_mb, ant_ep, ant_eb, ant_tp, ant_tb = get_metrics(dff_ant)

# # Função de Delta com Lógica Invertida para Evasão
# def fmt_delta(at, ant, invert=False):
#     if ant > 0:
#         var = ((at - ant) / ant) * 100
#         # Se invert=True (Evasão), subir é ruim (vermelho)
#         if invert:
#             cor = "#dc3545" if var > 0 else "#28a745"
#         else:
#             cor = "#28a745" if var >= 0 else "#dc3545"
            
#         seta = "▲" if var >= 0 else "▼"
#         return f"<span style='color:{cor}; font-weight:bold;'>{seta} {var:.1f}%</span> <span style='color:gray;'>vs ano ant.</span>"
#     return "<span style='color:gray;'>---</span>"

# delta_pag = fmt_delta(val_pag_atual, val_pag_prev)
# delta_bols = fmt_delta(val_bols_atual, val_bols_prev)

# # ─────────────────────────────────────────────
# # EXIBIÇÃO DOS CARDS
# # ─────────────────────────────────────────────

# st.markdown("""
# <style>
#     .kpi-container {
#         display: flex;
#         justify-content: space-between;
#         gap: 10px;
#         margin-bottom: 20px;
#     }
#     .kpi-box {
#         background: white;
#         padding: 15px;
#         border-radius: 12px;
#         border: 1px solid #E0E0E0;
#         box-shadow: 0 4px 6px rgba(0,0,0,0.02);
#         flex: 1;
#         min-width: 150px;
#         border-left: 5px solid #DDD;
#     }
#     .kpi-title {
#         color: #666;
#         font-size: 0.75rem;
#         text-transform: uppercase;
#         font-weight: 700;
#         margin-bottom: 8px;
#     }
#     .kpi-value {
#         color: #1A1A1A;
#         font-size: 1.8rem;
#         font-weight: 800;
#         line-height: 1;
#         margin-bottom: 5px;
#     }
# </style>
# """, unsafe_allow_html=True)

# # Exibição
# c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

# metrics = [
#     (c1, "Matrículas Pagante", f"{int(at_mp)}", fmt_delta(at_mp, ant_mp), "#004587"),
#     (c2, "Evasão Pagante", f"{int(at_ep)}", fmt_delta(at_ep, ant_ep, invert=True), "#dc8d26"),
#     (c3, "Taxa Evasão Pag.", f"{at_tp:.1f}%", fmt_delta(at_tp, ant_tp, invert=True), "#69280D"),
#     (c4, "Matrículas Bolsista", f"{int(at_mb)}", fmt_delta(at_mb, ant_mb), "#004587"),
#     (c5, "Evasão Bolsista", f"{int(at_eb)}", fmt_delta(at_eb, ant_eb, invert=True), "#dc8d26"),
#     (c6, "Taxa Evasão Bols.", f"{at_tb:.1f}%", fmt_delta(at_tb, ant_tb, invert=True), "#69280D"),
#     (c7, "Concorrentes", f"{int(total_conc)}", "", "#00A199")
# ]

# for col, label, val, delta, color in metrics:
#     with col:
#         st.markdown(f"""
#             <div class="kpi-box" style="border-left-color: {color};">
#                 <div class="kpi-title">{label}</div>
#                 <div class="kpi-value">{val}</div>
#                 <div class="kpi-delta">{delta}</div>
#             </div>
#         """, unsafe_allow_html=True)


# # ─────────────────────────────────────────────
# # TABELA PRINCIPAL
# # ─────────────────────────────────────────────

# # Definimos as colunas de agrupamento (dimensões que não mudam)
# group_cols = ["CURSO", "MODALIDADE", "TURNO"]
# if "Esforço de Venda" in dff_tabela.columns: group_cols.append("Esforço de Venda")
# if "Turmas Potenciais" in dff_tabela.columns: group_cols.append("Turmas Potenciais")
# if "CLASSIFICAÇÃO" in dff_tabela.columns: group_cols.append("CLASSIFICAÇÃO")
# if "OFERTA_SENAI" in dff_tabela.columns: group_cols.append("OFERTA_SENAI")

# # Gerar a tabela aplicando a nova função de medidas
# dff_tabela = dff_tabela.groupby(group_cols, dropna=False, as_index=False).apply(medidas).reset_index()
# dff_tabela.rename(columns={"CLASSIFICAÇÃO":"CLASSIFICAÇÃO", 
#                     "Esforço de Venda":"ESFORÇO DE VENDA", 
#                     "Turmas Potenciais":"TURMAS POTENCIAIS", 
#                     "OFERTA_SENAI":"OFERTA SENAI"}, inplace=True)

# # Limpeza de colunas duplicadas por causa do merge/apply
# if "level_0" in dff_tabela.columns: dff_tabela = dff_tabela.drop(columns=["level_0"])

# st.divider()
# # st.markdown('<div class="page-title">📊 RECOMENDAÇÃO DE CURSO</div>', unsafe_allow_html=True)

# st.markdown('<div class="page-title">Detalhamento Temporal por Curso / Unidade</div>', unsafe_allow_html=True)
# st.caption("#### Valores exibidos na sequência: **2023 | 2024 | 2025 | 2026**")

# # ─────────────────────────────────────────────
# # FILTROS DE TOPO (CLASSIFICAÇÃO E OFERTA)
# # ─────────────────────────────────────────────
# st.markdown("##### 🔍Observatório/PA")
# c_topo1, c_topo2 = st.columns([0.5, 1])

# with c_topo1:
#     class_opts = sorted(dff_tabela["CLASSIFICACAO"].dropna().unique())
#     class_sel = st.multiselect("🏷️  Preditiva: Classificação", class_opts, placeholder="Todas as Classificações")
#     if not class_sel: class_sel = list(class_opts)

# with c_topo2:
#     # Flag Sim/Não (Se não selecionar nada, traz todos)
#     of_val = st.pills(
#         "🚀 Oferta SENAI", 
#         options=["Sim", "Não"], 
#         selection_mode="single"
#     )
#     of_opts = sorted(df["OFERTA_SENAI"].dropna().unique())
#     of_sel = [of_val] if of_val else list(of_opts)

# # Aplicação dos filtros finais antes do groupby
# mask_tabela &= dff_tabela["CLASSIFICACAO"].isin(class_sel)
# mask_tabela &= dff_tabela["OFERTA_SENAI"].isin(of_sel)

# # Dataframe que será usado na função medidas
# tabela_final = dff_tabela[mask_tabela].copy()
# # Agora chame o groupby e a função medidas usando tabela_final...
# tabela_exibicao = tabela_final.groupby(group_cols, dropna=False, as_index=False).apply(medidas).reset_index()

# # Exibição com itables (interactive_table)
# interactive_table(
#     tabela_exibicao, # Resultado do apply(medidas)
#     paging=False, 
#     scrollY="600px", 
#     scrollCollapse=True,
#     scrollX=True,
#     columnDefs=[{"className": "dt-center", "targets": "_all"}]
# )
# st.divider()
# # ─────────────────────────────────────────────
# # EXPORTAÇÃO
# # ─────────────────────────────────────────────
# st.markdown('<div class="section-title">Exportação</div>', unsafe_allow_html=True)

# # INSERI TABELA DE APROVEITAMENTO BOLSA
# # AJUSTAR OS CARDS PARA EVASÃO PAGANTES E EVAÇÃO BOLSITA E MATRICULA PAGANTE E MATRIOCULA BOLSISTA
# # VER CALCULO DE VAGA DE BOLSISTA
# # INSERIT TABELA DE TENDÊNCIA DE MATRICULAS
# # TABELA DE RECOMENDAÇÃO E A TABELA DE VIABILIDADE DE TURMA


# ===============================================================================================================================================

# import pickle
# import warnings
# import pandas as pd
# import numpy as np
# import streamlit as st
# from itables.streamlit import interactive_table
# from io import BytesIO

# warnings.filterwarnings("ignore")

# # ─────────────────────────────────────────────
# # 1. CONFIGURAÇÃO DA PÁGINA
# # ─────────────────────────────────────────────
# st.set_page_config(
#     page_title="Recomendação de Curso | SENAI Bahia",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# def apply_custom_styles():
#     st.markdown("""
#     <style>
#     @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@300;400;500&display=swap');
#     html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }
#     .main { background: #f8f9fa; }
    
#     /* Títulos */
#     .page-title { font-family: 'Barlow Condensed', sans-serif; font-size: 2.2rem; font-weight: 700; color: #1a1a1a; letter-spacing: .02em; }
#     .page-sub { font-size: .9rem; color: #666; margin-bottom: 1.5rem; }
#     .section-title { font-family: 'Barlow Condensed', sans-serif; font-size: 1.2rem; font-weight: 600; text-transform: uppercase; color: #004587; margin: 1rem 0; border-left: 4px solid #004587; padding-left: 10px; }

#     /* Cards KPI */
#     .kpi-box { background: white; padding: 15px; border-radius: 12px; border: 1px solid #E0E0E0; border-left: 5px solid #DDD; }
#     .kpi-title { color: #666; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 5px; }
#     .kpi-value { color: #1A1A1A; font-size: 1.6rem; font-weight: 800; }
#     .kpi-delta { font-size: 0.75rem; margin-top: 5px; }

#     /* Filtros Sidebar */
#     section[data-testid="stSidebar"] { background: #ffffff; }
#     div[data-baseweb="select"] > div:focus-within { border-color: #004587 !important; }
#     </style>
#     """, unsafe_allow_html=True)

# # ─────────────────────────────────────────────
# # 2. CARREGAMENTO DE DADOS
# # ─────────────────────────────────────────────
# @st.cache_data
# def load_raw_data():
#     files = {
#         "bd": "BD_Plan_Curso_Tecnico.pkl",
#         "conc": "Base_Concorrentes.pkl",
#         "ev": "Base_de_Evasao.pkl",
#         "vagas": "dVagas.pkl"}
    
#     data = {}
#     for key, path in files.items():
#         with open(path, "rb") as f:
#             data[key] = pickle.load(f)
#     return data["bd"], data["conc"], data["ev"], data["vagas"]

# # ─────────────────────────────────────────────
# # 3. PROCESSAMENTO E JOINS
# # ─────────────────────────────────────────────
# def process_data(bd, conc, ev, vagas):
#     # --- A. Evasão ---
#     ev_agg = (ev.groupby("COD_Base_de_Evasao")
#                 .agg(EVASAO_PAG=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="PAGANTE"].sum()),
#                      EVASAO_BOLS=("EVASAO", lambda x: x[ev.loc[x.index,"CONDIÇÃO"]=="GRATUITO"].sum()))
#                 .reset_index())
#     df = bd.merge(ev_agg, on="COD_Base_de_Evasao", how="left")

#     # --- B. Vagas ---
#     if not vagas.empty:
#         vagas_m = vagas.rename(columns={"VAGAS_2": "VAGAS_ULTIM"}).drop_duplicates(subset=["COD_VAGAS"])
#         df = df.merge(vagas_m[["COD_VAGAS", "VAGAS_ULTIM"]], on="COD_VAGAS", how="left")
    
#     # --- C. Observatório (Classificação e Oferta) ---
#     if not bd.empty:
#         # Padronização de nomes de colunas do Observatório
#         obs_clean = bd.copy()
#         col_map = {
#             next((c for c in ["CLASSIFICACAO", "CLASSIFICAÇÃO", "Classificação"] if c in bd.columns), "CLASSIFICACAO"): "CLASSIFICACAO",
#             next((c for c in ["OFERTA_SENAI", "Oferta Senai", "OFERTA SENAI"] if c in bd.columns), "OFERTA_SENAI"): "OFERTA_SENAI"
#         }
#         obs_clean = obs_clean.rename(columns=col_map)
#         obs_reduced = obs_clean[["COD_Observatorio", "CLASSIFICACAO", "OFERTA_SENAI"]].drop_duplicates(subset=["COD_Observatorio"])
#         df = df.merge(obs_reduced, on="COD_Observatorio", how="left")

#     # --- D. Concorrentes ---
#     conc_agg = conc.groupby("COD_Concorrentes")["INSTITUIÇÃO"].nunique().reset_index().rename(columns={"INSTITUIÇÃO": "QTD_CONCORRENTES"})
#     df = df.merge(conc_agg, on="COD_Concorrentes", how="left")
    
#     # Preenchimento de nulos básicos
#     df["Valor"] = df["Valor"].fillna(0)
#     for col in ["VAGAS_ULTIM", "TURMA", "QTD_CONCORRENTES", "EVASAO_PAG", "EVASAO_BOLS"]:
#         if col in df.columns:
#             df[col] = df[col].fillna(0)
            
#     return df

# # ─────────────────────────────────────────────
# # 4. MOTOR DE CÁLCULO (MEDIDAS TEMPORAIS)
# # ─────────────────────────────────────────────
# def medidas_temporais(g):
#     anos_ref = [2023, 2024, 2025, 2026]
    
#     def gerar_serie_temporal(condicao, coluna, is_sum=True):
#         valores_num = []
#         for ano in anos_ref:
#             mask = (g["ANO"] == ano)
#             if condicao: mask &= (g["CONDIÇÃO"] == condicao)
            
#             sub = g.loc[mask, coluna]
#             res = (sub.sum() if is_sum else sub.max()) if not sub.empty else 0
#             val = 0 if pd.isna(res) else int(round(float(res)))
#             valores_num.append(val)
        
#         if sum(valores_num) == 0: return "-"
        
#         # Lógica de ícones de tendência
#         res_str = []
#         for i, atual in enumerate(valores_num):
#             if atual == 0: res_str.append("-")
#             elif i > 0 and valores_num[i-1] > 0:
#                 if atual > valores_num[i-1]: res_str.append(f"🡅 {atual}")
#                 elif atual < valores_num[i-1]: res_str.append(f"🡇 {atual}")
#                 else: res_str.append(str(atual))
#             else: res_str.append(str(atual))
#         return " | ".join(res_str)

#     return pd.Series({
#         "MAT. PAG. (23-26)":  gerar_serie_temporal("PAGANTE", "Valor"),
#         "MAT. BOLS. (23-26)": gerar_serie_temporal("GRATUITO", "Valor"),
#         "MAT. CANC. (23-26)": gerar_serie_temporal("CANCELADA", "Valor"),
#         "VAGAS (23-26)":      gerar_serie_temporal(None, "VAGAS_ULTIM", False),
#         "TURMAS (23-26)":     gerar_serie_temporal(None, "TURMA", False),
#         "CONCORRENTES":       int(g["QTD_CONCORRENTES"].max()) if "QTD_CONCORRENTES" in g.columns else 0
#     })

# # ─────────────────────────────────────────────
# # 5. INTERFACE SIDEBAR (FILTROS)
# # ─────────────────────────────────────────────
# def build_sidebar(df):
#     with st.sidebar:
#         st.markdown("### ✦ CENTRO DE COMANDO")
#         st.divider()

#         def multiselect_all(label, options, key):
#             sel = st.multiselect(label, ["Selecionar Todos"] + list(options), key=key)
#             if "Selecionar Todos" in sel or not sel: return list(options)
#             return sel

#         # Agrupamento Temporal
#         st.markdown("**📅 TEMPORAL**")
#         c1, c2 = st.columns(2)
#         with c1: ano_sel = multiselect_all("ANO", sorted(df["ANO"].unique()), "f_ano")
#         with c2: sem_sel = multiselect_all("SEM.", sorted(df["SEMESTRE"].unique()), "f_sem")
        
#         st.divider()
#         # Agrupamento Geográfico
#         st.markdown("**🌎 GEOGRÁFICO**")
#         reg_sel = multiselect_all("REGIONAL", sorted(df["REGIONAL"].unique()), "f_reg")
#         uni_sel = multiselect_all("UNIDADE", sorted(df[df["REGIONAL"].isin(reg_sel)]["UNIDADE"].unique()), "f_uni")
        
#         st.divider()
#         # Agrupamento Educacional
#         st.markdown("**📚 EDUCACIONAL**")
#         mod_sel = multiselect_all("MODALIDADE", sorted(df["MODALIDADE"].unique()), "f_mod")
#         tur_sel = multiselect_all("TURNO", sorted(df["TURNO"].unique()), "f_tur")
#         curso_sel = multiselect_all("CURSO", sorted(df["CURSO"].unique()), "f_curso")
        
#     return ano_sel, sem_sel, reg_sel, uni_sel, mod_sel, tur_sel, curso_sel

# # ─────────────────────────────────────────────
# # 6. EXECUÇÃO PRINCIPAL
# # ─────────────────────────────────────────────
# apply_custom_styles()
# bd, conc, ev, vagas = load_raw_data() # obs
# df = process_data(bd, conc, ev, vagas)

# # Sidebar e Filtros
# ano_sel, sem_sel, reg_sel, uni_sel, mod_sel, tur_sel, curso_sel = build_sidebar(df)

# # Criação das Máscaras
# mask_base = (df["SEMESTRE"].isin(sem_sel) & df["UNIDADE"].isin(uni_sel) & 
#              df["MODALIDADE"].isin(mod_sel) & df["TURNO"].isin(tur_sel) & df["CURSO"].isin(curso_sel))

# dff_tabela = df[mask_base].copy()
# dff_kpi = df[mask_base & df["ANO"].isin(ano_sel)].copy()

# # --- HEADER ---
# st.markdown('<div class="page-title">📊 INTELIGÊNCIA DE MERCADO</div>', unsafe_allow_html=True)
# st.markdown('<div class="page-sub">SENAI Bahia · Matriz de Recomendação de Cursos Técnicos</div>', unsafe_allow_html=True)

# # --- BLOCO DE KPIs ---
# st.markdown('<div class="section-title">Indicadores de Performance (Ano Selecionado)</div>', unsafe_allow_html=True)

# def calc_kpis(current_df, full_df, ano_atual, mask_filtros):
#     ano_ant = ano_atual - 1
#     prev_df = full_df[(full_df["ANO"] == ano_ant) & mask_filtros]
    
#     def get_v(dataframe, cond): return dataframe[dataframe["CONDIÇÃO"] == cond]["Valor"].sum()
    
#     # Matrículas
#     m_pag = get_v(current_df, "PAGANTE"); m_pag_ant = get_v(prev_df, "PAGANTE")
#     m_bols = get_v(current_df, "GRATUITO"); m_bols_ant = get_v(prev_df, "GRATUITO")
    
#     # Evasão
#     e_pag = current_df[current_df["CONDIÇÃO"] == "PAGANTE"]["EVASAO_PAG"].sum()
#     e_pag_ant = prev_df[prev_df["CONDIÇÃO"] == "PAGANTE"]["EVASAO_PAG"].sum()
    


#     return (m_pag, m_pag_ant), (m_bols, m_bols_ant), (e_pag, e_pag_ant)

# # Cálculo dos Deltas e Exibição
# ult_ano = max(ano_sel) if ano_sel else 2025
# (mp, mp_a), (mb, mb_a), (ep, ep_a) = calc_kpis(dff_kpi, df, ult_ano, mask_base)

# def render_kpi(col, label, val, ant, color, is_evasao=False):
#     delta = ((val - ant)/ant*100) if ant > 0 else 0
#     seta = "▲" if delta >= 0 else "▼"
#     # Se for evasão, subir é ruim (vermelho)
#     cor_delta = ("#dc3545" if delta > 0 else "#28a745") if is_evasao else ("#28a745" if delta >= 0 else "#dc3545")
    
#     with col:
#         st.markdown(f"""
#         <div class="kpi-box" style="border-left-color: {color};">
#             <div class="kpi-title">{label}</div>
#             <div class="kpi-value">{int(val)}</div>
#             <div class="kpi-delta"><span style="color:{cor_delta}">{seta} {delta:.1f}%</span> vs {ult_ano-1}</div>
#         </div>
#         """, unsafe_allow_html=True)

# ck1, ck2, ck3, ck4 = st.columns(4)
# render_kpi(ck1, "Matrículas Pagante", mp, mp_a, "#004587")
# render_kpi(ck2, "Matrículas Bolsista", mb, mb_a, "#004587")
# render_kpi(ck3, "Evasão Pagante", ep, ep_a, "#dc8d26", is_evasao=True)
# with ck4:
#     total_conc = dff_kpi["QTD_CONCORRENTES"].sum() if "QTD_CONCORRENTES" in dff_kpi.columns else 0
#     st.markdown(f"""<div class="kpi-box" style="border-left-color: #00A199;"><div class="kpi-title">Concorrentes Diretos</div><div class="kpi-value">{int(total_conc)}</div><div class="kpi-delta">Mapeamento Atual</div></div>""", unsafe_allow_html=True)

# # --- FILTROS DE TOPO (OBSERVATÓRIO) ---
# st.divider()
# st.markdown('<div class="section-title">🔍 Refinar Detalhamento (Observatório/PA)</div>', unsafe_allow_html=True)
# ct1, ct2 = st.columns([2, 1])
# with ct1:
#     c_opts = sorted(df["CLASSIFICACAO"].dropna().unique()) if "CLASSIFICACAO" in df.columns else []
#     c_sel = st.multiselect("🏷️ Classificação Preditiva", c_opts, placeholder="Todas as Classificações")
# with ct2:
#     o_val = st.pills("🚀 Oferta SENAI Atual", options=["Sim", "Não"], selection_mode="single")

# # Aplicação Final e Tabela
# if c_sel: dff_tabela = dff_tabela[dff_tabela["CLASSIFICACAO"].isin(c_sel)]
# if o_val: dff_tabela = dff_tabela[dff_tabela["OFERTA_SENAI"] == o_val]

# if not dff_tabela.empty:
#     g_cols = ["CURSO", "MODALIDADE", "TURNO"]
#     for c in ["CLASSIFICACAO", "OFERTA_SENAI"]:
#         if c in dff_tabela.columns: g_cols.append(c)
        
#     tabela_final = dff_tabela.groupby(g_cols, dropna=False, as_index=False).apply(medidas_temporais).reset_index()
#     if "level_0" in tabela_final.columns: tabela_final.drop(columns=["level_0"], inplace=True)
    
#     interactive_table(tabela_final, paging=False, scrollY="500px", scrollX=True, columnDefs=[{"className": "dt-center", "targets": "_all"}])
# else:
#     st.warning("Nenhum dado encontrado para os filtros selecionados.")

# ==========================================================================================================================================================
# ==========================================================================================================================================================

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
        res_str = []
        for i, atual in enumerate(valores_num):
            if atual == 0: res_str.append("-")
            elif i > 0 and valores_num[i-1] > 0:
                if atual > valores_num[i-1]: res_str.append(f"🡅 {atual}")
                elif atual < valores_num[i-1]: res_str.append(f"🡇 {atual}")
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
        st.markdown("**📅 TEMPORAL**")
        c1, c2 = st.columns(2)
        with c1: ano_sel = multiselect_all("ANO", sorted(df["ANO"].unique()), "f_ano")
        with c2: sem_sel = multiselect_all("SEM.", sorted(df["SEMESTRE"].unique()), "f_sem")
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
st.markdown('<div class="section-title">🔍 Refinar Detalhamento (Observatório/PA)</div>', unsafe_allow_html=True)
ct1, ct2 = st.columns([2, 1])
with ct1:
    c_opts = sorted(df["CLASSIFICACAO"].dropna().unique()) if "CLASSIFICACAO" in df.columns else []
    c_sel = st.multiselect("🏷️ Classificação Preditiva", c_opts, placeholder="Todas as Classificações")
with ct2:
    o_val = st.pills("🚀 Oferta SENAI Atual", options=["Sim", "Não"], selection_mode="single")

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