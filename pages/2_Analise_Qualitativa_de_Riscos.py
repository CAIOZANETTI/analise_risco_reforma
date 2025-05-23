import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Importar configurações
from config import (
    STATE_RISKS_DF, STATE_USER_DATA, STATE_PROJECT_DATA, STATE_USER_CONFIG_COMPLETED,
    PROBABILIDADE_OPTIONS, IMPACTO_OPTIONS
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
st.title("📊 Análise Qualitativa de Riscos")

# Informações sobre a etapa
st.info("""
A análise qualitativa é uma avaliação subjetiva da probabilidade e impacto de cada risco, 
para priorização e foco nos mais significativos. Aqui você classificará cada risco de acordo 
com a probabilidade de ocorrência e seu impacto potencial em diferentes objetivos do projeto.
""")

# Função para converter escalas qualitativas em numéricas
def qualitative_to_numeric(value, options):
    """Converte uma escala qualitativa em valor numérico (0-1)"""
    if pd.isna(value) or value == "":
        return 0.0
    try:
        # Índice na lista / (tamanho - 1) para normalizar entre 0 e 1
        return options.index(value) / (len(options) - 1)
    except (ValueError, IndexError):
        return 0.0

# Função para calcular score de risco
def calculate_risk_score(prob, impact_cost, impact_schedule, impact_quality, urgency=None):
    """
    Calcula um score composto de risco com base em:
    - Probabilidade
    - Impacto em custo
    - Impacto em prazo
    - Impacto em qualidade
    - Urgência (opcional, peso menor)
    """
    # Converter de string para valor numérico (0-1)
    p = qualitative_to_numeric(prob, PROBABILIDADE_OPTIONS)
    ic = qualitative_to_numeric(impact_cost, IMPACTO_OPTIONS)
    is_ = qualitative_to_numeric(impact_schedule, IMPACTO_OPTIONS)
    iq = qualitative_to_numeric(impact_quality, IMPACTO_OPTIONS)
    
    # Calcular a média dos impactos
    avg_impact = (ic + is_ + iq) / 3
    
    # Score base: probabilidade * impacto médio
    score = p * avg_impact * 100  # Multiplicar por 100 para escala mais intuitiva (0-100)
    
    # Adicionar influência da urgência, se fornecida
    if urgency and urgency in PROBABILIDADE_OPTIONS:
        u = qualitative_to_numeric(urgency, PROBABILIDADE_OPTIONS)
        # Urgência tem peso menor (20% da pontuação final)
        score = score * 0.8 + u * 20  
    
    return round(score, 1)  # Arredondar para 1 casa decimal

# Função para criar matriz de calor para visualização
def create_heatmap_matrix():
    """Cria a matriz de calor para visualização"""
    # Criar grade para matriz
    x = list(range(len(IMPACTO_OPTIONS)))
    y = list(range(len(PROBABILIDADE_OPTIONS)))
    
    # Calcular valores Z (scores)
    z = []
    for i in range(len(PROBABILIDADE_OPTIONS)):
        row = []
        for j in range(len(IMPACTO_OPTIONS)):
            # Probabilidade * impacto normalizado
            prob_value = i / (len(PROBABILIDADE_OPTIONS) - 1)
            impact_value = j / (len(IMPACTO_OPTIONS) - 1)
            score = prob_value * impact_value * 100
            row.append(score)
        z.append(row)
    
    # Criar heatmap
    colorscale = [
        [0, "green"],
        [0.3, "yellow"],
        [0.6, "orange"],
        [1, "red"]
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=IMPACTO_OPTIONS,
        y=PROBABILIDADE_OPTIONS,
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(title="Score de Risco"),
        text=[[f"Score: {round(val, 1)}" for val in row] for row in z],
        hovertemplate="Probabilidade: %{y}<br>Impacto: %{x}<br>%{text}<extra></extra>"
    ))
    
    fig.update_layout(
        title="Matriz de Probabilidade x Impacto",
        xaxis_title="Impacto",
        yaxis_title="Probabilidade",
        height=500,
        yaxis=dict(autorange="reversed"),  # Inverte o eixo y para ter "Muito Alta" no topo
    )
    
    return fig

# Layout principal
st.subheader("Análise Qualitativa dos Riscos Identificados")

# Carregar riscos existentes
df_risks = st.session_state[STATE_RISKS_DF].copy()

# Explicação das escalas
with st.expander("Escalas de Avaliação", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Escala de Probabilidade")
        prob_df = pd.DataFrame({
            "Nível": PROBABILIDADE_OPTIONS,
            "Descrição": [
                "Evento extremamente raro (<10%)",
                "Evento improvável (10-30%)",
                "Evento possível (30-50%)",
                "Evento provável (50-70%)",
                "Evento muito provável (>70%)"
            ]
        })
        st.table(prob_df)
    
    with col2:
        st.markdown("### Escala de Impacto")
        impact_df = pd.DataFrame({
            "Nível": IMPACTO_OPTIONS,
            "Descrição": [
                "Efeito mínimo, sem impacto significativo",
                "Efeito pequeno, impacto administrável",
                "Efeito moderado, ajustes necessários",
                "Efeito significativo, objetivos comprometidos",
                "Efeito severo, falha em objetivos centrais"
            ]
        })
        st.table(impact_df)

# Tabela editável para análise qualitativa
st.write("Classifique cada risco de acordo com as escalas definidas:")

# Configurar colunas para visualização e edição
cols_to_show = [
    "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Categoria_Risco", 
    "Probabilidade_Qualitativa", "Impacto_Custo_Qualitativo", 
    "Impacto_Prazo_Qualitativo", "Impacto_Qualidade_Qualitativo", 
    "Urgencia_Risco", "Score_Risco"
]

# Garantir que todas as colunas existam
for col in cols_to_show:
    if col not in df_risks.columns:
        df_risks[col] = ""

# Configuração das colunas para o editor
column_config = {
    "ID_Risco": st.column_config.TextColumn("ID", width="small", disabled=True),
    "Descricao_Risco": st.column_config.TextColumn("Descrição", width="large", disabled=True),
    "Tipo_Risco": st.column_config.TextColumn("Tipo", width="small", disabled=True),
    "Categoria_Risco": st.column_config.TextColumn("Categoria", width="small", disabled=True),
    "Probabilidade_Qualitativa": st.column_config.SelectboxColumn(
        "Probabilidade", options=PROBABILIDADE_OPTIONS, width="medium",
        help="Classificação da probabilidade de ocorrência do risco"),
    "Impacto_Custo_Qualitativo": st.column_config.SelectboxColumn(
        "Impacto (Custo)", options=IMPACTO_OPTIONS, width="medium",
        help="Classificação do impacto no custo"),
    "Impacto_Prazo_Qualitativo": st.column_config.SelectboxColumn(
        "Impacto (Prazo)", options=IMPACTO_OPTIONS, width="medium",
        help="Classificação do impacto no prazo"),
    "Impacto_Qualidade_Qualitativo": st.column_config.SelectboxColumn(
        "Impacto (Qualidade)", options=IMPACTO_OPTIONS, width="medium",
        help="Classificação do impacto na qualidade"),
    "Urgencia_Risco": st.column_config.SelectboxColumn(
        "Urgência", options=PROBABILIDADE_OPTIONS, width="medium",
        help="Quão urgente é responder a este risco"),
    "Score_Risco": st.column_config.NumberColumn(
        "Score", format="%.1f", width="small", disabled=True,
        help="Pontuação calculada de acordo com a probabilidade e impacto")
}

# Mostrar o editor de dados
edited_df = st.data_editor(
    df_risks[cols_to_show],
    column_config=column_config,
    use_container_width=True,
    key="qualitative_analysis_editor",
    hide_index=True
)

# Botão para calcular scores de risco
if st.button("Calcular Scores de Risco", use_container_width=True):
    # Calcular scores para todos os riscos
    for idx, row in edited_df.iterrows():
        edited_df.at[idx, "Score_Risco"] = calculate_risk_score(
            row["Probabilidade_Qualitativa"],
            row["Impacto_Custo_Qualitativo"],
            row["Impacto_Prazo_Qualitativo"],
            row["Impacto_Qualidade_Qualitativo"],
            row["Urgencia_Risco"]
        )
        
        # Calcular probabilidade numérica (0-1) para uso na análise quantitativa
        edited_df.at[idx, "Probabilidade_Num"] = qualitative_to_numeric(
            row["Probabilidade_Qualitativa"], PROBABILIDADE_OPTIONS
        )
    
    st.success("✅ Scores de risco calculados com sucesso!")
    st.experimental_rerun()  # Para atualizar o data_editor com os novos scores

# Botão para salvar análise qualitativa
if st.button("💾 Salvar Análise Qualitativa", use_container_width=True):
    # Verificar se todas as linhas têm as classificações necessárias
    missing_analysis = edited_df[
        (edited_df["Probabilidade_Qualitativa"].isna()) | 
        (edited_df["Probabilidade_Qualitativa"] == "") |
        (edited_df["Impacto_Custo_Qualitativo"].isna()) | 
        (edited_df["Impacto_Custo_Qualitativo"] == "") |
        (edited_df["Impacto_Prazo_Qualitativo"].isna()) |
        (edited_df["Impacto_Prazo_Qualitativo"] == "")
    ]
    
    if not missing_analysis.empty:
        st.warning(f"⚠️ {len(missing_analysis)} riscos estão com análise incompleta. Por favor, preencha todas as classificações.")
    
    # Atualizar o DataFrame principal preservando outras colunas
    original_df = st.session_state[STATE_RISKS_DF].copy()
    
    # Para cada coluna em edited_df, atualizar o valor correspondente no DataFrame original
    for col in cols_to_show:
        if col in edited_df.columns:
            # Usando o ID_Risco como chave para mapear as linhas
            for idx, row in edited_df.iterrows():
                risk_id = row["ID_Risco"]
                mask = original_df["ID_Risco"] == risk_id
                if any(mask):  # Se o risco existe no DataFrame original
                    original_df.loc[mask, col] = row[col]
    
    # Salvar de volta ao session_state
    st.session_state[STATE_RISKS_DF] = original_df
    
    # Log da ação
    record_log(
        user_id=st.session_state[STATE_USER_DATA].get('Email'),
        project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
        page="Analise_Qualitativa",
        action="Salvar Analise Qualitativa",
        details=f"Analisados {len(edited_df)} riscos"
    )
    
    st.success("✅ Análise qualitativa salva com sucesso!")

# Visualização da matriz de Probabilidade x Impacto
st.subheader("Matriz de Probabilidade x Impacto")
st.plotly_chart(create_heatmap_matrix(), use_container_width=True)

# Se houver scores calculados, mostrar gráfico de barras com os riscos mais críticos
if not edited_df[edited_df["Score_Risco"] > 0].empty:
    st.subheader("Top Riscos por Score")
    
    # Ordenar por Score_Risco e obter os 10 principais
    top_risks = edited_df.sort_values(by="Score_Risco", ascending=False).head(10)
    
    # Criar gráfico de barras para os top riscos
    fig = go.Figure()
    
    # Adicionar barras separadas para ameaças e oportunidades com cores diferentes
    threats = top_risks[top_risks["Tipo_Risco"] == "Ameaça"]
    opportunities = top_risks[top_risks["Tipo_Risco"] == "Oportunidade"]
    
    if not threats.empty:
        fig.add_trace(go.Bar(
            x=threats["Score_Risco"],
            y=threats["ID_Risco"] + " - " + threats["Descricao_Risco"].str[:50],
            orientation='h',
            name='Ameaças',
            marker_color='red',
            hovertemplate="%{y}<br>Score: %{x}<extra></extra>"
        ))
    
    if not opportunities.empty:
        fig.add_trace(go.Bar(
            x=opportunities["Score_Risco"],
            y=opportunities["ID_Risco"] + " - " + opportunities["Descricao_Risco"].str[:50],
            orientation='h',
            name='Oportunidades',
            marker_color='green',
            hovertemplate="%{y}<br>Score: %{x}<extra></extra>"
        ))
    
    fig.update_layout(
        title="Top Riscos por Score",
        xaxis_title="Score de Risco",
        yaxis=dict(autorange="reversed"),  # Para ter o maior score no topo
        height=400 + len(top_risks) * 25,  # Altura dinâmica baseada no número de riscos
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Botão para exportar análise qualitativa para CSV
if st.button("📥 Exportar Análise Qualitativa para CSV", help="Baixe a análise em formato CSV"):
    csv = edited_df.to_csv(index=False)
    
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"analise_qualitativa_{st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto', 'projeto')}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="download_qual_analysis_csv"
    )
    
    # Log da ação
    record_log(
        user_id=st.session_state[STATE_USER_DATA].get('Email'),
        project_id=st.session_state[STATE_PROJECT_DATA].get('Nome_da_Obra_ou_ID_Projeto'),
        page="Analise_Qualitativa",
        action="Exportar Analise CSV",
        details=f"Exportados {len(edited_df)} riscos analisados"
    )

# Rodapé com instruções
st.divider()
st.caption("""
**Próximos passos:** Após classificar qualitativamente seus riscos, você pode avançar para a 
"Análise Quantitativa e Probabilística" para aprofundar a análise numérica dos riscos mais críticos.
""") 