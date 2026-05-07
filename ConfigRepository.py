import time
from typing import Dict, Any
from pymongo.errors import PyMongoError

class ConfigRepository:
    def __init__(self, mongo_uri: str, db_name: str, gitlab_service=None):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.gitlab = gitlab_service
        self.MAX_RETRIES = 3  # 最大重試次數

    def get_full_provision_dict(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        target_func = input_params.get("function", "UNKNOWN")
        result_dict = {target_func: {}}
        
        for coll_name, config in COLLECTION_REGISTRY.items():
            strategy_type = config["strategy"]
            required_keys = QUERY_STRATEGIES[strategy_type]
            query_filter = {key: input_params.get(key) for key in required_keys}
            
            data = None
            success = False
            
            # --- 連續重試邏輯 ---
            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    # 執行查詢
                    data = self.db[coll_name].find_one(query_filter, {"_id": 0})
                    
                    # 只要不噴 Exception，就算查詢成功 (即便 data 為 None 也代表連線正常)
                    success = True
                    break 
                except PyMongoError as e:
                    print(f" [Attempt {attempt}] 存取 MongoDB {coll_name} 失敗: {e}")
                    if attempt < self.MAX_RETRIES:
                        time.sleep(0.5)  # 重試前的短暫緩衝
            
            # --- 判斷是否需要 Fallback ---
            # 觸發條件：連續 3 次 Exception (success=False) 或是 Mongo 連線正常但查無資料 (data=None)
            if not success or data is None:
                if self.gitlab:
                    print(f" [Fallback] MongoDB 連續失敗或查無資料，改由 GitLab 撈取: {coll_name}")
                    try:
                        data = self.gitlab.get_config(coll_name, input_params)
                    except Exception as ge:
                        print(f" [Critical] GitLab 撈取也失敗: {ge}")
                        data = {}
                else:
                    data = {}

            result_dict[target_func][coll_name] = data
            
        return result_dict