"""Main Function."""

from typing import List, Dict, Any


def make_hashable(obj):
    """將 list 遞迴轉換為 tuple，確保可以作為 dict 的 key"""
    if isinstance(obj, list):
        return tuple(make_hashable(i) for i in obj)
    if isinstance(obj, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
    return obj


def merge_vg_configs(all_vg_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    合併多個 VG Config 中的 vg_list
    規則 1: 屬性不同或值不同（除 number 外）視為不同項目
    規則 2: 屬性相同時，保留 number 較大的項目
    """
    # 使用 dict 來儲存唯一項目，Key 是除了 number 以外的所有資訊
    merged_map: Dict[tuple, Dict[str, Any]] = {}

    for config in all_vg_configs:
        vg_list = config.get("DB2_VG_INFO", {}).get("vg_list", [])

        for vg_item in vg_list:
            # 1. 提取除 number 以外的所有屬性並排序，確保組成 key 的一致性
            # 將 dict 轉換為 sorted tuple of items，使其成為可雜湊 (hashable) 的 key
            core_features = {k: v for k, v in vg_item.items() if k != "number"}
            print(f"Core features for item {vg_item['vg_name']}: {core_features}")

            # 2. 關鍵修正：將整個 core_features 轉換成完全可雜湊的結構
            feature_key = make_hashable(core_features)
            print(f"Feature key for item {vg_item['vg_name']}: {feature_key}")

            # 2. 檢查是否已存在相同特徵的項目
            if feature_key in merged_map:
                # 規則 2: 比較 number，保留大的
                if vg_item.get("number", 0) > merged_map[feature_key].get("number", 0):
                    merged_map[feature_key] = vg_item
            else:
                # 規則 1: 第一次見到的特徵，直接加入
                merged_map[feature_key] = vg_item

            print(f"Current merged map: {merged_map}")

    # 回傳合併後的 list
    return list(merged_map.values())


if __name__ == "__main__":
    # 執行合併
    final_result = merge_vg_configs([mm_config, spc_config, spc1_config])
    print(final_result)
