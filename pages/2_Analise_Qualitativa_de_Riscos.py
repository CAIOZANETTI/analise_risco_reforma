import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# Importar configurações
from config import (STATE_RISKS_DF, STATE_USER_DATA, STATE_PROJECT_DATA, 
                   STATE_USER_CONFIG_COMPLETED, PROBABILIDADE_OPTIONS, 
                   IMPACTO_OPTIONS)
from utils.gspread_logger import record_log

# Verificar se usuário já completou configuração
if not st.session_state.get(STATE_USER_CONFIG_COMPLETED, False):
    st.warning("⚠️ Por favor, complete as configurações de usuário e projeto primeiro!")
    st.page_link("0_Configuracao_Usuario_e_Projeto.py", label="Ir para Configuração")
    st.stop()

# Verificar se existem riscos cadastrados
if STATE_RISKS_DF not in st.session_state or st.session_state[STATE_RISKS_DF].empty:
    st.warning("⚠️ Nenhum risco foi cadastrado ainda. Por favor, identifique e cadastre riscos primeiro.")
    st.page_link("1_Identificacao_e_Cadastro_de_Riscos.py", label="Ir para Identificação de Riscos")
    st.stop()

# Título e introdução
st.title("📊 Análise Qualitativa de Riscos")

st.markdown("""
Após identificar os riscos, o próximo passo é avaliá-los qualitativamente para estabelecer prioridades.
Nesta etapa, você atribuirá valores subjetivos para a probabilidade de ocorrência e para os impactos 
em diferentes aspectos do projeto (custo, prazo, qualidade).

Esta análise ajuda a determinar quais riscos merecem maior atenção e recursos.
""")

# Funções auxiliares
def calcular_score_risco(probabilidade, impacto_custo, impacto_prazo, impacto_qualidade, tipo_risco):
    """
    Calcula o score de risco baseado na probabilidade e nos diferentes impactos.
    Para ameaças: score positivo (quanto maior, pior)
    Para oportunidades: score negativo (quanto menor/mais negativo, melhor/maior oportunidade)
    """
    # Converter valores qualitativos para numéricos
    prob_dict = {"Muito Baixa": 0.1, "Baixa": 0.3, "Média": 0.5, "Alta": 0.7, "Muito Alta": 0.9}
    impacto_dict = {"Insignificante": 0.1, "Baixo": 0.3, "Médio": 0.5, "Alto": 0.7, "Crítico": 0.9}
    
    # Obter valores numéricos
    prob_num = prob_dict.get(probabilidade, 0)
    ic_num = impacto_dict.get(impacto_custo, 0)
    ip_num = impacto_dict.get(impacto_prazo, 0)
    iq_num = impacto_dict.get(impacto_qualidade, 0)
    
    # Calcular média ponderada dos impactos (adaptar pesos conforme necessário)
    impacto_medio = (ic_num * 0.4) + (ip_num * 0.4) + (iq_num * 0.2)
    
    # Calcular score base
    score = prob_num * impacto_medio * 10  # Multiplicar por 10 para ter escala 0-10
    
    # Ajustar pelo tipo de risco (ameaça ou oportunidade)
    if tipo_risco == "Oportunidade":
        score = -score  # Negativo para oportunidades
        
    return round(score, 2), prob_num

def criar_matriz_probabilidade_impacto(df):
    """
    Cria uma matriz de probabilidade x impacto usando Plotly
    """
    # Mapeamento para posições na matriz
    prob_map = {"Muito Baixa": 0, "Baixa": 1, "Média": 2, "Alta": 3, "Muito Alta": 4}
    impacto_map = {"Insignificante": 0, "Baixo": 1, "Médio": 2, "Alto": 3, "Crítico": 4}
    
    # Cores para diferentes níveis de risco
    cores_ameacas = [[0, 'green'], [0.33, 'yellow'], [0.66, 'orange'], [1, 'red']]
    cores_oportunidades = [[0, 'lightblue'], [0.33, 'royalblue'], [0.66, 'blue'], [1, 'darkblue']]
    
    # Criar figuras separadas para ameaças e oportunidades
    fig_ameacas = go.Figure()
    fig_oportunidades = go.Figure()
    
    # Dividir riscos por tipo
    ameacas = df[df['Tipo_Risco'] == 'Ameaça']
    oportunidades = df[df['Tipo_Risco'] == 'Oportunidade']
    
    # Adicionar pontos para ameaças
    for _, risco in ameacas.iterrows():
        prob_pos = prob_map.get(risco['Probabilidade_Qualitativa'], 0)
        # Usar o impacto de custo como default, mas poderia ser uma média
        impacto_pos = impacto_map.get(risco['Impacto_Custo_Qualitativo'], 0)
        
        fig_ameacas.add_trace(go.Scatter(
            x=[impacto_pos], 
            y=[prob_pos],
            mode='markers+text',
            marker=dict(size=30, color='rgba(255,0,0,0.7)'),
            text=[risco['ID_Risco']],
            textposition="middle center",
            hovertext=f"{risco['ID_Risco']}: {risco['Descricao_Risco']} (Score: {risco['Score_Risco']})",
            hoverinfo='text'
        ))
    
    # Adicionar pontos para oportunidades
    for _, risco in oportunidades.iterrows():
        prob_pos = prob_map.get(risco['Probabilidade_Qualitativa'], 0)
        impacto_pos = impacto_map.get(risco['Impacto_Custo_Qualitativo'], 0)
        
        fig_oportunidades.add_trace(go.Scatter(
            x=[impacto_pos], 
            y=[prob_pos],
            mode='markers+text',
            marker=dict(size=30, color='rgba(0,0,255,0.7)'),
            text=[risco['ID_Risco']],
            textposition="middle center",
            hovertext=f"{risco['ID_Risco']}: {risco['Descricao_Risco']} (Score: {risco['Score_Risco']})",
            hoverinfo='text'
        ))
    
    # Configurar layout para ameaças
    fig_ameacas.update_layout(
        title="Matriz de Probabilidade x Impacto - Ameaças",
        xaxis=dict(
            title="Impacto",
            tickvals=[0, 1, 2, 3, 4],
            ticktext=IMPACTO_OPTIONS,
            range=[-0.5, 4.5]
        ),
        yaxis=dict(
            title="Probabilidade",
            tickvals=[0, 1, 2, 3, 4],
            ticktext=PROBABILIDADE_OPTIONS,
            range=[-0.5, 4.5]
        ),
        width=500,
        height=500,
        plot_bgcolor='rgba(240, 240, 240, 0.5)'
    )
    
    # Adicionar áreas coloridas para níveis de risco (ameaças)
    for i in range(5):
        for j in range(5):
            risk_level = (i * j) / 16  # Normalizado para 0-1
            fig_ameacas.add_shape(
                type="rect",
                x0=j-0.5, y0=i-0.5, x1=j+0.5, y1=i+0.5,
                line=dict(width=1, color="gray"),
                fillcolor=f"rgba({255*risk_level}, {255*(1-risk_level)}, 0, 0.3)"
            )
    
    # Configurar layout para oportunidades
    fig_oportunidades.update_layout(
        title="Matriz de Probabilidade x Impacto - Oportunidades",
        xaxis=dict(
            title="Impacto",
            tickvals=[0, 1, 2, 3, 4],
            ticktext=IMPACTO_OPTIONS,
            range=[-0.5, 4.5]
        ),
        yaxis=dict(
            title="Probabilidade",
            tickvals=[0, 1, 2, 3, 4],
            ticktext=PROBABILIDADE_OPTIONS,
            range=[-0.5, 4.5]
        ),
        width=500,
        height=500,
        plot_bgcolor='rgba(240, 240, 240, 0.5)'
    )
    
    # Adicionar áreas coloridas para níveis de risco (oportunidades)
    for i in range(5):
        for j in range(5):
            risk_level = (i * j) / 16  # Normalizado para 0-1
            fig_oportunidades.add_shape(
                type="rect",
                x0=j-0.5, y0=i-0.5, x1=j+0.5, y1=i+0.5,
                line=dict(width=1, color="gray"),
                fillcolor=f"rgba(0, 0, {255*risk_level}, 0.3)"
            )
    
    return fig_ameacas, fig_oportunidades

# Layout em duas abas
tab_analise, tab_resultados = st.tabs(["🔍 Realizar Análise", "📊 Resultados e Matriz"])

# Aba 1: Realizar Análise
with tab_analise:
    st.subheader("Avaliação Qualitativa por Risco")
    
    # Listar todos os riscos para análise
    df_riscos = st.session_state[STATE_RISKS_DF].copy()
    
    # Selecionar um risco para análise
    id_riscos = df_riscos['ID_Risco'].tolist()
    
    if id_riscos:
        risco_selecionado = st.selectbox(
            "Selecione um risco para analisar:",
            id_riscos,
            format_func=lambda x: f"{x}: {df_riscos[df_riscos['ID_Risco']==x]['Descricao_Risco'].iloc[0][:50]}..."
        )
        
        # Obter detalhes do risco selecionado
        risco_atual = df_riscos[df_riscos['ID_Risco'] == risco_selecionado].iloc[0]
        tipo_risco = risco_atual['Tipo_Risco']
        
        # Mostrar detalhes do risco
        st.markdown(f"""
        **Detalhes do Risco:**
        * **ID:** {risco_atual['ID_Risco']}
        * **Descrição:** {risco_atual['Descricao_Risco']}
        * **Tipo:** {risco_atual['Tipo_Risco']}
        * **Categoria:** {risco_atual['Categoria_Risco']}
        """)
        
        # Formulário para avaliação qualitativa
        with st.form(key="analise_qualitativa_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                probabilidade = st.selectbox(
                    "Probabilidade de Ocorrência",
                    options=PROBABILIDADE_OPTIONS,
                    index=PROBABILIDADE_OPTIONS.index(risco_atual['Probabilidade_Qualitativa']) if risco_atual['Probabilidade_Qualitativa'] in PROBABILIDADE_OPTIONS else 0
                )
                
                impacto_custo = st.selectbox(
                    "Impacto em Custo",
                    options=IMPACTO_OPTIONS,
                    index=IMPACTO_OPTIONS.index(risco_atual['Impacto_Custo_Qualitativo']) if risco_atual['Impacto_Custo_Qualitativo'] in IMPACTO_OPTIONS else 0
                )
                
                impacto_prazo = st.selectbox(
                    "Impacto em Prazo",
                    options=IMPACTO_OPTIONS,
                    index=IMPACTO_OPTIONS.index(risco_atual['Impacto_Prazo_Qualitativo']) if risco_atual['Impacto_Prazo_Qualitativo'] in IMPACTO_OPTIONS else 0
                )
            
            with col2:
                impacto_qualidade = st.selectbox(
                    "Impacto em Qualidade",
                    options=IMPACTO_OPTIONS,
                    index=IMPACTO_OPTIONS.index(risco_atual['Impacto_Qualidade_Qualitativo']) if risco_atual['Impacto_Qualidade_Qualitativo'] in IMPACTO_OPTIONS else 0
                )
                
                urgencia = st.selectbox(
                    "Urgência de Resposta",
                    options=["Baixa", "Média", "Alta"],
                    index=["Baixa", "Média", "Alta"].index(risco_atual['Urgencia_Risco']) if risco_atual['Urgencia_Risco'] in ["Baixa", "Média", "Alta"] else 0
                )
            
            # Calcular e exibir score de risco
            score, prob_num = calcular_score_risco(probabilidade, impacto_custo, impacto_prazo, impacto_qualidade, tipo_risco)
            
            if tipo_risco == "Ameaça":
                st.info(f"Score de Risco calculado: {score} (quanto maior, maior a severidade do risco)")
            else:
                st.info(f"Score de Oportunidade calculado: {score} (quanto mais negativo, maior o potencial da oportunidade)")
            
            # Botão para salvar análise
            submitted = st.form_submit_button("Salvar Análise")
            
            if submitted:
                # Atualizar o DataFrame de riscos
                idx = df_riscos[df_riscos['ID_Risco'] == risco_selecionado].index[0]
                
                # Atualizar valores
                df_riscos.loc[idx, 'Probabilidade_Qualitativa'] = probabilidade
                df_riscos.loc[idx, 'Impacto_Custo_Qualitativo'] = impacto_custo
                df_riscos.loc[idx, 'Impacto_Prazo_Qualitativo'] = impacto_prazo
                df_riscos.loc[idx, 'Impacto_Qualidade_Qualitativo'] = impacto_qualidade
                df_riscos.loc[idx, 'Urgencia_Risco'] = urgencia
                df_riscos.loc[idx, 'Score_Risco'] = score
                df_riscos.loc[idx, 'Probabilidade_Num'] = prob_num
                
                # Atualizar o session_state
                st.session_state[STATE_RISKS_DF] = df_riscos
                
                # Log da ação
                record_log(
                    user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"),
                    project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"),
                    page="Analise_Qualitativa",
                    action="Salvar Analise Individual",
                    details=f"ID: {risco_selecionado}, Score: {score}"
                )
                
                st.success(f"✅ Análise qualitativa do risco {risco_selecionado} salva com sucesso!")
        
        # Espaço entre o formulário e a tabela
        st.divider()
    
    # Visualização de todos os riscos e análise em massa
    st.subheader("Visão Geral e Análise em Massa")
    
    # Criar uma cópia do DataFrame para edição
    df_analise = st.session_state[STATE_RISKS_DF][['ID_Risco', 'Descricao_Risco', 'Tipo_Risco', 
                                                 'Probabilidade_Qualitativa', 'Impacto_Custo_Qualitativo',
                                                 'Impacto_Prazo_Qualitativo', 'Impacto_Qualidade_Qualitativo',
                                                 'Urgencia_Risco', 'Score_Risco']].copy()
    
    # Configuração das colunas para o editor
    column_config = {
        'ID_Risco': st.column_config.TextColumn("ID", disabled=True),
        'Descricao_Risco': st.column_config.TextColumn("Descrição", disabled=True),
        'Tipo_Risco': st.column_config.TextColumn("Tipo", disabled=True),
        'Probabilidade_Qualitativa': st.column_config.SelectboxColumn("Probabilidade", options=PROBABILIDADE_OPTIONS),
        'Impacto_Custo_Qualitativo': st.column_config.SelectboxColumn("Impacto Custo", options=IMPACTO_OPTIONS),
        'Impacto_Prazo_Qualitativo': st.column_config.SelectboxColumn("Impacto Prazo", options=IMPACTO_OPTIONS),
        'Impacto_Qualidade_Qualitativo': st.column_config.SelectboxColumn("Impacto Qualidade", options=IMPACTO_OPTIONS),
        'Urgencia_Risco': st.column_config.SelectboxColumn("Urgência", options=["Baixa", "Média", "Alta"]),
        'Score_Risco': st.column_config.NumberColumn("Score", format="%.2f", disabled=True)
    }
    
    # Editor de tabela
    df_edited = st.data_editor(
        df_analise,
        column_config=column_config,
        hide_index=True,
        key="mass_analysis_editor",
        use_container_width=True
    )
    
    if st.button("Recalcular e Salvar Todos os Scores"):
        # Verificar se todos os campos necessários estão preenchidos
        required_cols = ['Probabilidade_Qualitativa', 'Impacto_Custo_Qualitativo', 
                        'Impacto_Prazo_Qualitativo', 'Impacto_Qualidade_Qualitativo']
        
        missing_values = df_edited[required_cols].isnull().any().any()
        
        if missing_values:
            st.error("Por favor, preencha todos os campos de probabilidade e impacto para todos os riscos!")
        else:
            # Atualizar todos os scores
            updated_df = df_riscos.copy()
            
            for idx, row in df_edited.iterrows():
                id_risco = row['ID_Risco']
                tipo_risco = row['Tipo_Risco']
                
                # Calcular novo score
                score, prob_num = calcular_score_risco(
                    row['Probabilidade_Qualitativa'],
                    row['Impacto_Custo_Qualitativo'],
                    row['Impacto_Prazo_Qualitativo'],
                    row['Impacto_Qualidade_Qualitativo'],
                    tipo_risco
                )
                
                # Atualizar no DataFrame
                idx_original = updated_df[updated_df['ID_Risco'] == id_risco].index
                if len(idx_original) > 0:
                    updated_df.loc[idx_original[0], 'Probabilidade_Qualitativa'] = row['Probabilidade_Qualitativa']
                    updated_df.loc[idx_original[0], 'Impacto_Custo_Qualitativo'] = row['Impacto_Custo_Qualitativo']
                    updated_df.loc[idx_original[0], 'Impacto_Prazo_Qualitativo'] = row['Impacto_Prazo_Qualitativo']
                    updated_df.loc[idx_original[0], 'Impacto_Qualidade_Qualitativo'] = row['Impacto_Qualidade_Qualitativo']
                    updated_df.loc[idx_original[0], 'Urgencia_Risco'] = row['Urgencia_Risco']
                    updated_df.loc[idx_original[0], 'Score_Risco'] = score
                    updated_df.loc[idx_original[0], 'Probabilidade_Num'] = prob_num
            
            # Atualizar o session_state
            st.session_state[STATE_RISKS_DF] = updated_df
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"),
                project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"),
                page="Analise_Qualitativa",
                action="Salvar Analise Qualitativa",
                details=f"Riscos analisados: {len(df_edited)}"
            )
            
            st.success("✅ Análises qualitativas e scores de todos os riscos atualizados com sucesso!")

# Aba 2: Resultados e Matriz
with tab_resultados:
    st.subheader("Resultados da Análise Qualitativa")
    
    # Verificar se existem análises realizadas
    df_resultados = st.session_state[STATE_RISKS_DF].copy()
    
    # Filtrar riscos que já foram analisados (com Score_Risco preenchido)
    df_analisados = df_resultados[df_resultados['Score_Risco'] != 0]
    
    if df_analisados.empty:
        st.info("Nenhum risco foi analisado qualitativamente ainda. Utilize a aba anterior para realizar análises.")
    else:
        # Preparar dados para visualização
        st.markdown("### Ranking de Riscos por Score")
        
        # Separar ameaças e oportunidades
        ameacas = df_analisados[df_analisados['Tipo_Risco'] == 'Ameaça'].sort_values(by='Score_Risco', ascending=False)
        oportunidades = df_analisados[df_analisados['Tipo_Risco'] == 'Oportunidade'].sort_values(by='Score_Risco', ascending=True)
        
        # Criar tabs para ameaças e oportunidades
        tab_ameacas, tab_oportunidades, tab_matriz = st.tabs(["Ameaças", "Oportunidades", "Matriz P x I"])
        
        with tab_ameacas:
            if ameacas.empty:
                st.info("Nenhuma ameaça analisada até o momento.")
            else:
                st.write("Top Ameaças (Score mais alto = maior severidade):")
                
                # Configurar colunas para visualização
                cols_display = ['ID_Risco', 'Descricao_Risco', 'Score_Risco', 'Probabilidade_Qualitativa', 
                              'Impacto_Custo_Qualitativo', 'Urgencia_Risco']
                
                st.dataframe(
                    ameacas[cols_display],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        'ID_Risco': 'ID',
                        'Descricao_Risco': 'Descrição',
                        'Score_Risco': st.column_config.NumberColumn('Score', format="%.2f"),
                        'Probabilidade_Qualitativa': 'Probabilidade',
                        'Impacto_Custo_Qualitativo': 'Impacto (Custo)',
                        'Urgencia_Risco': 'Urgência'
                    }
                )
        
        with tab_oportunidades:
            if oportunidades.empty:
                st.info("Nenhuma oportunidade analisada até o momento.")
            else:
                st.write("Top Oportunidades (Score mais negativo = maior potencial):")
                
                cols_display = ['ID_Risco', 'Descricao_Risco', 'Score_Risco', 'Probabilidade_Qualitativa', 
                              'Impacto_Custo_Qualitativo', 'Urgencia_Risco']
                
                st.dataframe(
                    oportunidades[cols_display],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        'ID_Risco': 'ID',
                        'Descricao_Risco': 'Descrição',
                        'Score_Risco': st.column_config.NumberColumn('Score', format="%.2f"),
                        'Probabilidade_Qualitativa': 'Probabilidade',
                        'Impacto_Custo_Qualitativo': 'Impacto (Custo)',
                        'Urgencia_Risco': 'Urgência'
                    }
                )
        
        with tab_matriz:
            st.write("Matrizes de Probabilidade x Impacto")
            st.markdown("""
            As matrizes abaixo mostram a distribuição dos riscos conforme sua probabilidade e impacto.
            - Quanto mais próximo do canto superior direito, maior o risco/oportunidade
            - O código de cores indica a severidade/potencial
            """)
            
            # Criar matrizes
            fig_ameacas, fig_oportunidades = criar_matriz_probabilidade_impacto(df_analisados)
            
            # Exibir matrizes lado a lado
            matriz_col1, matriz_col2 = st.columns(2)
            
            with matriz_col1:
                st.plotly_chart(fig_ameacas, use_container_width=True)
            
            with matriz_col2:
                st.plotly_chart(fig_oportunidades, use_container_width=True)

# Explicação sobre análise qualitativa
with st.expander("💡 Sobre a Análise Qualitativa de Riscos"):
    st.markdown("""
    ### Conceitos Fundamentais
    
    A análise qualitativa avalia os riscos com base em escalas predefinidas em vez de valores numéricos precisos, 
    permitindo uma rápida priorização.
    
    **Componentes da Análise:**
    
    1. **Probabilidade**: A chance do risco ocorrer, de "Muito Baixa" a "Muito Alta".
    
    2. **Impacto**: A severidade do efeito, caso o risco ocorra, em diferentes aspectos:
       - **Impacto em Custo**: Efeito financeiro
       - **Impacto em Prazo**: Efeito no cronograma
       - **Impacto em Qualidade**: Efeito na qualidade entregue
    
    3. **Urgência**: Quão rapidamente o risco requer resposta. Um risco pode ter alto impacto,
       mas só se manifestar em uma fase distante do projeto.
    
    4. **Score de Risco**: Valor calculado que combina probabilidade e impacto para facilitar a priorização.
       Para ameaças, quanto maior o valor, mais severo o risco. Para oportunidades, quanto mais negativo, maior o benefício potencial.
    
    **A Matriz Probabilidade x Impacto** é uma ferramenta visual que mostra a distribuição dos riscos
    e ajuda a identificar quais devem receber mais atenção.
    """)

# Rodapé com botões de navegação
st.divider()
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    st.page_link("1_Identificacao_e_Cadastro_de_Riscos.py", label="← Voltar para Identificação", use_container_width=True)

with col3:
    st.page_link("3_Analise_Quantitativa_e_Probabilistica.py", label="Avançar para Análise Quantitativa →", use_container_width=True) 