import json
import sys
from collections.abc import Mapping

def sort_keys_by_template(data, template):
    if isinstance(template, dict) and isinstance(data, dict):
        sorted_dict = {}
        for key in template:
            if key in data:
                sorted_dict[key] = sort_keys_by_template(data[key], template[key])
        # Add keys not in template at the end
        for key in data:
            if key not in template:
                sorted_dict[key] = sort_keys_by_template(data[key], data[key])
        return sorted_dict
    elif isinstance(template, list) and isinstance(data, list):
        # Try to sort each element by the first template element if possible
        if template:
            return [sort_keys_by_template(item, template[0]) for item in data]
        else:
            return data
    else:
        return data

def main():
    if len(sys.argv) != 4:
        print("Usage: python sort_keys.py <input.json> <template.json> <output.json>")
        sys.exit(1)

    input_file, template_file, output_file = sys.argv[1:4]

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(template_file, 'r', encoding='utf-8') as f:
        template = json.load(f)

    sorted_data = sort_keys_by_template(data, template)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()