import re
import yaml
from jinja2 import Template

class ConfigTransformService:
    def __init__(self):
        # 預先編譯正則表達式，提升效能
        self.re_filter = re.compile(r"\$\{(.*?)\}#\.(.*?)\(\)#")
        self.re_basic = re.compile(r"\$\{(.*?)\}")
        self.IS_COMMON_DICT = "common" # 假設這是一個標記非分類配置的常數

    def _translate_syntax(self, template_str):
        """將你的自定義語法轉換為標準 Jinja2 語法"""
        # 1. 處理帶過濾器的語法: ${key}#.func()# -> {{ key | func }}
        t = self.re_filter.sub(r"{{ \1 | \2 }}", template_str)
        # 2. 處理普通語法: ${key} -> {{ key }}
        t = self.re_basic.sub(r"{{ \1 }}", t)
        return t

    def render_and_parse(self, raw_yaml_str, context):
        """核心渲染引擎：翻譯語法 -> Jinja2 渲染 -> YAML 解析"""
        if not raw_yaml_str:
            return None
            
        try:
            jinja_str = self._translate_syntax(raw_yaml_str)
            template = Template(jinja_str)
            rendered_str = template.render(context)
            # 使用 safe_load 確保格式安全性
            return yaml.safe_load(rendered_str)
        except Exception as e:
            print(f" [Render Error] 渲染失敗: {e}")
            raise

    def execute_pipeline(self, gl_service, params, pipeline_def):
        """
        執行 Pipeline：
        1. 依賴驗證 (Validation)
        2. 階段性渲染 (Context Propagation)
        3. 最終結果處理 (Dynamic Key Mapping)
        """
        global_context = params.copy()
        folder_names = gl_service.get_all_folder_names()
        raw_files = {f: gl_service.get_file_raw_content(f, params) for f in folder_names}
        final_results = {}

        for stage in pipeline_def.get('stages', []):
            # 1. 驗證階段：檢查是否缺少依賴
            self._validate_stage(stage, global_context)

            # 2. 處理 context_providers (更新 global_context)
            for provider in stage.get('context_providers', []):
                folder = provider['folder']
                if raw_files.get(folder):
                    data = self.render_and_parse(raw_files[folder], global_context)
                    # 自動將產出的結果併入 global_context
                    for key in stage.get('exports', []):
                        if key in data:
                            global_context[key] = data[key]

            # 3. 處理 render_all (最終輸出階段)
            if stage.get('render_all'):
                for folder, raw in raw_files.items():
                    if not raw: continue
                    rendered = self.render_and_parse(raw, global_context)
                    
                    # 動態取得 target_key (如 function 或 db2_version)
                    target_key = self._detect_target_key(rendered)
                    
                    if target_key and target_key != self.IS_COMMON_DICT:
                        # --- 關鍵優化：動態取值 ---
                        # params.get(target_key) 會自動對應 function 或 db2_version
                        target_val = params.get(target_key)
                        final_results[folder] = self.get_final_config(
                            rendered, target_key, target_val
                        )
                    else:
                        final_results[folder] = rendered
                        
        return final_results

    def _validate_stage(self, stage, context):
        """私有方法：驗證當前環境是否有足夠變數執行此 Stage"""
        required = set(stage.get("requires", []))
        missing = required - set(context.keys())
        if missing:
            raise ValueError(f"Stage '{stage['name']}' 缺少變數: {missing}")

    def _detect_target_key(self, data):
        """根據渲染後的結構偵測分類 Key"""
        if "function" in data: return "function"
        if "db2_version" in data: return "db2_version"
        return self.IS_COMMON_DICT

    def get_final_config(self, rendered, target_key, target_val):
        """邏輯：從渲染結果中取出對應分類的那一筆 Config"""
        # 這裡假設 rendered 是一個字典結構，根據 target_val 過濾
        # 具體邏輯可視你的資料結構調整
        return rendered.get(target_val) or rendered