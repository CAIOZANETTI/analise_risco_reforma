import streamlit as st
import pandas as pd
import uuid
import os
from datetime import datetime

# Importar configurações e logger
from config import (RISCOS_COMUNS_CSV, STATE_RISKS_DF, RISKS_DF_EXPECTED_COLUMNS, 
                   STATE_USER_DATA, STATE_PROJECT_DATA, STATE_USER_CONFIG_COMPLETED,
                   TIPO_RISCO_OPTIONS, CATEGORIA_RISCO_OPTIONS)
from utils.gspread_logger import record_log

# Verificar se usuário já completou configuração
if not st.session_state.get(STATE_USER_CONFIG_COMPLETED, False):
    st.warning("⚠️ Por favor, complete as configurações de usuário e projeto primeiro!")
    st.page_link("0_Configuracao_Usuario_e_Projeto.py", label="Ir para Configuração")
    st.stop()

# Título e introdução
st.title("🔍 Identificação e Cadastro de Riscos")

st.markdown("""
Esta é a primeira etapa do ciclo de gerenciamento de riscos. Aqui você irá listar todos os eventos 
incertos que podem impactar o seu projeto, sejam eles ameaças (riscos negativos) ou 
oportunidades (riscos positivos).

Uma identificação ampla e detalhada é fundamental para evitar surpresas durante a execução 
do projeto.
""")

# Função para carregar riscos comuns do CSV com cache
@st.cache_data
def load_common_risks_cached():
    """
    Carrega riscos comuns do CSV com caching para melhor performance.
    """
    try:
        df = pd.read_csv(RISCOS_COMUNS_CSV)
        # Verificar colunas essenciais
        colunas_essenciais = ["ID_Risco", "Descricao_Risco", "Tipo_Risco"]
        if not all(col in df.columns for col in colunas_essenciais):
            st.warning(f"O arquivo {RISCOS_COMUNS_CSV} parece estar com colunas essenciais faltando.")
        return df
    except FileNotFoundError:
        st.error(f"Arquivo de riscos comuns '{RISCOS_COMUNS_CSV}' não encontrado.")
        return pd.DataFrame(columns=RISKS_DF_EXPECTED_COLUMNS)

# Função para gerar um ID único para novos riscos
def generate_risk_id():
    """Gera um ID único para novos riscos cadastrados"""
    existing_ids = []
    if STATE_RISKS_DF in st.session_state and not st.session_state[STATE_RISKS_DF].empty:
        existing_ids = st.session_state[STATE_RISKS_DF]['ID_Risco'].tolist()
    
    counter = 1
    new_id = f"R{counter:03d}"
    while new_id in existing_ids:
        counter += 1
        new_id = f"R{counter:03d}"
    return new_id

# Layout em abas
tab_importar, tab_cadastro, tab_tabela = st.tabs([
    "📎 Importar Riscos", 
    "📝 Cadastro Manual", 
    "📋 Tabela de Riscos"
])

# Aba 1: Importar Riscos
with tab_importar:
    st.subheader("Importar de Fontes Externas")
    
    # Importar de CSV modelo
    st.markdown("### Carregar Riscos Comuns")
    st.markdown("""
    Carregue uma lista pré-definida de riscos comuns em projetos de reforma. 
    Isso serve como um ponto de partida que você pode personalizar.
    """)
    
    if st.button("Carregar Riscos Comuns (CSV)"):
        df_riscos_comuns = load_common_risks_cached()
        
        if not df_riscos_comuns.empty:
            # Verificar se já existem riscos no session_state
            if STATE_RISKS_DF in st.session_state and not st.session_state[STATE_RISKS_DF].empty:
                # Identificar riscos já existentes pelo ID para evitar duplicações
                existing_ids = st.session_state[STATE_RISKS_DF]['ID_Risco'].tolist()
                novos_riscos = df_riscos_comuns[~df_riscos_comuns['ID_Risco'].isin(existing_ids)]
                
                if not novos_riscos.empty:
                    # Adicionar apenas novos riscos
                    st.session_state[STATE_RISKS_DF] = pd.concat([st.session_state[STATE_RISKS_DF], novos_riscos], ignore_index=True)
                    st.success(f"✅ {len(novos_riscos)} novos riscos adicionados com sucesso!")
                else:
                    st.info("Todos os riscos do arquivo já foram cadastrados anteriormente.")
            else:
                # Se não existirem riscos, simplesmente utilizar o DataFrame carregado
                st.session_state[STATE_RISKS_DF] = df_riscos_comuns.copy()
                st.success(f"✅ {len(df_riscos_comuns)} riscos carregados com sucesso!")
            
            # Registrar o evento no log
            record_log(
                user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"),
                project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"),
                page="Identificacao",
                action="Carregar CSV Riscos",
                details=f"Carregados {len(df_riscos_comuns)} riscos comuns"
            )
    
    st.divider()
    
    # Upload de arquivo CSV
    st.markdown("### Upload de Arquivo CSV")
    st.markdown("""
    Você também pode fazer upload de um arquivo CSV personalizado com seus próprios riscos.
    O arquivo deve conter pelo menos as colunas: ID_Risco, Descricao_Risco, Tipo_Risco.
    """)
    
    uploaded_file = st.file_uploader("Escolha seu arquivo CSV", type=["csv"])
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            
            # Verificar colunas mínimas
            colunas_minimas = ["ID_Risco", "Descricao_Risco", "Tipo_Risco"]
            if not all(col in df_upload.columns for col in colunas_minimas):
                st.error("O arquivo não contém todas as colunas necessárias!")
            else:
                # Preview dos dados
                st.write("Preview dos dados (5 primeiras linhas):")
                st.dataframe(df_upload.head())
                
                if st.button("Confirmar Importação"):
                    # Similar ao processo de importação de riscos comuns
                    if STATE_RISKS_DF in st.session_state and not st.session_state[STATE_RISKS_DF].empty:
                        existing_ids = st.session_state[STATE_RISKS_DF]['ID_Risco'].tolist()
                        novos_riscos = df_upload[~df_upload['ID_Risco'].isin(existing_ids)]
                        
                        if not novos_riscos.empty:
                            st.session_state[STATE_RISKS_DF] = pd.concat([st.session_state[STATE_RISKS_DF], novos_riscos], ignore_index=True)
                            st.success(f"✅ {len(novos_riscos)} riscos importados com sucesso!")
                        else:
                            st.info("Todos os riscos do arquivo já foram cadastrados.")
                    else:
                        st.session_state[STATE_RISKS_DF] = df_upload.copy()
                        st.success(f"✅ {len(df_upload)} riscos importados com sucesso!")
                    
                    # Log da ação
                    record_log(
                        user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"),
                        project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"),
                        page="Identificacao",
                        action="Upload CSV Riscos",
                        details=f"Importados {len(df_upload)} riscos via upload"
                    )
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

# Aba 2: Cadastro Manual
with tab_cadastro:
    st.subheader("Cadastro Manual de Riscos")
    
    with st.form("form_novo_risco"):
        # ID automático
        risk_id = generate_risk_id()
        st.text_input("ID do Risco", value=risk_id, disabled=True)
        
        # Campos de cadastro
        descricao = st.text_area("Descrição do Risco*", 
                               help="Descreva o evento incerto de forma clara, específica e sem ambiguidades.")
        
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo de Risco*", options=TIPO_RISCO_OPTIONS,
                             help="Ameaça: evento com impacto negativo. Oportunidade: evento com impacto positivo.")
        with col2:
            categoria = st.selectbox("Categoria*", options=CATEGORIA_RISCO_OPTIONS,
                                  help="Classifique o risco em uma categoria geral para facilitar análises.")
        
        subcategoria = st.text_input("Subcategoria", 
                                  help="Opcional: uma classificação mais específica dentro da categoria escolhida.")
        
        st.subheader("Impactos Potenciais")
        col1, col2 = st.columns(2)
        
        with col1:
            efeito_custo_min = st.number_input("Impacto Mínimo em Custo (R$)", value=0.0,
                                             help="Para ameaças: custo adicional mínimo. Para oportunidades: valor positivo (economia).")
            efeito_prazo_min = st.number_input("Impacto Mínimo em Prazo (dias)", value=0,
                                             help="Para ameaças: dias adicionais. Para oportunidades: valor positivo (economia de dias).")
        
        with col2:
            efeito_custo_max = st.number_input("Impacto Máximo em Custo (R$)", value=0.0,
                                             help="Para ameaças: custo adicional máximo. Para oportunidades: valor positivo máximo.")
            efeito_prazo_max = st.number_input("Impacto Máximo em Prazo (dias)", value=0,
                                             help="Para ameaças: dias adicionais máximos. Para oportunidades: economia máxima de dias.")
        
        st.subheader("Informações Adicionais")
        gatilhos = st.text_area("Gatilhos/Sinais de Alerta", 
                             help="Indícios que sinalizam que o risco está prestes a ocorrer ou já está ocorrendo.")
        causas = st.text_area("Possíveis Causas Raiz", 
                           help="Fatores ou eventos que podem dar origem a este risco. Útil para desenvolver respostas preventivas.")
        
        submitted = st.form_submit_button("Cadastrar Risco")
        
        if submitted:
            # Validar campos obrigatórios
            if not descricao or not tipo or not categoria:
                st.error("Por favor, preencha todos os campos obrigatórios!")
            else:
                # Criar dicionário com os dados do risco
                novo_risco = {
                    "ID_Risco": risk_id,
                    "Descricao_Risco": descricao,
                    "Tipo_Risco": tipo,
                    "Categoria_Risco": categoria,
                    "Subcategoria_Risco": subcategoria,
                    "Efeito_Custo_Min": efeito_custo_min,
                    "Efeito_Custo_Max": efeito_custo_max,
                    "Efeito_Prazo_Min_Dias": efeito_prazo_min,
                    "Efeito_Prazo_Max_Dias": efeito_prazo_max,
                    "Gatilhos_Risco": gatilhos,
                    "Possiveis_Causas_Raiz": causas,
                    # Campos que serão preenchidos em etapas posteriores
                    "Probabilidade_Qualitativa": "",
                    "Impacto_Custo_Qualitativo": "",
                    "Impacto_Prazo_Qualitativo": "",
                    "Impacto_Qualidade_Qualitativo": "",
                    "Urgencia_Risco": "",
                    "Probabilidade_Num": 0.0,
                    "Score_Risco": 0.0,
                    "VME_Custo": 0.0,
                    "Estrategia_Resposta": "",
                    "Descricao_Acao_Resposta": "",
                    "Proprietario_do_Risco": "",
                    "Prazo_Implementacao_Resposta": "",
                    "Custo_Estimado_Resposta": 0.0,
                    "Plano_de_Contingencia": "",
                    "Riscos_Secundarios_Identificados": "",
                    "Status_Acao_Resposta": "",
                    "Status_Risco": "Ativo",
                    "Observacoes_Monitoramento": ""
                }
                
                # Adicionar à lista de riscos
                if STATE_RISKS_DF in st.session_state:
                    # Converter para DataFrame e concatenar
                    novo_df = pd.DataFrame([novo_risco])
                    st.session_state[STATE_RISKS_DF] = pd.concat([st.session_state[STATE_RISKS_DF], novo_df], ignore_index=True)
                else:
                    # Criar novo DataFrame
                    st.session_state[STATE_RISKS_DF] = pd.DataFrame([novo_risco])
                
                # Log da ação
                record_log(
                    user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"),
                    project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"),
                    page="Identificacao",
                    action="Adicionar Risco Manual",
                    details=f"ID: {risk_id} - {descricao[:30]}..."
                )
                
                st.success(f"✅ Risco {risk_id} cadastrado com sucesso!")

# Aba 3: Tabela de Riscos
with tab_tabela:
    st.subheader("Visualização e Edição de Riscos Cadastrados")
    
    # Verificar se existem riscos cadastrados
    if STATE_RISKS_DF not in st.session_state or st.session_state[STATE_RISKS_DF].empty:
        st.info("Nenhum risco cadastrado até o momento. Use as abas anteriores para adicionar riscos.")
    else:
        # Opções de filtro
        st.caption("Filtros:")
        col1, col2 = st.columns(2)
        with col1:
            filtro_tipo = st.multiselect("Filtrar por Tipo", options=TIPO_RISCO_OPTIONS)
        with col2:
            filtro_categoria = st.multiselect("Filtrar por Categoria", options=CATEGORIA_RISCO_OPTIONS)
        
        # Aplicar filtros
        df_filtrado = st.session_state[STATE_RISKS_DF].copy()
        if filtro_tipo:
            df_filtrado = df_filtrado[df_filtrado["Tipo_Risco"].isin(filtro_tipo)]
        if filtro_categoria:
            df_filtrado = df_filtrado[df_filtrado["Categoria_Risco"].isin(filtro_categoria)]
        
        # Definir colunas para exibição e edição na tabela
        display_cols = [
            "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Categoria_Risco", "Subcategoria_Risco",
            "Efeito_Custo_Min", "Efeito_Custo_Max", "Efeito_Prazo_Min_Dias", "Efeito_Prazo_Max_Dias",
            "Gatilhos_Risco", "Possiveis_Causas_Raiz"
        ]
        
        # Configuração das colunas para edição
        column_config = {
            "ID_Risco": st.column_config.TextColumn("ID", disabled=True),
            "Descricao_Risco": st.column_config.TextColumn("Descrição"),
            "Tipo_Risco": st.column_config.SelectboxColumn("Tipo", options=TIPO_RISCO_OPTIONS),
            "Categoria_Risco": st.column_config.SelectboxColumn("Categoria", options=CATEGORIA_RISCO_OPTIONS),
            "Efeito_Custo_Min": st.column_config.NumberColumn("Custo Min", format="R$ %.2f"),
            "Efeito_Custo_Max": st.column_config.NumberColumn("Custo Max", format="R$ %.2f"),
            "Efeito_Prazo_Min_Dias": st.column_config.NumberColumn("Prazo Min (dias)"),
            "Efeito_Prazo_Max_Dias": st.column_config.NumberColumn("Prazo Max (dias)")
        }
        
        # Exibir tabela editável
        df_edited = st.data_editor(
            df_filtrado[display_cols], 
            column_config=column_config,
            hide_index=True,
            key="risk_table_editor",
            num_rows="dynamic"  # Permitir adicionar novas linhas
        )
        
        if st.button("Atualizar Lista de Riscos"):
            # Validar dados editados
            if df_edited.isnull().any().any():
                st.error("Por favor, preencha todos os campos antes de salvar!")
            else:
                # Para cada linha editada, atualizar o DataFrame principal
                changes_made = False
                
                for idx, row in df_edited.iterrows():
                    # Verificar se é uma nova linha (não existente no DataFrame original)
                    if row["ID_Risco"] == "" or pd.isna(row["ID_Risco"]):
                        # Gerar novo ID para a linha
                        row["ID_Risco"] = generate_risk_id()
                        st.session_state[STATE_RISKS_DF] = pd.concat([st.session_state[STATE_RISKS_DF], pd.DataFrame([row])], ignore_index=True)
                        changes_made = True
                    else:
                        # Atualizar linha existente
                        id_risco = row["ID_Risco"]
                        idx_original = st.session_state[STATE_RISKS_DF].index[st.session_state[STATE_RISKS_DF]["ID_Risco"] == id_risco].tolist()
                        
                        if idx_original:
                            # Atualizar apenas as colunas exibidas/editadas
                            for col in display_cols:
                                st.session_state[STATE_RISKS_DF].loc[idx_original[0], col] = row[col]
                            changes_made = True
                
                if changes_made:
                    # Log da ação
                    record_log(
                        user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"),
                        project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"),
                        page="Identificacao",
                        action="Editar Risco via Tabela",
                        details=f"Atualizados {len(df_edited)} registros"
                    )
                    
                    st.success("✅ Riscos atualizados com sucesso!")
                else:
                    st.info("Nenhuma alteração foi detectada.")
        
        # Opção para exclusão de riscos
        with st.expander("Excluir Riscos"):
            st.warning("ATENÇÃO: A exclusão de riscos é permanente e não pode ser desfeita!")
            
            # Lista de IDs para seleção
            ids_para_excluir = st.multiselect(
                "Selecione os IDs dos riscos a serem excluídos:",
                options=df_filtrado["ID_Risco"].unique().tolist()
            )
            
            if ids_para_excluir and st.button("Confirmar Exclusão"):
                # Remover os riscos selecionados
                st.session_state[STATE_RISKS_DF] = st.session_state[STATE_RISKS_DF][~st.session_state[STATE_RISKS_DF]["ID_Risco"].isin(ids_para_excluir)]
                
                # Log da ação
                record_log(
                    user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"),
                    project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"),
                    page="Identificacao",
                    action="Excluir Risco",
                    details=f"IDs excluídos: {', '.join(ids_para_excluir)}"
                )
                
                st.success(f"✅ {len(ids_para_excluir)} riscos foram excluídos com sucesso!")

# Dicas sobre técnicas de identificação de riscos (mostrada em expander)
with st.expander("💡 Técnicas para Identificar Riscos"):
    st.markdown("""
    ### Técnicas Úteis para Identificação Abrangente de Riscos
    
    1. **Brainstorming**: Reúna equipe e stakeholders para discussão livre de possíveis riscos.
    
    2. **Checklists**: Utilize listas padronizadas de riscos comuns em reformas como ponto de partida.
    
    3. **Entrevistas**: Converse com especialistas e pessoas experientes em reformas similares.
    
    4. **Análise SWOT**: Identifique Forças, Fraquezas, Oportunidades e Ameaças do projeto.
    
    5. **Revisão de Documentação**: Analise plantas, orçamentos e cronogramas para identificar riscos.
    
    6. **Análise de Premissas**: Questione as premissas do projeto para identificar riscos potenciais.
    
    7. **Categorização**: Organize riscos em categorias como técnicos, externos, organizacionais, etc.
    """)

# Rodapé com botão para próxima etapa
st.divider()
col1, col2 = st.columns([4, 1])
with col2:
    st.page_link("2_Analise_Qualitativa_de_Riscos.py", label="Próxima Etapa: Análise Qualitativa →", use_container_width=True) 