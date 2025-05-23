# utils/html_generator.py
import pandas as pd

def dataframe_to_html_custom(df: pd.DataFrame, table_id: str = None, table_classes: str = "minha-tabela-bonita streamlit-table") -> str:
    """
    Converte um DataFrame Pandas em uma string HTML com classes CSS personalizadas e um ID opcional.
    O uso de `escape=False` é crucial para que as classes CSS sejam renderizadas como atributos HTML
    e não como texto literal. `index=False` remove o índice do DataFrame da tabela HTML.
    Args:
        df (pd.DataFrame): O DataFrame a ser convertido.
        table_id (str, optional): Um ID para a tag <table> HTML. Útil para CSS/JS específico se necessário.
        table_classes (str): Classes CSS a serem aplicadas à tag <table>.
    Returns:
        str: A representação HTML do DataFrame, ou uma mensagem se o DataFrame estiver vazio.
    """
    if df is None or df.empty:
        return "<p style='text-align: center; color: #777;'>Não há dados para exibir nesta seção.</p>"
    
    # Garantir que o ID da tabela seja um atributo válido se fornecido
    table_attributes = f'class="{table_classes}"'
    if table_id:
        table_attributes += f' id="{table_id}"'
    
    # A opção `na_rep` substitui valores NaN por uma string (ex: '-' ou 'N/A')
    html_output = df.to_html(escape=False, index=False, justify='center', na_rep='-')
    # Adicionar manualmente os atributos à tag <table> gerada, pois to_html não tem um param direto para todos os atributos
    # Esta é uma forma de garantir que table_id e classes sejam aplicados corretamente.
    if "<table" in html_output:
         html_output = html_output.replace("<table", f"<table {table_attributes}", 1)
    else: # Fallback se a estrutura do to_html mudar
         html_output = f"<table {table_attributes}>{html_output}</table>"


    return html_output

# Exemplo de outra função utilitária que poderia ser adicionada:
def create_summary_card_html(title: str, value: str, icon_class: str = None, card_color_class: str = "bg-light") -> str:
    """
    Gera o HTML para um "card" de resumo simples (requer CSS correspondente).
    Args:
        title (str): O título do card.
        value (str): O valor principal a ser exibido.
        icon_class (str, optional): Classe de um ícone (ex: FontAwesome).
        card_color_class (str, optional): Classe CSS para a cor de fundo do card.
    Returns:
        str: String HTML para o card.
    """
    icon_html = f'<i class="{icon_class} fa-2x"></i>' if icon_class else ""
    return f"""
    <div class="summary-card {card_color_class}">
        {icon_html}
        <div class="card-content">
            <h4>{title}</h4>
            <p class="card-value">{value}</p>
        </div>
    </div>
    """
# O CSS para .summary-card, .card-content, .card-value, .bg-light precisaria ser definido em assets/style.css 