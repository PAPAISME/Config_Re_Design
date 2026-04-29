import copy
import yaml
from jinja2 import Template

class ConfigProcessor:
    _BASE_LABEL = "BASIC"
    # 自動偵測標籤的候選清單
    _POSSIBLE_KEYS = ["function", "db2_version"]

    @staticmethod
    def detect_target_key(raw_data):
        """自動偵測哪一個 Key 包含了 'BASIC'"""
        if not isinstance(raw_data, list): return None
        for item in raw_data:
            for key in ConfigProcessor._POSSIBLE_KEYS:
                val = item.get(key, [])
                vals = val if isinstance(val, list) else [val]
                if ConfigProcessor._BASE_LABEL in vals:
                    return key
        return None

    @staticmethod
    def render_and_parse(raw_yaml_str, context):
        """執行 Jinja2 渲染並解析為 Dict"""
        if not raw_yaml_str: return None
        template = Template(raw_yaml_str)
        rendered = template.render(context)
        return yaml.safe_load(rendered)

    @staticmethod
    def get_all_target_values(raw_data, target_key):
        """收集所有不含 BASIC 的目標值"""
        targets = set()
        if not isinstance(raw_data, list): return list(targets)
        for item in raw_data:
            val = item.get(target_key, [])
            vals = val if isinstance(val, list) else [val]
            for v in vals:
                if v != ConfigProcessor._BASE_LABEL:
                    targets.add(v)
        return list(targets)

    @staticmethod
    def get_final_config(raw_data, target_key, target_value):
        """執行合併邏輯 (保留你原本的檢查與合併代碼)"""
        if not isinstance(raw_data, list): return raw_data
        if target_key == ConfigProcessor._BASE_LABEL:
            raise ValueError(f"target_key 不可為 {ConfigProcessor._BASE_LABEL}")

        base_obj, matched_deltas, base_count = None, [], 0

        for item in raw_data:
            val_list = item.get(target_key, [])
            current_vals = val_list if isinstance(val_list, list) else [val_list]
            
            if ConfigProcessor._BASE_LABEL in current_vals:
                base_count += 1
                if base_count > 1:
                    raise ValueError(f"偵測到多個 {ConfigProcessor._BASE_LABEL}")
                base_obj = item
            
            if target_value in current_vals and ConfigProcessor._BASE_LABEL not in current_vals:
                matched_deltas.append(item)

        if not base_obj and not matched_deltas: return {}

        final_config = copy.deepcopy(base_obj) if base_obj else copy.deepcopy(matched_deltas.pop(0))
        for delta in matched_deltas:
            ConfigProcessor._deep_merge(final_config, delta, target_key)

        # 確保輸出的標籤一致
        final_config[target_key] = target_value
        return final_config

    @staticmethod
    def _deep_merge(base, delta, skip_key):
        """你提供的原始遞迴合併邏輯"""
        for key, value in delta.items():
            if key == skip_key: continue
            if key in base and isinstance(base[key], list) and isinstance(value, list):
                base[key].extend(value)
            elif key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigProcessor._deep_merge(base[key], value, skip_key)
            else:
                base[key] = copy.deepcopy(value)