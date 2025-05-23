import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Importar configurações
from config import (
    STATE_RISKS_DF, STATE_USER_DATA, STATE_PROJECT_DATA, 
    STATE_USER_CONFIG_COMPLETED, STATE_SIMULATION_RESULTS_DF,
    SIMULATION_ITERATIONS_DEFAULT
)

# Importar módulos de utilidades
from utils.probabilistic_analysis import run_monte_carlo_simulation
from utils.gspread_logger import record_log

# Verificação de configurações
if not st.session_state[STATE_USER_CONFIG_COMPLETED]:
    st.error("⚠️ É necessário preencher as informações de usuário e projeto antes de prosseguir!")
    st.page_link("0_Configuracao_Usuario_e_Projeto.py", label="Ir para Configuração")
    st.stop()

# Verificar se há riscos cadastrados
if STATE_RISKS_DF not in st.session_state or st.session_state[STATE_RISKS_DF].empty:
    st.error("⚠️ Não há riscos cadastrados. Por favor, identifique e cadastre riscos primeiro.")
    st.page_link("1_Identificacao_e_Cadastro_de_Riscos.py", label="Ir para Identificação de Riscos")
    st.stop()

# Título da página
st.title("📈 Análise Quantitativa e Probabilística")

# Informações sobre a etapa
st.info("""
A análise quantitativa aprofunda o entendimento numérico dos riscos mais críticos. 
Nesta etapa, você refinará as estimativas de impacto com faixas de valores, calculará o 
Valor Monetário Esperado (VME) e realizará simulações de Monte Carlo para gerar 
distribuições de probabilidade para custo e prazo totais do projeto.
""")

# Carregar os dados do projeto
project_data = st.session_state[STATE_PROJECT_DATA]
base_cost = project_data.get("Valor_Total_Estimado", 0.0)
base_duration = project_data.get("Prazo_Total_Dias", 0)

# Verificar valores base válidos
if base_cost <= 0 or base_duration <= 0:
    st.warning("""
    ⚠️ Os valores base do projeto (custo e prazo) não são válidos ou estão em branco. 
    Por favor, atualize estes valores na página de Configuração antes de prosseguir.
    """)
    st.page_link("0_Configuracao_Usuario_e_Projeto.py", label="Ir para Configuração")

# Função para calcular VME (Valor Monetário Esperado)
def calculate_vme(prob_num, min_cost, max_cost):
    """Calcula o VME baseado na probabilidade e nos efeitos de custo min/max"""
    if pd.isna(prob_num) or pd.isna(min_cost) or pd.isna(max_cost):
        return 0.0
    
    # Converter para números se forem strings
    try:
        p = float(prob_num)
        cmin = float(min_cost)
        cmax = float(max_cost)
    except (ValueError, TypeError):
        return 0.0
    
    # VME = probabilidade * média dos efeitos
    # Simplificação: assume distribuição triangular com valor mais provável = média
    vme = p * ((cmin + cmax) / 2)
    return round(vme, 2)

# Carregar riscos existentes
df_risks = st.session_state[STATE_RISKS_DF].copy()

# Garantir que colunas numéricas são do tipo correto
numeric_cols = ['Efeito_Custo_Min', 'Efeito_Custo_Max', 'Efeito_Prazo_Min_Dias', 
               'Efeito_Prazo_Max_Dias', 'Probabilidade_Num', 'Score_Risco']
for col in numeric_cols:
    if col in df_risks.columns:
        df_risks[col] = pd.to_numeric(df_risks[col], errors='coerce').fillna(0.0)

# Filtrar riscos que já têm análise qualitativa (score calculado)
df_analyzed = df_risks[df_risks["Score_Risco"] > 0].copy()

if df_analyzed.empty:
    st.warning("""
    ⚠️ Nenhum risco com análise qualitativa encontrado. Por favor, complete a 
    análise qualitativa antes de prosseguir com a análise quantitativa.
    """)
    st.page_link("pages/2_Analise_Qualitativa_de_Riscos.py", label="Ir para Análise Qualitativa")
else:
    # 1. Análise de VME
    st.subheader("Valor Monetário Esperado (VME)")
    st.markdown("""
    O VME é uma medida estatística que quantifica o impacto médio esperado 
    de um risco considerando sua probabilidade de ocorrência. É calculado como:
    
    **VME = Probabilidade × Impacto Médio**
    
    Use esta tabela para refinar seus valores de impacto numérico e visualizar o VME:
    """)
    
    # Colunas para a tabela de VME
    vme_cols = [
        "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Score_Risco",
        "Probabilidade_Num", "Efeito_Custo_Min", "Efeito_Custo_Max", "VME_Custo"
    ]
    
    # Garantir que todas as colunas existam
    for col in vme_cols:
        if col not in df_analyzed.columns:
            if col == "VME_Custo":
                df_analyzed[col] = 0.0
            else:
                df_analyzed[col] = ""
    
    # Configuração das colunas para o editor
    vme_column_config = {
        "ID_Risco": st.column_config.TextColumn("ID", width="small", disabled=True),
        "Descricao_Risco": st.column_config.TextColumn("Descrição", width="large", disabled=True),
        "Tipo_Risco": st.column_config.TextColumn("Tipo", width="small", disabled=True),
        "Score_Risco": st.column_config.NumberColumn("Score", format="%.1f", width="small", disabled=True),
        "Probabilidade_Num": st.column_config.NumberColumn(
            "Probabilidade", format="%.2f", min_value=0.0, max_value=1.0, step=0.05,
            help="Valor numérico da probabilidade (0-1)"),
        "Efeito_Custo_Min": st.column_config.NumberColumn(
            "Efeito Mín. Custo (R$)", format="R$ %.2f", min_value=0.0,
            help="Impacto mínimo esperado em custo (R$)"),
        "Efeito_Custo_Max": st.column_config.NumberColumn(
            "Efeito Máx. Custo (R$)", format="R$ %.2f", min_value=0.0,
            help="Impacto máximo esperado em custo (R$)"),
        "VME_Custo": st.column_config.NumberColumn(
            "VME (R$)", format="R$ %.2f", disabled=True,
            help="Valor Monetário Esperado = Probabilidade × Média dos Efeitos")
    }
    
    # Ordenar por Score_Risco para focar nos mais críticos
    df_vme = df_analyzed.sort_values(by="Score_Risco", ascending=False).copy()

    # Colunas que o usuário pode editar na tabela VME e que precisam ser salvas
    editable_vme_cols_for_save = ["Probabilidade_Num", "Efeito_Custo_Min", "Efeito_Custo_Max"]

    # Garantir que estas colunas sejam numéricas em df_vme antes de passar ao editor
    for col in editable_vme_cols_for_save:
        if col in df_vme.columns:
            df_vme[col] = pd.to_numeric(df_vme[col], errors='coerce').fillna(0.0)
        else:
            df_vme[col] = 0.0 # Se não existir, inicializa como float

    # A coluna VME_Custo também deve ser numérica
    if "VME_Custo" in df_vme.columns:
        df_vme["VME_Custo"] = pd.to_numeric(df_vme["VME_Custo"], errors='coerce').fillna(0.0)
    else:
        df_vme["VME_Custo"] = 0.0
    
    # Editor de dados para VME
    edited_vme_df = st.data_editor(
        df_vme[vme_cols], # vme_cols define as colunas mostradas no editor
        column_config=vme_column_config,
        use_container_width=True,
        key="vme_editor",
        hide_index=True
    )
    
    # Botão para calcular VME
    if st.button("Calcular VME", use_container_width=True):
        # Obter o DataFrame principal do session_state para atualização
        df_riscos_main = st.session_state[STATE_RISKS_DF].copy()

        # Iterar sobre as linhas do DataFrame editado no st.data_editor (edited_vme_df)
        for idx_edited, row_edited in edited_vme_df.iterrows():
            risk_id_edited = row_edited["ID_Risco"]
            
            # Encontrar a linha correspondente no DataFrame principal (df_riscos_main)
            mask = df_riscos_main["ID_Risco"] == risk_id_edited
            if mask.any():
                # 1. Atualizar colunas editáveis (Probabilidade_Num, Efeito_Custo_Min, Efeito_Custo_Max)
                for col_editable in editable_vme_cols_for_save:
                    if col_editable in row_edited.index:
                        # Certificar que o valor é numérico antes de atribuir
                        value_to_assign = pd.to_numeric(row_edited[col_editable], errors='coerce')
                        df_riscos_main.loc[mask, col_editable] = value_to_assign if pd.notna(value_to_assign) else 0.0
                
                # 2. Calcular o novo VME_Custo com base nos valores (possivelmente atualizados) do editor
                new_vme_custo = calculate_vme(
                    row_edited["Probabilidade_Num"], # Usa o valor do editor
                    row_edited["Efeito_Custo_Min"],  # Usa o valor do editor
                    row_edited["Efeito_Custo_Max"]   # Usa o valor do editor
                )
                df_riscos_main.loc[mask, "VME_Custo"] = new_vme_custo
        
        # Salvar o DataFrame principal atualizado de volta no session_state
        st.session_state[STATE_RISKS_DF] = df_riscos_main
        
        st.success("✅ VME calculado e atualizado com sucesso!")
        st.rerun()  # Para atualizar o data_editor com os novos VMEs e valores editados

    # 2. Simulação de Monte Carlo
    st.subheader("Simulação de Monte Carlo")
    st.markdown("""
    A simulação de Monte Carlo permite modelar a incerteza inerente ao projeto, 
    gerando milhares de cenários possíveis através de amostragem aleatória das 
    distribuições de probabilidade dos riscos. Os resultados mostram como os riscos 
    interagem e afetam o custo e prazo totais do projeto.
    """)
    
    # Configuração da simulação
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        iterations = st.number_input(
            "Número de Iterações",
            min_value=1000,
            max_value=100000,
            value=SIMULATION_ITERATIONS_DEFAULT,
            step=1000,
            help="Mais iterações produzem resultados mais estáveis, mas levam mais tempo"
        )
        
    with col2:
        confidence_level = st.selectbox(
            "Nível de Confiança",
            options=[0.50, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99],
            index=4,  # 0.90 como padrão
            format_func=lambda x: f"{int(x*100)}%",
            help="Nível de confiança para o cálculo das reservas de contingência"
        )
    
    with col3:
        st.markdown("""
        **Parâmetros da Simulação:**
        * **Base de Custo:** R$ {:.2f}
        * **Base de Prazo:** {} dias
        * **Amostragem:** Distribuição triangular
        """.format(base_cost, base_duration))
    
    # Botão para executar simulação
    run_simulation = st.button("▶️ Executar Simulação de Monte Carlo", type="primary", use_container_width=True)
    
    if run_simulation:
        # Verificar se há dados suficientes para simulação
        # Garantir que colunas necessárias são numéricas e preencher NaNs com 0 ou valor apropriado
        cols_for_sim_check = [
            "Probabilidade_Num", "Efeito_Custo_Min", "Efeito_Custo_Max",
            "Efeito_Prazo_Min_Dias", "Efeito_Prazo_Max_Dias"
        ]
        for col in cols_for_sim_check:
            if col in df_analyzed.columns:
                df_analyzed[col] = pd.to_numeric(df_analyzed[col], errors='coerce').fillna(0.0)
            else:
                # Se a coluna não existir, criá-la com 0.0 pode não ser ideal para todos os casos,
                # mas para a lógica de filtragem abaixo, permite que o risco seja avaliado.
                # A função de simulação interna também faz coerção e dropna.
                df_analyzed[col] = 0.0

        # Filtro 1: Riscos com probabilidade > 0 e pelo menos um par de efeitos (custo OU prazo) preenchido
        base_filter = (df_analyzed["Probabilidade_Num"] > 0) & \
                      ((df_analyzed["Efeito_Custo_Min"].notna() & df_analyzed["Efeito_Custo_Max"].notna()) | \
                       (df_analyzed["Efeito_Prazo_Min_Dias"].notna() & df_analyzed["Efeito_Prazo_Max_Dias"].notna()))
        
        df_sim_candidates = df_analyzed[base_filter].copy()

        # Filtro 2: Garantir Min <= Max para Custo
        # Para riscos onde custo min/max são preenchidos, mas min > max, eles são inválidos
        invalid_cost_range = (df_sim_candidates["Efeito_Custo_Min"].notna() & \
                              df_sim_candidates["Efeito_Custo_Max"].notna() & \
                              (df_sim_candidates["Efeito_Custo_Min"] > df_sim_candidates["Efeito_Custo_Max"]))
        
        if invalid_cost_range.any():
            st.warning(f"⚠️ {invalid_cost_range.sum()} risco(s) têm 'Efeito Mín. Custo' maior que 'Efeito Máx. Custo' e serão ignorados na simulação de custo.")
            # Opção 1: Ignorar estes para custo (eles ainda podem ter prazo válido)
            # Opção 2: Remover completamente - para simplificar, vamos zerar os campos de custo inválidos
            # para que a lógica da simulação (que usa 0 se um não for preenchido) os trate como sem impacto de custo.
            df_sim_candidates.loc[invalid_cost_range, ['Efeito_Custo_Min', 'Efeito_Custo_Max']] = 0.0


        # Filtro 3: Garantir Min <= Max para Prazo
        invalid_duration_range = (df_sim_candidates["Efeito_Prazo_Min_Dias"].notna() & \
                                  df_sim_candidates["Efeito_Prazo_Max_Dias"].notna() & \
                                  (df_sim_candidates["Efeito_Prazo_Min_Dias"] > df_sim_candidates["Efeito_Prazo_Max_Dias"]))

        if invalid_duration_range.any():
            st.warning(f"⚠️ {invalid_duration_range.sum()} risco(s) têm 'Efeito Mín. Prazo' maior que 'Efeito Máx. Prazo' e serão ignorados na simulação de prazo.")
            df_sim_candidates.loc[invalid_duration_range, ['Efeito_Prazo_Min_Dias', 'Efeito_Prazo_Max_Dias']] = 0.0
            
        # Filtro final: Riscos que ainda têm alguma combinação válida de (Prob > 0 E (Custo Min/Max válidos OU Prazo Min/Max válidos))
        # A função de simulação interna também faz um dropna nas colunas numéricas essenciais.
        # Este filtro aqui é mais para fornecer feedback ao usuário.
        valid_risks_for_sim = df_sim_candidates[
            (df_sim_candidates["Probabilidade_Num"] > 0) &
            (
                (df_sim_candidates["Efeito_Custo_Min"].notna() & df_sim_candidates["Efeito_Custo_Max"].notna()) |
                (df_sim_candidates["Efeito_Prazo_Min_Dias"].notna() & df_sim_candidates["Efeito_Prazo_Max_Dias"].notna())
            )
        ].copy() # .copy() para evitar SettingWithCopyWarning mais tarde

        if valid_risks_for_sim.empty:
            st.error("⚠️ Não há riscos válidos para simulação. Verifique se os riscos têm probabilidades e impactos definidos.")
        else:
            with st.spinner("Executando simulação de Monte Carlo..."):
                try:
                    # Executar simulação usando o módulo de análise probabilística
                    results_df = run_monte_carlo_simulation(
                        base_cost=base_cost,
                        base_duration=base_duration,
                        risks_df=valid_risks_for_sim,
                        num_iterations=iterations
                    )
                    
                    # Salvar resultados no session_state
                    st.session_state[STATE_SIMULATION_RESULTS_DF] = results_df
                    
                    # Log da ação
                    record_log(
                        user_id=st.session_state[STATE_USER_DATA].get('Email'),
                        project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                        page="Analise_Quantitativa",
                        action="Executar Simulacao Monte Carlo",
                        details=f"Iteracoes: {iterations}, Custo Base: {base_cost}, Prazo Base: {base_duration}"
                    )
                    
                    st.success("✅ Simulação concluída com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao executar simulação: {str(e)}")
    
    # Exibir resultados da simulação se disponíveis
    if STATE_SIMULATION_RESULTS_DF in st.session_state and not st.session_state[STATE_SIMULATION_RESULTS_DF].empty:
        # Resultados da simulação
        st.subheader("Resultados da Simulação")
        results_df = st.session_state[STATE_SIMULATION_RESULTS_DF]
        
        # Estatísticas básicas
        col1, col2 = st.columns(2)
        
        # Estatísticas para custo
        with col1:
            st.markdown("### Estatísticas de Custo")
            cost_mean = results_df["Custo_Total_Simulado"].mean()
            cost_median = results_df["Custo_Total_Simulado"].median()
            cost_std = results_df["Custo_Total_Simulado"].std()
            cost_percentile = np.percentile(results_df["Custo_Total_Simulado"], confidence_level * 100)
            cost_contingency = cost_percentile - base_cost
            cost_contingency_percent = (cost_contingency / base_cost) * 100 if base_cost > 0 else 0
            
            st.metric("Custo Médio", f"R$ {cost_mean:,.2f}")
            st.metric("Custo Mediano", f"R$ {cost_median:,.2f}")
            st.metric("Desvio Padrão", f"R$ {cost_std:,.2f}")
            st.metric(f"P{int(confidence_level*100)} (Nível de Confiança)", f"R$ {cost_percentile:,.2f}")
            st.metric("Reserva de Contingência", 
                     f"R$ {cost_contingency:,.2f} ({cost_contingency_percent:.1f}%)",
                     delta=f"{cost_contingency_percent:.1f}%")
        
        # Estatísticas para prazo
        with col2:
            st.markdown("### Estatísticas de Prazo")
            duration_mean = results_df["Prazo_Total_Simulado"].mean()
            duration_median = results_df["Prazo_Total_Simulado"].median()
            duration_std = results_df["Prazo_Total_Simulado"].std()
            duration_percentile = np.percentile(results_df["Prazo_Total_Simulado"], confidence_level * 100)
            duration_contingency = duration_percentile - base_duration
            duration_contingency_percent = (duration_contingency / base_duration) * 100 if base_duration > 0 else 0
            
            st.metric("Prazo Médio", f"{duration_mean:.1f} dias")
            st.metric("Prazo Mediano", f"{duration_median:.1f} dias")
            st.metric("Desvio Padrão", f"{duration_std:.1f} dias")
            st.metric(f"P{int(confidence_level*100)} (Nível de Confiança)", f"{duration_percentile:.1f} dias")
            st.metric("Reserva de Contingência", 
                     f"{duration_contingency:.1f} dias ({duration_contingency_percent:.1f}%)",
                     delta=f"{duration_contingency_percent:.1f}%")
        
        # Visualização em histogramas
        tab1, tab2 = st.tabs(["📊 Histogramas", "📈 Curvas S"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                # Histograma para custo
                fig_cost = px.histogram(
                    results_df, x="Custo_Total_Simulado", 
                    nbins=50, 
                    title="Distribuição do Custo Total",
                    labels={"Custo_Total_Simulado": "Custo Total (R$)"},
                    color_discrete_sequence=["lightblue"]
                )
                
                # Adicionar linhas verticais para valores de referência
                fig_cost.add_vline(x=base_cost, line_width=2, line_dash="dash", line_color="green",
                                  annotation_text="Base", annotation_position="top right")
                fig_cost.add_vline(x=cost_mean, line_width=2, line_color="blue",
                                  annotation_text="Média", annotation_position="top right")
                fig_cost.add_vline(x=cost_percentile, line_width=2, line_color="red",
                                  annotation_text=f"P{int(confidence_level*100)}", annotation_position="top right")
                
                fig_cost.update_layout(showlegend=False)
                st.plotly_chart(fig_cost, use_container_width=True)
            
            with col2:
                # Histograma para prazo
                fig_duration = px.histogram(
                    results_df, x="Prazo_Total_Simulado", 
                    nbins=50, 
                    title="Distribuição do Prazo Total",
                    labels={"Prazo_Total_Simulado": "Prazo Total (dias)"},
                    color_discrete_sequence=["lightgreen"]
                )
                
                # Adicionar linhas verticais para valores de referência
                fig_duration.add_vline(x=base_duration, line_width=2, line_dash="dash", line_color="green",
                                     annotation_text="Base", annotation_position="top right")
                fig_duration.add_vline(x=duration_mean, line_width=2, line_color="blue",
                                     annotation_text="Média", annotation_position="top right")
                fig_duration.add_vline(x=duration_percentile, line_width=2, line_color="red",
                                     annotation_text=f"P{int(confidence_level*100)}", annotation_position="top right")
                
                fig_duration.update_layout(showlegend=False)
                st.plotly_chart(fig_duration, use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                # Curva S para custo (CDF - Função de Distribuição Cumulativa)
                sorted_costs = np.sort(results_df["Custo_Total_Simulado"])
                p = 1. * np.arange(len(sorted_costs)) / (len(sorted_costs) - 1)
                
                fig_s_cost = go.Figure()
                fig_s_cost.add_trace(go.Scatter(
                    x=sorted_costs, y=p*100,
                    mode='lines',
                    name='CDF',
                    line=dict(color='blue')
                ))
                
                # Adicionar linhas de referência
                fig_s_cost.add_vline(x=base_cost, line_width=2, line_dash="dash", line_color="green",
                                   annotation_text="Base", annotation_position="top right")
                fig_s_cost.add_vline(x=cost_percentile, line_width=2, line_color="red",
                                   annotation_text=f"P{int(confidence_level*100)}", annotation_position="top right")
                
                fig_s_cost.update_layout(
                    title="Curva S - Probabilidade Acumulada do Custo",
                    xaxis_title="Custo Total (R$)",
                    yaxis_title="Probabilidade Acumulada (%)",
                    showlegend=False
                )
                st.plotly_chart(fig_s_cost, use_container_width=True)
            
            with col2:
                # Curva S para prazo (CDF - Função de Distribuição Cumulativa)
                sorted_durations = np.sort(results_df["Prazo_Total_Simulado"])
                p = 1. * np.arange(len(sorted_durations)) / (len(sorted_durations) - 1)
                
                fig_s_duration = go.Figure()
                fig_s_duration.add_trace(go.Scatter(
                    x=sorted_durations, y=p*100,
                    mode='lines',
                    name='CDF',
                    line=dict(color='green')
                ))
                
                # Adicionar linhas de referência
                fig_s_duration.add_vline(x=base_duration, line_width=2, line_dash="dash", line_color="green",
                                      annotation_text="Base", annotation_position="top right")
                fig_s_duration.add_vline(x=duration_percentile, line_width=2, line_color="red",
                                      annotation_text=f"P{int(confidence_level*100)}", annotation_position="top right")
                
                fig_s_duration.update_layout(
                    title="Curva S - Probabilidade Acumulada do Prazo",
                    xaxis_title="Prazo Total (dias)",
                    yaxis_title="Probabilidade Acumulada (%)",
                    showlegend=False
                )
                st.plotly_chart(fig_s_duration, use_container_width=True)
        
        # Análise de Sensibilidade (simplificada, pode ser expandida)
        st.subheader("Análise de Sensibilidade")
        st.info("""
        A análise de sensibilidade mostra quais riscos têm maior impacto potencial no resultado do projeto.
        Isso ajuda a priorizar recursos para mitigação e monitoramento.
        
        Para uma análise mais completa, utilize módulos avançados como gráficos de tornado ou análise de correlação.
        """)
        
        # Lista dos top riscos por VME
        top_risks_by_vme = edited_vme_df.sort_values(by="VME_Custo", ascending=False).head(5)
        
        if not top_risks_by_vme.empty:
            st.write("#### Top 5 Riscos por VME")
            
            # Criar gráfico de barras simples
            fig_vme = px.bar(
                top_risks_by_vme,
                x="VME_Custo",
                y="ID_Risco",
                orientation="h",
                title="Riscos com Maior Valor Monetário Esperado",
                labels={"VME_Custo": "VME (R$)", "ID_Risco": "ID do Risco"},
                hover_data=["Descricao_Risco", "Tipo_Risco", "Probabilidade_Num"]
            )
            
            # Cores diferentes para ameaças e oportunidades
            fig_vme.update_traces(
                marker_color=top_risks_by_vme["Tipo_Risco"].map({"Ameaça": "red", "Oportunidade": "green"})
            )
            
            st.plotly_chart(fig_vme, use_container_width=True)
            
            # Tabela com detalhes
            st.write("Detalhes dos riscos mais impactantes:")
            st.dataframe(
                top_risks_by_vme[["ID_Risco", "Descricao_Risco", "Tipo_Risco", 
                                 "Probabilidade_Num", "VME_Custo"]],
                hide_index=True,
                use_container_width=True
            )
    
    # Botão para salvar análise
    st.subheader("Salvar Análise Quantitativa")
    if st.button("💾 Salvar Análise", use_container_width=True):
        # Verificar se houve alterações no VME
        if "vme_editor" in st.session_state:
            # Atualizar o DataFrame principal
            updated_df = st.session_state[STATE_RISKS_DF].copy()
            
            # Para cada linha no editor de VME, atualizar o DataFrame principal
            for idx, row in edited_vme_df.iterrows():
                risk_id = row["ID_Risco"]
                mask = updated_df["ID_Risco"] == risk_id
                if any(mask):
                    # Atualizar colunas relevantes
                    cols_to_update = ["Probabilidade_Num", "Efeito_Custo_Min", 
                                     "Efeito_Custo_Max", "VME_Custo"]
                    for col in cols_to_update:
                        if col in row.index:
                            updated_df.loc[mask, col] = row[col]
            
            # Salvar de volta ao session_state
            st.session_state[STATE_RISKS_DF] = updated_df
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Analise_Quantitativa",
                action="Salvar Analise Quantitativa",
                details=f"Atualizados {len(edited_vme_df)} riscos com VME"
            )
            
            st.success("✅ Análise quantitativa salva com sucesso!")
    
    # Exportar resultados
    if STATE_SIMULATION_RESULTS_DF in st.session_state and not st.session_state[STATE_SIMULATION_RESULTS_DF].empty:
        if st.button("📥 Exportar Resultados da Simulação", help="Baixe os resultados da simulação em CSV"):
            csv = st.session_state[STATE_SIMULATION_RESULTS_DF].to_csv(index=False)
            
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"simulacao_monte_carlo_{st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto', 'projeto')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_sim_csv"
            )
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Analise_Quantitativa",
                action="Exportar Simulacao CSV"
            )

# Rodapé com instruções
st.divider()
st.caption("""
**Próximos passos:** Com base nas análises quantitativas, determine as reservas de contingência 
apropriadas e avance para o "Planejamento de Respostas aos Riscos" para definir estratégias 
específicas para os riscos mais significativos.
""") 