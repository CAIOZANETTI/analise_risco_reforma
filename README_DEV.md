# README para Desenvolvedores - Sistema de Análise de Risco em Reformas (Streamlit App)

Este documento contém informações técnicas e orientações para desenvolvedores que desejam manter, modificar ou expandir o Sistema de Análise de Risco em Reformas.

## Arquitetura do Projeto

O aplicativo segue uma arquitetura modular, orientada a funções específicas e serviços. Os principais componentes são:

- **Interface do usuário**: Implementada com Streamlit, composta por várias páginas que guiam o usuário através do processo de gestão de riscos.
- **Módulos de utilidades**: Funções reutilizáveis para análises de probabilidade, geração de HTML e logging.
- **Configuração centralizada**: Constantes e parâmetros centralizados para fácil manutenção.
- **Armazenamento de dados**: Utilização do `st.session_state` para persistência durante a sessão, com opção de exportação/importação via CSV.

## Configuração do Projeto

* **Constantes e Configurações (`config.py`):** Todas as constantes globais, nomes de arquivos (prefixados com `data/` quando aplicável), chaves do `st.session_state` e configurações (como nomes de planilhas Google e opções de selectbox) estão centralizadas em `config.py`. Este é o primeiro lugar para verificar ou modificar parâmetros da aplicação. Importe-as conforme necessário (ex: `from config import RISCOS_COMUNS_CSV, STATE_RISKS_DF`).

* **Credenciais do Google Sheets (`credentials.json`):** Essencial para o módulo `utils/gspread_logger.py`. Siga as instruções do Google Cloud para criar um Service Account, baixar o arquivo JSON de credenciais, renomeá-lo para `credentials.json` e colocá-lo na raiz do projeto. **Este arquivo NUNCA deve ser commitado no Git (adicione-o ao `.gitignore`)**. Certifique-se de que o nome da planilha e da aba no Google Sheets correspondem ao definido em `config.py` e que a Service Account tem permissões de edição na planilha.

## Estrutura do Código e Contribuições

* **Modularidade e `utils/`:**
    * **`utils/gspread_logger.py`:** Encapsula toda a lógica de logging para o Google Sheets. Utiliza `@st.cache_resource` para o cliente `gspread`, otimizando a conexão. A função `record_log` é o ponto de entrada principal para registrar eventos.
    * **`utils/html_generator.py`**: Contém funções para converter DataFrames Pandas em strings HTML formatadas para relatórios, como `dataframe_to_html_custom()`. Permite a aplicação de classes CSS para estilização centralizada.
    * **`utils/probabilistic_analysis.py`**: Abriga a lógica para análises probabilísticas, com foco principal na simulação de Monte Carlo (`run_monte_carlo_simulation()`). Projetado para ser expansível com outras técnicas analíticas.
    * **Importação:** Importar funções destes módulos usando caminhos relativos (ex: `from utils.gspread_logger import record_log`).

* **Estado da Sessão (`st.session_state`):**
    * **Inicialização Explícita e Estruturada:** Todas as chaves do `st.session_state` (idealmente definidas como constantes em `config.py`) DEVEM ser inicializadas com valores padrão apropriados em `app.py` antes de qualquer outro processamento ou navegação para as `pages`. Isso é crítico para evitar `KeyError` e para que o estado da aplicação seja previsível e testável. Exemplo em `app.py`:
      ```python
      import streamlit as st
      import pandas as pd
      from config import (STATE_RISKS_DF, RISKS_DF_EXPECTED_COLUMNS, 
                          STATE_USER_CONFIG_COMPLETED, STATE_USER_DATA, STATE_PROJECT_DATA,
                          STATE_SIMULATION_RESULTS_DF)

      # Função para inicializar o estado da sessão
      def initialize_session_state():
          if STATE_USER_CONFIG_COMPLETED not in st.session_state:
              st.session_state[STATE_USER_CONFIG_COMPLETED] = False
          if STATE_USER_DATA not in st.session_state:
              st.session_state[STATE_USER_DATA] = {} # ou None
          if STATE_PROJECT_DATA not in st.session_state:
              st.session_state[STATE_PROJECT_DATA] = {} # ou None
          if STATE_RISKS_DF not in st.session_state:
              st.session_state[STATE_RISKS_DF] = pd.DataFrame(columns=RISKS_DF_EXPECTED_COLUMNS)
          if STATE_SIMULATION_RESULTS_DF not in st.session_state:
              st.session_state[STATE_SIMULATION_RESULTS_DF] = pd.DataFrame()
          # Adicionar outras inicializações necessárias
      
      initialize_session_state() # Chamar no início de app.py
      ```

* **Cache do Streamlit (`@st.cache_data`, `@st.cache_resource`):**
    * **`@st.cache_data`:** Use para funções que carregam e retornam dados que são "imutáveis" ou não mudam durante a sessão (ex: carregar CSVs de `data/`, cálculos puros sobre dados imutáveis). O Streamlit faz hash dos inputs da função para decidir se reutiliza o resultado cacheado.
      ```python
      from config import TIPOS_CONSTRUCOES_CSV
      @st.cache_data # Cacheia o DataFrame retornado
      def load_construction_types():
          # Adicionar tratamento de erro FileNotFoundError aqui
          return pd.read_csv(TIPOS_CONSTRUCOES_CSV)
      ```
    * **`@st.cache_resource`:** Use para inicializar e cachear "recursos" que são caros de criar e que devem persistir durante a sessão (ex: conexões de banco de dados, clientes de API como `gspread_client` em `gspread_logger.py`). O recurso é configurado uma vez e reutilizado.

* **Validação de Dados:** Implementar validações robustas para todas as entradas do usuário (formulários, `st.data_editor`) **antes** de salvar no `st.session_state` ou usar em cálculos. Isso inclui:
    * Verificação de campos obrigatórios.
    * Verificação de tipo de dados (ex: números onde esperado).
    * Verificação de intervalo (ex: probabilidade entre 0 e 1, valores monetários não negativos).
    * Formato (ex: email, datas).
    * Exibir mensagens de erro claras e específicas usando `st.error()` próximo ao campo problemático.

## Solução de Problemas Comuns

### Erros no Google Sheets Logger

Se ocorrerem erros ao usar o módulo de logging para Google Sheets:

1. Verifique se o arquivo `credentials.json` está presente na raiz do projeto.
2. Confirme que a Service Account tem permissões de edição na planilha especificada.
3. Verifique se os escopos necessários estão configurados corretamente na criação do cliente gspread.

### Problemas com st.session_state

Se ocorrerem `KeyError` ao acessar o `st.session_state`:

1. Certifique-se de que todas as chaves usadas são inicializadas em `app.py`.
2. Sempre verifique a existência da chave antes de acessá-la: `if STATE_KEY in st.session_state and st.session_state[STATE_KEY] is not None`.
3. Use constantes de `config.py` ao invés de strings literais para as chaves do `st.session_state`.

### Problemas de Performance

Se o aplicativo estiver lento:

1. Certifique-se de utilizar `st.cache_data` e `st.cache_resource` apropriadamente.
2. Evite recalcular valores que podem ser reutilizados.
3. Na simulação de Monte Carlo, considere reduzir o número de iterações para testes.
4. Use operações vetorizadas do Pandas/NumPy sempre que possível ao invés de loops em Python.

## Guia de Instalação para Desenvolvimento

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/analise_risco_reforma_avancada_app.git
   cd analise_risco_reforma_avancada_app
   ```

2. Crie um ambiente virtual Python e ative-o:
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Execute o aplicativo:
   ```bash
   streamlit run app.py
   ```

## Estrutura de Arquivos Detalhada

```
analise_risco_reforma_avancada_app/
│
├── app.py                              # Ponto de entrada principal e inicialização do estado
├── README.md                           # Documentação para usuários finais
├── README_DEV.md                       # Esta documentação técnica
├── requirements.txt                    # Dependências do projeto
├── .gitignore                          # Arquivos a serem ignorados pelo Git
├── config.py                           # Configurações e constantes centralizadas
│
├── data/                               # Dados de exemplo e arquivos CSV
│   ├── riscos_comuns.csv               # Template de riscos comuns para carregar
│   └── tipos_construcoes.csv           # Categorias e propósitos de construção
│
├── utils/                              # Módulos de utilidades
│   ├── __init__.py                     # Torna utils um pacote Python
│   ├── html_generator.py               # Funções para geração de relatórios HTML
│   ├── probabilistic_analysis.py       # Funções para análises probabilísticas (Monte Carlo)
│   └── gspread_logger.py               # Funções para logging no Google Sheets
│
├── pages/                              # Páginas do Streamlit
│   ├── 0_Configuracao_Usuario_e_Projeto.py
│   ├── 1_Identificacao_e_Cadastro_de_Riscos.py
│   ├── 2_Analise_Qualitativa_de_Riscos.py
│   ├── 3_Analise_Quantitativa_e_Probabilistica.py
│   ├── 4_Planejamento_de_Respostas_aos_Riscos.py
│   └── 5_Monitoramento_e_Relatorios_de_Riscos.py
│
├── templates/                          # Templates para relatórios HTML
│   └── relatorio_risco_template.html
│
├── assets/                             # Arquivos estáticos
│   └── style.css                       # Estilos personalizados
│
└── credentials.json                    # Credenciais do Google Sheets API (não comitar!)
```

## Diretrizes de UI e UX

* **Consistência Visual:** Manter layout e estilo consistentes entre páginas, incluindo uso de cores, fontes e espaçamentos.
* **Feedback ao Usuário:** Fornecer mensagens claras de sucesso, erro ou aviso. Usar `st.success()`, `st.error()` e `st.warning()`.
* **Validação Proativa:** Validar dados de entrada antes que o usuário prossiga para evitar problemas futuros.
* **Tooltips Informativos:** Usar o parâmetro `help` nos widgets do Streamlit para fornecer informações adicionais.
* **Design Responsivo:** Aproveitar `st.columns()` para layouts que se adaptam bem em diferentes tamanhos de tela.

## Contribuindo com o Projeto

Ao contribuir para este projeto:

1. Mantenha a modularidade e a separação de responsabilidades.
2. Documente novas funções e módulos com docstrings claros.
3. Siga o padrão de estilo de código existente (PEP 8).
4. Valide entradas e trate exceções apropriadamente.
5. Atualize os READMEs caso adicione novos recursos ou altere comportamentos existentes. 