class DynamicFabResolver:
    def __init__(self, config_repo, gitlab_service=None):
        self.repo = config_repo  # 直接注入你寫好的 ConfigRepository
        self.gitlab = gitlab_service
        self.hardcoded_fallback = {"DEFAULT": "common"}

    def resolve_fab_type(self, fab_name: str) -> str:
        # 1. 直接當作一般 Config 呼叫（自動享有 3 次重試與 GitLab Fallback 的超強保護機制！）
        # 因為是 COMMON 策略，sp_need_input_param 隨便傳或傳空皆可
        result = self.repo.get_full_provision_dict({"function": "SYSTEM"})
        
        # 2. 從回傳的標準結構中挖出大 JSON
        # 結構為: {"SYSTEM": {"Sys_Metadata_Registry": {...}}}
        system_configs = result.get("SYSTEM", {})
        global_metadata = system_configs.get("Sys_Metadata_Registry") or {}
        
        # 3. 取出廠區映射表
        mapping = global_metadata.get("fab_mapping", self.hardcoded_fallback)
        
        if "DEFAULT" not in mapping:
            mapping["DEFAULT"] = "common"
            
        if not fab_name:
            return mapping.get("DEFAULT", "common")
            
        return mapping.get(fab_name.upper(), mapping.get("DEFAULT", "common"))