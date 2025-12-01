"""
批量导入用户画像和目标画像到数据库
"""
import os
import sys

# 获取项目根目录（脚本所在目录的父目录）
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

# 添加项目根目录到Python路径
sys.path.insert(0, project_dir)

from src.database.database import init_database, batch_insert_user_profiles_from_json, batch_insert_target_profiles_from_json

def main():
    # 使用绝对路径
    user_json_path = os.path.join(project_dir, 'outputs', 'user_persona.json')
    target_json_path = os.path.join(project_dir, 'outputs', 'target_profile.json')
    
    # 检查文件是否存在
    if not os.path.exists(user_json_path):
        print(f"✗ 文件不存在: {user_json_path}")
        return
    if not os.path.exists(target_json_path):
        print(f"✗ 文件不存在: {target_json_path}")
        return
    
    # 1. 初始化数据库（创建表，如果表已存在则跳过）
    print("=" * 50)
    print("初始化数据库...")
    print("=" * 50)
    init_database()
    
    # 2. 导入用户画像
    print("\n" + "=" * 50)
    print("开始导入用户画像...")
    print(f"文件路径: {user_json_path}")
    print("=" * 50)
    user_count = batch_insert_user_profiles_from_json(user_json_path)
    print(f"用户画像导入完成，共导入 {user_count} 条记录\n")
    
    # 3. 导入目标画像
    print("=" * 50)
    print("开始导入目标画像...")
    print(f"文件路径: {target_json_path}")
    print("=" * 50)
    target_count = batch_insert_target_profiles_from_json(target_json_path)
    print(f"目标画像导入完成，共导入 {target_count} 条记录\n")
    
    # 4. 总结
    print("=" * 50)
    print("导入完成!")
    print(f"用户画像: {user_count} 条")
    print(f"目标画像: {target_count} 条")
    print("=" * 50)

if __name__ == "__main__":
    main()
