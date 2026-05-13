# 初始化解析器（丟入你的 Mongo DB 與 GitLab Service）
fab_resolver = DynamicFabResolver(mongo_db_client=repo.db, gitlab_service=your_gitlab_service)

@app.post("/get_all_configs")
async def get_all_configs(req: AllConfigsRequest):
    
    # 👈 核心行：動態去對應的優先級中抓取廠區分類
    fab_type = fab_resolver.resolve_fab_type(req.fab_name)
    
    sp_need_input_param = {
        "function": req.function,
        "db2_version": req.db2_version,
        "db_main_version": ".".join(req.db2_version.split(".")[0:2]).lower(),
        "fab_type": fab_type,  # 這裡會拿到 "ebo"、"jp"、"eu" 或 "common"
        "gen_type": req.gen3_or_gen4,
        "lvs_type": req.lvs_type
    }
    
    # 送入功能一的核心 14 次撈取引擎
    return repo.get_full_provision_dict(sp_need_input_param)