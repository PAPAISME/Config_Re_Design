# config_registry.py

# 定義 5 種查詢策略的名稱
QUERY_STRATEGIES = {
    "BY_FUNCTION": ["function"],
    "BY_VERSION": ["db2_version"],
    "COMMON": [],
    "COMPOSITE_DB": ["db_main_version", "function", "is_ebo"],
    "COMPOSITE_HW": ["gen_type", "function", "lvs_type"]
}

# 14 個 Collection 與其對應的策略
COLLECTION_REGISTRY = {
    "DB2_ACCOUNT_INFO": {"strategy": "BY_FUNCTION"},
    "DB2_DB_INFO":      {"strategy": "BY_FUNCTION"},
    "DB2_GROUP_INFO":   {"strategy": "BY_FUNCTION"},
    "DB2_INST_INFO":    {"strategy": "BY_FUNCTION"},
    
    "DB2_CLIENT_INFO":   {"strategy": "BY_VERSION"},
    "DB2_SOFTWARE_INFO": {"strategy": "BY_VERSION"},
    
    "DB2_HA_INFO":     {"strategy": "COMMON"},
    "DB2_KDUMP_INFO":  {"strategy": "COMMON"},
    "DB2_TSM_INFO":    {"strategy": "COMMON"},
    
    "DB2_DB2SET_INFO":  {"strategy": "COMPOSITE_DB"},
    "DB2_DBCFG_INFO":   {"strategy": "COMPOSITE_DB"},
    "DB2_DBMCFG_INFO":  {"strategy": "COMPOSITE_DB"},
    
    "DB2_LV_INFO":      {"strategy": "COMPOSITE_HW"},
    "DB2_VG_INFO":      {"strategy": "COMPOSITE_HW"}
}

class ConfigRepository:
    def __init__(self, db_client):
        self.db = db_client.provision_config_db
        self.registry = COLLECTION_REGISTRY
        self.strategies = QUERY_STRATEGIES

    def get_config(self, coll_name, params):
        """統一撈取接口"""
        if coll_name not in self.registry:
            raise ValueError(f"Collection {coll_name} 未在 Registry 定義")
            
        strategy_type = self.registry[coll_name]["strategy"]
        required_keys = self.strategies[strategy_type]
        
        # 1. 自動建構 Query Filter
        query_filter = {key: params.get(key) for key in required_keys}
        
        # 2. 執行 MongoDB 查詢
        coll = self.db[coll_name]
        result = coll.find_one(query_filter)
        
        # 3. Fallback 機制 (這裡實作你的備援邏輯)
        if not result:
            print(f"⚠️ MongoDB 查無資料，嘗試從 GitLab 撈取... [{coll_name}]")
            result = self._fetch_from_gitlab(coll_name, params)
            
        return result

    def _fetch_from_gitlab(self, coll_name, params):
        # 這裡呼叫你原有的 GitLab Service
        # return gitlab_service.get_content(coll_name, params)
        pass