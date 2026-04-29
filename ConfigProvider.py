class ConfigProvider:
    def __init__(self, gl_service, processor, mongo_uri):
        self.gl = gl_service
        self.proc = processor
        self.db = MongoClient(mongo_uri)['ConfigDB']
        # 緩存基底資訊，避免每次 Fallback 都要去爬 GitLab
        self._context_cache = {} 

    def get_config(self, folder_name, target_value, target_key="function", force_remote=False):
        """
        統一獲取入口
        :param force_remote: 是否強制跳過 MongoDB 直接從 GitLab 讀取並渲染
        """
        # 1. 嘗試從 MongoDB 獲取
        if not force_remote:
            try:
                cached_cfg = self.db[folder_name].find_one({target_key: target_value})
                if cached_cfg:
                    print(f" [Cache Hit] 從 MongoDB 取得 {folder_name}/{target_value}")
                    return cached_cfg
            except Exception as e:
                print(f" [Cache Miss] MongoDB 存取失敗: {e}，準備切換至即時渲染...")

        # 2. Fallback: 從 GitLab 拿資料並現場「加工」
        return self._render_from_source(folder_name, target_value, target_key)

    def _render_from_source(self, folder_name, target_value, target_key):
        """
        即時渲染邏輯：GitLab 原料 -> Processor 加工 -> 回傳
        """
        print(f" [Live Render] 正在從 GitLab 即時產出 {folder_name} (Target: {target_value})...")
        
        # A. 取得原始內容
        raw_str = self.gl.get_file_raw_content(folder_name, 'default.yaml')
        if not raw_str:
            return None

        # B. 建立渲染上下文 (Context)
        # 注意：這裡會呼叫之前寫的 _get_global_context 邏輯
        context = self._get_live_context(target_value, target_key)
        
        # C. 渲染與合併
        rendered_data = self.proc.render_and_parse(raw_str, context)
        final_cfg = self.proc.get_final_config(rendered_data, target_key, target_value)
        
        return final_cfg

    def _get_live_context(self, target_value, target_key):
        """
        即時獲取基礎變數 (如 inst_name)
        """
        # 為了效能，這裡可以加上簡單的 Memory Cache
        cache_key = f"{target_key}_{target_value}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        context = {}
        # 這裡寫死基底資料夾，或是從設定讀取
        primary_folders = ["DB2_INST_INFO", "DB2_DB_INFO"]
        for folder in primary_folders:
            # 直接去 GitLab 拿基底 Raw Data
            data = self.gl.get_config_as_dict(folder, 'default.yaml')
            if data:
                # 合併出該 target 的配置
                final = self.proc.get_final_config(data, target_key, target_value)
                context.update(final)
        
        self._context_cache[cache_key] = context
        return context