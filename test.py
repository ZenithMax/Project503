#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project503统一测试脚本
"""

import json
import sys
import io
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置输出编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.algorithms import UserPersonaAlgorithm, TargetProfileAlgorithm
from src.utils import generate_sample_data, generate_smart_data


def test_user_persona():
    """测试用户画像"""
    print("\n" + "="*60)
    print("【测试1】用户画像模块")
    print("="*60)
    
    # 生成数据
    targets, missions = generate_sample_data(num_targets=50, num_missions=10000)
    print(f"✅ 生成数据: {len(targets)}个目标, {len(missions)}条任务")
    
    # 生成画像
    algorithm = UserPersonaAlgorithm()
    personas = algorithm.generate_user_persona(
        target_info=targets,
        mission=missions,
        algorithm={'preference_algorithm': 'percentage', 'top_n': 3}
    )
    
    print(f"✅ 生成用户画像: {len(personas)}个")
    
    # 保存结果
    result = {
        "module": "user_persona",
        "users_personas": [p.to_dict() for p in personas[:3]],
        "statistics": {"total": len(personas)}
    }
    
    with open('outputs/user_persona.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ 用户画像测试通过！\n")
    return True


def test_target_profile():
    """测试目标画像"""
    print("="*60)
    print("【测试2】目标画像模块")
    print("="*60)
    
    # 生成数据
    targets, missions = generate_smart_data(num_targets=50, num_missions=10000)
    print(f"✅ 生成数据: {len(targets)}个目标, {len(missions)}条任务")
    
    # 生成画像
    algorithm = TargetProfileAlgorithm()
    profiles = algorithm.generate_target_profile(
        target_info=targets,
        mission=missions,
        algorithm={'top_n': 3, 'spatial_eps_km': 60.0}
    )
    
    print(f"✅ 生成目标画像: {len(profiles)}个")
    
    # 保存结果
    result = {
        "module": "target_profile",
        "target_profiles": [p.to_dict() for p in profiles[:3]],
        "statistics": {"total": len(profiles)}
    }
    
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
    
    # 测试
    r1 = test_user_persona()
    r2 = test_target_profile()
    
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
