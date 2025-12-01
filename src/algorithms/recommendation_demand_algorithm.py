#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推荐需求生成算法
基于目标画像标签生成推荐需求
"""

import json
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from itertools import product
from datetime import datetime
import logging


class RecommendationDemandAlgorithm:
    """推荐需求生成算法类"""
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    def generate_recommendation_demands(self, 
                                       target_profile_json_path: str,
                                       top_n: int = 3) -> Dict[str, Any]:
        """
        基于目标画像生成推荐需求
        
        :param target_profile_json_path: 目标画像JSON文件路径
        :param top_n: 每个target_id输出前N个推荐需求（默认3）
        :return: 推荐需求结果字典
        """
        self.logger.info(f"开始生成推荐需求，读取目标画像文件: {target_profile_json_path}")
        
        # 读取目标画像JSON
        with open(target_profile_json_path, 'r', encoding='utf-8') as f:
            target_profiles_data = json.load(f)
        
        target_profiles = target_profiles_data.get('target_profiles', [])
        self.logger.info(f"共读取 {len(target_profiles)} 个目标画像")
        
        # 为每个target_id生成推荐需求（按目标ID分组）
        recommendation_demands_list = []
        total_recommendations = 0
        
        for profile in target_profiles:
            target_id = profile['target_id']
            profile_tags = profile.get('profile_tags', {})
            
            self.logger.info(f"处理目标 {target_id}")
            
            # 计算该目标的所有字段权重组合
            recommendations = self._generate_recommendations_for_target(
                target_id, 
                profile_tags, 
                top_n
            )
            
            # 添加到列表中，包含targetId字段
            recommendation_demands_list.append({
                "targetId": target_id,
                "demands": recommendations
            })
            total_recommendations += len(recommendations)
        
        # 格式化输出（数组格式）
        result = {
            "recommendation_demands": recommendation_demands_list,
            "statistics": {
                "total": total_recommendations,
                "target_count": len(target_profiles)
            },
            "generation_time": datetime.now().isoformat()
        }
        
        self.logger.info(f"推荐需求生成完成，共生成 {total_recommendations} 个推荐需求")
        return result
    
    def _generate_recommendations_for_target(self,
                                            target_id: str,
                                            profile_tags: Dict[str, Any],
                                            top_n: int) -> List[Dict[str, Any]]:
        """
        为单个target_id生成推荐需求
        
        :param target_id: 目标ID
        :param profile_tags: 目标画像标签
        :param top_n: 输出前N个
        :return: 推荐需求列表
        """
        # 提取所有独立字段的权重取值（组合单元已拆分为独立字段）
        independent_fields = self._extract_independent_fields_with_weights(profile_tags)
        
        # 计算所有字段组合的权重乘积
        combinations = self._calculate_field_combinations(independent_fields)
        
        # 排序并取前N个
        top_combinations = sorted(
            combinations, 
            key=lambda x: x['score'], 
            reverse=True
        )[:top_n]
        
        # 转换为推荐需求格式
        recommendations = []
        for idx, combo in enumerate(top_combinations):
            rec = self._build_recommendation_demand(
                target_id, 
                combo['values'], 
                profile_tags,
                combo['score']
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _extract_independent_fields_with_weights(self, 
                                                 profile_tags: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        提取所有独立字段的取值及其权重（组合单元已拆分为独立字段）
        
        :param profile_tags: 目标画像标签
        :return: 独立字段字典
        """
        independent_fields = defaultdict(list)  # 所有字段都作为独立字段
        
        # 1. 侦察场景字段拆分处理（taskType, scoutType, taskScene, isPrecise）
        # 拆分时，累加相同字段相同取值的percentage作为权重
        scenario_labels = profile_tags.get('preferred_scout_scenario_label', [])
        if scenario_labels:
            # 累加各个字段取值的percentage作为权重
            task_type_weights = defaultdict(float)
            scout_type_weights = defaultdict(float)
            task_scene_weights = defaultdict(float)
            is_precise_weights = defaultdict(float)
            
            for label in scenario_labels:
                task_type = label.get('task_type')
                scout_type = label.get('scout_type')
                task_scene = label.get('task_scene')
                is_precise = label.get('is_precise', False)
                
                # 使用percentage字段，累加相同字段相同取值的percentage
                percentage = label.get('percentage', 0) / 100.0
                
                if task_type:
                    task_type_weights[task_type] += percentage
                if scout_type:
                    scout_type_weights[scout_type] += percentage
                if task_scene:
                    task_scene_weights[task_scene] += percentage
                if is_precise is not None:
                    is_precise_weights[is_precise] += percentage
            
            # 转换为独立字段，权重不超过1.0
            for task_type, weight in task_type_weights.items():
                independent_fields['taskType'].append({
                    'value': task_type,
                    'weight': min(weight, 1.0)  # 累加不超过1.0
                })
            
            for scout_type, weight in scout_type_weights.items():
                independent_fields['scoutType'].append({
                    'value': scout_type,
                    'weight': min(weight, 1.0)
                })
            
            for task_scene, weight in task_scene_weights.items():
                independent_fields['taskScene'].append({
                    'value': task_scene,
                    'weight': min(weight, 1.0)
                })
            
            for is_precise, weight in is_precise_weights.items():
                independent_fields['isPrecise'].append({
                    'value': is_precise,
                    'weight': min(weight, 1.0)
                })
        else:
            # 默认值
            independent_fields['taskType'].append({'value': '5', 'weight': 1.0})
            independent_fields['scoutType'].append({'value': 'LDCXMB', 'weight': 1.0})
            independent_fields['taskScene'].append({'value': '1陆上态势-目标核查', 'weight': 1.0})
            independent_fields['isPrecise'].append({'value': False, 'weight': 1.0})
        
        # 2. 侦察周期型 vs 侦察频次 - 比较占比，只保留占比更高的
        cycle_labels = profile_tags.get('scout_cycle_label', [])
        frequency_labels = profile_tags.get('scout_frequency_label', [])
        
        # 计算侦察周期型标签的有效占比（排除空值/NAN）
        cycle_valid_percentage = 0.0
        for label in cycle_labels:
            cycle_label = label.get('cycle_label')
            # 排除空值、NAN等无效值
            if cycle_label and cycle_label != "NAN" and str(cycle_label).strip():
                percentage = label.get('percentage', 0)
                if percentage == 0:
                    # 如果没有percentage，尝试用count计算占比
                    count = label.get('count', 0)
                    total_count = sum(l.get('count', 0) for l in cycle_labels)
                    percentage = (count / total_count * 100.0) if total_count > 0 else 0.0
                cycle_valid_percentage += percentage
        
        # 计算侦察频次标签的有效占比（排除空值）
        frequency_valid_percentage = 0.0
        for label in frequency_labels:
            req_times = label.get('req_times')
            # 排除空值、None等无效值
            if req_times is not None and str(req_times).strip() and str(req_times) != "频率未指定":
                percentage = label.get('percentage', 0)
                if percentage == 0:
                    count = label.get('count', 0)
                    total_count = sum(l.get('count', 0) for l in frequency_labels)
                    percentage = (count / total_count * 100.0) if total_count > 0 else 0.0
                frequency_valid_percentage += percentage
        
        # 比较占比，决定优先使用哪种类型（相等时优先使用侦察周期型）
        use_cycle_type = cycle_valid_percentage >= frequency_valid_percentage
        
        # 先尝试处理占比高的类型
        cycle_has_valid_data = False
        frequency_has_valid_data = False
        
        # 处理侦察周期型标签（reqCycle, reqCycleTimes）
        if cycle_labels:
            req_cycle_weights = defaultdict(float)
            req_cycle_times_weights = defaultdict(float)
            
            for label in cycle_labels:
                cycle_label = label.get('cycle_label')
                # 只处理有效的cycle_label（排除NAN和空值）
                if cycle_label and cycle_label != "NAN" and str(cycle_label).strip():
                    percentage = label.get('percentage', 0)
                    if percentage == 0:
                        count = label.get('count', 1)
                        total_count = sum(l.get('count', 1) for l in cycle_labels)
                        percentage = (count / total_count * 100.0) if total_count > 0 else 100.0
                    percentage = percentage / 100.0
                    
                    parts = str(cycle_label).split(',')
                    if len(parts) == 2:
                        req_cycle = parts[0].strip()
                        req_cycle_times = parts[1].strip()
                        req_cycle_weights[req_cycle] += percentage
                        req_cycle_times_weights[req_cycle_times] += percentage
                        cycle_has_valid_data = True
            
            if cycle_has_valid_data:
                for req_cycle, weight in req_cycle_weights.items():
                    independent_fields['reqCycle'].append({
                        'value': req_cycle,
                        'weight': min(weight, 1.0)
                    })
                
                for req_cycle_times, weight in req_cycle_times_weights.items():
                    try:
                        value = int(float(req_cycle_times)) if req_cycle_times.replace('.', '').replace('-', '').isdigit() else 1
                    except:
                        value = 1
                    independent_fields['reqCycleTimes'].append({
                        'value': value,
                        'weight': min(weight, 1.0)
                    })
        
        # 处理侦察频次标签（reqTimes）
        if frequency_labels:
            for label in frequency_labels:
                req_times = label.get('req_times')
                if req_times is not None and str(req_times).strip() and str(req_times) != "频率未指定":
                    percentage = label.get('percentage', 0) / 100.0
                    independent_fields['reqTimes'].append({
                        'value': req_times,
                        'weight': percentage
                    })
                    frequency_has_valid_data = True
        
        # 根据占比和实际数据可用性决定最终使用哪种类型
        # 优先级：占比高的类型 > 另一个类型 > 默认值
        if use_cycle_type and cycle_has_valid_data:
            # 占比高且有有效数据，使用侦察周期型
            # 确保reqTimes为None
            if 'reqTimes' in independent_fields:
                independent_fields['reqTimes'] = []
            independent_fields['reqTimes'].append({'value': None, 'weight': 1.0})
        elif not use_cycle_type and frequency_has_valid_data:
            # 占比高且有有效数据，使用侦察频次
            # 确保reqCycle和reqCycleTimes为None
            if 'reqCycle' in independent_fields:
                independent_fields['reqCycle'] = []
            if 'reqCycleTimes' in independent_fields:
                independent_fields['reqCycleTimes'] = []
            independent_fields['reqCycle'].append({'value': None, 'weight': 1.0})
            independent_fields['reqCycleTimes'].append({'value': None, 'weight': 1.0})
        elif cycle_has_valid_data:
            # 占比高的类型没有有效数据，但另一个类型有，使用另一个类型（侦察周期型）
            # 确保reqTimes为None
            if 'reqTimes' in independent_fields:
                independent_fields['reqTimes'] = []
            independent_fields['reqTimes'].append({'value': None, 'weight': 1.0})
        elif frequency_has_valid_data:
            # 占比高的类型没有有效数据，但另一个类型有，使用另一个类型（侦察频次）
            # 确保reqCycle和reqCycleTimes为None
            if 'reqCycle' in independent_fields:
                independent_fields['reqCycle'] = []
            if 'reqCycleTimes' in independent_fields:
                independent_fields['reqCycleTimes'] = []
            independent_fields['reqCycle'].append({'value': None, 'weight': 1.0})
            independent_fields['reqCycleTimes'].append({'value': None, 'weight': 1.0})
        else:
            # 都空，使用默认值（优先使用侦察频次）
            if 'reqCycle' in independent_fields:
                independent_fields['reqCycle'] = []
            if 'reqCycleTimes' in independent_fields:
                independent_fields['reqCycleTimes'] = []
            if 'reqTimes' in independent_fields:
                independent_fields['reqTimes'] = []
            independent_fields['reqCycle'].append({'value': None, 'weight': 1.0})
            independent_fields['reqCycleTimes'].append({'value': None, 'weight': 1.0})
            independent_fields['reqTimes'].append({'value': '1', 'weight': 1.0})
        
        # 3. 目标类型组合（targetType, targetCategory）- 特殊处理
        type_labels = profile_tags.get('target_type_label', [])
        type_category_combos = defaultdict(lambda: {'count': 0, 'percentage': 0.0})
        
        for label in type_labels:
            target_type = label.get('target_type')
            target_category = label.get('target_category')
            percentage = label.get('percentage', 0) / 100.0
            
            combo_key = (target_type, target_category)
            type_category_combos[combo_key]['count'] += label.get('count', 0)
            type_category_combos[combo_key]['percentage'] += percentage
        
        # 将组合转换为独立字段（按需求说明，targetType和targetCategory分别计算权重）
        # 拆分时，累加相同字段相同取值的percentage作为权重
        type_weights = defaultdict(float)
        category_weights = defaultdict(float)
        
        for label in type_labels:
            target_type = label.get('target_type')
            target_category = label.get('target_category')
            percentage = label.get('percentage', 0) / 100.0
            # target_type的权重是累加percentage
            type_weights[target_type] += percentage
            # target_category的权重也是累加percentage
            category_weights[target_category] += percentage
        
        for target_type, weight in type_weights.items():
            independent_fields['targetType'].append({
                'value': target_type,
                'weight': min(weight, 1.0)  # 权重累加不超过1.0
            })
        
        for target_category, weight in category_weights.items():
            independent_fields['targetCategory'].append({
                'value': target_category,
                'weight': min(weight, 1.0)  # 权重累加不超过1.0
            })
        
        # 4. 独立字段
        # targetPriority - 从 target_priority_label 提取
        priority_labels = profile_tags.get('target_priority_label', [])
        if priority_labels:
            for label in priority_labels:
                priority = label.get('target_priority_label')
                percentage = label.get('percentage', 0) / 100.0
                independent_fields['targetPriority'].append({
                    'value': priority,
                    'weight': percentage
                })
        else:
            independent_fields['targetPriority'].append({
                'value': 1.0,
                'weight': 1.0
            })
        
        # resolution - 从 resolution_label 提取
        resolution_labels = profile_tags.get('resolution_label', [])
        if resolution_labels:
            for label in resolution_labels:
                resolution = label.get('resolution')
                percentage = label.get('percentage', 0) / 100.0
                independent_fields['resolution'].append({
                    'value': resolution,
                    'weight': percentage
                })
        else:
            independent_fields['resolution'].append({
                'value': '（0.5-1.0）',
                'weight': 1.0
            })
        
        # reqTimes 已在上面根据占比比较结果处理，这里不再重复处理
        
        # missionPlanType - 从 mission_plan_type_label 提取
        plan_type_labels = profile_tags.get('mission_plan_type_label', [])
        if plan_type_labels:
            for label in plan_type_labels:
                mission_plan_type = label.get('mission_plan_type')
                percentage = label.get('percentage', 0) / 100.0
                independent_fields['missionPlanType'].append({
                    'value': int(mission_plan_type) if mission_plan_type and str(mission_plan_type).isdigit() else mission_plan_type,
                    'weight': percentage
                })
        else:
            independent_fields['missionPlanType'].append({
                'value': 2,
                'weight': 1.0
            })
        
        # targetType和targetCategory如果为空，添加默认值
        if not independent_fields.get('targetType'):
            independent_fields['targetType'].append({
                'value': 'POINT',
                'weight': 1.0
            })
        
        if not independent_fields.get('targetCategory'):
            independent_fields['targetCategory'].append({
                'value': '其他',
                'weight': 1.0
            })
        
        return dict(independent_fields)
    
    def _calculate_field_combinations(self,
                                     independent_fields: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        计算所有独立字段的组合权重乘积
        
        :param independent_fields: 独立字段字典
        :return: 组合列表，每个包含values和score
        """
        # 优化：只取每个字段权重最高的前N个选项（N=3）
        optimized_fields = {}
        for field_name, field_list in independent_fields.items():
            sorted_fields = sorted(field_list, key=lambda x: x.get('weight', 0), reverse=True)
            optimized_fields[field_name] = sorted_fields[:3]
        
        # 生成所有字段的组合
        field_names = list(optimized_fields.keys())
        field_lists = [optimized_fields[field] for field in field_names]
        combinations = list(product(*field_lists)) if field_lists else []
        
        results = []
        for combo in combinations:
            # 计算权重乘积
            score = 1.0
            values = {}
            
            for field_name, field_item in zip(field_names, combo):
                values[field_name] = field_item.get('value')
                score *= field_item.get('weight', 1.0)
            
            results.append({
                'values': values,
                'score': score
            })
        
        return results
    
    def _build_recommendation_demand(self,
                                    target_id: str,
                                    field_values: Dict[str, Any],
                                    profile_tags: Dict[str, Any],
                                    score: float) -> Dict[str, Any]:
        """
        构建单个推荐需求对象
        
        :param target_id: 目标ID
        :param field_values: 字段值字典
        :param profile_tags: 目标画像标签（用于提取时间范围等信息）
        :param score: 权重得分
        :return: 推荐需求字典
        """
        # 获取数据时间范围
        data_time_range = {}
        
        # 构建时间（使用当前时间作为基准）
        now = datetime.now()
        creation_time = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # 生成reqStartTime和reqEndTime（可以基于数据时间范围，这里使用默认值）
        req_start_time = now.strftime('%Y-%m-%d %H:%M:%S')
        # 结束时间设为开始时间后7天
        from datetime import timedelta
        req_end_time = (now + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取字段值（占比比较已在_extract_independent_fields_with_weights中完成）
        # 如果使用侦察周期型，reqCycle和reqCycleTimes有值，reqTimes为None
        # 如果使用侦察频次，reqTimes有值，reqCycle和reqCycleTimes为None
        req_cycle = field_values.get('reqCycle')
        req_cycle_times = field_values.get('reqCycleTimes')
        req_times = field_values.get('reqTimes')
        
        # 判断使用哪种类型：只保留占比更高的那一个
        use_cycle = (req_cycle is not None and req_cycle_times is not None)
        use_frequency = (req_times is not None)
        
        # 如果都空，使用默认值（reqTimes='1'）
        if not use_cycle and not use_frequency:
            use_frequency = True
            req_times = '1'
        
        # 构建推荐需求对象
        # 先添加确认字段，再添加默认字段
        demand = {
            # 确认字段（从标签中提取）
            'targetId': str(target_id),
            'targetPriority': field_values.get('targetPriority', 1.0),
            'taskType': str(field_values.get('taskType', '5')),
            'scoutType': str(field_values.get('scoutType', 'LDCXMB')),
            'taskScene': str(field_values.get('taskScene', '1陆上态势-目标核查')),
            'isPrecise': str(field_values.get('isPrecise', False)),
            'resolution': str(field_values.get('resolution', '（0.5-1.0）')),
            # 根据占比比较结果设置字段：只保留占比更高的那一个，另一个不输出
        }
        
        # 只添加选择的类型的字段
        if use_cycle:
            # 使用侦察周期型，只输出reqCycle和reqCycleTimes
            demand['reqCycle'] = str(req_cycle)
            demand['reqCycleTimes'] = req_cycle_times
        elif use_frequency:
            # 使用侦察频次，只输出reqTimes
            demand['reqTimes'] = str(req_times)
        
        # 继续添加其他字段
        demand.update({
            'targetType': str(field_values.get('targetType', 'POINT')),
            'targetCategory': str(field_values.get('targetCategory', '其他')),
            'missionPlanType': field_values.get('missionPlanType', 2),
            
            # 默认字段（权重为1）
            'messageType': 'SCOUTREQ',
            'messageId': 123456,
            'originatorAddress': '中国台湾',
            'creationTime': creation_time,
            'messageStatus': 0,
            'reqCount': 1,
            'reqGround': '20251021-ZQ-2161',
            'generateReqId': '20251021-MPSS-00000901',
            'reqOperation': '0',
            'reqUnit': 'CC-BJ',
            'reqGroup': 'CC-BJ',
            'reqName': 'GE-二岛链监视区覆盖',
            'reqStartTime': req_start_time,
            'reqEndTime': req_end_time,
            'topicName': '默认专题',
            'topicId': '0',
            'topicLevel': 1.0,
            'targetName': '二岛链监视区域',
            'countryName': '未知',
            'isEmcon': '0',
            'centerLocation': '(110.4,31.5)',
            'elevation': '9',
            'reqIntervalMax': 7200.0,
            'reqIntervalMin': 3600.0,
            'speed': 0.0,
            'heading': 0.0,
            
            # 元数据
            'weight_score': score
        })
        
        return demand
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('RecommendationDemandAlgorithm')
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger


def recommendation_demand_algorithm_api(target_profile_json_path: str,
                                       top_n: int = 3) -> Dict[str, Any]:
    """
    推荐需求生成算法API入口函数
    
    :param target_profile_json_path: 目标画像JSON文件路径
    :param top_n: 每个target_id输出前N个推荐需求（默认3）
    :return: 推荐需求结果字典
    """
    algorithm = RecommendationDemandAlgorithm()
    return algorithm.generate_recommendation_demands(target_profile_json_path, top_n)


__all__ = ["RecommendationDemandAlgorithm", "recommendation_demand_algorithm_api"]

