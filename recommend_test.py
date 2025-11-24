#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟任务推荐系统 - 主入口
根据用户画像为用户推荐最适合的虚拟任务
"""

import json
from src.algorithms import VirtualTaskRecommendationAlgorithm
from src.algorithms.recommendation_algorithm import (
    load_virtual_tasks_and_personas,
    save_task_recommendations
)

def main():
    print("="*60)
    print("虚拟任务推荐系统")
    print("="*60)
    
    # 1. 加载数据
    print("\n📂 加载数据...")
    virtual_tasks, user_personas, target_profiles = load_virtual_tasks_and_personas()
    print(f"✅ 虚拟任务: {len(virtual_tasks)} 个")
    print(f"✅ 用户画像: {len(user_personas)} 个")
    print(f"✅ 目标画像: {len(target_profiles)} 个")
    
    # 2. 创建推荐算法
    print("\n🤖 初始化虚拟任务推荐算法...")
    recommender = VirtualTaskRecommendationAlgorithm(
        weight_target_match=0.25,        # 目标匹配权重 (preferred_targets)
        weight_region_match=0.20,        # 区域匹配权重 (preferred_regions)
        weight_category_match=0.20,      # 目标类别匹配权重 (preferred_target_category)
        weight_topic_match=0.15,         # 主题组匹配权重 (preferred_topic_group)
        weight_scout_scenario=0.20       # 侦察场景匹配权重 (preferred_scout_scenario)
    )
    print("✅ 推荐算法初始化完成")
    
    # 3. 生成推荐
    print("\n🎯 为所有用户生成虚拟任务推荐...")
    print("   (推荐数量将根据用户的request_frequency动态调整)")
    recommendations = recommender.recommend_tasks_for_users(
        virtual_tasks=virtual_tasks,
        user_personas=user_personas,
        target_profiles=target_profiles,
        base_top_n=10  # 基础推荐数量，会根据用户活跃度调整
    )
    
    # 4. 保存结果
    print("\n💾 保存推荐结果...")
    save_task_recommendations(recommendations)
    
    # 5. 显示统计信息
    print("\n" + "="*60)
    print("推荐结果统计")
    print("="*60)
    
    total_recommendations = sum(len(recs) for recs in recommendations.values())
    
    # 统计不同推荐数量的用户分布
    rec_count_distribution = {}
    for recs in recommendations.values():
        count = len(recs)
        rec_count_distribution[count] = rec_count_distribution.get(count, 0) + 1
    
    print(f"✅ 推荐用户数: {len(recommendations)}")
    print(f"✅ 总推荐数: {total_recommendations}")
    print(f"✅ 平均推荐数: {total_recommendations / len(recommendations):.1f} 个/用户")
    print(f"\n📊 推荐数量分布 (根据用户活跃度):")
    for count in sorted(rec_count_distribution.keys()):
        user_count = rec_count_distribution[count]
        print(f"   - {count}个推荐: {user_count} 个用户")
    
    # 6. 显示Top-5用户的推荐样例
    print("\n" + "="*60)
    print("推荐样例（Top-5用户）")
    print("="*60)
    
    for i, (user_key_str, recs) in enumerate(list(recommendations.items())[:5], 1):
        # 解析用户ID
        user_id = json.loads(user_key_str)
        req_unit = user_id.get('req_unit', '')
        req_group = user_id.get('req_group', '')
        
        print(f"\n【{i}】用户:")
        print(f"   单位: {req_unit}")
        print(f"   组别: {req_group}")
        print(f"   推荐任务数: {len(recs)}")
        
        if recs:
            print(f"\n   推荐的虚拟任务:")
            for j, rec in enumerate(recs[:5], 1):
                task_id = rec['task_id']
                target_id = rec['target_id']
                score = rec['score']
                print(f"      {j}. {task_id}")
                print(f"         目标: {target_id}")
                print(f"         推荐分数: {score:.4f}")
    
    print("\n" + "="*60)
    print("✅ 虚拟任务推荐完成！")

if __name__ == "__main__":
    main()
