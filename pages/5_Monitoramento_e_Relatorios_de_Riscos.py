import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import base64

# Importar configurações
from config import (
    STATE_RISKS_DF, STATE_USER_DATA, STATE_PROJECT_DATA, STATE_USER_CONFIG_COMPLETED,
    STATUS_RISCO_OPTIONS, STATUS_ACAO_OPTIONS
)

# Importar módulos de utilidades
from utils.html_generator import dataframe_to_html_custom, create_summary_card_html
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
st.title("📊 Monitoramento e Relatórios de Riscos")

# Informações sobre a etapa
st.info("""
O monitoramento contínuo é crucial para o sucesso da gestão de riscos. Nesta etapa, você acompanhará 
o status dos riscos e a implementação das ações de resposta, atualizando o progresso e ajustando 
estratégias conforme necessário. Relatórios periódicos ajudam na comunicação com stakeholders e 
na documentação do histórico do projeto.
""")

# Carregar riscos existentes
df_risks = st.session_state[STATE_RISKS_DF].copy()

# Garantir que colunas numéricas são do tipo correto
numeric_cols = ['Score_Risco', 'VME_Custo', 'Custo_Estimado_Resposta']
for col in numeric_cols:
    if col in df_risks.columns:
        df_risks[col] = pd.to_numeric(df_risks[col], errors='coerce').fillna(0.0)

# Filtrar riscos significativos (com score > 0)
df_significant = df_risks[df_risks["Score_Risco"] > 0].copy()

if df_significant.empty:
    st.warning("""
    ⚠️ Nenhum risco com análise qualitativa encontrado. Por favor, complete a 
    análise qualitativa antes de monitorar os riscos.
    """)
    st.page_link("2_Analise_Qualitativa_de_Riscos.py", label="Ir para Análise Qualitativa")
else:
    # Criar abas para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["🔄 Atualizar Status", "📈 Dashboard de Monitoramento", "📄 Gerar Relatório"])
    
    with tab1:
        st.subheader("Atualizar Status dos Riscos")
        
        # Configurar colunas para monitoramento
        monitoring_cols = [
            "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Score_Risco",
            "Estrategia_Resposta", "Status_Acao_Resposta", "Status_Risco",
            "Observacoes_Monitoramento"
        ]
        
        # Garantir que todas as colunas existam
        for col in monitoring_cols:
            if col not in df_significant.columns:
                df_significant[col] = ""
        
        # Configuração das colunas para o editor
        column_config = {
            "ID_Risco": st.column_config.TextColumn("ID", width="small", disabled=True),
            "Descricao_Risco": st.column_config.TextColumn("Descrição", width="large", disabled=True),
            "Tipo_Risco": st.column_config.TextColumn("Tipo", width="small", disabled=True),
            "Score_Risco": st.column_config.NumberColumn("Score", format="%.1f", width="small", disabled=True),
            "Estrategia_Resposta": st.column_config.TextColumn("Estratégia", width="medium", disabled=True),
            "Status_Acao_Resposta": st.column_config.SelectboxColumn(
                "Status da Ação", width="medium", options=STATUS_ACAO_OPTIONS,
                help="Status atual da ação de resposta"),
            "Status_Risco": st.column_config.SelectboxColumn(
                "Status do Risco", width="medium", options=STATUS_RISCO_OPTIONS,
                help="Status atual do risco no projeto"),
            "Observacoes_Monitoramento": st.column_config.TextAreaColumn(
                "Observações de Monitoramento", width="large",
                help="Notas sobre o monitoramento, gatilhos observados, etc.")
        }
        
        # Mostrar o editor de dados
        edited_monitoring_df = st.data_editor(
            df_significant[monitoring_cols],
            column_config=column_config,
            use_container_width=True,
            key="monitoring_editor",
            hide_index=True,
            num_rows="fixed"  # Evitar adição de novas linhas
        )
        
        # Botão para salvar atualizações de status
        if st.button("💾 Salvar Atualizações de Status", use_container_width=True):
            # Atualizar o DataFrame principal
            updated_df = st.session_state[STATE_RISKS_DF].copy()
            
            # Para cada linha no editor de monitoramento, atualizar o DataFrame principal
            for idx, row in edited_monitoring_df.iterrows():
                risk_id = row["ID_Risco"]
                mask = updated_df["ID_Risco"] == risk_id
                if any(mask):
                    # Atualizar colunas relevantes
                    for col in ["Status_Acao_Resposta", "Status_Risco", "Observacoes_Monitoramento"]:
                        updated_df.loc[mask, col] = row[col]
            
            # Salvar de volta ao session_state
            st.session_state[STATE_RISKS_DF] = updated_df
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Monitoramento_Riscos",
                action="Atualizar Status Riscos",
                details=f"Atualizados {len(edited_monitoring_df)} riscos"
            )
            
            st.success("✅ Status dos riscos atualizado com sucesso!")
    
    with tab2:
        st.subheader("Dashboard de Monitoramento")
        
        # Verificar se há dados suficientes para dashboard
        if all(col in df_significant.columns for col in ["Status_Risco", "Status_Acao_Resposta"]):
            # Dashboard com KPIs e gráficos
            col1, col2, col3 = st.columns(3)
            
            # Estatísticas gerais
            with col1:
                total_risks = len(df_significant)
                active_risks = len(df_significant[df_significant["Status_Risco"] == "Ativo"])
                closed_risks = len(df_significant[df_significant["Status_Risco"].isin(["Ocorreu", "Não Ocorreu/Fechado"])])
                
                st.metric("Riscos Monitorados", total_risks)
                
                # Calcular % de conclusão
                if total_risks > 0:
                    completion = (closed_risks / total_risks) * 100
                    st.metric("Riscos Fechados", f"{closed_risks} ({completion:.1f}%)")
                else:
                    st.metric("Riscos Fechados", "0 (0%)")
                
                st.metric("Riscos Ativos", active_risks)
            
            with col2:
                # Status das ações de resposta
                actions_completed = len(df_significant[df_significant["Status_Acao_Resposta"] == "Concluída"])
                actions_in_progress = len(df_significant[df_significant["Status_Acao_Resposta"] == "Em Andamento"])
                actions_not_started = len(df_significant[df_significant["Status_Acao_Resposta"] == "Não Iniciada"])
                
                if total_risks > 0:
                    actions_completion = (actions_completed / total_risks) * 100
                    st.metric("Ações Concluídas", f"{actions_completed} ({actions_completion:.1f}%)")
                else:
                    st.metric("Ações Concluídas", "0 (0%)")
                
                st.metric("Ações em Andamento", actions_in_progress)
                st.metric("Ações Não Iniciadas", actions_not_started)
            
            with col3:
                # Riscos por tipo
                threats = len(df_significant[df_significant["Tipo_Risco"] == "Ameaça"])
                opportunities = len(df_significant[df_significant["Tipo_Risco"] == "Oportunidade"])
                
                # Riscos com gatilhos detectados
                triggers_detected = len(df_significant[df_significant["Status_Risco"] == "Novo Gatilho Identificado"])
                
                st.metric("Ameaças", threats)
                st.metric("Oportunidades", opportunities)
                st.metric("Gatilhos Detectados", triggers_detected, delta=triggers_detected, delta_color="inverse")
            
            # Gráficos para visualização do status
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de status do risco
                risk_status_counts = df_significant["Status_Risco"].value_counts().reset_index()
                risk_status_counts.columns = ["Status", "Contagem"]
                
                # Definir cores para os diferentes status
                risk_status_colors = {
                    "Ativo": "blue",
                    "Ocorreu": "red",
                    "Não Ocorreu/Fechado": "green",
                    "Novo Gatilho Identificado": "orange",
                    "Monitorando": "purple"
                }
                
                fig_risk_status = px.pie(
                    risk_status_counts,
                    values="Contagem",
                    names="Status",
                    title="Status dos Riscos",
                    color="Status",
                    color_discrete_map=risk_status_colors,
                    hole=0.4
                )
                
                fig_risk_status.update_traces(textposition="inside", textinfo="percent+label")
                
                st.plotly_chart(fig_risk_status, use_container_width=True)
            
            with col2:
                # Gráfico de status da ação
                action_status_counts = df_significant["Status_Acao_Resposta"].value_counts().reset_index()
                action_status_counts.columns = ["Status", "Contagem"]
                
                # Definir cores para os diferentes status
                action_status_colors = {
                    "Não Iniciada": "lightgray",
                    "Em Andamento": "orange",
                    "Concluída": "green",
                    "Cancelada": "red",
                    "Bloqueada": "purple"
                }
                
                fig_action_status = px.pie(
                    action_status_counts,
                    values="Contagem",
                    names="Status",
                    title="Status das Ações de Resposta",
                    color="Status",
                    color_discrete_map=action_status_colors,
                    hole=0.4
                )
                
                fig_action_status.update_traces(textposition="inside", textinfo="percent+label")
                
                st.plotly_chart(fig_action_status, use_container_width=True)
            
            # Tabela de riscos que precisam de atenção
            st.subheader("Riscos que Precisam de Atenção")
            
            # Filtrar riscos que precisam de atenção
            attention_needed = df_significant[
                (df_significant["Status_Risco"] == "Novo Gatilho Identificado") |
                ((df_significant["Status_Risco"] == "Ativo") & (df_significant["Status_Acao_Resposta"] != "Concluída"))
            ].sort_values(by="Score_Risco", ascending=False)
            
            if not attention_needed.empty:
                st.dataframe(
                    attention_needed[["ID_Risco", "Descricao_Risco", "Tipo_Risco", "Score_Risco", 
                                    "Status_Risco", "Status_Acao_Resposta", "Observacoes_Monitoramento"]],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Não há riscos que necessitem de atenção imediata no momento.")
        
        else:
            st.warning("""
            Dados insuficientes para gerar o dashboard de monitoramento. 
            Por favor, atualize o status dos riscos na aba "Atualizar Status".
            """)
    
    with tab3:
        st.subheader("Gerar Relatório de Riscos")
        
        # Opções para o relatório
        st.write("### Configurações do Relatório")
        
        col1, col2 = st.columns(2)
        
        with col1:
            include_all_risks = st.checkbox("Incluir todos os riscos", value=False, 
                                           help="Se desmarcado, incluirá apenas riscos significativos (com score > 0)")
            include_charts = st.checkbox("Incluir gráficos de status", value=True,
                                        help="Adiciona visualizações gráficas ao relatório")
            include_details = st.checkbox("Incluir detalhes completos", value=False,
                                         help="Se marcado, inclui todos os detalhes dos riscos. Se desmarcado, inclui apenas informações essenciais.")
        
        with col2:
            format_option = st.radio(
                "Formato do Relatório",
                ["HTML", "CSV"],
                help="Escolha o formato para download do relatório"
            )
            
            report_title = st.text_input(
                "Título do Relatório",
                value=f"Relatório de Riscos - {st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto', 'Projeto')}",
                help="Título que aparecerá no topo do relatório"
            )
        
        # Botão para gerar relatório
        if st.button("🔄 Gerar Relatório", use_container_width=True, type="primary"):
            # Decidir quais riscos incluir
            if include_all_risks:
                report_df = df_risks.copy()
            else:
                report_df = df_significant.copy()
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Monitoramento_Riscos",
                action="Gerar Relatorio",
                details=f"Formato: {format_option}, Riscos: {len(report_df)}"
            )
            
            if format_option == "CSV":
                # Gerar CSV
                csv = report_df.to_csv(index=False)
                
                # Download button
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"relatorio_riscos_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_report_csv"
                )
                
                st.success("✅ Relatório CSV gerado com sucesso!")
            
            elif format_option == "HTML":
                # Gerar HTML
                try:
                    # Dados do projeto e usuário para o relatório
                    project_data = st.session_state[STATE_PROJECT_DATA]
                    user_data = st.session_state[STATE_USER_DATA]
                    
                    # Caminho para template se existir
                    template_path = "templates/relatorio_risco_template.html"
                    
                    # Verificar se o diretório existe, caso contrário, criar
                    os.makedirs("templates", exist_ok=True)
                    
                    # CSS para o relatório
                    css = """
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }
                        h1, h2, h3 { color: #2c3e50; }
                        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; font-weight: bold; }
                        tr:nth-child(even) { background-color: #f9f9f9; }
                        tr:hover { background-color: #f1f1f1; }
                        .report-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; margin-bottom: 20px; padding-bottom: 20px; }
                        .project-info { margin-bottom: 30px; }
                        .summary-card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 10px 0; background-color: #f8f9fa; }
                        .card-content { display: flex; flex-direction: column; }
                        .card-value { font-size: 1.5em; font-weight: bold; color: #2c3e50; }
                        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
                        .bg-warning { background-color: #fff3cd; }
                        .bg-success { background-color: #d1e7dd; }
                        .bg-danger { background-color: #f8d7da; }
                        .bg-info { background-color: #cff4fc; }
                        .alert { padding: 10px; border-radius: 5px; margin: 10px 0; }
                        .alert-warning { background-color: #fff3cd; border: 1px solid #ffecb5; }
                        .chart-container { margin: 20px 0; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
                        .footer { margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; font-size: 0.8em; color: #666; }
                        @media print { 
                            .no-print { display: none; } 
                            body { max-width: 100%; }
                        }
                    </style>
                    """
                    
                    # Criar HTML básico para o relatório
                    html = f"""
                    <!DOCTYPE html>
                    <html lang="pt-br">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>{report_title}</title>
                        {css}
                    </head>
                    <body>
                        <div class="report-header">
                            <h1>{report_title}</h1>
                            <div>Data: {datetime.now().strftime('%d/%m/%Y')}</div>
                        </div>
                        
                        <div class="project-info">
                            <h2>Informações do Projeto</h2>
                            <table>
                                <tr><th>Nome do Projeto</th><td>{project_data.get('Nome_da_Obra_ou_ID_Projeto', 'N/A')}</td></tr>
                                <tr><th>Descrição</th><td>{project_data.get('Descricao_Projeto', 'N/A')}</td></tr>
                                <tr><th>Tipo de Construção</th><td>{project_data.get('Tipo_Construcao', 'N/A')}</td></tr>
                                <tr><th>Localização</th><td>{project_data.get('Cidade', 'N/A')}/{project_data.get('UF', 'N/A')}</td></tr>
                                <tr><th>Valor Total Estimado</th><td>R$ {project_data.get('Valor_Total_Estimado', 0):,.2f}</td></tr>
                                <tr><th>Prazo Total (dias)</th><td>{project_data.get('Prazo_Total_Dias', 0)}</td></tr>
                                <tr><th>Responsável pelo Relatório</th><td>{user_data.get('Nome', 'N/A')} ({user_data.get('Cargo', 'N/A')})</td></tr>
                            </table>
                        </div>
                    """
                    
                    # Adicionar resumo de status
                    html += """
                        <h2>Resumo do Status dos Riscos</h2>
                        <div class="card-grid">
                    """
                    
                    # Contagens para resumo
                    total_risks = len(report_df)
                    active_risks = len(report_df[report_df["Status_Risco"] == "Ativo"])
                    occurred_risks = len(report_df[report_df["Status_Risco"] == "Ocorreu"])
                    closed_risks = len(report_df[report_df["Status_Risco"] == "Não Ocorreu/Fechado"])
                    trigger_risks = len(report_df[report_df["Status_Risco"] == "Novo Gatilho Identificado"])
                    
                    # Funções auxiliares para cores de status
                    def status_color(status):
                        colors = {
                            "Ativo": "info",
                            "Ocorreu": "warning",
                            "Não Ocorreu/Fechado": "success",
                            "Novo Gatilho Identificado": "danger",
                            "Monitorando": "info"
                        }
                        return colors.get(status, "light")
                    
                    # Adicionar cards de resumo
                    html += create_summary_card_html("Riscos Monitorados", str(total_risks), "fas fa-list", "bg-light")
                    html += create_summary_card_html("Riscos Ativos", str(active_risks), "fas fa-exclamation-triangle", "bg-info")
                    html += create_summary_card_html("Riscos Ocorridos", str(occurred_risks), "fas fa-times-circle", "bg-warning")
                    html += create_summary_card_html("Riscos Fechados", str(closed_risks), "fas fa-check-circle", "bg-success")
                    html += create_summary_card_html("Gatilhos Identificados", str(trigger_risks), "fas fa-bell", "bg-danger")
                    
                    html += """
                        </div>
                    """
                    
                    # Adicionar gráficos se solicitado
                    if include_charts and not report_df.empty:
                        html += """
                            <h2>Visualizações</h2>
                            <div class="chart-container">
                                <h3>Status dos Riscos</h3>
                                <p>Esta seção deveria conter um gráfico. Como HTML estático não suporta gráficos interativos, 
                                   considere exportar gráficos como imagens para relatórios futuros.</p>
                            </div>
                        """
                    
                    # Lista de riscos que precisam de atenção
                    attention_risks = report_df[
                        (report_df["Status_Risco"] == "Novo Gatilho Identificado") |
                        ((report_df["Status_Risco"] == "Ativo") & 
                         (report_df["Status_Acao_Resposta"] != "Concluída") &
                         (report_df["Score_Risco"] > 60))
                    ].sort_values(by="Score_Risco", ascending=False)
                    
                    if not attention_risks.empty:
                        html += """
                            <div class="alert alert-warning">
                                <h3>⚠️ Riscos que Precisam de Atenção</h3>
                        """
                        
                        # Colunas para riscos que precisam de atenção
                        attention_cols = ["ID_Risco", "Descricao_Risco", "Score_Risco", 
                                        "Status_Risco", "Status_Acao_Resposta", "Observacoes_Monitoramento"]
                        
                        # Usar função do módulo html_generator para converter para HTML
                        html += dataframe_to_html_custom(
                            attention_risks[attention_cols],
                            table_id="attention-risks",
                            table_classes="attention-table"
                        )
                        
                        html += """
                            </div>
                        """
                    
                    # Tabela principal de riscos
                    html += """
                        <h2>Lista de Riscos</h2>
                    """
                    
                    if include_details:
                        # Se incluir detalhes, mostrar mais colunas
                        display_cols = [
                            "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Categoria_Risco",
                            "Score_Risco", "Status_Risco", "Estrategia_Resposta", 
                            "Descricao_Acao_Resposta", "Status_Acao_Resposta", 
                            "Proprietario_do_Risco", "Observacoes_Monitoramento"
                        ]
                    else:
                        # Versão resumida
                        display_cols = [
                            "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Score_Risco",
                            "Status_Risco", "Status_Acao_Resposta", "Observacoes_Monitoramento"
                        ]
                    
                    # Filtrar apenas colunas existentes
                    display_cols = [col for col in display_cols if col in report_df.columns]
                    
                    # Ordenar por Score_Risco para priorizar visualmente os mais importantes
                    sorted_df = report_df.sort_values(by="Score_Risco", ascending=False)
                    
                    # Converter para HTML
                    html += dataframe_to_html_custom(
                        sorted_df[display_cols],
                        table_id="risks-table",
                        table_classes="risks-table"
                    )
                    
                    # Adicionar rodapé
                    html += f"""
                        <div class="footer">
                            <p>Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} pelo Sistema de Análise e Gestão de Riscos em Reformas</p>
                        </div>
                        
                        <div class="no-print">
                            <button onclick="window.print()">Imprimir</button>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Codificar para download
                    b64 = base64.b64encode(html.encode()).decode()
                    
                    # Link de download
                    href = f'<a href="data:text/html;base64,{b64}" download="relatorio_riscos_{datetime.now().strftime("%Y%m%d")}.html">📥 Download HTML</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    # Exibir no streamlit
                    with st.expander("Pré-visualização do Relatório", expanded=True):
                        st.components.v1.html(html, height=600, scrolling=True)
                    
                    st.success("✅ Relatório HTML gerado com sucesso! Clique no link acima para baixar.")
                
                except Exception as e:
                    st.error(f"Erro ao gerar relatório HTML: {str(e)}")

# Rodapé com instruções
st.divider()
st.caption("""
**Ciclo Contínuo:** A gestão de riscos é um processo iterativo. Conforme o projeto avança, 
novos riscos podem surgir e riscos existentes podem mudar. Volte regularmente à etapa de 
Identificação para manter seu registro de riscos atualizado.
""") 