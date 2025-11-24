"""目标画像算法主模块"""

import logging
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

from ..models import TargetInfo, Mission, TargetProfile
from .target_tag_calculator import TargetTagCalculator


class TargetProfileAlgorithm:
    """目标画像算法主类"""
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    def generate_target_profile(self,
                                target_info: List[TargetInfo],
                                mission: List[Mission],
                                start_time: str = None,
                                end_time: str = None,
                                algorithm: Dict[str, Any] = None,
                                params: Dict[str, Any] = None) -> List[TargetProfile]:
        """
        生成目标画像
        :param target_info: 目标信息数据列表
        :param mission: 历史需求数据列表
        :param start_time: 开始时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
        :param end_time: 结束时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
        :param algorithm: 算法配置参数（可选）
            - top_n: 输出前N个结果，默认3
            - spatial_eps_km: DBSCAN邻域半径（公里），默认60.0
            - spatial_min_samples: DBSCAN最小样本数，默认4
            - spatial_auto_tune: 是否自动调参，默认True
            - spatial_min_clusters: 期望的最小簇数，默认7
        :param params: 扩充参数（预留）
        :return: 目标画像结果列表
        """
        
        if params is None:
            params = {}
        if algorithm is None:
            algorithm = {}
        
        self.logger.info("开始生成目标画像")
        
        if start_time or end_time:
            self.logger.info(f"时间范围过滤: {start_time} 到 {end_time}")
            mission = self._filter_missions_by_time(mission, start_time, end_time)
            self.logger.info(f"过滤后需求数量: {len(mission)}")
        
        # 按目标ID分组
        self.logger.info("按目标分组历史需求数据")
        missions_by_target = self._group_missions_by_target(mission)
        self.logger.info(f"共有 {len(missions_by_target)} 个目标")
        
        # 先对所有目标进行全局聚类（一次性聚类所有目标）
        self.logger.info("对所有目标进行全局空间聚类...")
        global_cluster_labels = self._compute_global_clustering(target_info, mission, algorithm)
        self.logger.info(f"全局聚类完成，共 {len(set(global_cluster_labels.values())) - (1 if -1 in global_cluster_labels.values() else 0)} 个簇")
        
        # 创建标签计算器，传入全局聚类结果
        tag_calculator = TargetTagCalculator(algorithm, global_cluster_labels=global_cluster_labels)
        
        # 生成每个目标的画像
        profiles = []
        for target_id, target_missions in missions_by_target.items():
            self.logger.info(f"处理目标 {target_id}, 相关需求数量: {len(target_missions)}")
            
            # 生成画像标签
            profile_tags = tag_calculator.generate_profile_tags(target_missions, target_info)
            self.logger.info(f"目标 {target_id} 画像标签生成完成")
            
            # 创建目标画像对象
            data_time_range = {}
            if start_time:
                data_time_range['start_time'] = start_time
            if end_time:
                data_time_range['end_time'] = end_time
            
            profile = TargetProfile(
                target_id=target_id,
                profile_tags=profile_tags,
                generation_time=datetime.now().isoformat(),
                data_time_range=data_time_range
            )
            profiles.append(profile)
            self.logger.info(f"目标 {target_id} 画像生成完成")
        
        self.logger.info(f"目标画像生成完成, 共生成 {len(profiles)} 个画像")
        return profiles
    
    def _filter_missions_by_time(self, missions: List[Mission], start_time: str = None, end_time: str = None) -> List[Mission]:
        """根据时间范围过滤任务"""
        from datetime import datetime
        
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
        
        filtered = []
        for m in missions:
            mission_time = parse_time(m.req_start_time)
            if mission_time is None:
                continue
            
            if start_dt and mission_time < start_dt:
                continue
            if end_dt and mission_time > end_dt:
                continue
            
            filtered.append(m)
        
        return filtered
    
    def _group_missions_by_target(self, missions: List[Mission]) -> Dict[str, List[Mission]]:
        """按目标ID分组任务"""
        grouped = defaultdict(list)
        for mission in missions:
            grouped[mission.target_id].append(mission)
        return dict(grouped)
    
    def _compute_global_clustering(self, 
                                   target_info: List[TargetInfo], 
                                   mission: List[Mission],
                                   algorithm: Dict[str, Any]) -> Dict[str, int]:
        """
        对所有目标进行全局空间聚类
        
        :param target_info: 所有目标信息列表
        :param mission: 所有任务列表
        :param algorithm: 算法配置参数
        :return: target_id -> cluster_id 的映射字典
        """
        from .clustering import compute_spatial_clustering_from_missions
        
        # 获取聚类参数
        eps_km = algorithm.get('spatial_eps_km', 60.0)
        min_samples = algorithm.get('spatial_min_samples', 4)
        auto_tune = algorithm.get('spatial_auto_tune', True)
        desired_min_clusters = algorithm.get('spatial_min_clusters', 7)
        max_attempts = algorithm.get('spatial_max_attempts', 10)
        noise_ratio_threshold = algorithm.get('spatial_noise_ratio_threshold', 0.45)
        
        # 对所有目标的所有 missions 进行聚类
        # 使用 target_id 作为标识符，这样同一个 target_id 的所有 missions 会被聚到同一个簇
        spatial_labels = compute_spatial_clustering_from_missions(
            missions=mission,  # 传入所有 missions
            target_info_list=target_info,
            item_id_extractor=lambda m: m.target_id,  # 使用 target_id 作为标识符
            eps_km=eps_km,
            min_samples=min_samples,
            auto_tune=auto_tune,
            desired_min_clusters=desired_min_clusters,
            max_attempts=max_attempts,
            noise_ratio_threshold=noise_ratio_threshold,
        )
        
        return spatial_labels
    
    def format_output(self, 
                      profiles: List[TargetProfile],
                      start_time: str = None,
                      end_time: str = None) -> Dict[str, Any]:
        """
        格式化目标画像输出为标准JSON结构
        
        :param profiles: 目标画像列表
        :param start_time: 数据源开始时间
        :param end_time: 数据源结束时间
        :return: 格式化的字典结构
        """
        result = {
            "target_profiles": [p.to_dict() for p in profiles],
            "statistics": {"total": len(profiles)}
        }
        
        # 添加数据源时间范围
        if start_time or end_time:
            result["data_source"] = {"time_range": {}}
            if start_time:
                result["data_source"]["time_range"]["start"] = start_time
            if end_time:
                result["data_source"]["time_range"]["end"] = end_time
        
        return result
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('TargetProfileAlgorithm')
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger


def target_profile_algorithm_api(target_info: List[TargetInfo],
                                mission: List[Mission],
                                start_time: str = None,
                                end_time: str = None,
                                algorithm: Dict[str, Any] = None,
                                params: Dict[str, Any] = None) -> List[TargetProfile]:
    """
    目标画像算法API入口函数
    
    :param target_info: 目标信息数据列表
    :param mission: 历史需求数据列表
    :param start_time: 开始时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
    :param end_time: 结束时间（可选，格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
    :param algorithm: 算法配置参数（可选）
    :param params: 扩充参数（预留）
    :return: 目标画像结果列表
    """
    
    # 创建算法实例并执行
    profile_algorithm = TargetProfileAlgorithm()
    return profile_algorithm.generate_target_profile(
        target_info, mission, start_time, end_time, algorithm, params
    )


__all__ = ["TargetProfileAlgorithm", "target_profile_algorithm_api"]
