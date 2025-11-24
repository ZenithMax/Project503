from typing import List, Dict, Any, Counter, Tuple, Optional
from collections import Counter as PyCounter, defaultdict
import math


class TargetTagCalculator:
    """目标画像标签计算器 - 基于统计规则"""
    
    def __init__(self, config: Dict[str, Any] = None, global_cluster_labels: Dict[str, int] = None):
        """
        初始化标签计算器
        :param config: 算法配置字典
            - top_n: 输出前N个结果，默认3
            - spatial_eps_km: DBSCAN邻域半径（公里），默认60.0
            - spatial_min_samples: DBSCAN最小样本数，默认4
            - spatial_auto_tune: 是否自动调参，默认True
            - spatial_min_clusters: 期望的最小簇数，默认7
        :param global_cluster_labels: 全局聚类结果（target_id -> cluster_id 的映射），如果提供则直接使用，否则会进行聚类
        """
        self.config = config or {}
        self.top_n = self.config.get('top_n', 3)
        self.spatial_eps_km = self.config.get('spatial_eps_km', 60.0)
        self.spatial_min_samples = self.config.get('spatial_min_samples', 4)
        self.spatial_auto_tune = self.config.get('spatial_auto_tune', True)
        self.spatial_min_clusters = self.config.get('spatial_min_clusters', 7)
        self.global_cluster_labels = global_cluster_labels  # 全局聚类结果
    
    def generate_profile_tags(self, 
                              missions: List[Any], 
                              target_info_list: List[Any]) -> Dict[str, Any]:
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
        profile_tags['preferred_scout_scenario_label'] = self._calculate_scout_scenario(missions)
        
        # 4. 空间密度标签（需要全局目标信息）
        profile_tags['spatial_density_label'] = self._calculate_spatial_density(missions, target_info_list)
        
        # 5. 目标类型标签
        profile_tags['target_type_label'] = self._calculate_target_type(missions, target_info_list)
        
        # 6. 目标优先级标签
        profile_tags['target_priority_label'] = self._calculate_target_priority(missions)

        # 7. 分辨率要求标签（新增）
        profile_tags['resolution_label'] = self._calculate_resolution(missions)

        # 8. 筹划方式标签（新增）
        profile_tags['mission_plan_type_label'] = self._calculate_mission_plan_type(missions)
        
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
        
        return self._build_top_label_stats(frequency_counter, key_name='req_times')
    
    def _calculate_scout_scenario(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算偏爱侦察场景标签"""
        scenario_counter = PyCounter()
        
        for mission in missions:
            # 统一处理 NaN 值，确保相同的场景能被正确聚合
            # 因为 NaN == NaN 返回 False，所以需要统一处理
            is_precise_value = mission.is_precise

            # 处理 None 和 NaN 值，默认值为 False（无精确需求）
            if is_precise_value is None:
                is_precise_value = False
            else:
                try:
                    # 检查是否为 NaN（NaN != NaN）
                    if is_precise_value != is_precise_value:
                        is_precise_value = False
                except (TypeError, ValueError):
                    is_precise_value = False

            # 确保是布尔类型
            is_precise_value = bool(is_precise_value)
            
            scenario_key = (
                mission.task_type or "未知类型",
                mission.scout_type or "未知侦察",
                mission.task_scene or "未知场景",
                is_precise_value,
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
                'is_precise': is_precise,  # 这里可能是 None（原为 NaN）
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return result
    
    def _calculate_spatial_density(self, missions: List[Any], target_info_list: List[Any]) -> List[Dict[str, Any]]:
        """计算空间密度标签（固定目标，簇是唯一的，只返回 cluster_id）"""
        if not missions:
            return []
        
        # 获取当前目标的 target_id
        target_id = missions[0].target_id
        
        # 如果提供了全局聚类结果，直接使用
        if self.global_cluster_labels is not None:
            cluster_id = self.global_cluster_labels.get(target_id, -1)
            return [{'cluster_id': cluster_id}]
        
        # 否则，进行聚类（向后兼容，但应该避免这种情况）
        from ..algorithms.clustering import compute_spatial_clustering_from_missions
        
        # 使用统一的接口从 missions 中提取坐标进行聚类
        # 对于目标画像，使用 target_id 作为标识符
        spatial_labels = compute_spatial_clustering_from_missions(
            missions=missions,
            target_info_list=target_info_list,
            item_id_extractor=lambda m: m.target_id,  # 使用 target_id 作为标识符
            eps_km=self.spatial_eps_km,
            min_samples=self.spatial_min_samples,
            auto_tune=self.spatial_auto_tune,
            desired_min_clusters=self.spatial_min_clusters,
        )
        
        # 获取当前目标的 cluster_id（固定目标，簇是唯一的）
        cluster_id = spatial_labels.get(target_id, -1)
        
        # 直接返回简化格式，只包含 cluster_id
        return [{'cluster_id': cluster_id}]
    
    def _calculate_target_type(self, missions: List[Any], target_info_list: List[Any]) -> List[Dict[str, Any]]:
        """计算目标类型标签（由target_type和target_category两个字段决定）"""
        if not missions:
            return []
        
        # 获取当前目标的 target_id
        target_id = missions[0].target_id
        
        # 从 target_info_list 中查找对应的目标信息
        target_info = None
        for info in target_info_list:
            if str(info.target_id) == str(target_id):
                target_info = info
                break
        
        if not target_info:
            return []
        
        # 使用 target_type 和 target_category 的组合作为 key
        type_category_key = (
            target_info.target_type or "未知类型",
            target_info.target_category or "未知类别"
        )
        
        # 统计该组合出现的次数（对于固定目标，应该只有一次，但为了保持格式一致）
        type_counter = PyCounter()
        type_counter[type_category_key] = len(missions)
        
        # 返回 top3 结果（虽然只有一个，但保持格式一致）
        total = sum(type_counter.values())
        if total == 0:
            return []
        
        top_items = sorted(type_counter.items(), key=lambda item: (-item[1], str(item[0])))[:self.top_n]
        result = []
        for (target_type, target_category), count in top_items:
            result.append({
                'target_type': target_type,
                'target_category': target_category,
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return result
    
    def _calculate_target_priority(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算目标优先级标签"""
        priority_counter = PyCounter()
        
        for mission in missions:
            priority_counter[mission.target_priority] += 1
        
        return self._build_top_label_stats(priority_counter, key_name='target_priority_label')
    
    def _parse_resolution_interval(self, interval_str: str) -> Tuple[float, float]:
        """解析分辨率区间字符串，返回 (最小值, 最大值)
           例如: "0.5-1" -> (0.5, 1.0)
        """
        try:
            if '-' not in interval_str:
                value=float(interval_str.strip())
                return (value, value)

            parts=interval_str.split('-')
            if(len(parts)!=2):
                return None

            min_val=float(parts[0].strip())
            max_val=float(parts[1].strip())

            #如果最小值大于最大值，则交换
            if min_val>max_val:
                min_val,max_val=max_val,min_val

            return (min_val, max_val)
        except(ValueError, IndexError):
            return None

    def _merge_resolution_intervals(self,intervals:List[str]) -> Optional[str]:
        """
        合并多个分辨率区间为并集
        例如: ["0.5-0.7", "0.6-0.8", "0.7-0.9"] -> "0.5-0.9"
        """
        if not intervals:
            return None
        
        parsed_intervals=[]
        for interval_str in intervals:
            parsed=self._parse_resolution_interval(interval_str)
            if parsed is not None:
                parsed_intervals.append(parsed)

        if not parsed_intervals:
            return None
        
        min_val=min(interval[0] for interval in parsed_intervals)
        max_val=max(interval[1] for interval in parsed_intervals)
        #格式化输出
        return f"{min_val:.1f}-{max_val:.1f}"

    def _calculate_resolution(self, missions: List[Any]) -> List[Dict[str,Any]]:
        """
        计算分辨率要求的标签(取TopN区间并集)
        """
        resolution_counter = PyCounter()

        for mission in missions:
            # 分辨率是 float，这里转成字符串作为标签输出
            resolution_value = getattr(mission, 'resolution', None)
            if not resolution_value:
                continue
            # resolution 是字符串类型（区间格式，如 "0.5-1"） 
            label = str(resolution_value).strip()
            # 如果标签为空，则跳过
            if not label:
                continue
            #统计标签
            resolution_counter[label]+=1
        #如果没有有效数据，则返回空列表
        if not resolution_counter:
            return []

        # 分离有效标签和无效标签
        valid_items = []
        invalid_items = []

        for label, count in resolution_counter.items():
            if self._is_invalid_label(label):
                invalid_items.append((label, count))
            else:
                valid_items.append((label, count))
        
        # 如果只有无效标签，返回简化格式
        if not valid_items:
            if invalid_items:
                return [{'resolution': "NAN"}]
            return []

        # 获取 Top-N 的有效区间
        total = sum(count for _, count in valid_items)
        top_items = sorted(valid_items, key=lambda item: (-item[1], str(item[0])))[:self.top_n]
    
        # 提取 Top-N 的区间字符串
        top_intervals = [label for label, _ in top_items]
        
        # 计算并集（返回字符串格式的区间）
        merged_interval = self._merge_resolution_intervals(top_intervals)
        
        if merged_interval is None:
            return []
        
        # 计算合并区间的统计信息（使用 Top-N 的总数）
        top_count = sum(count for _, count in top_items)
        
        # 返回一条合并后的区间记录（resolution 是字符串类型）
        return [{
            'resolution': merged_interval,  # 这是字符串，如 "0.5-0.9"
            'count': top_count,
            'percentage': round(top_count / total * 100, 2)
        }]

    def _calculate_mission_plan_type(self, missions: List[Any]) -> List[Dict[str, Any]]:
        """计算筹划方式标签（按筹划方式聚合，TopN，降序统计）"""
        plan_type_counter = PyCounter()

        for mission in missions:
            plan_type = getattr(mission, 'mission_plan_type', None)
            if not plan_type:
                plan_type = "无筹划方式"
            plan_type_counter[plan_type] += 1

        return self._build_top_label_stats(plan_type_counter, key_name='mission_plan_type')
    
    def _is_invalid_label(self, label: Any) -> bool:
        """判断标签是否为无效标签（None/NAN/未知等）"""
        if label is None:
            return True
        
        # 检查是否为 NaN（float 类型的 NaN）
        if isinstance(label, float) and math.isnan(label):
            return True
        
        label_str = str(label).strip().lower()
        invalid_values = {
            'none', 'nan', 'null', '未知类型', '未知侦察', '未知场景', 
            '未知筹划方式', '频率未指定', '未知'
        }
        
        return label_str in invalid_values or label_str == ''
    
    def _build_top_label_stats(self, counter: PyCounter, key_name: str) -> List[Dict[str, Any]]:
        """根据标签计数生成TopN统计"""
        total = sum(counter.values())
        if total == 0:
            return []
        
        # 分离有效标签和无效标签
        valid_items = []
        invalid_items = []
        
        for label, count in counter.items():
            if self._is_invalid_label(label):
                invalid_items.append((label, count))
            else:
                valid_items.append((label, count))
        
        # 如果有有效标签，只返回有效标签（过滤掉无效标签）
        if valid_items:
            top_items = sorted(valid_items, key=lambda item: (-item[1], str(item[0])))[:self.top_n]
            result = []
            for label, count in top_items:
                result.append({
                    key_name: label,
                    'count': count,
                    'percentage': round(count / total * 100, 2)
                })
            return result
        
        # 如果只有无效标签，返回简化格式（只包含 key_name 和值）
        if invalid_items:
            # 统一转换为 "NAN" 字符串
            return [{key_name: "NAN"}]
        
        return []


__all__ = ["TargetTagCalculator"]
