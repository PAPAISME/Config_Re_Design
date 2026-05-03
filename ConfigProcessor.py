"""Config Transform Service."""

import copy
import yaml
from jinja2 import Template


class ConfigTransformService:
    """Config Transform Service."""

    _BASE_LABEL = "BASIC"
    _POSSIBLE_KEYS = ["function", "db2_version"]
    IS_COMMON_DICT = "IS_COMMON_DICT"

    # --- 1. 原有核心合併與渲染邏輯 ---
    @staticmethod
    def detect_target_key(raw_data):
        """
        優化後的偵測邏輯：
        1. 若為 Dict -> 判定為通用配置 (IS_COMMON_DICT)。
        2. 若為 List -> 只要物件中包含我們定義的候選標籤鍵，就回傳該鍵。
           (不再強迫一定要有 BASIC 才能偵測)
        """

        if isinstance(raw_data, dict):
            return ConfigTransformService.IS_COMMON_DICT

        if isinstance(raw_data, list):
            for item in raw_data:
                if not isinstance(item, dict):
                    continue

                for p_key in ConfigTransformService._POSSIBLE_KEYS:
                    if p_key in item:
                        return p_key
        return None

    @staticmethod
    def render_and_parse(raw_yaml_str, context):
        """使用上下文環境執行 Jinja2 渲染並解析"""

        if not raw_yaml_str:
            return None

        template = Template(raw_yaml_str)

        return yaml.safe_load(template.render(context or {}))

    @staticmethod
    def get_all_target_values(raw_data, target_key):
        """僅針對 List 結構收集標籤 (如 MM, SM)"""

        targets = set()

        if not isinstance(raw_data, list):
            return list(targets)

        for item in raw_data:
            val = item.get(target_key, [])

            vals = val if isinstance(val, list) else [val]

            for v in vals:
                if v != ConfigTransformService._BASE_LABEL:
                    targets.add(v)

        return list(targets)

    @staticmethod
    def get_final_config(raw_data, target_key, target_value):
        """
        執行合併邏輯。
        若為通用配置 (Dict)，直接回傳，不執行 BASIC 合併。
        """

        if target_key == ConfigTransformService.IS_COMMON_DICT or not isinstance(
            raw_data, list
        ):
            return raw_data

        base_obj, matched_deltas, base_count = None, [], 0

        for item in raw_data:
            val_list = item.get(target_key, [])

            current_vals = val_list if isinstance(val_list, list) else [val_list]

            if ConfigTransformService._BASE_LABEL in current_vals:
                base_count += 1

                if base_count > 1:
                    raise ValueError("偵測到多個 BASIC")

                base_obj = item

            if (
                target_value in current_vals
                and ConfigTransformService._BASE_LABEL not in current_vals
            ):
                matched_deltas.append(item)

        if not base_obj and not matched_deltas:
            return {}

        final_config = (
            copy.deepcopy(base_obj)
            if base_obj
            else copy.deepcopy(matched_deltas.pop(0))
        )

        for delta in matched_deltas:
            ConfigTransformService._deep_merge(final_config, delta, target_key)

        final_config[target_key] = target_value

        return final_config

    @staticmethod
    def _deep_merge(base, delta, skip_key):
        for key, value in delta.items():
            if key == skip_key:
                continue

            if key in base and isinstance(base[key], list) and isinstance(value, list):
                base[key].extend(value)
            elif (
                key in base and isinstance(base[key], dict) and isinstance(value, dict)
            ):
                ConfigTransformService._deep_merge(base[key], value, skip_key)
            else:
                base[key] = copy.deepcopy(value)

    # --- 2. 新增的 Pipeline 執行器 ---
    def execute_pipeline(self, gitlab_service, params):
        """Execute pipeline."""

        global_context = params.copy()

        print(f"Initial global_context: {global_context}")
        print()

        # 取得 metadata
        pipeline_def = gitlab_service.get_metadata("pipeline_definition.json")

        print(f"pipeline_def: {pipeline_def}")
        print()

        all_yaml_paths = gitlab_service.get_all_yaml_paths(params["db2_main_version"])

        raw_files = {
            path.split("/")[0]: gitlab_service.get_file_raw_content(
                path.split("/")[0], path.split("/")[1]
            )
            for path in all_yaml_paths
        }

        # print(f"raw_files: {raw_files}")

        for stage in pipeline_def["stages"]:
            for provider in stage.get("context_providers", []):
                folder = provider["folder"]

                if raw_files.get(folder):
                    data = self.render_and_parse(raw_files[folder], global_context)

                    print(f"Rendered data for folder '{folder}': {data}")
                    print()

                    for key in provider.get("export_keys", []):
                        if key in data:
                            global_context[key] = data[key]

                    print(
                        f"Updated global_context after processing folder '{folder}': {global_context}"
                    )
                    print()

            if stage.get("render_all"):
                final_results = {}

                for folder, raw in raw_files.items():
                    if not raw:
                        continue

                    rendered = self.render_and_parse(raw, global_context)

                    target_key = self.detect_target_key(rendered)

                    if target_key and target_key != self.IS_COMMON_DICT:
                        # --- 這裡直接動態取值 ---
                        # 如果 target_key 是 "function"，就會取 params["function"]
                        # 如果 target_key 是 "db2_version"，就會取 params["db2_version"]
                        target_val = params.get(target_key)

                        final_results[folder] = self.get_final_config(
                            rendered, target_key, target_val
                        )
                    else:
                        final_results[folder] = rendered

                return final_results
