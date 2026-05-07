from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
repo = ConfigRepository("mongodb://localhost:27017", "Provision_DB")

class AllConfigsRequest(BaseModel):
    function: str
    db2_version: str
    is_ebo: bool
    gen3_or_gen4: str
    lvs_type: str

@app.post("/get_all_configs")
async def get_all_configs(req: AllConfigsRequest):
    # (i) - (v) 參數轉化邏輯
    sp_need_input_param = {
        "function": req.function,
        "db2_version": req.db2_version,
        "db_main_version": ".".join(req.db2_version.split(".")[0:2]).lower(),
        "is_ebo": req.is_ebo,
        "gen_type": req.gen3_or_gen4,
        "lvs_type": req.lvs_type
    }
    
    return repo.get_full_provision_dict(sp_need_input_param)