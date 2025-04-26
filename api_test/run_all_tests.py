import os
import json
import subprocess
from datetime import datetime

# Скрипты для тестирования
test_scripts = [
    "test_tinkoff.py",
    "test_yahoo.py",
    "test_moex.py",
    "test_alpha_vantage.py",
    "test_finnhub.py",
    "test_rbc.py",
    "test_investing.py"
]

results = {}
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Запуск каждого скрипта и сохранение результатов
for script in test_scripts:
    print(f"Running {script}...")
    api_name = script.replace("test_", "").replace(".py", "")
    try:
        output = subprocess.check_output(
            ["python", script], 
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        ).strip()
        
        # Пытаемся распарсить JSON если результат в формате JSON
        try:
            data = json.loads(output)
            results[api_name] = {
                "status": "success",
                "data": data
            }
        except json.JSONDecodeError:
            # Если не JSON, сохраняем как есть
            results[api_name] = {
                "status": "error" if "error" in output.lower() or "not found" in output.lower() else "success",
                "data": output
            }
    except subprocess.CalledProcessError as e:
        results[api_name] = {
            "status": "error",
            "error": e.output
        }

# Добавляем метаданные
results["_meta"] = {
    "timestamp": timestamp,
    "ticker": "OZON"
}

# Сохраняем результаты в JSON
output_file = "api_test_results.json"
with open(output_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"Results saved to {output_file}") 