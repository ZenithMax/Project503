from typing import List, Dict, Any
from collections import Counter


class PersonaTagCalculator:
    """用户画像标签计算器 - 基于统计规则"""
    
    def __init__(self, algorithm_config: Dict[str, Any] = None):
        """
        初始化标签计算器
        :param algorithm_config: 算法配置字典
            - preference_algorithm: 偏好计算算法，可选值:
                - 'auto': 自动选择（基于数据特征智能选择）[默认]
                    规则：HHI>0.05用percentage
                         HHI≤0.05时根据用户数、目标数、变异系数选择tfidf/bm25/zscore
                - 'percentage': 简单百分比Top-N
                - 'tfidf': TF-IDF算法（多用户多目标场景）
                - 'bm25': BM25算法（高变异场景，饱和控制）
                - 'zscore': Z-score显著性过滤（中等规模统计检验）
            - top_n: 输出前N个结果，默认3
            - global_stats: 全局统计信息（用于TF-IDF/BM25）
        """
        self.algorithm_config = algorithm_config or {}
        self.preference_algorithm = self.algorithm_config.get('preference_algorithm', 'auto')
        self.top_n = self.algorithm_config.get('top_n', 3)
        self.global_stats = self.algorithm_config.get('global_stats', {})
    
    def _calculate_concentration_index(self, counts: List[int]) -> Dict[str, Any]:
        """
        计算HHI集中度指标
        :param counts: 计数列表（如各目标的任务数量）
        :return: 包含HHI指标的字典
        """
        if not counts or len(counts) == 0 or sum(counts) == 0:
            return {
                'hhi': 0,
                'concentration_level': '未知',
                'is_concentrated': False
            }
        
        # 计算HHI (Herfindahl-Hirschman Index)
        # HHI = Σ(pi^2), 范围0-1，越大越集中
        total = sum(counts)
        proportions = [count / total for count in counts]
        hhi = sum(p ** 2 for p in proportions)
        
        # 简化判断：只用0.05这个关键阈值
        if hhi > 0.05:
            concentration_level = "集中"
            is_concentrated = True
        else:
            concentration_level = "分散"
            is_concentrated = False
        
        return {
            'hhi': round(hhi, 4),
            'concentration_level': concentration_level,
            'is_concentrated': is_concentrated
        }
    
    
    def generate_persona_tags(self, 
                             missions: List[Any],
                             target_info: List[Any]) -> Dict[str, Any]:
        """
        基于统计规则生成用户画像标签
        :param missions: 用户的历史任务列表
        :param target_info: 目标信息列表
        :return: 画像标签字典
        """
        if not missions:
            return {}
        persona_tags = {}
        
        # 创建目标信息字典，便于查找
        target_dict = {t.target_id: t for t in target_info}
        
        # 1. 提报需求频率标签
        persona_tags['request_frequency'] = self._calculate_request_frequency(missions)
        
        # 2. 侦察目标占比标签
        persona_tags['target_proportion'] = self._calculate_target_proportion(missions)
        
        # 3. 侦察区域占比标签
        persona_tags['region_proportion'] = self._calculate_region_proportion(missions, target_dict)
        
        # 4. 偏爱目标类别标签
        persona_tags['preferred_target_category'] = self._calculate_target_category(missions, target_dict)
        
        # 5. 偏爱目标专题与分组标签
        persona_tags['preferred_topic_group'] = self._calculate_topic_group(missions, target_dict)
        
        # 6. 偏爱侦察场景标签
        persona_tags['preferred_scout_scenario'] = self._calculate_scout_scenario(missions)
        
        return persona_tags
    
    def _calculate_request_frequency(self, missions: List[Any]) -> Dict[str, Any]:
        """计算提报需求频率标签"""
        return {
            'total_count': len(missions)
        }
    
    def _calculate_target_proportion(self, missions: List[Any]) -> Dict[str, Any]:
        """计算侦察目标占比标签 - 支持多种算法"""
        target_counts = Counter([m.target_id for m in missions])
        total = len(missions)
        counts = list(target_counts.values())
        
        # 计算集中度
        concentration = self._calculate_concentration_index(counts)
        
        # 根据算法配置选择计算方法
        algorithm = self.preference_algorithm
        
        # 自动选择算法
        if algorithm == 'auto':
            if concentration['hhi'] > 0.05:
                # 集中度较高 -> 百分比
                algorithm = 'percentage'
            else:
                # HHI <= 0.05，分散数据，需要进一步区分
                total_users = self.global_stats.get('total_users', 0) if self.global_stats else 0
                unique_targets = len(target_counts)
                
                # 检查是否有全局统计（TF-IDF和BM25需要）
                if total_users >= 10 and unique_targets >= 20:
                    # 多用户多目标 -> TF-IDF（识别用户特有偏好）
                    algorithm = 'tfidf'
                elif total_users >= 5 and unique_targets >= 10:
                    # 计算变异系数判断是否需要BM25
                    import statistics
                    mean_count = statistics.mean(counts) if counts else 0
                    std_count = statistics.stdev(counts) if len(counts) > 1 else 0
                    cv = (std_count / mean_count) if mean_count > 0 else 0
                    
                    if cv > 1.0:
                        # 高变异系数（数据差异大）-> BM25（饱和控制）
                        algorithm = 'bm25'
                    else:
                        # 中等变异 -> TF-IDF
                        algorithm = 'tfidf'
                elif unique_targets >= 5:
                    # 目标数适中，无需全局统计 -> Z-score（统计检验）
                    algorithm = 'zscore'
                else:
                    # 目标太少 -> 百分比
                    algorithm = 'percentage'
        
        # 执行对应算法
        if algorithm == 'percentage':
            return self._target_proportion_percentage(target_counts, total)
        elif algorithm == 'tfidf':
            return self._target_proportion_tfidf(target_counts, total)
        elif algorithm == 'bm25':
            return self._target_proportion_bm25(target_counts, total)
        elif algorithm == 'zscore':
            return self._target_proportion_zscore(target_counts, total, counts)
        else:
            # 默认使用百分比
            return self._target_proportion_percentage(target_counts, total)
    
    def _target_proportion_percentage(self, target_counts: Counter, total: int) -> List[Dict[str, Any]]:
        """算法1: 简单百分比Top-N"""
        top_targets = []
        for target_id, count in target_counts.most_common(self.top_n):
            top_targets.append({
                'target_id': target_id,
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return top_targets
    
    def _target_proportion_zscore(self, target_counts: Counter, total: int, 
                                  counts: List[int]) -> List[Dict[str, Any]]:
        """算法2: Z-score显著性过滤"""
        import numpy as np
        
        mean_count = np.mean(counts)
        std_count = np.std(counts)
        
        # 找出显著高于平均的目标（Z-score > 1.0）
        significant_targets = []
        for target_id, count in target_counts.items():
            z_score = (count - mean_count) / std_count if std_count > 0 else 0
            
            if z_score > 1.0:  # 高于平均1个标准差
                significant_targets.append({
                    'target_id': target_id,
                    'count': count,
                    'percentage': round(count / total * 100, 2),
                    '_z_score': z_score  # 临时用于排序
                })
        
        # 按Z-score排序
        significant_targets.sort(key=lambda x: x['_z_score'], reverse=True)
        
        # 移除内部排序字段，统一输出格式
        for item in significant_targets:
            del item['_z_score']
        
        # 如果有显著目标则返回，否则返回Top-N
        if significant_targets:
            return significant_targets[:self.top_n]
        else:
            top_by_count = []
            for target_id, count in target_counts.most_common(self.top_n):
                top_by_count.append({
                    'target_id': target_id,
                    'count': count,
                    'percentage': round(count / total * 100, 2)
                })
            return top_by_count
    
    def _target_proportion_tfidf(self, target_counts: Counter, total: int) -> List[Dict[str, Any]]:
        """算法3: TF-IDF算法"""
        import math
        
        # 从全局统计获取IDF信息
        target_user_count = self.global_stats.get('target_user_count', {})
        total_users = self.global_stats.get('total_users', 1)
        
        # 计算TF-IDF得分
        tfidf_scores = []
        for target_id, count in target_counts.items():
            # TF: 该目标在当前用户的频率
            tf = count / total
            
            # IDF: log(总用户数 / 使用该目标的用户数)
            users_with_target = target_user_count.get(target_id, 1)
            idf = math.log((total_users + 1) / (users_with_target + 1)) + 1
            
            # TF-IDF得分
            tfidf_score = tf * idf
            
            tfidf_scores.append({
                'target_id': target_id,
                'count': count,
                'percentage': round(count / total * 100, 2),
                '_tfidf_score': tfidf_score  # 临时用于排序
            })
        
        # 按TF-IDF得分排序
        tfidf_scores.sort(key=lambda x: x['_tfidf_score'], reverse=True)
        
        # 移除内部排序字段，统一输出格式
        result = []
        for item in tfidf_scores[:self.top_n]:
            result.append({
                'target_id': item['target_id'],
                'count': item['count'],
                'percentage': item['percentage']
            })
        
        return result
    
    def _target_proportion_bm25(self, target_counts: Counter, total: int) -> List[Dict[str, Any]]:
        """算法4: BM25算法"""
        import math
        
        # 从全局统计获取信息
        target_user_count = self.global_stats.get('target_user_count', {})
        total_users = self.global_stats.get('total_users', 1)
        avg_mission_count = self.global_stats.get('avg_mission_count', total)
        
        # BM25参数
        k1 = 1.5  # 控制TF饱和度
        b = 0.75  # 长度归一化参数
        
        # 计算BM25得分
        bm25_scores = []
        for target_id, count in target_counts.items():
            # IDF部分
            users_with_target = target_user_count.get(target_id, 1)
            idf = math.log((total_users - users_with_target + 0.5) / (users_with_target + 0.5) + 1)
            
            # TF部分（带饱和）
            tf_part = (count * (k1 + 1)) / (count + k1 * (1 - b + b * (total / avg_mission_count)))
            
            # BM25得分
            bm25_score = idf * tf_part
            
            bm25_scores.append({
                'target_id': target_id,
                'count': count,
                'percentage': round(count / total * 100, 2),
                '_bm25_score': bm25_score  # 临时用于排序
            })
        
        # 按BM25得分排序
        bm25_scores.sort(key=lambda x: x['_bm25_score'], reverse=True)
        
        # 移除内部排序字段，统一输出格式
        result = []
        for item in bm25_scores[:self.top_n]:
            result.append({
                'target_id': item['target_id'],
                'count': item['count'],
                'percentage': item['percentage']
            })
        
        return result
    
    def _calculate_region_proportion(self, missions: List[Any], target_dict: Dict[str, Any]) -> Dict[str, Any]:
        """计算侦察区域占比标签 - Top-N区域及占比"""
        region_counts = Counter()
        
        for mission in missions:
            target = target_dict.get(mission.target_id)
            if target and hasattr(target, 'target_area_type'):
                region_counts[target.target_area_type] += 1
        
        total = sum(region_counts.values())
        if total == 0:
            return []
        
        # 计算Top-N区域及占比
        top_regions = []
        for region, count in region_counts.most_common(self.top_n):
            top_regions.append({
                'region': region,
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return top_regions
    
    def _calculate_target_category(self, missions: List[Any], target_dict: Dict[str, Any]) -> Dict[str, Any]:
        """计算偏爱目标类别标签 - 统计target_type和target_category组合的Top-N及占比"""
        category_counts = Counter()
        
        for mission in missions:
            target = target_dict.get(mission.target_id)
            if target:
                # 组合 target_type 和 target_category
                combo = f"{target.target_type}_{target.target_category}"
                category_counts[combo] += 1
        
        total = sum(category_counts.values())
        if total == 0:
            return []
        
        # 获取Top-N组合及占比
        top_categories = []
        for combo, count in category_counts.most_common(self.top_n):
            type_category = combo.split('_', 1)
            top_categories.append({
                'target_type': type_category[0] if len(type_category) > 0 else '',
                'target_category': type_category[1] if len(type_category) > 1 else '',
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return top_categories
    
    def _calculate_topic_group(self, missions: List[Any], target_dict: Dict[str, Any]) -> Dict[str, Any]:
        """计算偏爱目标专题与分组标签 - 统计topic_id和group_list组合的Top-N及占比"""
        topic_group_counts = Counter()
        
        for mission in missions:
            topic_id = mission.topic_id
            target = target_dict.get(mission.target_id)
            
            if target and hasattr(target, 'group_list') and target.group_list:
                # 遍历目标的所有分组
                for group in target.group_list:
                    group_name = group.group_name if hasattr(group, 'group_name') else str(group)
                    combo = f"{topic_id}_{group_name}"
                    topic_group_counts[combo] += 1
            else:
                # 如果没有group_list，只统计topic_id
                combo = f"{topic_id}_无分组"
                topic_group_counts[combo] += 1
        
        total = sum(topic_group_counts.values())
        if total == 0:
            return []
        
        # 获取Top-N组合及占比
        top_combinations = []
        for combo, count in topic_group_counts.most_common(self.top_n):
            parts = combo.split('_', 1)
            top_combinations.append({
                'topic_id': parts[0] if len(parts) > 0 else '',
                'group_name': parts[1] if len(parts) > 1 else '',
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return top_combinations
    
    def _calculate_scout_scenario(self, missions: List[Any]) -> Dict[str, Any]:
        """计算偏爱侦察场景标签 - 统计task_type, scout_type, task_scene, is_precise组合的Top-N及占比"""
        scenario_counts = Counter()
        
        for mission in missions:
            # 使用4个字段组合：task_type, scout_type, task_scene, is_precise
            # 将布尔值转换为字符串用于组合键
            is_precise_key = str(mission.is_precise)
            combo = f"{mission.task_type}_{mission.scout_type}_{mission.task_scene}_{is_precise_key}"
            scenario_counts[combo] += 1
        
        total = len(missions)
        if total == 0:
            return []
        
        # 获取Top-N组合及占比
        top_scenarios = []
        for combo, count in scenario_counts.most_common(self.top_n):
            parts = combo.rsplit('_', 3)
            # 将字符串 'True'/'False' 转换回布尔值
            is_precise_str = parts[3] if len(parts) > 3 else 'False'
            is_precise_bool = is_precise_str == 'True'
            
            top_scenarios.append({
                'task_type': parts[0] if len(parts) > 0 else '',
                'scout_type': parts[1] if len(parts) > 1 else '',
                'task_scene': parts[2] if len(parts) > 2 else '',
                'is_precise': is_precise_bool,
                'count': count,
                'percentage': round(count / total * 100, 2)
            })
        
        return top_scenarios
