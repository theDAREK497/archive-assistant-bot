@echo off
echo Запуск тестов...

python -m pytest tests/test_basic.py -v

if %errorlevel% equ 0 (
    echo ✅ Все тесты прошли успешно
) else (
    echo ❌ Обнаружены failed тесты
)

pause