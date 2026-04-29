import copy
import yaml
from jinja2 import Template

class ConfigProcessor:
    _BASE_LABEL = "BASIC"
    _POSSIBLE_KEYS = ["function", "db2_version"]
    
    # 用於識別通用配置的內部標記
    IS_COMMON_DICT = "IS_COMMON_DICT"

    @staticmethod
    def detect_target_key(raw_data):
        """
        優化後的偵測邏輯：
        1. 若為 Dict -> 判定為通用配置 (IS_COMMON_DICT)。
        2. 若為 List -> 只要物件中包含我們定義的候選標籤鍵，就回傳該鍵。
           (不再強迫一定要有 BASIC 才能偵測)
        """
        if isinstance(raw_data, dict):
            return ConfigProcessor.IS_COMMON_DICT
        
        if isinstance(raw_data, list):
            # 遍歷 List 裡的所有物件
            for item in raw_data:
                if not isinstance(item, dict): continue
                # 只要物件裡有任何一個 Key 屬於我們定義的候選鍵
                for possible_key in ConfigProcessor._POSSIBLE_KEYS:
                    if possible_key in item:
                        # 找到了！這份 Config 是以 possible_key (如 function) 作為分類
                        return possible_key
        
        return None

    @staticmethod
    def render_and_parse(raw_yaml_str, context):
        """使用上下文環境執行 Jinja2 渲染並解析"""
        if not raw_yaml_str: return None
        template = Template(raw_yaml_str)
        rendered = template.render(context or {})
        return yaml.safe_load(rendered)

    @staticmethod
    def get_all_target_values(raw_data, target_key):
        """僅針對 List 結構收集標籤 (如 MM, SM)"""
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
        """
        執行合併邏輯。
        若為通用配置 (Dict)，直接回傳，不執行 BASIC 合併。
        """
        if target_key == ConfigProcessor.IS_COMMON_DICT or not isinstance(raw_data, list):
            return raw_data

        # --- 以下為你原本提供的 List 合併邏輯 ---
        base_obj, matched_deltas, base_count = None, [], 0
        for item in raw_data:
            val_list = item.get(target_key, [])
            current_vals = val_list if isinstance(val_list, list) else [val_list]
            if ConfigProcessor._BASE_LABEL in current_vals:
                base_count += 1
                if base_count > 1: raise ValueError("偵測到多個 BASIC")
                base_obj = item
            if target_value in current_vals and ConfigProcessor._BASE_LABEL not in current_vals:
                matched_deltas.append(item)

        if not base_obj and not matched_deltas: return {}
        final_config = copy.deepcopy(base_obj) if base_obj else copy.deepcopy(matched_deltas.pop(0))
        for delta in matched_deltas:
            ConfigProcessor._deep_merge(final_config, delta, target_key)

        final_config[target_key] = target_value
        return final_config

    @staticmethod
    def _deep_merge(base, delta, skip_key):
        for key, value in delta.items():
            if key == skip_key: continue
            if key in base and isinstance(base[key], list) and isinstance(value, list):
                base[key].extend(value)
            elif key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigProcessor._deep_merge(base[key], value, skip_key)
            else:
                base[key] = copy.deepcopy(value)