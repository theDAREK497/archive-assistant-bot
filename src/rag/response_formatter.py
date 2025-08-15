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
    # Проверяем наличие ссылок в ответе
    if not re.search(r'\[\d+\]', answer):
        return answer.replace('\n', '<br>')
    
    # Собираем все номера ссылок из ответа
    used_numbers = set(re.findall(r'\[(\d+)\]', answer))
    max_num = max(map(int, used_numbers)) if used_numbers else 0
    
    # Проверяем последовательность (1,2,3 без пропусков)
    if len(used_numbers) > 0 and max_num > len(used_numbers):
        # Если есть пропуски, удаляем все ссылки из ответа
        clean_answer = re.sub(r'\[\d+\]', '', answer)
        return clean_answer.replace('\n', '<br>')
    
    # Создаем маппинг только для использованных номеров
    source_map = {num: sources[int(num)-1] for num in used_numbers 
                  if int(num) <= len(sources)}
    
    # Заменяем ссылки
    pattern = r'\[(\d+)\]'
    def replace_match(match):
        num = match.group(1)
        url = source_map.get(num)
        return f'<a href="{url}">[{num}]</a>' if url else match.group(0)
    
    return re.sub(pattern, replace_match, answer).replace('\n', '<br>')