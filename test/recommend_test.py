#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟任务推荐系统 - 主入口
根据用户画像为用户推荐最适合的虚拟任务
支持纯内容推荐和混合推荐（内容+协同过滤）
"""

import os
import sys
import json

# 添加项目根目录到 Python 路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)

from src.algorithms import VirtualTaskRecommendationAlgorithm
from src.algorithms.recommendation_algorithm import (
    load_virtual_tasks_and_personas,
    save_task_recommendations
)

def test_content_based_recommendation():
    print("="*60)
    print("虚拟任务推荐系统")
    print("="*60)
    
    # 1. 加载数据
    print("\n📂 加载数据...")
    # 使用绝对路径，确保在任意目录都能运行
    outputs_dir = os.path.join(project_dir, 'outputs')
    virtual_tasks, user_personas, target_profiles = load_virtual_tasks_and_personas(
        virtual_task_file=os.path.join(outputs_dir, 'virtual_tasks.json'),
        user_persona_file=os.path.join(outputs_dir, 'user_persona.json'),
        target_profile_file=os.path.join(outputs_dir, 'target_profile.json')
    )
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
    save_task_recommendations(
        recommendations,
        output_file=os.path.join(outputs_dir, 'recommendations.json'),
        virtual_task_file=os.path.join(outputs_dir, 'virtual_tasks.json')
    )
    
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
    
    return recommendations


def test_hybrid_recommendation():
    """演示混合推荐（内容推荐 + User-based协同过滤）"""
    print("\n" + "="*60)
    print("【混合推荐测试】内容推荐 + User-based协同过滤")
    print("="*60)
    
    # 1. 加载数据
    print("\n📂 加载数据...")
    # 使用绝对路径，确保在任意目录都能运行
    outputs_dir = os.path.join(project_dir, 'outputs')
    virtual_tasks, user_personas, target_profiles = load_virtual_tasks_and_personas(
        virtual_task_file=os.path.join(outputs_dir, 'virtual_tasks.json'),
        user_persona_file=os.path.join(outputs_dir, 'user_persona.json'),
        target_profile_file=os.path.join(outputs_dir, 'target_profile.json')
    )
    print(f"✅ 虚拟任务: {len(virtual_tasks)} 个")
    print(f"✅ 用户画像: {len(user_personas)} 个")
    print(f"✅ 目标画像: {len(target_profiles)} 个")
    
    # 2. 创建混合推荐算法（启用User-based协同过滤）
    print("\n🤖 初始化混合推荐算法...")
    print("   配置: 内容推荐(70%) + User-based协同过滤(30%)")
    recommender = VirtualTaskRecommendationAlgorithm(
        # 内容推荐权重配置
        weight_target_match=0.25,
        weight_region_match=0.20,
        weight_category_match=0.20,
        weight_topic_match=0.15,
        weight_scout_scenario=0.20,
        # User-based协同过滤配置
        enable_collaborative_filtering=True,  # 启用协同过滤
        content_weight=0.7,                   # 内容推荐权重
        cf_weight=0.3,                        # 协同过滤权重
        similarity_metric='cosine',           # 'cosine' 或 'jaccard'
        top_k_neighbors=5                     # K近邻数量
    )
    print("✅ 混合推荐算法初始化完成")
    
    # 3. 生成推荐
    print("\n🎯 为所有用户生成混合推荐...")
    recommendations = recommender.recommend_tasks_for_users(
        virtual_tasks=virtual_tasks,
        user_personas=user_personas,
        target_profiles=target_profiles,
        base_top_n=10
    )
    
    # 4. 保存结果
    print("\n💾 保存混合推荐结果...")
    save_task_recommendations(
        recommendations,
        output_file=os.path.join(outputs_dir, 'recommendations_hybrid.json'),
        virtual_task_file=os.path.join(outputs_dir, 'virtual_tasks.json')
    )
    
    # 5. 显示统计
    print("\n" + "="*60)
    print("混合推荐结果统计")
    print("="*60)
    total_recommendations = sum(len(recs) for recs in recommendations.values())
    print(f"✅ 推荐用户数: {len(recommendations)}")
    print(f"✅ 总推荐数: {total_recommendations}")
    print(f"✅ 平均推荐数: {total_recommendations / len(recommendations):.1f} 个/用户")
    
    print("\n" + "="*60)
    print("✅ 混合推荐完成！")
    print("💡 提示: 协同过滤可以发现用户潜在兴趣，增加推荐多样性")
    
    return recommendations


def main():
    """主函数：选择推荐模式"""
    import sys
    
    print("\n" + "🚀"*30)
    print("虚拟任务推荐系统")
    print("🚀"*30)
    
    # 如果有命令行参数
    mode = sys.argv[1] if len(sys.argv) > 1 else 'content'
    
    if mode == 'hybrid':
        print("\n【模式】混合推荐 (内容 + 协同过滤)")
        test_hybrid_recommendation()
    elif mode == 'content':
        print("\n【模式】纯内容推荐")
        test_content_based_recommendation()
    elif mode == 'compare':
        print("\n【模式】对比测试")
        print("\n" + "-"*60)
        print("【测试1】纯内容推荐")
        print("-"*60)
        content_recs = test_content_based_recommendation()
        
        print("\n" + "-"*60)
        print("【测试2】混合推荐")
        print("-"*60)
        hybrid_recs = test_hybrid_recommendation()
        
        # 简单对比
        print("\n" + "="*60)
        print("【对比结果】")
        print("="*60)
        if content_recs and hybrid_recs:
            first_user = list(content_recs.keys())[0]
            content_tasks = [r['task_id'] for r in content_recs[first_user][:10]]
            hybrid_tasks = [r['task_id'] for r in hybrid_recs[first_user][:10]]
            overlap = len(set(content_tasks) & set(hybrid_tasks))
            print(f"示例用户Top10推荐重叠度: {overlap}/10 ({overlap*10}%)")
            print(f"差异越大说明协同过滤引入了更多新颖性")
    else:
        print(f"\n❌ 未知模式: {mode}")
        print("用法:")
        print("  python recommend_test.py content  # 纯内容推荐（默认）")
        print("  python recommend_test.py hybrid   # 混合推荐")
        print("  python recommend_test.py compare  # 对比测试")


if __name__ == "__main__":
    main()
