"""
Скрипт проверки работоспособности системы перед запуском.
Проверяет наличие необходимых файлов, сервисов и корректность настроек.
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_environment():
    """Проверка переменных окружения."""
    required_vars = ["TELEGRAM_TOKEN", "LMSTUDIO_BASE_URL"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("   Создайте файл .env на основе .env.example и заполните необходимые переменные")
        return False
        
    print("✅ Переменные окружения настроены корректно")
    return True

def check_services():
    """Проверка доступности LM Studio."""
    try:
        base_url = os.getenv("LMSTUDIO_BASE_URL")
        if not base_url:
            print("❌ LMSTUDIO_BASE_URL не установлен")
            return False
            
        response = requests.get(f"{base_url}/models", timeout=10)
        
        if response.status_code == 200:
            print("✅ LM Studio доступен")
            return True
        else:
            print(f"❌ LM Studio недоступен (код: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения к LM Studio: {str(e)}")
        print("   Убедитесь, что LM Studio запущен и доступен по указанному URL")
        return False

def check_files():
    """Проверка наличия необходимых файлов."""
    required_files = [
        "sources.txt",
        "src/storage/files/url_mapping.json"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
            
    if missing_files:
        print(f"❌ Отсутствуют необходимые файлы: {', '.join(missing_files)}")
        print("   Запустите run_ingestion.bat для создания недостающих файлов")
        return False
        
    print("✅ Все необходимые файлы присутствуют")
    return True

def check_index():
    """Проверка наличия и валидности векторного индекса."""
    index_path = Path("src/storage/index.faiss")
    meta_path = Path("src/storage/meta.pkl")
    
    if not index_path.exists() or not meta_path.exists():
        print("⚠️  Векторный индекс отсутствует. Запустите run_ingestion.bat")
        return False
        
    # Проверяем размер индекс файла
    if index_path.stat().st_size < 1024:  # Меньше 1KB
        print("❌ Индекс файл слишком мал, возможно он поврежден")
        return False
        
    print("✅ Векторный индекс корректен")
    return True

def main():
    """Основная функция проверки."""
    print("🔍 Запуск проверки системы...\n")
    
    checks = [
        check_environment(),
        check_services(),
        check_files(),
        check_index()
    ]
    
    if all(checks):
        print("\n✅ Все проверки пройдены. Система готова к работе!")
        return True
    else:
        print("\n❌ Обнаружены проблемы в системе. Исправьте их перед запуском.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)