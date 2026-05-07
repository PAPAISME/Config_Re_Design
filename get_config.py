from typing import Optional

class SingleConfigRequest(BaseModel):
    config_item: str
    all: bool = False
    # 使用一個字典來接收所有可能的 filter 參數，不需要預先定義全部
    query_params: Optional[Dict[str, Any]] = {}

@app.post("/get_config")
async def get_single_config(req: SingleConfigRequest):
    coll_name = req.config_item
    
    if coll_name not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=400, detail="無效的 Config 名稱")

    # 1. 處理 'all' 參數
    if req.all:
        data = list(repo.db[coll_name].find({}, {"_id": 0}))
        return {coll_name: data}

    # 2. 處理特定查詢
    strategy_type = COLLECTION_REGISTRY[coll_name]["strategy"]
    required_keys = QUERY_STRATEGIES[strategy_type]
    
    # 檢查 User 是否提供了該 Strategy 必備的 Key
    query_filter = {}
    for key in required_keys:
        val = req.query_params.get(key)
        if val is None:
            raise HTTPException(
                status_code=400,
                # detail=f"{coll_name} 需要參數: {key}，但你只給了 {list(req.query_params.keys())}"
                detail={
                    "error": "Missing Required Parameter",
                    "config_item": coll_name,
                    "required_fields": required_keys,
                    "strategy": strategy_type
                }
            )
        query_filter[key] = val

    result = repo.db[coll_name].find_one(query_filter, {"_id": 0})
    return {coll_name: result or {}}