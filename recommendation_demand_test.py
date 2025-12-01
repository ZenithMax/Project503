#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推荐需求生成测试脚本
"""

import json
import os
from src.algorithms.recommendation_demand_algorithm import RecommendationDemandAlgorithm

def main():
    # 目标画像JSON文件路径
    target_profile_json_path = "outputs/target_profile.json"
    
    if not os.path.exists(target_profile_json_path):
        print(f"错误：目标画像文件不存在: {target_profile_json_path}")
        return
    
    print("开始生成推荐需求...")
    print(f"读取目标画像文件: {target_profile_json_path}")
    
    # 创建算法实例
    algorithm = RecommendationDemandAlgorithm()
    
    # 生成推荐需求（每个target_id输出前3个）
    result = algorithm.generate_recommendation_demands(target_profile_json_path, top_n=3)
    
    # 输出结果到JSON文件
    output_path = "outputs/recommendation_demands.json"
    os.makedirs("outputs", exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n推荐需求生成完成！")
    print(f"输出文件: {output_path}")
    print(f"共生成 {result['statistics']['total']} 个推荐需求")
    print(f"涉及 {result['statistics']['target_count']} 个目标")
    
    # 打印前3个目标的推荐需求摘要
    print("\n前3个目标的推荐需求摘要：")
    demands_list = result['recommendation_demands']
    for i, target_data in enumerate(demands_list[:3], 1):
        target_id = target_data.get('targetId', '')
        demands = target_data.get('demands', [])
        print(f"\n{i}. 目标ID: {target_id} (共 {len(demands)} 个需求)")
        for j, demand in enumerate(demands[:2], 1):  # 每个目标最多显示2个需求
            print(f"   需求{j}: 权重得分: {demand.get('weight_score', 0):.4f}")
            print(f"     - 任务类型: {demand['taskType']}, 侦察类型: {demand['scoutType']}")
            print(f"     - 任务场景: {demand['taskScene']}")
            print(f"     - 目标优先级: {demand['targetPriority']}")
            print(f"     - 分辨率: {demand['resolution']}")

if __name__ == "__main__":
    main()

