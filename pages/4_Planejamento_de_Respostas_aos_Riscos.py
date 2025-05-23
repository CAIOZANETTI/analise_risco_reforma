import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Importar configurações
from config import (
    STATE_RISKS_DF, STATE_USER_DATA, STATE_PROJECT_DATA, STATE_USER_CONFIG_COMPLETED,
    THRESHOLD_SCORE_DEFAULT, ESTRATEGIA_RESPOSTA_AMEACA_OPTIONS, 
    ESTRATEGIA_RESPOSTA_OPORTUNIDADE_OPTIONS, STATUS_ACAO_OPTIONS, STATUS_RISCO_OPTIONS
)

# Importar logger para registro de eventos
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
st.title("📝 Planejamento de Respostas aos Riscos")

# Informações sobre a etapa
st.info("""
Esta é a etapa em que as análises se transformam em ações. Para cada risco prioritário, 
defina uma estratégia clara de resposta e detalhe as ações específicas, responsáveis, prazos e custos.
Lembre-se que diferentes tipos de riscos (ameaças vs. oportunidades) demandam diferentes estratégias.
""")

# Carregar riscos existentes
df_risks = st.session_state[STATE_RISKS_DF].copy()

# Garantir que colunas numéricas são do tipo correto
numeric_cols = ['Score_Risco', 'VME_Custo']
for col in numeric_cols:
    if col in df_risks.columns:
        df_risks[col] = pd.to_numeric(df_risks[col], errors='coerce').fillna(0.0)

# Filtrar riscos significativos (com score > 0)
df_significant = df_risks[df_risks["Score_Risco"] > 0].copy()

if df_significant.empty:
    st.warning("""
    ⚠️ Nenhum risco com análise qualitativa encontrado. Por favor, complete a 
    análise qualitativa antes de planejar respostas.
    """)
    st.page_link("2_Analise_Qualitativa_de_Riscos.py", label="Ir para Análise Qualitativa")
else:
    # Mostrar explicação das estratégias de resposta
    with st.expander("Estratégias de Resposta a Riscos", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Estratégias para Ameaças")
            threats_df = pd.DataFrame({
                "Estratégia": ESTRATEGIA_RESPOSTA_AMEACA_OPTIONS,
                "Descrição": [
                    "Eliminar completamente a ameaça ou proteger o projeto de seu impacto",
                    "Reduzir a probabilidade e/ou impacto da ameaça a níveis aceitáveis",
                    "Passar a responsabilidade e impacto para terceiros (seguro, contratos)",
                    "Reconhecer e não agir, monitorar e rever se necessário",
                    "Elevar o problema para níveis superiores da organização"
                ]
            })
            st.table(threats_df)
        
        with col2:
            st.markdown("### Estratégias para Oportunidades")
            opportunities_df = pd.DataFrame({
                "Estratégia": ESTRATEGIA_RESPOSTA_OPORTUNIDADE_OPTIONS,
                "Descrição": [
                    "Garantir que a oportunidade seja capturada, eliminando incerteza",
                    "Aumentar a probabilidade e/ou impacto positivo da oportunidade",
                    "Atribuir parte da oportunidade a terceiros melhor posicionados",
                    "Reconhecer a oportunidade, mas não buscar ativamente"
                ]
            })
            st.table(opportunities_df)
    
    # Ordenar riscos por Score para focar nos mais significativos
    df_significant = df_significant.sort_values(by="Score_Risco", ascending=False)
    
    # Criar abas para visualizar diferentes aspectos
    tab1, tab2 = st.tabs(["🔄 Planejamento de Respostas", "📈 Visualização e Resumo"])
    
    with tab1:
        st.subheader("Definir Respostas aos Riscos")
        
        # Configurar colunas para visualização e edição
        response_cols = [
            "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Score_Risco", 
            "Estrategia_Resposta", "Descricao_Acao_Resposta", 
            "Proprietario_do_Risco", "Prazo_Implementacao_Resposta", 
            "Custo_Estimado_Resposta", "Plano_de_Contingencia", 
            "Riscos_Secundarios_Identificados", "Status_Acao_Resposta"
        ]
        
        # Garantir que todas as colunas existam
        for col in response_cols:
            if col not in df_significant.columns:
                df_significant[col] = ""
        
        # Configuração das colunas para o editor
        column_config = {
            "ID_Risco": st.column_config.TextColumn("ID", width="small", disabled=True),
            "Descricao_Risco": st.column_config.TextColumn("Descrição", width="large", disabled=True),
            "Tipo_Risco": st.column_config.TextColumn("Tipo", width="small", disabled=True),
            "Score_Risco": st.column_config.NumberColumn("Score", format="%.1f", width="small", disabled=True),
            "Estrategia_Resposta": st.column_config.SelectboxColumn(
                "Estratégia", width="medium",
                options=list(set(ESTRATEGIA_RESPOSTA_AMEACA_OPTIONS + ESTRATEGIA_RESPOSTA_OPORTUNIDADE_OPTIONS)),
                help="Estratégia de resposta. Valide se é apropriada para o Tipo de Risco ao salvar."),
            "Descricao_Acao_Resposta": st.column_config.TextAreaColumn(
                "Descrição da Ação", width="large",
                help="Detalhe as ações específicas para implementar a estratégia"),
            "Proprietario_do_Risco": st.column_config.TextColumn(
                "Responsável", width="medium",
                help="Pessoa responsável por implementar e monitorar a resposta"),
            "Prazo_Implementacao_Resposta": st.column_config.DateColumn(
                "Prazo", width="medium", format="DD/MM/YYYY",
                help="Data limite para implementação da resposta"),
            "Custo_Estimado_Resposta": st.column_config.NumberColumn(
                "Custo Estimado (R$)", format="R$ %.2f", min_value=0.0,
                help="Custo estimado para implementar a resposta"),
            "Plano_de_Contingencia": st.column_config.TextAreaColumn(
                "Plano de Contingência", width="large",
                help="O que fazer se o risco ocorrer mesmo com a resposta planejada"),
            "Riscos_Secundarios_Identificados": st.column_config.TextAreaColumn(
                "Riscos Secundários", width="large",
                help="Novos riscos que podem surgir como resultado da resposta planejada"),
            "Status_Acao_Resposta": st.column_config.SelectboxColumn(
                "Status da Ação", width="medium", options=STATUS_ACAO_OPTIONS,
                help="Status atual da implementação da resposta")
        }
        
        # Mostrar o editor de dados
        edited_responses_df = st.data_editor(
            df_significant[response_cols],
            column_config=column_config,
            use_container_width=True,
            key="responses_editor",
            hide_index=True,
            num_rows="fixed"  # Evitar adição de novas linhas
        )
        
        # Botão para salvar plano de respostas
        if st.button("💾 Salvar Plano de Respostas", use_container_width=True):
            # Atualizar o DataFrame principal
            updated_df = st.session_state[STATE_RISKS_DF].copy()
            
            # Para cada linha no editor de respostas, atualizar o DataFrame principal
            for idx, row in edited_responses_df.iterrows():
                risk_id = row["ID_Risco"]
                mask = updated_df["ID_Risco"] == risk_id
                if any(mask):
                    # Atualizar colunas relevantes
                    for col in response_cols:
                        if col != "ID_Risco" and col != "Descricao_Risco" and col != "Tipo_Risco" and col != "Score_Risco":
                            updated_df.loc[mask, col] = row[col]
            
            # Salvar de volta ao session_state
            st.session_state[STATE_RISKS_DF] = updated_df
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Planejamento_Respostas",
                action="Salvar Plano de Respostas",
                details=f"Atualizadas respostas para {len(edited_responses_df)} riscos"
            )
            
            st.success("✅ Plano de respostas salvo com sucesso!")
    
    with tab2:
        st.subheader("Resumo do Plano de Respostas")
        
        # Se houver dados de resposta, exibir visualizações e resumos
        has_responses = not df_significant[df_significant["Estrategia_Resposta"] != ""].empty
        
        if has_responses:
            col1, col2 = st.columns(2)
            
            with col1:
                # Contagem de estratégias por tipo de risco
                st.write("### Estratégias por Tipo de Risco")
                
                # Dados para ameaças
                threats = df_significant[df_significant["Tipo_Risco"] == "Ameaça"]
                threat_strategies = threats["Estrategia_Resposta"].value_counts().reset_index()
                threat_strategies.columns = ["Estratégia", "Contagem"]
                
                # Dados para oportunidades
                opportunities = df_significant[df_significant["Tipo_Risco"] == "Oportunidade"]
                opp_strategies = opportunities["Estrategia_Resposta"].value_counts().reset_index()
                opp_strategies.columns = ["Estratégia", "Contagem"]
                
                # Criar gráficos de barras sobrepostos
                fig_strategies = go.Figure()
                
                if not threat_strategies.empty:
                    fig_strategies.add_trace(go.Bar(
                        x=threat_strategies["Estratégia"],
                        y=threat_strategies["Contagem"],
                        name="Ameaças",
                        marker_color="red",
                    ))
                
                if not opp_strategies.empty:
                    fig_strategies.add_trace(go.Bar(
                        x=opp_strategies["Estratégia"],
                        y=opp_strategies["Contagem"],
                        name="Oportunidades",
                        marker_color="green",
                    ))
                
                fig_strategies.update_layout(
                    title="Estratégias de Resposta Utilizadas",
                    xaxis_title="Estratégia",
                    yaxis_title="Número de Riscos",
                    barmode="group",
                    height=400
                )
                
                st.plotly_chart(fig_strategies, use_container_width=True)
            
            with col2:
                # Status das ações de resposta
                st.write("### Status das Ações de Resposta")
                
                # Contagens de status
                status_counts = df_significant["Status_Acao_Resposta"].value_counts().reset_index()
                status_counts.columns = ["Status", "Contagem"]
                
                # Definir cores para os diferentes status
                status_colors = {
                    "Não Iniciada": "lightgray",
                    "Em Andamento": "orange",
                    "Concluída": "green",
                    "Cancelada": "red",
                    "Bloqueada": "purple"
                }
                
                # Criar gráfico de pizza
                fig_status = px.pie(
                    status_counts,
                    values="Contagem",
                    names="Status",
                    title="Status das Ações de Resposta",
                    color="Status",
                    color_discrete_map=status_colors,
                    hole=0.4
                )
                
                fig_status.update_traces(textposition="inside", textinfo="percent+label")
                fig_status.update_layout(height=400)
                
                st.plotly_chart(fig_status, use_container_width=True)
            
            # Resumo de custos de respostas
            st.write("### Resumo Financeiro das Respostas")
            
            # Converter custos para número
            df_significant["Custo_Estimado_Resposta"] = pd.to_numeric(df_significant["Custo_Estimado_Resposta"], errors="coerce").fillna(0)
            
            # Calcular totais
            total_response_cost = df_significant["Custo_Estimado_Resposta"].sum()
            
            # Mostrar métricas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Custo Total das Respostas",
                    f"R$ {total_response_cost:,.2f}"
                )
            
            with col2:
                if "VME_Custo" in df_significant.columns:
                    total_vme = df_significant["VME_Custo"].sum()
                    st.metric(
                        "VME Total dos Riscos",
                        f"R$ {total_vme:,.2f}"
                    )
                else:
                    st.metric(
                        "VME Total dos Riscos",
                        "N/A - Execute Análise Quantitativa"
                    )
            
            with col3:
                project_cost = st.session_state[STATE_PROJECT_DATA].get("Valor_Total_Estimado", 0)
                if project_cost > 0:
                    response_cost_percent = (total_response_cost / project_cost) * 100
                    st.metric(
                        "% do Orçamento do Projeto",
                        f"{response_cost_percent:.2f}%"
                    )
                else:
                    st.metric(
                        "% do Orçamento do Projeto",
                        "N/A"
                    )
            
            # Tabela de riscos sem resposta definida
            risks_without_response = df_significant[
                (df_significant["Estrategia_Resposta"].isna()) | 
                (df_significant["Estrategia_Resposta"] == "")
            ]
            
            if not risks_without_response.empty:
                st.warning(f"⚠️ {len(risks_without_response)} riscos prioritários ainda não têm uma estratégia de resposta definida.")
                
                with st.expander("Ver riscos sem resposta", expanded=False):
                    st.dataframe(
                        risks_without_response[["ID_Risco", "Descricao_Risco", "Tipo_Risco", "Score_Risco"]],
                        hide_index=True,
                        use_container_width=True
                    )
        else:
            st.warning("""
            Nenhuma estratégia de resposta definida ainda. 
            Use a aba "Planejamento de Respostas" para definir como você vai lidar com cada risco.
            """)
    
        # Exportar plano de respostas para CSV
        if st.button("📥 Exportar Plano de Respostas para CSV", help="Baixe o plano em formato CSV"):
            csv = edited_responses_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"plano_respostas_{st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto', 'projeto')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_responses_csv"
            )
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Planejamento_Respostas",
                action="Exportar Plano CSV",
                details=f"Exportadas {len(edited_responses_df)} respostas"
            )

# Rodapé com instruções
st.divider()
st.caption("""
**Próximos passos:** Após definir as estratégias e ações de resposta para os riscos prioritários,
avance para "Monitoramento e Relatórios de Riscos" para acompanhar a implementação e eficácia das respostas.
""") 