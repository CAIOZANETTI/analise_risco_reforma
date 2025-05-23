# config.py

# Nomes de Arquivos de Dados (usar constantes evita erros de digitação e facilita refatoração)
RISCOS_COMUNS_CSV = "data/riscos_comuns.csv"
TIPOS_CONSTRUCOES_CSV = "data/tipos_construcoes.csv"

# Configurações do Google Sheets (para gspread_logger.py)
GSHEET_CREDENTIALS_FILE = "credentials.json"
GSHEET_LOG_SPREADSHEET_NAME = "Logs_App_Analise_Risco_Reforma" # Usuário pode precisar criar/compartilhar
GSHEET_LOG_WORKSHEET_NAME = "Eventos" # Nome da aba/planilha específica para os logs
GSHEET_LOG_COLUMNS = ["Timestamp", "UserID", "ProjectID", "Pagina_Acessada", "Acao_Realizada", "Detalhes_Adicionais"] # Garante ordem e consistência dos logs

# Chaves do st.session_state (para consistência e evitar erros de digitação ao acessar o estado)
STATE_USER_DATA = "user_data"
STATE_PROJECT_DATA = "project_data"
STATE_USER_CONFIG_COMPLETED = "user_config_completed" # Flag para controlar o fluxo inicial
STATE_RISKS_DF = "risks_df" # DataFrame principal com todos os dados de riscos
# Adicionar outras chaves conforme necessário para dados de análise, simulação, etc.
STATE_SIMULATION_RESULTS_DF = "simulation_results_df"

# Colunas Esperadas no DataFrame de Riscos (RISKS_DF_EXPECTED_COLUMNS)
# Definir esta lista é crucial para:
# 1. Inicializar o DataFrame de riscos com a estrutura correta em st.session_state.
# 2. Validar DataFrames carregados de CSVs ou após edições.
# 3. Garantir que todos os módulos que consomem este DataFrame esperem as mesmas colunas.
RISKS_DF_EXPECTED_COLUMNS = [
    "ID_Risco", "Descricao_Risco", "Tipo_Risco", "Categoria_Risco", "Subcategoria_Risco",
    "Efeito_Custo_Min", "Efeito_Custo_Max", "Efeito_Prazo_Min_Dias", "Efeito_Prazo_Max_Dias",
    "Gatilhos_Risco", "Possiveis_Causas_Raiz", "Probabilidade_Qualitativa", "Impacto_Custo_Qualitativo",
    "Impacto_Prazo_Qualitativo", "Impacto_Qualidade_Qualitativo", "Urgencia_Risco",
    "Probabilidade_Num", "Score_Risco", "VME_Custo", "Estrategia_Resposta", "Descricao_Acao_Resposta",
    "Proprietario_do_Risco", "Prazo_Implementacao_Resposta", "Custo_Estimado_Resposta",
    "Plano_de_Contingencia", "Riscos_Secundarios_Identificados", "Status_Acao_Resposta", "Status_Risco",
    "Observacoes_Monitoramento" # Adicionando um campo que faltava para o monitoramento
]

# Opções para Selectboxes (Exemplos)
# Para listas muito extensas ou que mudam com frequência, considerar carregá-las de CSVs dedicados em data/
UF_OPTIONS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
PROBABILIDADE_OPTIONS = ["Muito Baixa", "Baixa", "Média", "Alta", "Muito Alta"] # Usado em st.column_config
IMPACTO_OPTIONS = ["Insignificante", "Baixo", "Médio", "Alto", "Crítico"] # Usado em st.column_config
TIPO_RISCO_OPTIONS = ["Ameaça", "Oportunidade"]
CATEGORIA_RISCO_OPTIONS = ["Técnico", "Externo", "Gerencial", "Financeiro", "Ambiental", "Regulatório", "Segurança", "Recursos Humanos", "Fornecedor", "Mercado"] # Expandido
ESTRATEGIA_RESPOSTA_AMEACA_OPTIONS = ["Eliminar", "Mitigar", "Transferir", "Aceitar", "Escalar"]
ESTRATEGIA_RESPOSTA_OPORTUNIDADE_OPTIONS = ["Explorar", "Melhorar/Potencializar", "Compartilhar", "Aceitar"]
STATUS_ACAO_OPTIONS = ["Não Iniciada", "Em Andamento", "Concluída", "Cancelada", "Bloqueada"]
STATUS_RISCO_OPTIONS = ["Ativo", "Ocorreu", "Não Ocorreu/Fechado", "Novo Gatilho Identificado", "Monitorando"]
SIMULATION_ITERATIONS_DEFAULT = 10000 