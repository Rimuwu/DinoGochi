import json
import os
import sys
from typing import Dict, Any, List, Optional

class JsonInspector:
    """
    Скилл для оптимизации работы с тяжелыми JSON файлами (локализации, конфиги предметов).
    Предотвращает выедание токенов при чтении файлов целиком.
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    def _resolve_path(self, relative_path: str) -> str:
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(self.workspace_root, relative_path.lstrip("/"))

    def _get_nested_dict(self, data: Any, dot_path: str) -> tuple[Optional[Any], Optional[str]]:
        """
        Traverses data using dot_path. If not found and data has a single language-like root key,
        automatically tries to traverse under that root key.
        Returns (parent_dict, last_key) if successful, otherwise (None, None).
        """
        if not dot_path:
            return data, None
            
        parts = dot_path.split(".")
        
        # Try direct path
        curr = data
        for part in parts[:-1]:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                curr = None
                break
                
        if curr is not None and isinstance(curr, dict) and parts[-1] in curr:
            return curr, parts[-1]
            
        # Try path under single root key (e.g. "ru" or "en")
        if isinstance(data, dict) and len(data) == 1:
            root_key = list(data.keys())[0]
            curr = data[root_key]
            for part in parts[:-1]:
                if isinstance(curr, dict) and part in curr:
                    curr = curr[part]
                else:
                    curr = None
                    break
            if curr is not None and isinstance(curr, dict) and parts[-1] in curr:
                return curr, parts[-1]
                
        return None, None

    def get_json_keys(self, file_path: str, dot_path: Optional[str] = None) -> List[str]:
        """
        Возвращает список доступных ключей на определенном уровне JSON (через dot-notation).
        Позволяет агенту понять структуру без чтения контента.
        """
        full_path = self._resolve_path(file_path)
        if not os.path.exists(full_path):
            return []
            
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not dot_path:
            if isinstance(data, dict):
                return list(data.keys())
            return []
            
        # Try smart resolving
        parent, key = self._get_nested_dict(data, dot_path)
        if parent is not None and key is not None:
            target = parent[key]
            if isinstance(target, dict):
                return list(target.keys())
            elif isinstance(target, list):
                return [str(i) for i in range(len(target))]
                
        # Fallback to literal traversal
        curr = data
        for part in dot_path.split("."):
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            elif isinstance(curr, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
                else:
                    return []
            else:
                return []
                
        if isinstance(curr, dict):
            return list(curr.keys())
        elif isinstance(curr, list):
            return [str(i) for i in range(len(curr))]
        return []

    def get_json_value(self, file_path: str, dot_path: str) -> Any:
        """
        Точечно достает значение по пути (например, "combat_properties.names.stun_strike").
        """
        full_path = self._resolve_path(file_path)
        if not os.path.exists(full_path):
            return None
            
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Try smart resolving first
        parent, key = self._get_nested_dict(data, dot_path)
        if parent is not None and key is not None:
            return parent[key]
            
        # Literal fallback traversal
        curr = data
        for part in dot_path.split("."):
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            elif isinstance(curr, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
                else:
                    return f"Index '{part}' out of range"
            else:
                return f"Key '{dot_path}' not found"
                
        return curr

    def sync_localization_keys(self, base_file: str, target_files: List[str], section_path: str):
        """
        Автоматически проверяет и синхронизирует структуру конкретной секции 
        между базовой локализацией (ru) и остальными (en, es, id).
        """
        full_base_path = self._resolve_path(base_file)
        if not os.path.exists(full_base_path):
            print(f"Error: Base file {base_file} not found.")
            return
            
        with open(full_base_path, "r", encoding="utf-8") as f:
            base_data = json.load(f)
            
        # Smart resolve base section
        parent, key = self._get_nested_dict(base_data, section_path)
        if parent is not None and key is not None:
            base_section = parent[key]
        else:
            # Fallback to direct path
            base_section = base_data
            for part in section_path.split("."):
                if isinstance(base_section, dict) and part in base_section:
                    base_section = base_section[part]
                else:
                    print(f"Error: Section path '{section_path}' not found in base file.")
                    return
                    
        if not isinstance(base_section, dict):
            print(f"Error: Base section at '{section_path}' is not a dictionary.")
            return

        for target_rel in target_files:
            full_target_path = self._resolve_path(target_rel)
            if not os.path.exists(full_target_path):
                print(f"Warning: Target file {target_rel} not found. Skipping.")
                continue
                
            with open(full_target_path, "r", encoding="utf-8") as f:
                target_data = json.load(f)
                
            # Smart resolve target parent and last key. If it doesn't exist, create it.
            # First, check if target has a single root key (like "en")
            target_root_key = None
            if isinstance(target_data, dict) and len(target_data) == 1:
                target_root_key = list(target_data.keys())[0]
                
            parts = section_path.split(".")
            curr = target_data
            
            # If path doesn't start with the root key but the file has a root key, prepend it
            if target_root_key and parts[0] != target_root_key:
                # Check if user passed section_path containing the base root key, e.g. "ru.items_names".
                # If so, replace it with target root key
                base_root_key = list(base_data.keys())[0] if isinstance(base_data, dict) and len(base_data) == 1 else None
                if base_root_key and parts[0] == base_root_key:
                    parts[0] = target_root_key
                else:
                    parts.insert(0, target_root_key)
                    
            # Navigate/create path
            for part in parts[:-1]:
                if not isinstance(curr, dict):
                    break
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
                
            if not isinstance(curr, dict):
                print(f"Warning: Could not resolve/create parent section for '{section_path}' in {target_rel}.")
                continue
                
            last_key = parts[-1]
            if last_key not in curr:
                curr[last_key] = {}
            target_section = curr[last_key]
            
            if not isinstance(target_section, dict):
                print(f"Warning: Section '{section_path}' in {target_rel} is not a dictionary.")
                continue

            # Merge/Sync keys recursively
            def merge_dicts(base_dict, target_dict):
                updated = False
                for k, v in base_dict.items():
                    if k not in target_dict:
                        # Copy from base
                        target_dict[k] = v
                        updated = True
                    elif isinstance(v, dict) and isinstance(target_dict[k], dict):
                        if merge_dicts(v, target_dict[k]):
                            updated = True
                return updated

            if merge_dicts(base_section, target_section):
                with open(full_target_path, "w", encoding="utf-8") as f:
                    json.dump(target_data, f, ensure_ascii=False, indent=4)
                print(f"Synced keys in {target_rel} at {section_path}")
            else:
                print(f"No missing keys in {target_rel} at {section_path}")

def main():
    import argparse
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="JSON Inspector and Syncer CLI")
    parser.add_argument("--action", choices=["get_keys", "get_value", "sync"], required=True)
    parser.add_argument("--file", help="Path to JSON file relative to workspace root")
    parser.add_argument("--dot-path", help="Dot-notation path to get keys or value")
    parser.add_argument("--base-file", help="Base file for sync action")
    parser.add_argument("--target-files", help="Comma-separated paths to target files for sync action")
    parser.add_argument("--section-path", help="Section path for sync action")
    
    args = parser.parse_args()
    
    workspace_root = os.getcwd()
    inspector = JsonInspector(workspace_root)
    
    if args.action == "get_keys":
        if not args.file:
            print("Error: --file is required for action get_keys.")
            sys.exit(1)
        keys = inspector.get_json_keys(args.file, args.dot_path if args.dot_path else None)
        print(json.dumps(keys, ensure_ascii=False, indent=2))
        
    elif args.action == "get_value":
        if not args.file or not args.dot_path:
            print("Error: --file and --dot-path are required for action get_value.")
            sys.exit(1)
        val = inspector.get_json_value(args.file, args.dot_path)
        print(json.dumps(val, ensure_ascii=False, indent=2))
        
    elif args.action == "sync":
        if not args.base_file or not args.target_files or not args.section_path:
            print("Error: --base-file, --target-files, and --section-path are required for action sync.")
            sys.exit(1)
        targets = [t.strip() for t in args.target_files.split(",")]
        inspector.sync_localization_keys(args.base_file, targets, args.section_path)

if __name__ == "__main__":
    main()
