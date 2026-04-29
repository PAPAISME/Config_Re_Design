import os
from pymongo import MongoClient
from ConfigProcessor import ConfigProcessor

class ConfigSyncTask:
    def __init__(self, gl_service, processor, mongo_uri):
        """
        :param gl_service: 負責與 GitLab 溝通的 Service
        :param processor: 負責解析、渲染與合併的 ConfigProcessor
        :param mongo_uri: MongoDB 連線字串
        """
        self.gl = gl_service
        self.proc = processor
        self.db = MongoClient(mongo_uri)['ConfigDB']
        # 定義哪些資料夾提供基礎變數 (如 inst_name)
        self.primary_folders = ["DB2_INST_INFO", "DB2_DB_INFO"]

    def _get_global_context(self, target_value, version_tag=None):
        """
        從 Primary 資料夾中蒐集特定環境的變數，建立渲染上下文。
        此 function 僅在處理 List 型配置時被呼叫。
        """
        context = {}
        for folder in self.primary_folders:
            # 從 GitLab 取得基底檔案內容
            data = self.gl.get_config_as_dict(folder, version_tag=version_tag)
            if not data:
                continue
            
            # 偵測基底檔案的標籤鍵 (例如 function)
            key = self.proc.detect_target_key(data)
            
            # 如果基底檔案是 List 結構，合併出該環境(target_value)的結果作為變數源
            if key and key != ConfigProcessor.IS_COMMON_DICT:
                final = self.proc.get_final_config(data, key, target_value)
                context.update(final)
            # 如果基底檔案本身就是 Dict，則整份直接視為全域變數
            elif key == ConfigProcessor.IS_COMMON_DICT:
                context.update(data)
                
        return context

    def sync_file(self, file_path, version_tag=None):
        """
        同步單一 YAML 檔案至 MongoDB。
        會根據檔案結構 (Dict 或 List) 自動切換同步模式。
        """
        # 解析路徑取得資料夾名稱 (對應 MongoDB Collection)
        folder_name = file_path.split('/')[0]
        
        # 1. 取得 GitLab 原始資料 (Dict 格式用於偵測結構)
        initial_data = self.gl.get_config_as_dict(folder_name, version_tag=version_tag)
        if not initial_data:
            print(f" [Error] 無法讀取檔案內容: {file_path}")
            return

        # 2. 偵測配置結構類型
        detected_key = self.proc.detect_target_key(initial_data)
        if not detected_key:
            print(f" [Skip] 檔案格式無法識別標籤鍵: {file_path}")
            return

        # 3. 根據類型執行分流同步
        if detected_key == ConfigProcessor.IS_COMMON_DICT:
            # --- 情況 A: 通用型配置 (Dict) ---
            # 規則：不執行變數渲染，Collection 內僅存單一 Document
            print(f" [Common Sync] 正在處理通用配置 (單一文件): {folder_name}")
            
            # 清空舊資料並存入新 Dict
            self.db[folder_name].delete_many({}) 
            self.db[folder_name].insert_one(initial_data)
            print(f" [Sync OK] {folder_name} (Common) 已更新")

        else:
            # --- 情況 B: 差異化配置 (List) ---
            # 規則：蒐集變數 -> 渲染渲染 -> 合併區塊 -> 存入多筆文件
            target_key = detected_key
            # 取得該檔案中定義的所有目標環境 (如 ['MM', 'SM'])
            targets = self.proc.get_all_target_values(initial_data, target_key)
            
            # 取得原始字串用於 Jinja2 渲染
            raw_str = self.gl.get_file_raw_content(folder_name, version_tag=version_tag)

            for t_val in targets:
                # A. 建立該環境的變數對照表
                context = self._get_global_context(t_val, version_tag)
                
                # B. 執行變數渲染
                rendered_data = self.proc.render_and_parse(raw_str, context)
                
                # C. 執行繼承合併邏輯 (處理 BASIC 與 多個同標籤區塊的疊加)
                final_cfg = self.proc.get_final_config(rendered_data, target_key, t_val)

                # D. 寫入 MongoDB (根據環境標籤 upsert)
                if final_cfg:
                    self.db[folder_name].update_one(
                        {target_key: t_val},
                        {"$set": final_cfg},
                        upsert=True
                    )
                    print(f" [Sync OK] {folder_name} -> {target_key}: {t_val}")

    def run_full_sync(self, version_tag=None):
        """全量同步入口"""
        paths = self.gl.get_all_yaml_paths(version_tag)
        for p in paths:
            self.sync_file(p, version_tag)

    def run_incremental_sync(self):
        """增量同步入口 (比對 GitLab Tag)"""
        new_tag, old_tag = self.gl.get_latest_two_tags()
        if not new_tag: return
        
        paths = self.gl.get_changed_files(new_tag, old_tag)
        for p in paths:
            self.sync_file(p, new_tag)