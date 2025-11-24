#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟任务推荐算法
基于用户画像为用户推荐最适合的虚拟任务
"""

import json
from typing import List, Dict, Any, Tuple
import logging


class VirtualTaskRecommendationAlgorithm:
    """虚拟任务推荐算法类"""
    
    def __init__(self,
                 weight_target_match: float = 0.25,
                 weight_region_match: float = 0.20,
                 weight_category_match: float = 0.20,
                 weight_topic_match: float = 0.15,
                 weight_scout_scenario: float = 0.20):
        """
        初始化推荐算法
        :param weight_target_match: 目标匹配权重 (preferred_targets)
        :param weight_region_match: 区域匹配权重 (preferred_regions)
        :param weight_category_match: 目标类别匹配权重 (preferred_target_category)
        :param weight_topic_match: 主题组匹配权重 (preferred_topic_group)
        :param weight_scout_scenario: 侦察场景匹配权重 (preferred_scout_scenario)
        """
        self.weight_target_match = weight_target_match
        self.weight_region_match = weight_region_match
        self.weight_category_match = weight_category_match
        self.weight_topic_match = weight_topic_match
        self.weight_scout_scenario = weight_scout_scenario
        
        self.logger = self._setup_logger()
        
        # 归一化权重
        total_weight = sum([
            weight_target_match,
            weight_region_match,
            weight_category_match,
            weight_topic_match,
            weight_scout_scenario
        ])
        # 使用精度容差比较浮点数
        if abs(total_weight - 1.0) > 1e-6:
            self.weight_target_match /= total_weight
            self.weight_region_match /= total_weight
            self.weight_category_match /= total_weight
            self.weight_topic_match /= total_weight
            self.weight_scout_scenario /= total_weight
    
    def recommend_tasks_for_users(self,
                                  virtual_tasks: List[Dict[str, Any]],
                                  user_personas: List[Dict[str, Any]],
                                  target_profiles: List[Dict[str, Any]],
                                  base_top_n: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        为所有用户推荐虚拟任务
        
        :param virtual_tasks: 虚拟任务列表（字典格式）
        :param user_personas: 用户画像列表（字典格式）
        :param target_profiles: 目标画像列表（字典格式）
        :param base_top_n: 基础推荐数量，会根据用户request_frequency动态调整
        :return: 字典，键为用户组，值为推荐任务列表
        """
        # 输入验证
        if base_top_n <= 0:
            raise ValueError(f"base_top_n 必须大于0，当前值: {base_top_n}")
        
        if not virtual_tasks:
            self.logger.warning("虚拟任务列表为空")
            return {}
        if not user_personas:
            self.logger.warning("用户画像列表为空")
            return {}
        if not target_profiles:
            self.logger.warning("目标画像列表为空")
            target_profiles = []  # 允许继续，但结果可能不准确
        
        self.logger.info(f"开始为 {len(user_personas)} 个用户推荐 {len(virtual_tasks)} 个虚拟任务...")
        
        # 构建目标画像映射
        target_profile_map = {
            tp['target_id']: tp for tp in target_profiles
        }
        
        all_recommendations = {}
        
        for i, user_persona in enumerate(user_personas, 1):
            user_id = user_persona.get('user_id', {})
            req_unit = user_id.get('req_unit', '')
            req_group = user_id.get('req_group', f'User_{i}')
            
            # 构建用户标识（使用req_unit和req_group）
            user_key = json.dumps({
                'req_unit': req_unit,
                'req_group': req_group
            }, ensure_ascii=False)
            
            # 根据用户的request_frequency动态计算推荐数量
            persona_tags = user_persona.get('persona_tags', {})
            user_top_n = self._calculate_recommendation_count(
                persona_tags.get('request_frequency', {}),
                base_top_n
            )
            
            # 为每个用户计算推荐
            recommendations = self._recommend_for_single_user(
                user_persona,
                virtual_tasks,
                target_profile_map,
                user_top_n
            )
            
            all_recommendations[user_key] = recommendations
            
            if i % 20 == 0:
                self.logger.info(f"  进度: {i}/{len(user_personas)}")
        
        self.logger.info("所有用户推荐生成完成")
        
        return all_recommendations
    

    ##
    # TODO
    # 1.根据内容生成的
    # 2.热点目标：
    #   有些热点目标，推送給相关用户，推1，2个
    # 3.协同先不管
    def _recommend_for_single_user(self,
                                   user_persona: Dict[str, Any],
                                   virtual_tasks: List[Dict[str, Any]],
                                   target_profile_map: Dict[str, Dict[str, Any]],
                                   top_n: int) -> List[Dict[str, Any]]:
        """为单个用户推荐虚拟任务"""
        # 计算每个虚拟任务的推荐分数
        scored_tasks = []
        
        for vt in virtual_tasks:
            target_id = vt.get('targetId')
            target_profile = target_profile_map.get(target_id, {})
            
            # 计算综合分数
            score_details = self._calculate_task_score(
                user_persona,
                vt,
                target_profile
            )
            
            scored_tasks.append({
                'task_id': vt.get('generateTaskId'),
                'target_id': target_id,
                'score': score_details['total_score']
            })
        
        # 按分数排序
        scored_tasks.sort(key=lambda x: x['score'], reverse=True)
        
        # 返回Top-N
        return scored_tasks[:top_n]
    
    def _calculate_task_score(self,
                             user_persona: Dict[str, Any],
                             virtual_task: Dict[str, Any],
                             target_profile: Dict[str, Any]) -> Dict[str, float]:
        """计算虚拟任务对用户的推荐分数"""
        persona_tags = user_persona.get('persona_tags', {})
        
        # 1. 目标匹配分数（preferred_targets）
        target_match_score = self._match_target(
            persona_tags.get('preferred_targets', []),
            virtual_task.get('targetId')
        )
        
        # 2. 区域匹配分数（preferred_regions）
        region_match_score = self._match_region_from_profile(
            persona_tags.get('preferred_regions', []),
            target_profile.get('profile_tags', {}).get('spatial_density_label', [])
        )
        
        # 3. 目标类别匹配分数（preferred_target_category）
        category_match_score = self._match_target_category(
            persona_tags.get('preferred_target_category', []),
            target_profile.get('profile_tags', {}).get('target_category', [])
        )
        
        # 4. 主题组匹配分数（preferred_topic_group）
        topic_match_score = self._match_topic_group(
            persona_tags.get('preferred_topic_group', []),
            target_profile.get('profile_tags', {}).get('topic_group', [])
        )
        
        # 5. 侦察场景匹配分数（preferred_scout_scenario）
        scenario_score = self._match_scout_scenario(
            persona_tags.get('preferred_scout_scenario', []),
            target_profile.get('profile_tags', {}).get('preferred_scout_scenario_label', [])
        )
        
        # 计算总分
        total_score = (
            target_match_score * self.weight_target_match +
            region_match_score * self.weight_region_match +
            category_match_score * self.weight_category_match +
            topic_match_score * self.weight_topic_match +
            scenario_score * self.weight_scout_scenario
        )
        
        return {
            'total_score': round(total_score, 4),
            'target_match_score': round(target_match_score, 4),
            'region_match_score': round(region_match_score, 4),
            'category_match_score': round(category_match_score, 4),
            'topic_match_score': round(topic_match_score, 4),
            'scenario_score': round(scenario_score, 4)
        }
    
    def _match_target(self,
                     preferred_targets: List[Dict],
                     target_id: str) -> float:
        """匹配用户偏好目标"""
        if not preferred_targets:
            return 0.5  # 中等分数
        
        for i, pref in enumerate(preferred_targets):
            if pref.get('target_id') == target_id:
                # 根据偏好排名给分：第一个1.0，第二个0.8，第三个0.6...
                # 都是线性的
                score = 1.0 - i * 0.2
                return max(score, 0.2)
        
        return 0.1  # 不在偏好列表中，给低分
    
    def _match_region_from_profile(self,
                                   preferred_regions: List[Dict],
                                   spatial_density_labels: List[Dict]) -> float:
        """从目标画像匹配区域"""
        # 区分无偏好和无画像两种情况
        if not preferred_regions:
            return 0.5  # 用户无区域偏好，给中等分
        if not spatial_density_labels:
            return 0.3  # 目标无区域信息，给较低分
        
        # 获取目标的簇ID（已经验证spatial_density_labels不为空）
        target_cluster = spatial_density_labels[0].get('cluster_id', -1)
        
        # 检查是否在用户偏好区域
        for i, pref in enumerate(preferred_regions):
            if pref.get('cluster_id') == target_cluster:
                score = 1.0 - i * 0.2
                return max(score, 0.2)
        
        return 0.1  # 不在偏好区域，给低分（统一最低分标准）
    
    def _match_scout_scenario(self,
                              preferred_scenarios: List[Dict],
                              target_scout_scenarios: List[Dict]) -> float:
        """匹配侦察场景（基于用户偏好与目标画像标签的重合度）"""
        # 用户无侦察偏好时直接给中等分
        if not preferred_scenarios:
            return 0.5
        # 目标画像缺少侦察场景信息时给较低分
        if not target_scout_scenarios:
            return 0.3

        def _scenario_key(item: Dict[str, Any]) -> tuple:
            """将场景字典统一转换为可比较的元组"""
            return (
                item.get('task_type', '') or '',
                item.get('scout_type', '') or '',
                item.get('task_scene', '') or '',
                bool(item.get('is_precise', False))
            )

        target_keys = {_scenario_key(s) for s in target_scout_scenarios}

        match_count = 0
        for scenario in preferred_scenarios:
            if _scenario_key(scenario) in target_keys:
                match_count += 1

        if match_count == 0:
            return 0.1  # 没有匹配时给最低分

        match_ratio = match_count / len(preferred_scenarios)
        return max(round(match_ratio, 4), 0.1)
    
    def _match_target_category(self,
                              preferred_categories: List[Dict],
                              target_categories: List[Dict]) -> float:
        """匹配目标类别（preferred_target_category）"""
        # 区分无偏好和无类别两种情况
        if not preferred_categories:
            return 0.5  # 用户无类别偏好，给中等分
        if not target_categories:
            return 0.3  # 目标无类别信息，给较低分
        
        # 提取目标类别名称
        target_category_names = set()
        for tc in target_categories:
            category = tc.get('target_category', '')
            if category:
                target_category_names.add(category)
        
        # 检查用户偏好类别是否匹配
        max_score = 0.0
        for i, pref in enumerate(preferred_categories):
            pref_category = pref.get('target_category', '')
            if pref_category in target_category_names:
                # 根据偏好排名给分：第一个1.0，第二个0.8，第三个0.6
                # TODO 是不是可以暴露出来 y = f(x)
                score = 1.0 - i * 0.2
                max_score = max(max_score, score)
        
        return max(max_score, 0.1)  # 不匹配时给低分
    
    def _match_topic_group(self,
                          preferred_topics: List[Dict],
                          target_topics: List[Dict]) -> float:
        """匹配主题组（preferred_topic_group）"""
        # 区分无偏好和无主题两种情况
        if not preferred_topics:
            return 0.5  # 用户无主题偏好，给中等分
        if not target_topics:
            return 0.3  # 目标无主题信息，给较低分
        
        # 提取目标主题组名称
        target_topic_names = set()
        for tt in target_topics:
            topic = tt.get('topic_group', '')
            if topic:
                target_topic_names.add(topic)
        
        # 检查用户偏好主题是否匹配
        match_count = 0
        for pref in preferred_topics:
            pref_topic = pref.get('topic_group', '')
            if pref_topic in target_topic_names:
                match_count += 1
        
        # 匹配度 = 匹配数量 / 用户偏好数量
        if len(preferred_topics) > 0:
            match_ratio = match_count / len(preferred_topics)
            return max(match_ratio, 0.1) if match_count > 0 else 0.1  # 至少给0.1分
        
        return 0.5
    
    def _calculate_recommendation_count(self,
                                       request_frequency: Dict[str, Any],
                                       base_count: int) -> int:
        """
        根据用户的request_frequency计算推荐数量
        
        :param request_frequency: 用户请求频率信息
        :param base_count: 基础推荐数量
        :return: 动态调整后的推荐数量
        """
        # 兼容 total_requests 和 total_count 两种字段名
        total_requests = request_frequency.get('total_requests')
        if total_requests is None:
            total_requests = request_frequency.get('total_count', 0)
        if not isinstance(total_requests, (int, float)):
            total_requests = 0
        
        # 根据请求总数调整推荐数量
        if total_requests == 0:
            # 新用户或不活跃用户：推荐较少任务
            return max(3, base_count // 2)
        elif total_requests < 5:
            # 低活跃度用户：推荐基础数量的70%
            return max(5, int(base_count * 0.7))
        elif total_requests < 10:
            # 中等活跃度用户：推荐基础数量
            return base_count
        elif total_requests < 20:
            # 较活跃用户：推荐基础数量的1.5倍
            return round(base_count * 1.5)
        else:
            # 高活跃度用户：推荐基础数量的2倍
            return base_count * 2
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('VirtualTaskRecommendation')
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger


def load_virtual_tasks_and_personas(
    virtual_task_file: str = 'outputs/virtual_tasks.json',
    user_persona_file: str = 'outputs/user_persona.json',
    target_profile_file: str = 'outputs/target_profile.json'
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    加载虚拟任务、用户画像和目标画像
    :return: (虚拟任务列表, 用户画像列表, 目标画像列表)
    """
    try:
        # 加载虚拟任务
        with open(virtual_task_file, 'r', encoding='utf-8') as f:
            vt_data = json.load(f)
        virtual_tasks = vt_data.get('virtual_tasks', [])
        
        # 加载用户画像
        with open(user_persona_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        user_personas = user_data.get('users_personas', [])
        
        # 加载目标画像
        with open(target_profile_file, 'r', encoding='utf-8') as f:
            target_data = json.load(f)
        target_profiles = target_data.get('target_profiles', [])
        
        return virtual_tasks, user_personas, target_profiles
    except FileNotFoundError as e:
        print(f"❌ 错误: 文件未找到 - {e.filename}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ 错误: JSON格式错误 - {e}")
        raise


def save_task_recommendations(
    recommendations: Dict[str, List[Dict[str, Any]]],
    output_file: str = 'outputs/recommendations.json',
    virtual_task_file: str = 'outputs/virtual_tasks.json'
):
    """保存虚拟任务推荐结果"""
    # 统计信息
    total_users = len(recommendations)
    total_recommendations = sum(len(recs) for recs in recommendations.values())
    
    # 加载虚拟任务数据
    try:
        with open(virtual_task_file, 'r', encoding='utf-8') as f:
            vt_data = json.load(f)
        virtual_tasks = vt_data.get('virtual_tasks', [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ 错误: 无法加载虚拟任务数据 - {e}")
        raise
    
    # 构建虚拟任务映射 (task_id -> 完整任务信息)
    task_map = {vt['generateTaskId']: vt for vt in virtual_tasks}
    
    # 转换为列表格式，每个元素包含user_id和推荐任务完整信息
    recommendations_list = []
    for user_key_str, tasks in recommendations.items():
        # 解析user_key，将JSON字符串转换回字典
        user_id = json.loads(user_key_str)
        
        # 获取完整的虚拟任务信息
        full_tasks = []
        for task in tasks:
            task_id = task.get('task_id')
            if not task_id:
                print(f"⚠️  警告: 推荐任务缺少 task_id 字段")
                continue
            if task_id in task_map:
                full_tasks.append(task_map[task_id])
            else:
                # 任务ID未找到，记录警告
                print(f"⚠️  警告: 任务 {task_id} 未在虚拟任务数据中找到")
        
        recommendations_list.append({
            'user_id': user_id,
            'recommended_tasks': full_tasks
        })
    
    # 计算实际保存的推荐数量
    total_recommendations_actual = sum(len(entry['recommended_tasks']) 
                                       for entry in recommendations_list)
    
    output = {
        'recommendations': recommendations_list,
        'statistics': {
            'total_users': total_users,
            'total_recommendations': total_recommendations_actual,
            'original_recommendations': total_recommendations
        }
    }
    
    # 保存文件，添加异常处理
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"✅ 虚拟任务推荐结果已保存: {output_file}")
        if total_recommendations != total_recommendations_actual:
            print(f"⚠️  注意: 原始推荐 {total_recommendations} 个，实际保存 {total_recommendations_actual} 个")
    except (IOError, OSError) as e:
        print(f"❌ 错误: 无法写入文件 {output_file} - {e}")
        raise
