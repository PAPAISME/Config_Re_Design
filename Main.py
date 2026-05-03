"""Main Function."""

from config_provider_service import ConfigProviderService
from config_sync_service import ConfigSyncService
from config_transform_service import ConfigTransformService
from gitlab_service import GitLabService
from typing import Any, Dict, List


def main():
    """Main function."""

    input_params = {
        "fab_name": "F21",
        "giga_name": "G1",
        "phase_name": "P2",
        "Build_Type": "New-Build",
        "db2_version": "v11.5.9.0_SB30641",
        "product_type": "DB2",
        "product_list": "MM,SPC,SPC1,SPC2",
        "apply_owner": "MAZHUANG",
    }

    # 初始化 GitLab Service
    gitlab_service = GitLabService(
        gitlab_url="https://gitlab.com",
        project_id="81840258",
        private_token="glpat-eaTtsi-m97cjmVxoV4SUcWM6MQpvOjEKdTptanJmMA8.01.170hr6mj2",
    )

    product_list: List[str] = input_params["product_list"].split(",")

    product_list = ["MM"]

    basic_context: Dict[str, str] = {
        "fab_name": input_params["fab_name"],
        "giga_name": input_params["giga_name"],
        "phase_name": input_params["phase_name"],
        "phase_number": input_params["phase_name"][1:],
        "db2_version": input_params["db2_version"],
        "product_type": input_params["product_type"],
        "apply_owner": input_params["apply_owner"],
    }

    db2_main_version: str = ".".join(input_params["db2_version"].split(".")[0:2])

    print(f"db2_main_version: {db2_main_version}")

    basic_context["db2_main_version"] = db2_main_version

    all_yaml_paths = gitlab_service.get_all_yaml_paths(db2_main_version)

    print(f"all_yaml_paths: {all_yaml_paths}")

    all_config_names: List[str] = gitlab_service.get_all_config_names(
        product_type=input_params["product_type"], db2_main_version=db2_main_version
    )

    print(f"all_config_names: {all_config_names}")

    config_transform_service = ConfigTransformService()

    for product_item in product_list:
        print(f"Processing product: {product_item}")

        all_config_raw_content: Dict[str, Any] = {}

        for path_item in all_yaml_paths:
            folder_name = path_item.rsplit("/", 1)[0]
            file_name = path_item.rsplit("/", 1)[1]

            all_config_raw_content[folder_name] = gitlab_service.get_file_raw_content(
                folder_name, file_name
            )

        # print(f"all_config_raw_content: {all_config_raw_content}")

        final_results: Dict[str, Any] = config_transform_service.execute_pipeline(
            gitlab_service=gitlab_service, params=basic_context
        )

        print(f"final_results for {product_item}: {final_results}")


if __name__ == "__main__":
    main()
