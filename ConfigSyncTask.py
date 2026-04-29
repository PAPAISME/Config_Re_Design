from pymongo import MongoClient

class ConfigSyncTask:
    def __init__(self, gl_service, processor, mongo_uri):
        self.gl = gl_service
        self.proc = processor
        self.db = MongoClient(mongo_uri)['ConfigDB']
        # 定義基底資料夾
        self.primary_folders = ["DB2_INST_INFO", "DB2_DB_INFO"]

    def _get_global_context(self, target_value, version_tag=None):
        """提取跨檔案變數 (如 inst_name)"""
        context = {}
        for folder in self.primary_folders:
            data = self.gl.get_config_as_dict(folder, version_tag=version_tag)
            if not data: continue
            
            key = self.proc.detect_target_key(data)
            if key:
                # 獲取該 target 的合併配置並併入 context
                final = self.proc.get_final_config(data, key, target_value)
                context.update(final)
        return context

    def sync_file(self, file_path, version_tag=None):
        """同步單一檔案邏輯"""
        # 拆分 folder 和 file
        parts = file_path.split('/')
        folder_name = parts[0]
        file_name = parts[-1]
        
        # 1. 抓取內容
        raw_str = self.gl.get_file_raw_content(folder_name, file_name, version_tag)
        initial_data = self.gl.get_config_as_dict(folder_name, file_name, version_tag)
        if not initial_data: return

        # 2. 偵測 Target Key 與所有 Target Values
        target_key = self.proc.detect_target_key(initial_data)
        if not target_key: return
        
        targets = self.proc.get_all_target_values(initial_data, target_key)

        for t_val in targets:
            # 3. 渲染並產出最終配置
            context = self._get_global_context(t_val, version_tag)
            rendered_data = self.proc.render_and_parse(raw_str, context)
            final_cfg = self.proc.get_final_config(rendered_data, target_key, t_val)

            # 4. 寫入 MongoDB
            if final_cfg:
                self.db[folder_name].update_one(
                    {target_key: t_val},
                    {"$set": final_cfg},
                    upsert=True
                )
                print(f" [Sync OK] {folder_name} -> {t_val}")

    def run_full_sync(self, version_tag=None):
        print(f"執行全量同步...版本: {version_tag if version_tag else 'Default'}")
        paths = self.gl.get_all_yaml_paths(version_tag)
        for p in paths:
            self.sync_file(p, version_tag)

    def run_incremental_sync(self):
        new_tag, old_tag = self.gl.get_latest_two_tags()
        print(f"執行增量同步: {old_tag} -> {new_tag}")
        paths = self.gl.get_changed_files(new_tag, old_tag)
        for p in paths:
            self.sync_file(p, new_tag)