import gitlab
import yaml

class GitLabService:
    def __init__(self, gitlab_url, project_id, default_branch='main', private_token=None):
        self.gl = gitlab.Gitlab(url=gitlab_url, private_token=private_token)
        self.project = self.gl.projects.get(project_id)
        self.default_ref = default_branch

    def get_config_as_dict(self, folder_name, file_name='default.yaml', version_tag=None):
        """讀取 YAML 並轉換為 Python Dictionary (用於獲取 metadata 或 targets)"""
        ref_point = version_tag if version_tag else self.default_ref
        file_path = f"{folder_name}/{file_name}"
        
        try:
            f = self.project.files.get(file_path=file_path, ref=ref_point)
            content = f.decode().decode('utf-8')
            config_dict = yaml.safe_load(content)
            
            if not isinstance(config_dict, (dict, list)):
                print(f"警告: 檔案 {file_path} 解析後格式不正確。")
            return config_dict
            
        except (gitlab.exceptions.GitlabGetError, yaml.YAMLError) as e:
            print(f"讀取 {file_path} 失敗: {e}")
            return None

    def get_file_raw_content(self, folder_name, file_name='default.yaml', version_tag=None):
        """取得原始字串，供 Jinja2 渲染使用"""
        ref_point = version_tag if version_tag else self.default_ref
        file_path = f"{folder_name}/{file_name}"
        try:
            f = self.project.files.get(file_path=file_path, ref=ref_point)
            return f.decode().decode('utf-8')
        except Exception:
            return None

    def get_latest_two_tags(self):
        """取得最後兩個 Tag Name"""
        tags = self.project.tags.list(per_page=2)
        if len(tags) < 2:
            raise Exception("需要至少兩個 Tag 才能進行增量比較")
        return tags[0].name, tags[1].name

    def get_all_yaml_paths(self, version_tag=None):
        """遞迴掃描 Repo 內所有 YAML 檔案"""
        ref_point = version_tag if version_tag else self.default_ref
        items = self.project.repository_tree(ref=ref_point, recursive=True, get_all=True)
        return [item['path'] for item in items if item['path'].endswith('.yaml')]

    def get_changed_files(self, new_tag, old_tag):
        """比對差異檔案清單"""
        comparison = self.project.repository_compare(old_tag, new_tag)
        return [diff['new_path'] for diff in comparison['diffs'] if diff['new_path'].endswith('.yaml')]