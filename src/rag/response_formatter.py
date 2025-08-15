import re

def add_html_links(answer: str, sources: list) -> str:
    """
    Преобразует ссылки в формате [1] в HTML-теги для Telegram
    
    Args:
        answer: Ответ от LLM с ссылками в формате [1]
        sources: Список URL источников
        
    Returns:
        Текст ответа с HTML-ссылками
    """
    # Создаем маппинг номеров на URL
    source_map = {str(i+1): url for i, url in enumerate(sources)}
    
    # Убираем существующие markdown-ссылки
    answer = re.sub(r'\[(\d+)\]\([^)]*\)', r'[\1]', answer)
    
    # Регулярка для поиска [1], [2] и т.д.
    pattern = r'\[(\d+)\]'
    
    def replace_match(match):
        """Функция замены найденных ссылок"""
        num = match.group(1)
        url = source_map.get(num)
        if url:
            return f'<a href="{url}">[{num}]</a>'
        return match.group(0)
    
    # Заменяем ссылки и форматируем переносы строк
    return re.sub(pattern, replace_match, answer).replace('\n', '<br>')