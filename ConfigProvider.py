"""Config Provider Service."""

import json


class ConfigProviderService:
    """Config Provider Service."""

    def __init__(self, gl_service):
        self.gl = gl_service

    def get_pipeline(self):
        """從 GitLab Repo 讀取 pipeline_def_metadata.json"""

        file_path = "pipeline_def_metadata.json"

        try:
            # 透過 gl_service 取得檔案內容
            f = self.gl.project.files.get(file_path=file_path, ref=self.gl.default_ref)

            content = f.decode().decode("utf-8")

            return json.loads(content)

        except Exception as e:
            print(f" [Error] 無法讀取 Pipeline 定義檔 {file_path}: {e}")

            # 若讀取失敗，回傳一個空的 Pipeline 或 raise Error 根據你的需求
            return {"stages": []}
