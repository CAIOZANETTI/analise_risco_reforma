import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Importar configurações do módulo config.py
from config import (STATE_RISKS_DF, RISKS_DF_EXPECTED_COLUMNS, 
                   STATE_USER_CONFIG_COMPLETED, STATE_USER_DATA, STATE_PROJECT_DATA,
                   STATE_SIMULATION_RESULTS_DF)

# Verificar e criar diretórios necessários
os.makedirs('data', exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('assets', exist_ok=True)

# Função para inicializar o session_state
def initialize_session_state():
    """
    Inicializa todas as variáveis de estado necessárias no st.session_state.
    Esta função é crucial para garantir que não ocorram KeyError ao acessar 
    o state e para que os valores padrão sejam consistentes.
    """
    if STATE_USER_CONFIG_COMPLETED not in st.session_state:
        st.session_state[STATE_USER_CONFIG_COMPLETED] = False
        
    if STATE_USER_DATA not in st.session_state:
        st.session_state[STATE_USER_DATA] = {
            "Nome": "",
            "Email": "",
            "Empresa": "",
            "Cargo": "",
            "Telefone": ""
        }
        
    if STATE_PROJECT_DATA not in st.session_state:
        st.session_state[STATE_PROJECT_DATA] = {
            "Nome_da_Obra_ou_ID_Projeto": "",
            "Descricao_Projeto": "",
            "Tipo_Construcao": "",
            "Proposito_Principal": "",
            "UF": "",
            "Cidade": "",
            "Area_Construida_m2": 0.0,
            "Valor_Total_Estimado": 0.0,
            "Prazo_Total_Dias": 0,
            "Data_Inicio": None,
            "Data_Prevista_Fim": None,
            "Nivel_Complexidade": "Médio",
            "Apetite_ao_Risco": "Moderado",
            "Tolerancia_Desvio_Custo": 0.10, # 10% padrão
            "Tolerancia_Desvio_Prazo": 0.15, # 15% padrão
            "Data_Cadastro": datetime.now().strftime("%Y-%m-%d")
        }
        
    if STATE_RISKS_DF not in st.session_state:
        # Inicializa com um DataFrame vazio mas com todas as colunas corretas
        st.session_state[STATE_RISKS_DF] = pd.DataFrame(columns=RISKS_DF_EXPECTED_COLUMNS)
        
    if STATE_SIMULATION_RESULTS_DF not in st.session_state:
        st.session_state[STATE_SIMULATION_RESULTS_DF] = pd.DataFrame(columns=['Custo_Total_Simulado', 'Prazo_Total_Simulado'])

# Chamar inicialização do estado da sessão
initialize_session_state()

# Configurar a página do Streamlit
st.set_page_config(
    page_title="Análise de Risco em Reformas",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título e introdução
st.title("📊 Sistema Avançado de Análise e Gestão de Riscos em Obras de Reforma")

# Verificar se as configurações de usuário/projeto já foram preenchidas
if not st.session_state[STATE_USER_CONFIG_COMPLETED]:
    st.warning("⚠️ Por favor, preencha suas informações e os detalhes do projeto na página de Configuração antes de prosseguir.")
    # Link para página de configuração
    st.page_link("pages/0_Configuracao_Usuario_e_Projeto.py", label="Ir para Configuração")
else:
    # Mostrar resumo do projeto quando configurado
    projeto = st.session_state[STATE_PROJECT_DATA]
    usuario = st.session_state[STATE_USER_DATA]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 Projeto: " + projeto["Nome_da_Obra_ou_ID_Projeto"])
        st.markdown(f"**Descrição:** {projeto['Descricao_Projeto']}")
        st.markdown(f"**Localização:** {projeto['Cidade']}/{projeto['UF']}")
        st.markdown(f"**Área:** {projeto['Area_Construida_m2']} m²")
    with col2:
        st.subheader("💰 Valores Estimados:")
        st.metric(label="Orçamento", value=f"R$ {projeto['Valor_Total_Estimado']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        st.metric(label="Prazo", value=f"{projeto['Prazo_Total_Dias']} dias")
        st.markdown(f"**Usuário:** {usuario['Nome']} ({usuario['Cargo']})")

# Diagrama de fluxo do processo de gestão de riscos usando Mermaid
st.subheader("Fluxo do Processo de Gestão de Riscos")

mermaid_code = """
graph TD
    A[1. Identificação de Riscos] -->|Cadastro de riscos e oportunidades| B[2. Análise Qualitativa]
    B -->|Avaliação subjetiva de probabilidade e impacto| C[3. Análise Quantitativa]
    C -->|Simulação Monte Carlo| D[4. Planejamento de Respostas]
    D -->|Definição de estratégias e ações| E[5. Monitoramento]
    E -->|Acompanhamento contínuo| A
    style A fill:#f9c74f,stroke:#f8961e,stroke-width:2px
    style B fill:#90be6d,stroke:#43aa8b,stroke-width:2px
    style C fill:#577590,stroke:#277da1,stroke-width:2px,color:white
    style D fill:#f94144,stroke:#f3722c,stroke-width:2px
    style E fill:#f8961e,stroke:#f9844a,stroke-width:2px
"""

st.markdown(f"""
```mermaid
{mermaid_code}
```
""")

# Navegação rápida para as páginas
st.subheader("Acesso Rápido às Páginas")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.page_link("pages/0_Configuracao_Usuario_e_Projeto.py", 
               label="⚙️ Configuração",
               help="Cadastre seus dados e as informações do projeto")
with col2:
    st.page_link("pages/1_Identificacao_e_Cadastro_de_Riscos.py", 
               label="🔍 Identificação", 
               help="Identifique e cadastre os riscos do seu projeto")
with col3:
    st.page_link("pages/2_Analise_Qualitativa_de_Riscos.py", 
               label="📊 Análise Qualitativa",
               help="Avalie a probabilidade e o impacto dos riscos")
with col4:
    st.page_link("pages/3_Analise_Quantitativa_e_Probabilistica.py", 
               label="📈 Análise Quantitativa",
               help="Realize simulações e análises numéricas dos riscos")
with col5:
    st.page_link("pages/4_Planejamento_de_Respostas_aos_Riscos.py", 
               label="📝 Plano de Respostas",
               help="Planeje como responder aos riscos identificados")

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p style='color: gray; font-size: small'>
            Sistema Avançado de Análise e Gestão de Riscos em Reformas • Streamlit App • v9.0
        </p>
    </div>
    """,
    unsafe_allow_html=True
) 