from GitLabService import GitLabService
from ConfigProcessor import ConfigProcessor
from ConfigSyncTask import ConfigSyncTask

# 1. 初始化各組件
gl_svc = GitLabService(
    url="https://gitlab.com",
    token="YOUR_TOKEN",
    project_id="group/repo"
)
proc = ConfigProcessor()
sync_task = ConfigSyncTask(gl_svc, proc, "mongodb://localhost:27017/")

# 2. 選擇執行模式
# 模式 A: 第一次啟動執行全量同步
sync_task.run_full_sync(tag_name="v1.0.0")

# 模式 B: 後續自動監控執行增量同步
# sync_task.run_incremental_sync()