# utils/probabilistic_analysis.py
import pandas as pd
import numpy as np
import streamlit as st # Para possível feedback ou configuração via UI no futuro

def run_monte_carlo_simulation(
    base_cost: float,
    base_duration: float,
    risks_df: pd.DataFrame, 
    num_iterations: int = 10000,
    cost_distribution_type: str = 'triangular', # Exemplo de parâmetro para expansão futura
    duration_distribution_type: str = 'triangular' # Exemplo
) -> pd.DataFrame:
    """
    Executa uma simulação de Monte Carlo para estimar as distribuições de probabilidade
    dos custos e prazos totais do projeto. Esta simulação leva em conta a incerteza inerente
    a cada risco (probabilidade de ocorrência e variação do impacto).
    O resultado é uma gama de possíveis custos e prazos finais, permitindo uma análise
    mais realista do que uma estimativa de ponto único. Assume independência entre os riscos para esta versão.

    Args:
        base_cost (float): Custo base determinístico do projeto.
        base_duration (float): Duração base determinística do projeto em dias.
        risks_df (pd.DataFrame): DataFrame com riscos. Colunas essenciais:
                                 'Probabilidade_Num' (float, 0-1),
                                 'Efeito_Custo_Min' (float), 'Efeito_Custo_Max' (float),
                                 'Efeito_Prazo_Min_Dias' (float), 'Efeito_Prazo_Max_Dias' (float),
                                 'Tipo_Risco' (str, 'Ameaça' ou 'Oportunidade').
                                 É crucial que os dados de entrada sejam limpos e validados antes de chamar esta função.
        num_iterations (int): Número de iterações da simulação. Mais iterações levam a resultados mais estáveis.
        cost_distribution_type (str): Tipo de distribuição para impacto de custo (atualmente fixo em triangular).
        duration_distribution_type (str): Tipo de distribuição para impacto de prazo (atualmente fixo em triangular).

    Returns:
        pd.DataFrame: DataFrame com colunas 'Custo_Total_Simulado' e 'Prazo_Total_Simulado'.
                      Cada linha representa o resultado de uma iteração da simulação.
                      Este DataFrame é a base para gerar histogramas, curvas S, e calcular
                      estatísticas como média, mediana, desvio padrão e percentis (P-valores)
                      para as reservas de contingência.
    """
    results_cost = np.zeros(num_iterations) # Usar arrays NumPy para performance
    results_duration = np.zeros(num_iterations)

    # Pré-processamento e validação dos dados de risco
    # É vital garantir que as colunas numéricas realmente contenham números.
    numeric_cols = ['Probabilidade_Num', 'Efeito_Custo_Min', 'Efeito_Custo_Max', 'Efeito_Prazo_Min_Dias', 'Efeito_Prazo_Max_Dias']
    
    # Cria uma cópia para evitar modificar o DataFrame original passado como argumento
    temp_risks_df = risks_df.copy()
    for col in numeric_cols:
        if col in temp_risks_df.columns:
            temp_risks_df[col] = pd.to_numeric(temp_risks_df[col], errors='coerce')
        else:
            # Se uma coluna essencial não existir, a simulação não pode prosseguir corretamente para esses riscos.
            # Considerar logar um aviso ou levantar um erro mais específico.
            # Para este exemplo, riscos sem essas colunas serão filtrados pelo dropna.
            pass 
    
    # Filtra riscos com dados inválidos (NaN) nas colunas numéricas essenciais e cria uma cópia final.
    # Apenas riscos com dados completos e válidos participarão da simulação.
    valid_risks = temp_risks_df.dropna(subset=numeric_cols).copy()

    if valid_risks.empty:
        # Se nenhum risco válido for fornecido, a simulação retorna o cenário base determinístico.
        # Isso evita erros e representa corretamente a situação de "sem riscos considerados".
        results_cost.fill(base_cost)
        results_duration.fill(base_duration)
        return pd.DataFrame({
            'Custo_Total_Simulado': results_cost,
            'Prazo_Total_Simulado': results_duration
        })

    # Extrair arrays NumPy para operações vetorizadas ou loops mais rápidos
    probabilidades = valid_risks['Probabilidade_Num'].values
    custo_min = valid_risks['Efeito_Custo_Min'].values
    custo_max = valid_risks['Efeito_Custo_Max'].values
    prazo_min = valid_risks['Efeito_Prazo_Min_Dias'].values
    prazo_max = valid_risks['Efeito_Prazo_Max_Dias'].values
    tipos_risco = valid_risks['Tipo_Risco'].values
    num_valid_risks = len(valid_risks)

    # Loop principal da simulação
    for i in range(num_iterations):
        current_sim_cost_iteration = base_cost
        current_sim_duration_iteration = base_duration

        # Gerar ocorrências para todos os riscos de uma vez
        ocorrencias = np.random.rand(num_valid_risks) < probabilidades

        for j in range(num_valid_risks):
            if ocorrencias[j]: # Se o risco j ocorreu nesta iteração
                # Amostragem do impacto do custo usando distribuição triangular.
                # O modo é aproximado como a média entre o mínimo e o máximo, uma simplificação comum
                # quando uma estimativa mais precisa do modo não está disponível.
                # A IA pode ser instruída a permitir que o usuário defina o modo se desejado.
                cost_impact = np.random.triangular(
                    left=custo_min[j],
                    mode=(custo_min[j] + custo_max[j]) / 2,
                    right=custo_max[j]
                )
                duration_impact = np.random.triangular(
                    left=prazo_min[j],
                    mode=(prazo_min[j] + prazo_max[j]) / 2,
                    right=prazo_max[j]
                )

                # Aplicação do impacto: Ameaças aumentam custo/prazo, Oportunidades reduzem.
                if tipos_risco[j] == 'Ameaça':
                    current_sim_cost_iteration += cost_impact
                    current_sim_duration_iteration += duration_impact
                elif tipos_risco[j] == 'Oportunidade':
                    current_sim_cost_iteration -= cost_impact
                    current_sim_duration_iteration -= duration_impact
        
        # Armazenar resultados da iteração, garantindo que não sejam negativos.
        # Um custo ou prazo negativo não faz sentido no contexto do projeto.
        results_cost[i] = max(0, current_sim_cost_iteration)
        results_duration[i] = max(0, current_sim_duration_iteration)

    return pd.DataFrame({
        'Custo_Total_Simulado': results_cost,
        'Prazo_Total_Simulado': results_duration
    })

# TODO para a IA (Melhorias e Expansões Potenciais para futuras versões ou se o tempo permitir):
# 1. Flexibilizar Distribuições de Impacto:
#    - Permitir que o usuário, para cada risco, selecione o tipo de distribuição de probabilidade para os impactos
#      (ex: uniforme, triangular com moda explícita, PERT/Beta, log-normal, normal).
#    - Justificativa: Diferentes riscos podem ter diferentes perfis de incerteza. A distribuição triangular é um bom começo,
#      mas outras podem ser mais apropriadas. Por exemplo, a log-normal é frequentemente usada para impactos de custo.
#      Isso aumentaria significativamente o realismo e a flexibilidade da simulação.

# 2. Implementar Cálculo de Valor Monetário Esperado (VME) Detalhado:
#    - Adicionar uma função separada `calculate_vme(risks_df)` que retorna o DataFrame de riscos com uma coluna adicional 'VME_Custo' e 'VME_Prazo'.
#    - O VME seria Probabilidade_Num * Média_Ponderada_Impacto (onde a média pode vir da distribuição escolhida).
#    - Justificativa: O VME é uma métrica chave na análise quantitativa, ajudando a priorizar riscos com base no seu "valor" esperado
#      e a avaliar o custo-benefício das estratégias de resposta. Também é um input para árvores de decisão.

# 3. Desenvolver Análise de Sensibilidade Robusta:
#    - Implementar a geração de Gráficos de Tornado ou Spider Plots para visualizar quais riscos individuais
#      têm a maior influência (sensibilidade) nas variações totais de custo e prazo do projeto.
#    - Isso pode ser feito correlacionando a ocorrência/impacto de cada risco com o resultado total da simulação.
#    - Justificativa: Permite focar os esforços de gerenciamento e mitigação nos riscos que realmente "movem a agulha",
#      otimizando a alocação de recursos para o tratamento de riscos.

# 4. Explorar Modelos Preditivos Adicionais (Consideração para Expansão Avançada):
#    - Regressão Linear: Se houvesse dados históricos de projetos e seus riscos/impactos, poderia-se tentar modelar
#      a relação entre características de riscos (ou do projeto) e seus impactos finais.
#    - Árvores de Decisão: Útil para modelar cenários com múltiplos estágios de decisão e incertezas, onde
#      o VME de diferentes caminhos pode ser comparado. Requer uma estruturação de dados e interface mais complexa.
#    - Justificativa: Adicionaria capacidades preditivas e de suporte à decisão mais sofisticadas, mas aumenta
#      a complexidade da aplicação. O foco principal desta versão deve ser um Monte Carlo sólido e compreensível. 