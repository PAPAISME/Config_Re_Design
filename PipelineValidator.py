class PipelineValidator:
    def __init__(self, pipeline_def):
        self.pipeline_def = pipeline_def

    def validate(self, initial_params):
        """
        驗證 Pipeline 的依賴順序是否合法。
        
        Args:
            initial_params (dict): 系統一開始擁有的外部變數 (如 fab_name, db_version)
            
        Returns:
            bool: 如果驗證通過回傳 True
        """
        # 使用 set 儲存當前可用的變數
        available_context = set(initial_params.keys())
        
        stages = self.pipeline_def.get("stages", [])
        
        print(f" [Validator] 開始驗證，初始環境變數: {sorted(list(available_context))}")

        for stage in stages:
            stage_name = stage.get("name", "Unknown")
            requires = set(stage.get("requires", []))
            exports = set(stage.get("exports", []))

            # 核心邏輯：檢查 Stage 所需的變數是否都在目前的 available_context 內
            missing = requires - available_context
            
            if missing:
                raise ValueError(
                    f"Pipeline 驗證失敗！Stage '{stage_name}' 缺少依賴變數: {missing}。 "
                    f"目前可用變數為: {available_context}"
                )
            
            # 更新上下文：將此階段產出的變數加入 context
            available_context.update(exports)
            print(f" [Validator] Stage '{stage_name}' 檢查通過，新增輸出變數: {list(exports)}")
            
        print(" [Validator] 驗證成功！所有 Stage 依賴皆滿足。")
        return True