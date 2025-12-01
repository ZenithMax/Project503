import pymysql
import json

def get_db_connection():
    connection = pymysql.connect(
        host = 'localhost',
        port = 3306,
        user = 'root',
        password = '123456',
        database = 'project503')
    return connection


def create_user_profile_table():
    """创建用户画像表"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                version VARCHAR(50) NOT NULL COMMENT '版本号',
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                req_unit VARCHAR(100) NOT NULL COMMENT '需求单元',
                req_group VARCHAR(100) NOT NULL COMMENT '需求组',
                user_profile TEXT NOT NULL COMMENT '用户画像',
                INDEX idx_req_unit (req_unit),
                INDEX idx_req_group (req_group),
                INDEX idx_version (version),
                INDEX idx_created_time (created_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户画像表';
            """
            cursor.execute(sql)
            connection.commit()
            print("用户画像表创建成功")
    except Exception as e:
        print(f"创建用户画像表失败: {e}")
        connection.rollback()
    finally:
        connection.close()


def create_target_profile_table():
    """创建目标画像表"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            CREATE TABLE IF NOT EXISTS target_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                version VARCHAR(50) NOT NULL COMMENT '版本号',
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                target_id VARCHAR(100) NOT NULL COMMENT '目标ID',
                target_profile TEXT NOT NULL COMMENT '目标画像',
                INDEX idx_target_id (target_id),
                INDEX idx_version (version),
                INDEX idx_created_time (created_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='目标画像表';
            """
            cursor.execute(sql)
            connection.commit()
            print("目标画像表创建成功")
    except Exception as e:
        print(f"创建目标画像表失败: {e}")
        connection.rollback()
    finally:
        connection.close()


def insert_user_profile(version, req_unit, req_group, user_profile_data):
    """
    插入用户画像数据
    
    Args:
        version: 版本号
        req_unit: 需求单元
        req_group: 需求组
        user_profile_data: 用户画像数据（dict或JSON字符串）
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 如果是字典，转换为JSON字符串
            if isinstance(user_profile_data, dict):
                user_profile_json = json.dumps(user_profile_data, ensure_ascii=False)
            else:
                user_profile_json = user_profile_data
            
            sql = """
            INSERT INTO user_profiles (version, req_unit, req_group, user_profile)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (version, req_unit, req_group, user_profile_json))
            connection.commit()
            print(f"成功插入用户画像: {req_unit}-{req_group}, 版本: {version}")
            return cursor.lastrowid
    except Exception as e:
        print(f"插入用户画像失败: {e}")
        connection.rollback()
        return None
    finally:
        connection.close()


def insert_target_profile(version, target_id, target_profile_data):
    """
    插入目标画像数据
    
    Args:
        version: 版本号
        target_id: 目标ID
        target_profile_data: 目标画像数据（dict或JSON字符串）
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 如果是字典，转换为JSON字符串
            if isinstance(target_profile_data, dict):
                target_profile_json = json.dumps(target_profile_data, ensure_ascii=False)
            else:
                target_profile_json = target_profile_data
            
            sql = """
            INSERT INTO target_profiles (version, target_id, target_profile)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (version, target_id, target_profile_json))
            connection.commit()
            print(f"成功插入目标画像: {target_id}, 版本: {version}")
            return cursor.lastrowid
    except Exception as e:
        print(f"插入目标画像失败: {e}")
        connection.rollback()
        return None
    finally:
        connection.close()


def batch_insert_user_profiles_from_json(json_file_path):
    """
    从JSON文件批量插入用户画像（版本号从数据时间范围自动生成）
    
    Args:
        json_file_path: JSON文件路径
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 从数据源提取时间范围生成版本号
        data_source = data.get('data_source', {})
        time_range = data_source.get('time_range', {})
        start_time = time_range.get('start', '').replace(' ', '_').replace(':', '-')
        end_time = time_range.get('end', '').replace(' ', '_').replace(':', '-')
        version = f"{start_time}-{end_time}"
        
        personas = data.get('users_personas', [])
        success_count = 0
        
        for persona in personas:
            user_id = persona.get('user_id', {})
            req_unit = user_id.get('req_unit', '')
            req_group = user_id.get('req_group', '')
            
            if req_unit and req_group:
                result = insert_user_profile(version, req_unit, req_group, persona)
                if result:
                    success_count += 1
        
        print(f"批量插入完成: 版本 {version}, 成功 {success_count}/{len(personas)}")
        return success_count
    except Exception as e:
        print(f"批量插入用户画像失败: {e}")
        return 0


def batch_insert_target_profiles_from_json(json_file_path):
    """
    从JSON文件批量插入目标画像（版本号从数据时间范围自动生成）
    
    Args:
        json_file_path: JSON文件路径
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 从数据源提取时间范围生成版本号
        data_source = data.get('data_source', {})
        time_range = data_source.get('time_range', {})
        start_time = time_range.get('start', '').replace(' ', '_').replace(':', '-')
        end_time = time_range.get('end', '').replace(' ', '_').replace(':', '-')
        version = f"{start_time}-{end_time}"
        
        profiles = data.get('target_profiles', [])
        success_count = 0
        
        for profile in profiles:
            target_id = profile.get('target_id', '')
            
            if target_id:
                result = insert_target_profile(version, target_id, profile)
                if result:
                    success_count += 1
        
        print(f"批量插入完成: 版本 {version}, 成功 {success_count}/{len(profiles)}")
        return success_count
    except Exception as e:
        print(f"批量插入目标画像失败: {e}")
        return 0


def init_database():
    """初始化数据库，创建所有表"""
    create_user_profile_table()
    create_target_profile_table()


if __name__ == "__main__":
    # 运行此文件以创建表
    init_database()
