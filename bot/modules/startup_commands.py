import os
import subprocess
import json
from bot.config import conf
from bot.modules.logs import log

def run_startup_commands():
    # Автоматический запуск команды, если задан флаг use_command
    if getattr(conf, 'use_command', False) and getattr(conf, 'command', ''):
        command_str = conf.command.strip()
        
        # Проверяем, запускалась ли уже эта команда успешно
        state_file_path = os.path.join('.state-save', 'executed_command.json')
        already_run = False
        if os.path.exists(state_file_path):
            try:
                with open(state_file_path, 'r', encoding='utf-8') as sf:
                    state_data = json.load(sf)
                    if state_data.get('command') == command_str and state_data.get('success') is True:
                        already_run = True
            except Exception:
                pass

        if not already_run:
            log(f"Обнаружен флаг use_command=True. Запуск команды: {command_str}")
            try:
                res = subprocess.run(command_str, shell=True)
                if res.returncode == 0:
                    log(f"[OK] Команда '{command_str}' выполнена успешно.")
                    
                    # Пытаемся сбросить флаг в config.json
                    try:
                        with open('config.json', 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        config_data['use_command'] = False
                        with open('config.json', 'w', encoding='utf-8') as f:
                            json.dump(config_data, f, ensure_ascii=False, indent=4)
                        log("Флаг use_command успешно сброшен на False в config.json.")
                    except OSError as config_err:
                        log(f"Предупреждение: Не удалось перезаписать config.json ({config_err}). Используем сохранение состояния в volume.")
                    
                    # Сохраняем состояние выполнения (только при успехе) в доступный для записи volume
                    try:
                        os.makedirs('.state-save', exist_ok=True)
                        with open(state_file_path, 'w', encoding='utf-8') as sf:
                            json.dump({'command': command_str, 'success': True}, sf, ensure_ascii=False, indent=4)
                        log("Состояние выполнения сохранено в .state-save/executed_command.json")
                    except Exception as sf_err:
                        log(f"Не удалось записать файл состояния: {sf_err}", prefix='Error', lvl=4)
                else:
                    log(f"[Error] Команда '{command_str}' завершилась с кодом {res.returncode}.", prefix='Error', lvl=4)
                    
            except Exception as err:
                log(f"Ошибка при автоматическом выполнении команды: {err}", prefix='Error', lvl=4)
        else:
            log(f"Команда '{command_str}' уже была выполнена ранее (пропуск).")
