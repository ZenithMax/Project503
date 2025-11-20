from typing import List, Dict, Any
from datetime import datetime
import logging

from ..models import Mission, TargetInfo, UserPersona
from .persona_tag_calculator import PersonaTagCalculator


class UserPersonaAlgorithm:
    """用户画像算法主类"""
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    def generate_user_persona(self,
                            target_info: List[TargetInfo],
                            mission: List[Mission],
                            start_time: str = None,
                            end_time: str = None,
                            algorithm: Dict[str, Any] = None,
                            params: Dict[str, Any] = None) -> List[UserPersona]:
        """
        生成用户画像
        :param target_info: 目标信息数据列表
        :param mission: 历史需求数据列表
        :param start_time: 开始时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
        :param end_time: 结束时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
        :param algorithm: 算法配置参数（可选）
            - preference_algorithm: 偏好计算算法
                - 'auto': 自动选择（根据数据特征）[默认]
                    - HHI > 0.05: percentage
                    - HHI ≤ 0.05 时:
                        - 用户≥10 + 目标≥20: tfidf
                        - 用户≥5 + 目标≥10 + CV>1.0: bm25
                        - 用户≥5 + 目标≥10 + CV≤1.0: tfidf
                        - 目标≥5: zscore
                        - 目标<5: percentage
                - 'percentage': 简单百分比Top-N
                - 'tfidf': TF-IDF算法（需全局统计，识别用户特有偏好）
                - 'bm25': BM25算法（需全局统计，考虑饱和度）
                - 'zscore': Z-score显著性过滤（单用户统计检验）
            - top_n: 输出前N个结果，默认3
        :param params: 扩充参数（预留）
        :return: 用户画像结果列表
        """
        
        if params is None:
            params = {}
        if algorithm is None:
            algorithm = {}
        
        self.logger.info("开始生成用户画像")
        
        # 解析算法配置
        preference_algo = algorithm.get('preference_algorithm', 'auto')
        self.logger.info(f"偏好计算算法: {preference_algo}")
        
        if start_time or end_time:
            self.logger.info(f"时间范围: {start_time or '不限'} 至 {end_time or '不限'}")
        self.logger.info(f"输入数据: {len(target_info)} 个目标, {len(mission)} 条历史需求")
        
        try:
            # 1. 数据预处理和验证
            self._validate_input_data(target_info, mission)
            
            # 2. 根据时间范围过滤任务
            filtered_mission = self._filter_missions_by_time(mission, start_time, end_time)
            if len(filtered_mission) < len(mission):
                self.logger.info(f"时间过滤后保留 {len(filtered_mission)} 条需求")
            mission = filtered_mission
            
            # 3. 计算全局统计（用于TF-IDF/BM25算法）
            if preference_algo in ['auto', 'tfidf', 'bm25']:
                global_stats = self._calculate_global_stats(mission)
                algorithm['global_stats'] = global_stats
                self.logger.info(f"全局统计: {global_stats['total_users']}个用户, "
                               f"平均每用户{global_stats['avg_mission_count']:.1f}条任务")
            
            # 4. 创建标签计算器（传入算法配置）
            tag_calculator = PersonaTagCalculator(algorithm_config=algorithm)
            
            # 5. 按用户分组处理
            user_personas = []
            user_groups = self._group_missions_by_user(mission, target_info)
            
            for user_key, (user_id, user_missions, related_targets) in user_groups.items():
                self.logger.info(f"处理用户 {user_key}, 相关需求数量: {len(user_missions)}")
                
                # 6. 使用统计规则生成画像标签
                persona_tags = tag_calculator.generate_persona_tags(
                    user_missions, related_targets
                )
                
                self.logger.info(f"用户 {user_key} 画像标签生成完成")
                
                # 7. 生成用户画像对象
                user_persona = UserPersona(
                    user_id=user_id,
                    persona_tags=persona_tags,
                    generation_time=datetime.now().isoformat()
                )
                
                user_personas.append(user_persona)
                self.logger.info(f"用户 {user_key} 画像生成完成")
            
            self.logger.info(f"用户画像生成完成, 共生成 {len(user_personas)} 个画像")
            return user_personas
            
        except Exception as e:
            self.logger.error(f"用户画像生成失败: {str(e)}")
            raise
    
    def _validate_input_data(self, target_info: List[TargetInfo], mission: List[Mission]):
        """验证输入数据"""
        if not target_info:
            raise ValueError("目标信息数据列表不能为空")
        
        if not mission:
            raise ValueError("历史需求数据列表不能为空")
    
    def _calculate_global_stats(self, missions: List[Mission]) -> Dict[str, Any]:
        """
        计算全局统计信息，用于TF-IDF和BM25算法
        :param missions: 所有用户的任务列表
        :return: 全局统计字典
        """
        from collections import Counter, defaultdict
        
        # 统计每个目标被多少个用户使用
        target_user_count = defaultdict(set)
        user_mission_count = defaultdict(int)
        
        for mission in missions:
            user_key = f"{mission.req_unit}_{mission.req_group}"
            target_user_count[mission.target_id].add(user_key)
            user_mission_count[user_key] += 1
        
        # 转换为计数
        target_user_count_dict = {
            target_id: len(users) 
            for target_id, users in target_user_count.items()
        }
        
        # 计算平均任务数
        total_users = len(user_mission_count)
        avg_mission_count = sum(user_mission_count.values()) / total_users if total_users > 0 else 0
        
        return {
            'target_user_count': target_user_count_dict,  # 每个目标被多少用户使用
            'total_users': total_users,                    # 总用户数
            'avg_mission_count': avg_mission_count         # 平均每用户任务数
        }
    
    def _group_missions_by_user(self, missions: List[Mission], targets: List[TargetInfo]) -> Dict[str, tuple]:
        """按用户分组需求数据"""
        target_dict = {target.target_id: target for target in targets}
        grouped_missions = {}
        
        for mission in missions:
            # 用户标识：部门+区组
            user_key = f"{mission.req_unit}_{mission.req_group}"
            
            if user_key not in grouped_missions:
                # 使用dict格式作为user_id
                user_id_dict = {
                    'req_unit': mission.req_unit,
                    'req_group': mission.req_group
                }
                grouped_missions[user_key] = (user_id_dict, [], [])
            
            # 添加任务到用户组
            grouped_missions[user_key][1].append(mission)
            
            # 添加相关目标到用户组（去重）
            if mission.target_id in target_dict:
                target = target_dict[mission.target_id]
                if target not in grouped_missions[user_key][2]:
                    grouped_missions[user_key][2].append(target)
        
        return grouped_missions
    
    def _filter_missions_by_time(self, 
                                  missions: List[Mission], 
                                  start_time: str = None, 
                                  end_time: str = None) -> List[Mission]:
        """
        根据时间范围过滤任务
        :param missions: 任务列表
        :param start_time: 开始时间（格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
        :param end_time: 结束时间（格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
        :return: 过滤后的任务列表
        """
        if not start_time and not end_time:
            return missions
        
        def parse_time(time_str: str) -> datetime:
            """解析时间字符串"""
            if not time_str:
                return None
            
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            self.logger.warning(f"无法解析时间: {time_str}")
            return None
        
        start_dt = parse_time(start_time) if start_time else None
        end_dt = parse_time(end_time) if end_time else None
        
        filtered_missions = []
        for mission in missions:
            mission_time = parse_time(mission.req_start_time)
            if mission_time is None:
                continue
            
            if start_dt and mission_time < start_dt:
                continue
            if end_dt and mission_time > end_dt:
                continue
                
            filtered_missions.append(mission)
        
        return filtered_missions
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('UserPersonaAlgorithm')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger


def user_persona_algorithm_api(target_info: List[TargetInfo],
                              mission: List[Mission],
                              start_time: str = None,
                              end_time: str = None,
                              algorithm: Dict[str, Any] = None,
                              params: Dict[str, Any] = None) -> List[UserPersona]:
    """
    用户画像算法API入口函数
    
    :param target_info: 目标信息数据列表
    :param mission: 历史需求数据列表
    :param start_time: 开始时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
    :param end_time: 结束时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
    :param algorithm: 算法配置参数（可选）
    :param params: 扩充参数（预留）
    :return: 用户画像结果列表
    """
    
    # 创建算法实例并执行
    persona_algorithm = UserPersonaAlgorithm()
    return persona_algorithm.generate_user_persona(
        target_info, mission, start_time, end_time, algorithm, params
    )
