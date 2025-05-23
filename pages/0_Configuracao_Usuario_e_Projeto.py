import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Importar configurações
from config import (
    TIPOS_CONSTRUCOES_CSV, STATE_USER_DATA, STATE_PROJECT_DATA, 
    STATE_USER_CONFIG_COMPLETED, UF_OPTIONS
)

# Importar logger para registro de eventos
from utils.gspread_logger import record_log

# Título da página
st.title("⚙️ Configuração de Usuário e Projeto")

# Função para carregar tipos de construção do CSV com cache
@st.cache_data
def load_construction_types():
    """
    Carrega os tipos de construção do arquivo CSV com caching para melhor performance.
    Retorna DataFrame vazio com colunas esperadas se arquivo não encontrado.
    """
    try:
        return pd.read_csv(TIPOS_CONSTRUCOES_CSV)
    except FileNotFoundError:
        st.warning(f"Arquivo '{TIPOS_CONSTRUCOES_CSV}' não encontrado. Será criado ao salvar.")
        return pd.DataFrame(columns=['ID_Tipo', 'Categoria_Construcao', 'Proposito_Construcao'])

# Carregar dados de tipos de construção
df_tipos = load_construction_types()

# Organizar layout em abas
tab1, tab2, tab3 = st.tabs(["📋 Dados do Usuário", "🏢 Dados do Projeto", "⚠️ Perfil de Risco"])

# Aba 1: Dados do Usuário
with tab1:
    st.subheader("Informações do Usuário")
    
    # Extrair dados atuais do usuário (se existirem)
    user_data = st.session_state[STATE_USER_DATA]
    
    # Formulário para dados do usuário
    with st.form(key="user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome completo*", value=user_data.get("Nome", ""))
            email = st.text_input("E-mail*", value=user_data.get("Email", ""))
            telefone = st.text_input("Telefone", value=user_data.get("Telefone", ""))
        
        with col2:
            empresa = st.text_input("Empresa/Organização", value=user_data.get("Empresa", ""))
            cargo = st.text_input("Cargo/Função", value=user_data.get("Cargo", ""))
        
        st.markdown("**Campos com * são obrigatórios**")
        salvar_usuario = st.form_submit_button("Salvar Dados do Usuário")
        
        if salvar_usuario:
            # Validação de dados obrigatórios
            if not nome or not email:
                st.error("Por favor, preencha os campos obrigatórios: Nome e E-mail.")
            elif "@" not in email or "." not in email:
                st.error("Por favor, insira um e-mail válido.")
            else:
                # Atualização de dados do usuário no session_state
                st.session_state[STATE_USER_DATA] = {
                    "Nome": nome,
                    "Email": email,
                    "Telefone": telefone,
                    "Empresa": empresa,
                    "Cargo": cargo
                }
                
                # Log da ação
                record_log(user_id=email, project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"), 
                           page="Configuracao", action="Salvar Dados Usuario")
                
                st.success("✅ Dados do usuário salvos com sucesso!")

# Aba 2: Dados do Projeto
with tab2:
    st.subheader("Detalhes do Projeto/Obra de Reforma")
    
    # Extrair dados atuais do projeto (se existirem)
    project_data = st.session_state[STATE_PROJECT_DATA]
    
    # Formulário para dados do projeto
    with st.form(key="project_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome_projeto = st.text_input("Nome da Obra/ID do Projeto*", value=project_data.get("Nome_da_Obra_ou_ID_Projeto", ""))
            descricao = st.text_area("Descrição do Projeto", value=project_data.get("Descricao_Projeto", ""), height=100)
            
            # Opções para tipo de construção baseadas no CSV
            tipos_opcoes = [""] + list(df_tipos["Categoria_Construcao"].unique()) if not df_tipos.empty else [""]
            tipo_construcao = st.selectbox("Tipo de Construção*", options=tipos_opcoes, 
                                           index=tipos_opcoes.index(project_data.get("Tipo_Construcao", "")) if project_data.get("Tipo_Construcao", "") in tipos_opcoes else 0)
            
            # Filtragem dinâmica baseada na seleção do tipo
            if tipo_construcao and not df_tipos.empty:
                propositos = [""] + list(df_tipos[df_tipos["Categoria_Construcao"] == tipo_construcao]["Proposito_Construcao"].unique())
                proposito = st.selectbox("Propósito Principal*", options=propositos, 
                                        index=propositos.index(project_data.get("Proposito_Principal", "")) if project_data.get("Proposito_Principal", "") in propositos else 0)
            else:
                proposito = st.text_input("Propósito Principal*", value=project_data.get("Proposito_Principal", ""))
        
        with col2:
            # Localização
            col2a, col2b = st.columns(2)
            with col2a:
                uf = st.selectbox("UF*", options=[""] + UF_OPTIONS, 
                                 index=([""] + UF_OPTIONS).index(project_data.get("UF", "")) if project_data.get("UF", "") in [""] + UF_OPTIONS else 0)
            with col2b:
                cidade = st.text_input("Cidade*", value=project_data.get("Cidade", ""))
            
            # Dados numéricos
            area = st.number_input("Área Construída (m²)", min_value=0.0, 
                                  value=float(project_data.get("Area_Construida_m2", 0.0)))
            valor = st.number_input("Valor Total Estimado (R$)*", min_value=0.0, format="%.2f",
                                   value=float(project_data.get("Valor_Total_Estimado", 0.0)))
            prazo = st.number_input("Prazo Total (dias)*", min_value=0, 
                                   value=int(project_data.get("Prazo_Total_Dias", 0)))
            
            # Datas
            data_inicio = st.date_input("Data de Início", 
                                      value=project_data.get("Data_Inicio") if project_data.get("Data_Inicio") else datetime.now())
            
            # Calcular data fim com base no prazo
            data_fim_calculada = data_inicio + timedelta(days=prazo) if prazo > 0 else data_inicio
            data_fim = st.date_input("Data Prevista de Conclusão", value=data_fim_calculada)
            
            # Nível de complexidade
            complexidade = st.selectbox("Nível de Complexidade", options=["Baixo", "Médio", "Alto"],
                                       index=["Baixo", "Médio", "Alto"].index(project_data.get("Nivel_Complexidade", "Médio")))
        
        st.markdown("**Campos com * são obrigatórios**")
        salvar_projeto = st.form_submit_button("Salvar Dados do Projeto")
        
        if salvar_projeto:
            # Validação de dados obrigatórios
            campos_obrigatorios = [
                (nome_projeto, "Nome da Obra/ID do Projeto"),
                (tipo_construcao, "Tipo de Construção"),
                (proposito, "Propósito Principal"),
                (uf, "UF"),
                (cidade, "Cidade"),
                (valor > 0, "Valor Total Estimado"),
                (prazo > 0, "Prazo Total")
            ]
            
            campos_vazios = [campo[1] for campo in campos_obrigatorios if not campo[0]]
            
            if campos_vazios:
                st.error(f"Por favor, preencha os campos obrigatórios: {', '.join(campos_vazios)}")
            else:
                # Atualização de dados do projeto no session_state
                st.session_state[STATE_PROJECT_DATA] = {
                    "Nome_da_Obra_ou_ID_Projeto": nome_projeto,
                    "Descricao_Projeto": descricao,
                    "Tipo_Construcao": tipo_construcao,
                    "Proposito_Principal": proposito,
                    "UF": uf,
                    "Cidade": cidade,
                    "Area_Construida_m2": area,
                    "Valor_Total_Estimado": valor,
                    "Prazo_Total_Dias": prazo,
                    "Data_Inicio": data_inicio,
                    "Data_Prevista_Fim": data_fim,
                    "Nivel_Complexidade": complexidade,
                    # Manter os valores de risco (serão definidos na próxima aba)
                    "Apetite_ao_Risco": project_data.get("Apetite_ao_Risco", "Moderado"),
                    "Tolerancia_Desvio_Custo": project_data.get("Tolerancia_Desvio_Custo", 0.10),
                    "Tolerancia_Desvio_Prazo": project_data.get("Tolerancia_Desvio_Prazo", 0.15),
                    "Data_Cadastro": project_data.get("Data_Cadastro", datetime.now().strftime("%Y-%m-%d"))
                }
                
                # Log da ação
                record_log(user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"), 
                           project_id=nome_projeto, 
                           page="Configuracao", action="Salvar Dados Projeto")
                
                st.success("✅ Dados do projeto salvos com sucesso!")

# Aba 3: Perfil de Risco
with tab3:
    st.subheader("Configurações de Perfil de Risco")
    st.markdown("""
    Nesta seção, defina o apetite geral a riscos do projeto e as tolerâncias específicas 
    para desvios de custo e prazo. Estas configurações ajudarão a calibrar as análises
    e a identificar quando os riscos excedem os limites aceitáveis.
    """)
    
    # Extrair dados atuais do projeto (se existirem)
    project_data = st.session_state[STATE_PROJECT_DATA]
    
    # Formulário para configurações de risco
    with st.form(key="risk_profile_form"):
        # Apetite ao risco
        apetite = st.select_slider(
            "Apetite geral ao risco",
            options=["Muito Baixo (Conservador)", "Baixo", "Moderado", "Alto", "Muito Alto (Arrojado)"],
            value=project_data.get("Apetite_ao_Risco", "Moderado")
        )
        
        st.info("""
        O apetite ao risco indica a disposição geral para aceitar incertezas no projeto.
        Um perfil conservador favorece abordagens mais seguras, enquanto um perfil arrojado
        aceita mais incerteza em busca de maiores benefícios potenciais.
        """)
        
        # Tolerâncias específicas
        col1, col2 = st.columns(2)
        
        with col1:
            tol_custo = st.slider(
                "Tolerância a desvios de custo (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(project_data.get("Tolerancia_Desvio_Custo", 0.10) * 100),
                step=1.0,
                format="%.1f%%"
            ) / 100.0  # Converter de porcentagem para decimal
            
            st.caption(f"""
            Um valor de {tol_custo:.1%} significa que o projeto pode tolerar um 
            aumento de até R$ {project_data.get('Valor_Total_Estimado', 0) * tol_custo:,.2f} 
            no orçamento total.
            """.replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        with col2:
            tol_prazo = st.slider(
                "Tolerância a desvios de prazo (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(project_data.get("Tolerancia_Desvio_Prazo", 0.15) * 100),
                step=1.0,
                format="%.1f%%"
            ) / 100.0  # Converter de porcentagem para decimal
            
            st.caption(f"""
            Um valor de {tol_prazo:.1%} significa que o projeto pode tolerar um 
            atraso de até {int(project_data.get('Prazo_Total_Dias', 0) * tol_prazo)} dias 
            em relação ao cronograma planejado.
            """)
        
        salvar_risco = st.form_submit_button("Salvar Configurações de Risco")
        
        if salvar_risco:
            # Atualizar apenas os campos de risco no dicionário de projeto
            project_data_updated = st.session_state[STATE_PROJECT_DATA].copy()
            project_data_updated["Apetite_ao_Risco"] = apetite
            project_data_updated["Tolerancia_Desvio_Custo"] = tol_custo
            project_data_updated["Tolerancia_Desvio_Prazo"] = tol_prazo
            
            st.session_state[STATE_PROJECT_DATA] = project_data_updated
            
            # Log da ação
            record_log(user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"), 
                       project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"), 
                       page="Configuracao", action="Salvar Perfil de Risco")
            
            st.success("✅ Perfil de risco configurado com sucesso!")

# Verificação final para confirmar se a configuração está completa
st.markdown("---")
st.subheader("Finalização da Configuração")

# Verificar se os dados mínimos foram preenchidos
user_complete = (st.session_state[STATE_USER_DATA].get("Nome") and st.session_state[STATE_USER_DATA].get("Email"))
project_complete = (st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto") and 
                   st.session_state[STATE_PROJECT_DATA].get("Valor_Total_Estimado", 0) > 0 and 
                   st.session_state[STATE_PROJECT_DATA].get("Prazo_Total_Dias", 0) > 0)

if user_complete and project_complete:
    if st.button("Confirmar e Concluir Configuração"):
        # Definir flag de configuração completa
        st.session_state[STATE_USER_CONFIG_COMPLETED] = True
        
        # Log da ação
        record_log(user_id=st.session_state[STATE_USER_DATA].get("Email", "N/A"), 
                   project_id=st.session_state[STATE_PROJECT_DATA].get("Nome_da_Obra_ou_ID_Projeto", "N/A"), 
                   page="Configuracao", action="Configuração Finalizada")
        
        st.success("✅ Configuração concluída com sucesso! Agora você pode prosseguir para as próximas etapas do processo de gestão de riscos.")
        
        # Link para próxima etapa
        st.page_link("1_Identificacao_e_Cadastro_de_Riscos.py", 
                   label="Prosseguir para Identificação de Riscos", use_container_width=True)
else:
    missing = []
    if not user_complete:
        missing.append("Dados do Usuário (Nome e E-mail)")
    if not project_complete:
        missing.append("Dados do Projeto (Nome, Valor e Prazo)")
    
    st.warning(f"⚠️ Para concluir a configuração, preencha todos os campos obrigatórios: {', '.join(missing)}")

# Adicionar informações contextuais no sidebar para ajudar o usuário
with st.sidebar:
    st.subheader("ℹ️ Sobre a Configuração")
    st.info("""
    Esta etapa é fundamental para personalizar o sistema às suas necessidades específicas.
    
    Os dados aqui fornecidos serão utilizados para:
    
    - Personalizar análises e relatórios
    - Ajustar limiares de alertas de risco
    - Contextualizar recomendações
    - Manter registros organizados
    
    Todas as informações ficam armazenadas apenas na sua sessão atual.
    """)
    
    st.markdown("### Próximos Passos")
    st.markdown("""
    Após concluir a configuração, você deve:
    
    1. **Identificar e cadastrar riscos** potenciais do seu projeto
    2. Realizar **análises qualitativas** desses riscos
    3. Aprofundar com **análises quantitativas**
    4. Desenvolver **planos de resposta** para os riscos prioritários
    5. Implementar um sistema de **monitoramento**
    """) 