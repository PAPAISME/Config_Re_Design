"""Config Sync Service."""

from pymongo import MongoClient

from config_provider_service import ConfigProviderService


class ConfigSyncService:
    """Config Sync Service."""

    def __init__(self, gl_service, transformer, mongo_uri):
        self.gl = gl_service
        self.transformer = transformer
        self.db = MongoClient(mongo_uri)["ConfigDB"]
        # 初始化 Provider 時傳入 gl_service
        self.provider = ConfigProviderService(gl_service)

    def run_full_sync(self, vg_variant="gen4_cat", db_version="v11.5"):
        """Run full sync."""

        # 1. 獲取定義檔
        pipeline = self.provider.get_pipeline()
        
        # 2. 執行飛行前檢查 (Static Analysis)
        initial_params = {"function": "TEST", "vg_variant": vg_variant, "db_version": db_version}
        validator = PipelineValidator(pipeline)
        try:
            validator.validate(initial_params)
        except ValueError as e:
            print(f" [Critical Error] Pipeline 驗證失敗: {e}")
            return # 直接中止，不執行 sync

        # 3. 檢查通過，開始真正的同步
        # 從 GitLab 讀取完整的 Pipeline 定義 (含 stages 與 functions 列表)
        pipeline = self.provider.get_pipeline()
        functions = pipeline.get("target_functions", [])

        for func in functions:
            params = {
                "function": func,
                "vg_variant": vg_variant,
                "db_version": db_version,
            }

            final_configs = self.transformer.execute_pipeline(self.gl, params, pipeline)

            # 存入 MongoDB
            doc = {
                "metadata": {
                    "function": func,
                    "vg_variant": vg_variant,
                    "db_version": db_version,
                },
                "configs": final_configs,
            }

            self.db.Provision_Config.update_one(
                {"metadata": doc["metadata"]}, {"$set": doc}, upsert=True
            )

            print(f" [Sync OK] Function: {func} saved.")
