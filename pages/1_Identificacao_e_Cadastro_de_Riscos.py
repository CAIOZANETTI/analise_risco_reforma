import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime

# Importar configurações
from config import (
    RISCOS_COMUNS_CSV, STATE_RISKS_DF, RISKS_DF_EXPECTED_COLUMNS,
    STATE_USER_DATA, STATE_PROJECT_DATA, STATE_USER_CONFIG_COMPLETED,
    TIPO_RISCO_OPTIONS, CATEGORIA_RISCO_OPTIONS
)

# Importar logger para registro de eventos
from utils.gspread_logger import record_log

# Verificar se as informações de usuário/projeto foram preenchidas
if not st.session_state[STATE_USER_CONFIG_COMPLETED]:
    st.error("⚠️ É necessário preencher as informações de usuário e projeto antes de prosseguir!")
    st.page_link("0_Configuracao_Usuario_e_Projeto.py", label="Ir para Configuração")
    st.stop()

# Título da página
st.title("🔍 Identificação e Cadastro de Riscos")

# Informações sobre a etapa
st.info("""
Esta etapa é o alicerce do processo de gestão de riscos. Aqui você deve listar todos os possíveis eventos 
incertos - tanto ameaças (riscos negativos) quanto oportunidades (riscos positivos) - que podem impactar sua obra.
""")

# Função para carregar riscos comuns do CSV
@st.cache_data
def load_common_risks_cached():
    """
    Carrega riscos comuns do CSV com cache para melhor performance.
    """
    try:
        df = pd.read_csv(RISCOS_COMUNS_CSV)
        # Verificar colunas essenciais
        if not all(col in df.columns for col in ["ID_Risco", "Descricao_Risco", "Tipo_Risco"]):
            st.warning(f"O arquivo {RISCOS_COMUNS_CSV} parece estar com colunas faltando.")
        return df
    except FileNotFoundError:
        st.warning(f"Arquivo de riscos comuns '{RISCOS_COMUNS_CSV}' não encontrado.")
        return pd.DataFrame(columns=RISKS_DF_EXPECTED_COLUMNS)

# Mostrar métodos de identificação de riscos
st.subheader("Técnicas para Identificação de Riscos")
with st.expander("Ver técnicas recomendadas", expanded=False):
    st.markdown("""
    **Para uma identificação completa, considere:**
    
    1. **Brainstorming** com a equipe do projeto e stakeholders
    2. **Checklists** de riscos comuns em projetos similares
    3. **Análise SWOT** (Forças, Fraquezas, Oportunidades, Ameaças)
    4. **Entrevistas** com especialistas no tipo de reforma
    5. **Revisão de documentação** técnica e projetos
    6. **Análise de premissas** e restrições do projeto
    7. **Lições aprendidas** de projetos anteriores
    """)

# Layout em duas colunas para botões de importação e cadastro
col1, col2 = st.columns(2)

with col1:
    # Botão para carregar riscos comuns do CSV
    if st.button("📄 Carregar Riscos Comuns (CSV)", help="Carrega uma lista pré-definida de riscos comuns em obras de reforma"):
        df_common = load_common_risks_cached()
        if not df_common.empty:
            # Adicionar riscos comuns ao dataframe principal, evitando duplicatas
            current_df = st.session_state[STATE_RISKS_DF]
            # Preservar riscos existentes (não substituir se ID já existe)
            combined_df = pd.concat([current_df, df_common]).drop_duplicates(subset=['ID_Risco'], keep='first')
            st.session_state[STATE_RISKS_DF] = combined_df
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Identificacao",
                action="Carregar CSV Riscos",
                details=f"Carregados {len(df_common)} riscos comuns"
            )
            
            st.success(f"✅ {len(df_common)} riscos comuns carregados com sucesso!")
        else:
            st.error("Não foi possível carregar riscos comuns.")

with col2:
    # Botão para upload de CSV personalizado
    uploaded_file = st.file_uploader("📤 Importar CSV Personalizado", type="csv", 
                                    help="Faça upload de um arquivo CSV com seus riscos específicos")
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            
            # Verificar se contém colunas mínimas necessárias
            required_cols = ["Descricao_Risco", "Tipo_Risco", "Categoria_Risco"]
            missing_cols = [col for col in required_cols if col not in df_upload.columns]
            
            if missing_cols:
                st.error(f"CSV inválido! Colunas obrigatórias ausentes: {', '.join(missing_cols)}")
            else:
                # Gerar IDs para linhas sem ID_Risco
                if "ID_Risco" not in df_upload.columns:
                    df_upload["ID_Risco"] = [f"R{i+1:04d}" for i in range(len(df_upload))]
                
                # Adicionar ao DataFrame principal, evitando duplicatas
                current_df = st.session_state[STATE_RISKS_DF]
                combined_df = pd.concat([current_df, df_upload]).drop_duplicates(subset=['ID_Risco'], keep='first')
                
                # Garantir que todas as colunas esperadas existam
                for col in RISKS_DF_EXPECTED_COLUMNS:
                    if col not in combined_df.columns:
                        combined_df[col] = ""
                
                st.session_state[STATE_RISKS_DF] = combined_df
                
                # Log da ação
                record_log(
                    user_id=st.session_state[STATE_USER_DATA].get('Email'),
                    project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                    page="Identificacao",
                    action="Importar CSV Personalizado",
                    details=f"Importados {len(df_upload)} riscos"
                )
                
                st.success(f"✅ {len(df_upload)} riscos importados com sucesso!")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")

# Cadastro manual de riscos
st.subheader("Cadastro Manual de Riscos")
with st.form("cadastro_risco_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        descricao = st.text_area("Descrição do Risco*", help="Descreva o evento de risco de forma clara e específica")
        tipo_risco = st.selectbox("Tipo de Risco*", options=TIPO_RISCO_OPTIONS, help="Ameaça (impacto negativo) ou Oportunidade (impacto positivo)")
        categoria = st.selectbox("Categoria*", options=CATEGORIA_RISCO_OPTIONS)
        subcategoria = st.text_input("Subcategoria", help="Especifique uma subcategoria para melhor organização")
    
    with col2:
        efeito_custo_min = st.number_input("Efeito Mínimo no Custo (R$)", value=0.0, help="Impacto financeiro mínimo estimado")
        efeito_custo_max = st.number_input("Efeito Máximo no Custo (R$)", value=0.0, help="Impacto financeiro máximo estimado")
        efeito_prazo_min = st.number_input("Efeito Mínimo no Prazo (dias)", value=0, step=1, help="Impacto mínimo no cronograma em dias")
        efeito_prazo_max = st.number_input("Efeito Máximo no Prazo (dias)", value=0, step=1, help="Impacto máximo no cronograma em dias")
    
    gatilhos = st.text_area("Gatilhos do Risco", help="Eventos ou condições que indicam que o risco está prestes a ocorrer")
    causas = st.text_area("Possíveis Causas Raiz", help="Fatores fundamentais que podem originar este risco")
    
    submitted = st.form_submit_button("Adicionar Risco")
    
    if submitted:
        if not descricao or not tipo_risco or not categoria:
            st.error("Por favor, preencha os campos obrigatórios marcados com *.")
        else:
            # Gerar ID único para o risco
            risk_id = f"R{uuid.uuid4().hex[:8].upper()}"
            
            # Criar novo registro de risco
            new_risk = {
                "ID_Risco": risk_id,
                "Descricao_Risco": descricao,
                "Tipo_Risco": tipo_risco,
                "Categoria_Risco": categoria,
                "Subcategoria_Risco": subcategoria,
                "Efeito_Custo_Min": efeito_custo_min,
                "Efeito_Custo_Max": efeito_custo_max,
                "Efeito_Prazo_Min_Dias": efeito_prazo_min,
                "Efeito_Prazo_Max_Dias": efeito_prazo_max,
                "Gatilhos_Risco": gatilhos,
                "Possiveis_Causas_Raiz": causas
            }
            
            # Adicionar ao DataFrame
            new_row = pd.DataFrame([new_risk])
            st.session_state[STATE_RISKS_DF] = pd.concat([st.session_state[STATE_RISKS_DF], new_row], ignore_index=True)
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Identificacao",
                action="Adicionar Risco Manual",
                details=f"ID: {risk_id}, Tipo: {tipo_risco}"
            )
            
            st.success(f"✅ Risco {risk_id} adicionado com sucesso!")

# Visualização e edição da tabela de riscos
st.subheader("Lista de Riscos Identificados")

# Obter DataFrame atual
df_risks = st.session_state[STATE_RISKS_DF]

if df_risks.empty:
    st.warning("Nenhum risco cadastrado ainda. Use as opções acima para adicionar riscos.")
else:
    # Configuração das colunas para o editor de dados
    cols_to_show = [
        "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Categoria_Risco", 
        "Subcategoria_Risco", "Efeito_Custo_Min", "Efeito_Custo_Max", 
        "Efeito_Prazo_Min_Dias", "Efeito_Prazo_Max_Dias", 
        "Gatilhos_Risco", "Possiveis_Causas_Raiz"
    ]
    
    # Configuração das colunas para formatação e edição
    column_config = {
        "ID_Risco": st.column_config.TextColumn("ID", width="small", disabled=True),
        "Descricao_Risco": st.column_config.TextColumn("Descrição", width="large"),
        "Tipo_Risco": st.column_config.SelectboxColumn(
            "Tipo", width="small", options=TIPO_RISCO_OPTIONS),
        "Categoria_Risco": st.column_config.SelectboxColumn(
            "Categoria", width="medium", options=CATEGORIA_RISCO_OPTIONS),
        "Subcategoria_Risco": st.column_config.TextColumn("Subcategoria", width="medium"),
        "Efeito_Custo_Min": st.column_config.NumberColumn("Custo Min (R$)", format="R$ %.2f"),
        "Efeito_Custo_Max": st.column_config.NumberColumn("Custo Max (R$)", format="R$ %.2f"),
        "Efeito_Prazo_Min_Dias": st.column_config.NumberColumn("Prazo Min (dias)", format="%d"),
        "Efeito_Prazo_Max_Dias": st.column_config.NumberColumn("Prazo Max (dias)", format="%d"),
        "Gatilhos_Risco": st.column_config.TextColumn("Gatilhos", width="medium"),
        "Possiveis_Causas_Raiz": st.column_config.TextColumn("Causas Raiz", width="medium")
    }
    
    # Mostrar tabela editável com os riscos
    st.caption("Edite diretamente na tabela abaixo e clique no botão 'Atualizar Lista de Riscos' após as alterações.")
    edited_df = st.data_editor(
        df_risks[cols_to_show], 
        num_rows="dynamic",
        column_config=column_config,
        key="risk_table_editor",
        use_container_width=True
    )
    
    # Botão para salvar alterações
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 Atualizar Lista de Riscos", use_container_width=True):
            # Preservar colunas não mostradas na edição
            for col in df_risks.columns:
                if col not in cols_to_show and col not in edited_df.columns:
                    edited_df[col] = ""
            
            # Validação rápida de dados
            if edited_df['ID_Risco'].duplicated().any():
                st.error("⚠️ Foram detectados IDs duplicados. Corrija os dados antes de salvar.")
            else:
                # Salvar dataframe atualizado
                st.session_state[STATE_RISKS_DF] = edited_df
                
                # Log da ação
                record_log(
                    user_id=st.session_state[STATE_USER_DATA].get('Email'),
                    project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                    page="Identificacao",
                    action="Editar Riscos via Tabela",
                    details=f"Editados/atualizados {len(edited_df)} riscos"
                )
                
                st.success("✅ Lista de riscos atualizada com sucesso!")
    
    # Botão para exportar para CSV
    with col2:
        if st.button("📥 Exportar Lista de Riscos para CSV", help="Baixe a tabela em formato CSV", use_container_width=True):
            csv = edited_df.to_csv(index=False)
            
            # Criar link de download
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"riscos_{st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto', 'projeto')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_csv"
            )
            
            # Log da ação
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get('Email'),
                project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
                page="Identificacao",
                action="Exportar Riscos CSV",
                details=f"Exportados {len(edited_df)} riscos"
            )

# Rodapé com instruções
st.divider()
st.caption("""
**Próximos passos:** Após identificar e cadastrar todos os riscos relevantes para seu projeto, 
prossiga para a "Análise Qualitativa de Riscos" para avaliar a probabilidade e o impacto de cada um.
""") 