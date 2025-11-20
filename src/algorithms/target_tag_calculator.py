from typing import List, Dict, Any, Counter, Tuple, Optional
from collections import Counter as PyCounter, defaultdict
import math


class TargetTagCalculator:
    """目标画像标签计算器 - 基于统计规则"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化标签计算器
        :param config: 算法配置字典
            - top_n: 输出前N个结果，默认3
            - spatial_eps_km: DBSCAN邻域半径（公里），默认60.0
            - spatial_min_samples: DBSCAN最小样本数，默认4
            - spatial_auto_tune: 是否自动调参，默认True
            - spatial_min_clusters: 期望的最小簇数，默认7
        """
        self.config = config or {}
        self.top_n = self.config.get('top_n', 3)
        self.spatial_eps_km = self.config.get('spatial_eps_km', 60.0)
        self.spatial_min_samples = self.config.get('spatial_min_samples', 4)
        self.spatial_auto_tune = self.config.get('spatial_auto_tune', True)
        self.spatial_min_clusters = self.config.get('spatial_min_clusters', 7)
    
    def generate_profile_tags(self, missions: List[Any], target_info_list: List[Any]) -> Dict[str, Any]:
        """
        生成目标画像标签
        :param missions: 该目标的历史任务列表
        :param target_info_list: 所有目标信息列表（用于空间聚类）
        :return: 包含多个维度标签的字典
        """
        profile_tags = {}
        
        # 1. 侦察周期标签
        profile_tags['scout_cycle_label'] = self._calculate_scout_cycle(missions)
        
        # 2. 侦察频率标签
        profile_tags['scout_frequency_label'] = self._calculate_scout_frequency(missions)
        
        # 3. 偏爱侦察场景标签
        profile_tags['preferred_scout_scenario'] = self._calculate_scout_scenario(missions)
        
        # 4. 空间密度标签（需要全局目标信息）
        profile_tags['spatial_density_label'] = self._calculate_spatial_density(missions, target_info_list)
        
        # 5. 目标类型标签
        profile_tags['target_type_label'] = self._calculate_target_type(missions)
        
        # 6. 目标优先级标签
        profile_tags['target_priority_label'] = self._calculate_target_priority(missions)

        # 7. 分辨率要求标签（新增）
        profile_tags['resolution'] = self._calculate_resolution(missions)

        # 8. 筹划方式标签（新增）
        profile_tags['mission_play_type'] = self._calculate_mission_play_type(missions)
        
        return profile_tags
    
    def _calculate_scout_cycle(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算侦察周期标签"""
        from ..utils.frequency_utils import build_scout_frequency_labels
        
        cycle_counter = PyCounter()
        for mission in missions:
            frequency_labels = build_scout_frequency_labels(
                mission.req_cycle, mission.req_cycle_time, mission.req_times
            )
            cycle_counter[frequency_labels.cycle_label] += 1
        
        return self._build_top_label_stats(cycle_counter, key_name='cycle_label')
    
    def _calculate_scout_frequency(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算侦察频率标签"""
        from ..utils.frequency_utils import build_scout_frequency_labels
        
        frequency_counter = PyCounter()
        for mission in missions:
            frequency_labels = build_scout_frequency_labels(
                mission.req_cycle, mission.req_cycle_time, mission.req_times
            )
            frequency_counter[frequency_labels.frequency_label] += 1
        
        return self._build_top_label_stats(frequency_counter, key_name='scout_frequency_label')
    
    def _calculate_scout_scenario(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算偏爱侦察场景标签"""
        scenario_counter = PyCounter()
        
        for mission in missions:
            scenario_key = (
                mission.task_type or "未知类型",
                mission.scout_type or "未知侦察",
                mission.task_scene or "未知场景",
                mission.is_precise,
            )
            scenario_counter[scenario_key] += 1
        
        total = sum(scenario_counter.values())
        if total == 0:
            return []
        
        top_items = sorted(scenario_counter.items(), key=lambda item: (-item[1], item[0]))[:self.top_n]
        result = []
        for (task_type, scout_type, task_scene, is_precise), count in top_items:
            result.append({
                'task_type': task_type,
                'scout_type': scout_type,
                'task_scene': task_scene,
                'is_precise': is_precise,
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return result
    
    def _calculate_spatial_density(self, missions: List[Any], target_info_list: List[Any]) -> List[Dict[str, Any]]:
        """计算空间密度标签"""
        from ..utils.spatial_utils import compute_spatial_density_labels
        
        # 计算所有目标的空间聚类
        spatial_labels = compute_spatial_density_labels(
            target_info_list,
            eps_km=self.spatial_eps_km,
            min_samples=self.spatial_min_samples,
            auto_tune=self.spatial_auto_tune,
            desired_min_clusters=self.spatial_min_clusters,
        )
        
        # 统计当前目标的空间密度标签
        spatial_counter = PyCounter()
        for mission in missions:
            spatial_density_label = spatial_labels.get(mission.target_id, -1)
            spatial_counter[spatial_density_label] += 1
        
        return self._build_top_label_stats(spatial_counter, key_name='spatial_density_label')
    
    def _calculate_target_type(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算目标类型标签"""
        type_counter = PyCounter()
        
        # 需要从任务关联的目标信息中获取类型
        # 这里简化处理，假设任务对象中有target_type字段或通过target_id查找
        for mission in missions:
            target_type = getattr(mission, 'target_type', '未知类型')
            type_counter[target_type] += 1
        
        return self._build_top_label_stats(type_counter, key_name='target_type_label')
    
    def _calculate_target_priority(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算目标优先级标签"""
        priority_counter = PyCounter()
        
        for mission in missions:
            priority_counter[mission.target_priority] += 1
        
        return self._build_top_label_stats(priority_counter, key_name='target_priority_label')
    
    def _calculate_resolution(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算分辨率要求标签（按分辨率值聚合，TopN，降序统计）"""
        resolution_counter = PyCounter()

        for mission in missions:
            # 分辨率是 float，这里转成字符串作为标签输出
            resolution_value = getattr(mission, 'resolution', None)
            if resolution_value is None:
                continue
            label = str(resolution_value)
            resolution_counter[label] += 1

        return self._build_top_label_stats(resolution_counter, key_name='resolution')

    def _calculate_mission_play_type(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算筹划方式标签（按筹划方式聚合，TopN，降序统计）"""
        play_type_counter = PyCounter()

        for mission in missions:
            play_type = getattr(mission, 'mission_play_type', None)
            if not play_type:
                play_type = "未知筹划方式"
            play_type_counter[play_type] += 1

        return self._build_top_label_stats(play_type_counter, key_name='mission_play_type')
    
    def _build_top_label_stats(self, counter: PyCounter, key_name: str) -> List[Dict[str, Any]]:
        """根据标签计数生成TopN统计"""
        total = sum(counter.values())
        if total == 0:
            return []
        
        top_items = sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))[:self.top_n]
        result = []
        for label, count in top_items:
            result.append({
                key_name: label,
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return result


__all__ = ["TargetTagCalculator"]
