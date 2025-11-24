#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project503统一测试脚本
"""

import json
import sys
import io
import csv
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置输出编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.algorithms import UserPersonaAlgorithm, TargetProfileAlgorithm
from src.models import TargetInfo, Group, Trajectory, Mission
from src.algorithms.clustering import cluster_coordinates


def load_data_from_csv():
    """从CSV文件加载数据"""
    print("\n📂 从CSV文件加载数据...")
    
    # 读取target.csv
    targets_dict = {}
    with open('data/target.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            targets_dict[row['id']] = row
    
    # 读取target_trajectory.csv
    trajectories = defaultdict(list)
    with open('data/target_trajectory.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trajectories[row['target_id']].append(row)
    
    # 读取target_group.csv
    groups_dict = {}
    with open('data/target_group.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups_dict[row['id']] = row
    
    # 读取target_group_detail.csv
    group_details = defaultdict(list)
    with open('data/target_group_detail.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_details[row['target_id']].append(row['group_id'])
    
    # 构建TargetInfo对象列表
    target_info_list = []
    for target_id, target_data in targets_dict.items():
        # 构建Group列表
        group_list = []
        for group_id in group_details.get(target_id, []):
            if group_id in groups_dict:
                g = groups_dict[group_id]
                group_list.append(Group(
                    group_name=g['group_name'],
                    source=g['source'],
                    status=g['status']
                ))
        
        # 构建Trajectory列表
        trajectory_list = []
        for traj_data in sorted(trajectories.get(target_id, []), key=lambda x: int(x['seq'])):
            trajectory_list.append(Trajectory(
                lon=traj_data['lon'],
                lat=traj_data['lat'],
                alt=traj_data['alt'],
                point_time=traj_data['point_time'],
                speed=traj_data['speed'],
                heading=traj_data['heading'],
                seq=traj_data['seq'],
                elect_silence=traj_data['elect_silence']
            ))
        
        # 创建TargetInfo对象
        target_info = TargetInfo(
            target_id=target_id,
            target_name=target_data['target_name'],
            target_type=target_data['target_type'],
            target_category=target_data['target_category'],
            target_priority=float(target_data['priority']),
            target_area_type=target_data['target_area_type'],
            group_list=group_list,
            trajectory_list=trajectory_list
        )
        target_info_list.append(target_info)
    
    print(f"✅ 加载了 {len(target_info_list)} 个目标")
    print(f"   - 轨迹点总数: {sum(len(t.trajectory_list) for t in target_info_list)}")
    print(f"   - 分组关联总数: {sum(len(t.group_list) for t in target_info_list)}")
    
    # 读取任务数据
    missions = []
    mission_file = 'data/original_single_target_mission_concat_topic.csv'
    # for i in range(1):
    try:
        with open(mission_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 处理字段映射（根据Mission类的需求）
                mission = Mission(
                    req_id=row.get('id', ''),
                    topic_id=row.get('topic_id', ''),
                    req_unit=row.get('req_unit', ''),
                    req_group=row.get('req_group', ''),
                    req_start_time=row.get('req_start_time', row.get('req_strat_time', '')),
                    req_end_time=row.get('req_end_time', ''),
                    task_type=row.get('task_type.1', ''),
                    target_id=row.get('target_id', ''),
                    country_name=row.get('country_name', ''),
                    target_priority=float(row.get('target_priority', 0)),
                    is_emcon=row.get('is_emcon', '否'),
                    is_precise=row.get('prior_info', '').strip().lower() in ['true', '1', 'yes', '是'],
                    scout_type=row.get('scout_type', ''),
                    task_scene=row.get('combat_scene', ''),
                    resolution=float(row.get('grid_level', 0.5)) if row.get('grid_level') else 0.5,
                    req_cycle=row.get('req_cycle', '1'),
                    req_cycle_time=int(float(row.get('req_cycle_times', 1))) if row.get('req_cycle_times') else None,
                    req_times=int(float(row.get('req_times', 1))) if row.get('req_times') else None,
                    mission_plan_type=row.get('mission_plan_type', '')
                )
                missions.append(mission)
        print(f"✅ 加载了 {len(missions)} 条任务")
    except FileNotFoundError:
        print(f"⚠️  未找到任务文件: {mission_file}")
    except Exception as e:
        print(f"⚠️  加载任务数据时出错: {e}")
    
    return target_info_list, missions


def test_user_persona(targets, missions, spatial_cluster_map, start_time, end_time):
    """测试用户画像"""
    print("\n" + "="*60)
    print("【测试1】用户画像模块")
    print("="*60)
        
    if not missions:
        print("⚠️  警告: 没有任务数据，跳过用户画像测试")
        return False
    
    print(f"✅ 数据加载完成: {len(targets)}个目标, {len(missions)}条任务")
    
    # 生成画像
    algorithm = UserPersonaAlgorithm()

    personas = algorithm.generate_user_persona(
        target_info=targets,
        mission=missions,
        start_time=start_time,
        end_time = end_time,
        algorithm={'preference_algorithm': 'auto',
                   'spatial_cluster_map' : spatial_cluster_map}
    )
    
    print(f"✅ 生成用户画像: {len(personas)}个")
    
    # 验证数据源时间
    if personas:
        first_persona = personas[0].to_dict()
        if 'data_time_range' in first_persona:
            print(f"✅ 数据源时间: {first_persona['data_time_range']['start_time']} 至 {first_persona['data_time_range']['end_time']}")
        else:
            print("⚠️  未包含数据源时间")
        
        # 验证输出数量
        target_prop_count = len(first_persona['persona_tags'].get('preferred_targets', []))
        region_prop_count = len(first_persona['persona_tags'].get('preferred_regions', []))
        print(f"✅ 偏爱侦察目标: {target_prop_count}个, 偏爱区域(簇ID): {region_prop_count}个")
        
        # 显示簇ID示例
        if region_prop_count > 0:
            cluster_example = first_persona['persona_tags']['preferred_regions'][0]
            print(f"   簇ID示例: cluster_{cluster_example.get('cluster_id', 'N/A')}, 任务数: {cluster_example.get('count', 0)}")
    
    # 使用算法类的format_output方法格式化输出
    result = algorithm.format_output(personas, start_time, end_time)
    
    with open('outputs/user_persona.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ 用户画像测试通过！\n")
    return True


def test_target_profile(targets, missions, spatial_cluster_map, start_time, end_time):
    """测试目标画像"""
    print("="*60)
    print("【测试2】目标画像模块")
    print("="*60)
    
    # 生成画像
    algorithm = TargetProfileAlgorithm()
    
    profiles = algorithm.generate_target_profile(
        target_info=targets,
        mission=missions,
        start_time=start_time,
        end_time=end_time,
        algorithm={
            'top_n': 3,
            'spatial_eps_km': 60.0,
            'spatial_cluster_map': spatial_cluster_map  # 传入预计算的聚类结果
        }
    )
    
    print(f"✅ 生成目标画像: {len(profiles)}个")
    
    # 验证数据源时间
    if profiles:
        first_profile = profiles[0].to_dict()
        if 'data_time_range' in first_profile:
            print(f"✅ 数据源时间: {first_profile['data_time_range']['start_time']} 至 {first_profile['data_time_range']['end_time']}")
        else:
            print("⚠️  未包含数据源时间")
    
    # 使用算法类的format_output方法格式化输出
    result = algorithm.format_output(profiles, start_time, end_time)
    
    with open('outputs/target_profile.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ 目标画像测试通过！\n")
    return True

def main():
    """主测试"""
    print("\n" + "🚀"*30)
    print("503项目统一测试")
    print("🚀"*30)
    
    # 创建输出目录
    Path('outputs').mkdir(exist_ok=True)

    targets, missions = load_data_from_csv()

    # 预先执行空间聚类
    print("\n🔍 正在计算空间聚类...")
    coordinates = []
    target_ids = []
    for target in targets:
        if hasattr(target, 'trajectory_list') and target.trajectory_list:
            first_traj = target.trajectory_list[0]
            try:
                lon = float(first_traj.lon)
                lat = float(first_traj.lat)
                coordinates.append((lon, lat))
                target_ids.append(target.target_id)
            except (ValueError, AttributeError):
                continue
    
    spatial_cluster_map = {}
    if coordinates:
        spatial_cluster_map = cluster_coordinates(
            coordinates=coordinates,
            item_ids=target_ids,
            eps_km=80.0,
            min_samples=3,
            auto_tune=True,
            desired_min_clusters=5
        )
        cluster_count = len(set(spatial_cluster_map.values()))
        print(f"✅ 聚类完成: {len(spatial_cluster_map)}个目标, {cluster_count}个簇")
    else:
        print("⚠️  无有效坐标，跳过聚类")
    
    # 从missions提取时间范围
    start_times = [m.req_start_time for m in missions if m.req_start_time]
    end_times = [m.req_end_time for m in missions if m.req_end_time]
    start_time = min(start_times) if start_times else None
    end_time = max(end_times) if end_times else None
    
    if start_time and end_time:
        print(f"📅 数据时间范围: {start_time} 至 {end_time}")
    
    # 测试
    r1 = test_user_persona(targets, missions, spatial_cluster_map, start_time, end_time)
    r2 = test_target_profile(targets, missions, spatial_cluster_map, start_time, end_time)
    
    # 总结
    print("="*60)
    print("测试总结")
    print("="*60)
    print(f"用户画像: {'✅ 通过' if r1 else '❌ 失败'}")
    print(f"目标画像: {'✅ 通过' if r2 else '❌ 失败'}")
    
    if r1 and r2:
        print("\n🎉 所有测试通过！项目运行正常！")
    else:
        print("\n⚠️  部分测试失败")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
