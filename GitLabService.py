"""Gitlab Service."""

from typing import List


import gitlab
import yaml


class GitLabService:
    """Gitlab Service."""

    def __init__(
        self, gitlab_url, project_id, default_branch="main", private_token=None
    ):
        self.gl = gitlab.Gitlab(url=gitlab_url, private_token=private_token)
        self.project = self.gl.projects.get(project_id)
        self.reference_point = self.get_latest_tag()
        self.default_ref = default_branch

    def get_config_as_dict(self, folder_name: str, file_name: str = "default.yaml"):
        """讀取 YAML 並轉換為 Python Dictionary (用於獲取 metadata 或 targets)"""

        file_path = f"{folder_name}/{file_name}"

        try:
            f = self.project.files.get(file_path=file_path, ref=self.reference_point)

            content = f.decode().decode("utf-8")

            config_dict = yaml.safe_load(content)

            if not isinstance(config_dict, (dict, list)):
                print(f"警告: 檔案 {file_path} 解析後格式不正確。")

            return config_dict

        except (gitlab.exceptions.GitlabGetError, yaml.YAMLError) as e:
            print(f"讀取 {file_path} 失敗: {e}")

            return None

    def get_file_raw_content(self, folder_name: str, file_name: str = "default.yaml"):
        """取得原始字串，供 Jinja2 渲染使用"""

        file_path = f"{folder_name}/{file_name}"

        try:
            f = self.project.files.get(file_path=file_path, ref=self.reference_point)

            return f.decode().decode("utf-8")

        except Exception:
            return None

    def get_latest_tag(self):
        """取得最後一個 Tag Name"""

        tag_list = self.project.tags.list()

        if len(tag_list) < 1:
            raise Exception("需要至少一個 Tag 才能進行操作")

        return tag_list[0].name

    def get_latest_two_tags(self):
        """取得最後兩個 Tag Name"""

        tag_list = self.project.tags.list()

        if len(tag_list) < 2:
            raise Exception("需要至少兩個 Tag 才能進行增量比較")

        return tag_list[0].name, tag_list[1].name

    def get_metadata(self, file_name: str):
        """取得原始字串，供 Jinja2 渲染使用"""

        file_path = f"METADATA/{file_name}"

        try:
            f = self.project.files.get(file_path=file_path, ref=self.reference_point)

            content = f.decode().decode("utf-8")

            metadata_dict = yaml.safe_load(content)

            if not isinstance(metadata_dict, (dict, list)):
                print(f"警告: 檔案 {file_path} 解析後格式不正確。")

            return metadata_dict

        except (gitlab.exceptions.GitlabGetError, yaml.YAMLError) as e:
            print(f"讀取 {file_path} 失敗: {e}")

            return None

    def get_all_yaml_paths(self, db2_main_version: str):
        """遞迴掃描 Repo 內所有 YAML 檔案"""

        items = self.project.repository_tree(
            ref=self.reference_point, recursive=True, get_all=True
        )

        return [
            item["path"]
            for item in items
            if (item["path"].startswith("DB2_"))
            and (
                (item["path"].endswith("default.yaml"))
                or (item["path"].endswith(f"{db2_main_version}.yaml"))
            )
        ]

    def get_all_config_names(
        self, product_type: str, db2_main_version: str
    ) -> List[str]:
        """動態掃描所有 YAML 檔案，自動列出所有 Config 資料夾，亦即 Config Name."""

        paths = self.get_all_yaml_paths(db2_main_version)
        # 只要資料夾中有 yaml 檔案，就視為一個 Config Folder
        return list(
            {
                path.split("/")[0]
                for path in paths
                if "/" in path and path.startswith(product_type)
            }
        )

    def get_changed_files(self, new_tag, old_tag):
        """比對差異檔案清單"""

        comparison = self.project.repository_compare(old_tag, new_tag)

        return [
            diff["new_path"]
            for diff in comparison["diffs"]
            if diff["new_path"].endswith(".yaml")
        ]
