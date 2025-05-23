# utils/gspread_logger.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials # Ou google.oauth2.service_account para google-auth
# from google.oauth2.service_account import Credentials # Alternativa moderna
import pandas as pd
from datetime import datetime
import streamlit as st # Para st.cache_resource e feedback ao usuário

# Importar configurações
from config import GSHEET_CREDENTIALS_FILE, GSHEET_LOG_SPREADSHEET_NAME, GSHEET_LOG_WORKSHEET_NAME, GSHEET_LOG_COLUMNS

@st.cache_resource(ttl=3600) # Cache do cliente gspread por 1 hora para otimizar e evitar re-autenticações repetidas.
def get_gspread_client():
    """
    Inicializa e retorna o cliente gspread autenticado.
    O cache garante que a conexão não seja restabelecida a cada log, melhorando a performance.
    """
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"] # Escopos necessários
        creds = ServiceAccountCredentials.from_json_keyfile_name(GSHEET_CREDENTIALS_FILE, scope)
        # creds = Credentials.from_service_account_file(GSHEET_CREDENTIALS_FILE, scopes=scope) # Para google-auth
        client = gspread.authorize(creds)
        # Testar a conexão tentando abrir uma planilha (opcional, mas bom para feedback imediato)
        # client.open(GSHEET_LOG_SPREADSHEET_NAME) # Pode gerar erro se não existir, tratar aqui ou em log_event
        return client
    except FileNotFoundError:
        st.error(f"Arquivo de credenciais '{GSHEET_CREDENTIALS_FILE}' não encontrado. Logging desabilitado.")
        return None
    except Exception as e:
        st.error(f"Falha ao conectar com Google Sheets API: {e}. Verifique 'credentials.json', permissões e escopos. Logging desabilitado.")
        return None

def log_event_to_gsheet(event_data: dict):
    """
    Registra um evento em uma nova linha na planilha Google Sheet especificada.
    Fornece feedback ao usuário através de st.warning em caso de falhas comuns.
    Args:
        event_data (dict): Dicionário contendo os dados do evento.
                           Deve incluir chaves correspondentes a GSHEET_LOG_COLUMNS.
    """
    client = get_gspread_client()
    if not client:
        print(f"Cliente Gspread não inicializado. Log não salvo: {event_data.get('Acao_Realizada')}") # Log para console do servidor
        # st.toast("Serviço de log indisponível no momento.", icon="⚠️") # Feedback sutil ao usuário
        return

    try:
        spreadsheet = client.open(GSHEET_LOG_SPREADSHEET_NAME)
        try:
            worksheet = spreadsheet.worksheet(GSHEET_LOG_WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            st.warning(f"Aba/Worksheet '{GSHEET_LOG_WORKSHEET_NAME}' não encontrada na planilha '{GSHEET_LOG_SPREADSHEET_NAME}'. Tentando criar...")
            try:
                worksheet = spreadsheet.add_worksheet(title=GSHEET_LOG_WORKSHEET_NAME, rows="1", cols=str(len(GSHEET_LOG_COLUMNS)))
                worksheet.append_row(GSHEET_LOG_COLUMNS, value_input_option='USER_ENTERED') # Adiciona cabeçalho
                st.info(f"Aba '{GSHEET_LOG_WORKSHEET_NAME}' criada com sucesso.")
            except Exception as create_e:
                st.error(f"Falha ao criar aba '{GSHEET_LOG_WORKSHEET_NAME}': {create_e}")
                return
        
        # Prepara a linha do log garantindo a ordem das colunas e tratando valores ausentes
        log_row = [str(event_data.get(col, "")) for col in GSHEET_LOG_COLUMNS] # Converte tudo para string para gspread
        worksheet.append_row(log_row, value_input_option='USER_ENTERED') # 'USER_ENTERED' interpreta os dados como se o usuário os tivesse digitado.

    except gspread.exceptions.SpreadsheetNotFound:
        st.warning(f"Planilha '{GSHEET_LOG_SPREADSHEET_NAME}' não encontrada. Crie-a e compartilhe com o email da Service Account: {client.auth.service_account_email if hasattr(client, 'auth') and hasattr(client.auth, 'service_account_email') else 'Verifique credentials.json'}. Logging desabilitado.")
    except Exception as e:
        st.warning(f"Erro ao registrar log no Google Sheets: {type(e).__name__} - {e}")
        print(f"Erro ao registrar log no Google Sheets: {type(e).__name__} - {e} | Dados: {event_data}") # Log detalhado para console do servidor

def record_log(user_id: str, project_id: str, page: str, action: str, details: str = ""):
    """
    Função helper para preparar e enviar dados de log.
    Simplifica a chamada da função de log nas diversas páginas da aplicação.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Formato ISO padrão
    event_data = {
        "Timestamp": timestamp,
        "UserID": user_id if user_id else "N/A", # Garante que UserID não seja None
        "ProjectID": project_id if project_id else "N/A", # Garante que ProjectID não seja None
        "Pagina_Acessada": page,
        "Acao_Realizada": action,
        "Detalhes_Adicionais": details
    }
    # Para aplicações Streamlit, chamadas síncronas para logging são geralmente aceitáveis.
    # Em cenários de alta carga ou se a chamada à API do Google for lenta,
    # considerar logging assíncrono ou em background (mais complexo de implementar com Streamlit).
    log_event_to_gsheet(event_data) 