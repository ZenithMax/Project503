#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟任务推荐算法
基于用户画像为用户推荐最适合的虚拟任务
"""

import json
import math
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict
import logging


class VirtualTaskRecommendationAlgorithm:
    """虚拟任务推荐算法类"""
    
    def __init__(self,
                 # 内容推荐权重
                 weight_target_match: float = 0.25,
                 weight_region_match: float = 0.20,
                 weight_category_match: float = 0.20,
                 weight_topic_match: float = 0.15,
                 weight_scout_scenario: float = 0.20,
                 # 协同过滤参数（User-based）
                 enable_collaborative_filtering: bool = False,
                 content_weight: float = 0.7,
                 cf_weight: float = 0.3,
                 similarity_metric: str = 'cosine',
                 top_k_neighbors: int = 10):
        """
        初始化推荐算法
        
        内容推荐参数:
        :param weight_target_match: 目标匹配权重 (preferred_targets)
        :param weight_region_match: 区域匹配权重 (preferred_regions)
        :param weight_category_match: 目标类别匹配权重 (preferred_target_category)
        :param weight_topic_match: 主题组匹配权重 (preferred_topic_group)
        :param weight_scout_scenario: 侦察场景匹配权重 (preferred_scout_scenario)
        
        User-based协同过滤参数:
        :param enable_collaborative_filtering: 是否启用协同过滤 (默认False)
        :param content_weight: 内容推荐权重 (默认0.7)
        :param cf_weight: 协同过滤权重 (默认0.3)
        :param similarity_metric: 相似度度量 ('cosine' 或 'jaccard'，默认'cosine')
        :param top_k_neighbors: K近邻数量 (默认10)
        """
        # 内容推荐权重
        self.weight_target_match = weight_target_match
        self.weight_region_match = weight_region_match
        self.weight_category_match = weight_category_match
        self.weight_topic_match = weight_topic_match
        self.weight_scout_scenario = weight_scout_scenario
        
        # User-based协同过滤配置
        self.enable_cf = enable_collaborative_filtering
        self.similarity_metric = similarity_metric
        self.top_k_neighbors = top_k_neighbors
        
        # 混合推荐权重归一化
        total_hybrid_weight = content_weight + cf_weight
        self.content_weight = content_weight / total_hybrid_weight
        self.cf_weight = cf_weight / total_hybrid_weight
        
        self.logger = self._setup_logger()
        
        # 归一化内容推荐权重
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
                                  base_top_n: int = 10,
                                  user_task_interactions: Dict[str, Set[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        为所有用户推荐虚拟任务（支持混合推荐）
        
        :param virtual_tasks: 虚拟任务列表（字典格式）
        :param user_personas: 用户画像列表（字典格式）
        :param target_profiles: 目标画像列表（字典格式）
        :param base_top_n: 基础推荐数量，会根据用户request_frequency动态调整
        :param user_task_interactions: 用户-任务交互记录（可选，用于协同过滤）
                                       格式: {user_id: {task_id集合}}
                                       示例: {'用户A': {'VTASK001', 'VTASK005'}}
                                       如果为None，将基于用户画像自动构建隐式交互
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
        
        # 判断是否使用混合推荐（User-based CF）
        use_cf = self.enable_cf and len(user_personas) > 1
        if use_cf:
            self.logger.info(f"开始混合推荐 (内容:{self.content_weight:.2f} + User-based CF:{self.cf_weight:.2f}) ...")
        else:
            self.logger.info(f"开始纯内容推荐...")
        
        self.logger.info(f"为 {len(user_personas)} 个用户推荐 {len(virtual_tasks)} 个虚拟任务")
        
        # 构建目标画像映射
        target_profile_map = {
            tp['target_id']: tp for tp in target_profiles
        }
        
        # 计算User-based协同过滤分数（如果启用）
        cf_scores = {}
        if use_cf:
            self.logger.info("计算User-based协同过滤分数...")
            cf_scores = self._user_based_cf(
                user_personas, virtual_tasks, user_task_interactions
            )
            self.logger.info(f"User-based CF分数计算完成: {len(cf_scores)} 个评分")
        
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
            if use_cf:
                # 混合推荐
                recommendations = self._recommend_for_single_user_hybrid(
                    user_persona,
                    virtual_tasks,
                    target_profile_map,
                    user_top_n,
                    cf_scores
                )
            else:
                # 纯内容推荐
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
    
    def _recommend_for_single_user_hybrid(self,
                                           user_persona: Dict[str, Any],
                                           virtual_tasks: List[Dict[str, Any]],
                                           target_profile_map: Dict[str, Dict[str, Any]],
                                           top_n: int,
                                           cf_scores: Dict[Tuple[str, str], float]) -> List[Dict[str, Any]]:
        """
        分层混合推荐：为单个用户推荐虚拟任务（内容 + User-based CF）
        
        策略：
        - 80%混合推荐（内容+CF加权）：保证推荐质量
        - 20%纯CF推荐（新奇任务）：保证CF发现的新内容不被埋没
        """
        user_id = self._get_user_id(user_persona)
        hybrid_recommendations = []  # 混合推荐列表
        cf_discovery = []            # CF发现的新奇任务列表
        
        for vt in virtual_tasks:
            target_id = vt.get('targetId')
            task_id = vt.get('generateTaskId')
            target_profile = target_profile_map.get(target_id, {})
            
            # 1. 内容推荐分数
            score_details = self._calculate_task_score(user_persona, vt, target_profile)
            content_score = score_details['total_score']
            
            # 2. User-based CF分数
            cf_score = cf_scores.get((user_id, task_id), 0.0)
            
            # 3. 混合分数
            hybrid_score = self.content_weight * content_score + self.cf_weight * cf_score
            
            # 添加到混合推荐列表
            hybrid_recommendations.append({
                'task_id': task_id,
                'target_id': target_id,
                'score': round(hybrid_score, 4),
                'content_score': round(content_score, 4),
                'cf_score': round(cf_score, 4)
            })
            
            # 识别CF发现的新奇任务：CF分数高但内容分数低
            if cf_score > 0.5 and content_score < 0.3:
                cf_discovery.append({
                    'task_id': task_id,
                    'target_id': target_id,
                    'score': round(cf_score, 4),  # 纯CF分数
                    'content_score': round(content_score, 4),
                    'cf_score': round(cf_score, 4),
                    'is_discovery': True  # 标记为发现任务
                })
        
        # 排序
        hybrid_recommendations.sort(key=lambda x: x['score'], reverse=True)
        cf_discovery.sort(key=lambda x: x['score'], reverse=True)
        
        # 分层组合：80%混合 + 20%纯CF发现
        num_hybrid = int(top_n * 0.8)
        num_discovery = top_n - num_hybrid
        
        # 构建最终推荐列表
        final_recommendations = hybrid_recommendations[:num_hybrid]
        
        # 添加CF发现的新奇任务（去重）
        existing_task_ids = {task['task_id'] for task in final_recommendations}
        discovery_count = 0
        for discovery_task in cf_discovery:
            if discovery_task['task_id'] not in existing_task_ids:
                final_recommendations.append(discovery_task)
                discovery_count += 1
                if discovery_count >= num_discovery:
                    break
        
        # 如果CF发现的任务不足，用混合推荐补足
        if len(final_recommendations) < top_n:
            for task in hybrid_recommendations[num_hybrid:]:
                if task['task_id'] not in existing_task_ids:
                    final_recommendations.append(task)
                    if len(final_recommendations) >= top_n:
                        break
        
        # 📊 调试日志：输出分层推荐详情（仅第一个用户）
        if self.enable_cf and hasattr(self, '_first_user_logged'):
            pass  # 已经记录过第一个用户
        elif self.enable_cf and len(cf_discovery) > 0:
            self._first_user_logged = True
            self.logger.info(f"  【分层推荐示例】用户: {user_id[:30]}...")
            self.logger.info(f"    - 混合推荐槽位: {num_hybrid}/{top_n}")
            self.logger.info(f"    - CF发现槽位: {num_discovery}/{top_n}")
            self.logger.info(f"    - CF发现候选: {len(cf_discovery)} 个新奇任务")
            self.logger.info(f"    - 实际采用CF发现: {discovery_count} 个")
            if discovery_count > 0:
                self.logger.info(f"    ✨ 示例CF发现任务: {cf_discovery[0]['task_id']} " +
                               f"(内容分:{cf_discovery[0]['content_score']}, CF分:{cf_discovery[0]['cf_score']})")
        
        return final_recommendations[:top_n]
    
    
    def _user_based_cf(self,
                       user_personas: List[Dict[str, Any]],
                       virtual_tasks: List[Dict[str, Any]],
                       user_task_interactions: Dict[str, Set[str]] = None) -> Dict[Tuple[str, str], float]:
        """User-based协同过滤"""
        # 构建隐式交互（如果没有提供显式交互数据）
        if user_task_interactions is None:
            self.logger.info("未提供显式交互数据，基于用户画像构建隐式交互...")
            user_task_interactions = self._build_implicit_interactions(user_personas, virtual_tasks)
            self.logger.info(f"隐式交互构建完成: {len(user_task_interactions)} 个用户")
        
        # 计算用户相似度
        user_similarities = self._compute_user_similarities(user_personas)
        
        # 生成推荐
        cf_scores = {}
        for user_persona in user_personas:
            user_id = self._get_user_id(user_persona)
            interacted_tasks = user_task_interactions.get(user_id, set())
            
            # 找到K个最相似用户
            similar_users = self._get_top_k_similar_users(user_id, user_similarities, self.top_k_neighbors)
            
            # 聚合相似用户的任务偏好
            task_scores = defaultdict(float)
            for similar_user_id, similarity in similar_users:
                similar_user_tasks = user_task_interactions.get(similar_user_id, set())
                for task_id in similar_user_tasks:
                    if task_id not in interacted_tasks:
                        task_scores[task_id] += similarity
            
            # 归一化
            if task_scores:
                max_score = max(task_scores.values())
                if max_score > 0:
                    for task_id in task_scores:
                        cf_scores[(user_id, task_id)] = task_scores[task_id] / max_score
        
        return cf_scores
    
    
    def _compute_user_similarities(self, user_personas: List[Dict[str, Any]]) -> Dict[Tuple[str, str], float]:
        """计算用户相似度"""
        similarities = {}
        n = len(user_personas)
        
        for i in range(n):
            for j in range(i + 1, n):
                user_i = user_personas[i]
                user_j = user_personas[j]
                user_i_id = self._get_user_id(user_i)
                user_j_id = self._get_user_id(user_j)
                
                # 提取特征向量
                vec_i = self._extract_user_feature_vector(user_i)
                vec_j = self._extract_user_feature_vector(user_j)
                
                # 计算相似度
                similarity = self._compute_similarity(vec_i, vec_j)
                
                if similarity > 0:
                    similarities[(user_i_id, user_j_id)] = similarity
                    similarities[(user_j_id, user_i_id)] = similarity
        
        return similarities
    
    
    def _extract_user_feature_vector(self, user_persona: Dict[str, Any]) -> Dict[str, Any]:
        """提取用户特征向量"""
        persona_tags = user_persona.get('persona_tags', {})
        features = {
            'preferred_targets': set(),
            'preferred_regions': set(),
            'preferred_categories': set(),
            'preferred_topics': set(),
            'preferred_scenarios': set()
        }
        
        # 提取偏好目标
        for target in persona_tags.get('preferred_targets', []):
            features['preferred_targets'].add(target.get('target_id'))
        
        # 提取偏好区域
        for region in persona_tags.get('preferred_regions', []):
            features['preferred_regions'].add(region.get('cluster_id'))
        
        # 提取偏好类别
        for category in persona_tags.get('preferred_target_category', []):
            cat_str = f"{category.get('target_type', '')}_{category.get('target_category', '')}"
            features['preferred_categories'].add(cat_str)
        
        # 提取偏好主题
        for topic in persona_tags.get('preferred_topic_group', []):
            topic_str = f"{topic.get('topic_id', '')}_{topic.get('group_name', '')}"
            features['preferred_topics'].add(topic_str)
        
        # 提取偏好场景
        for scenario in persona_tags.get('preferred_scout_scenario', []):
            scene_str = f"{scenario.get('task_type', '')}_{scenario.get('scout_type', '')}_{scenario.get('task_scene', '')}"
            features['preferred_scenarios'].add(scene_str)
        
        return features
    
    
    def _compute_similarity(self, vec_i: Dict[str, Any], vec_j: Dict[str, Any]) -> float:
        """计算相似度"""
        if self.similarity_metric == 'cosine':
            return self._cosine_similarity(vec_i, vec_j)
        elif self.similarity_metric == 'jaccard':
            return self._jaccard_similarity(vec_i, vec_j)
        else:
            return self._cosine_similarity(vec_i, vec_j)
    
    def _cosine_similarity(self, vec_i: Dict[str, Any], vec_j: Dict[str, Any]) -> float:
        """余弦相似度"""
        total_similarity = 0.0
        count = 0
        
        for key in vec_i.keys():
            if key in vec_j:
                val_i = vec_i[key]
                val_j = vec_j[key]
                
                if isinstance(val_i, set) and isinstance(val_j, set):
                    if len(val_i) > 0 and len(val_j) > 0:
                        intersection = len(val_i & val_j)
                        union_size = math.sqrt(len(val_i) * len(val_j))
                        if union_size > 0:
                            total_similarity += intersection / union_size
                            count += 1
                elif val_i is not None and val_j is not None:
                    if val_i == val_j:
                        total_similarity += 1.0
                    count += 1
        
        return total_similarity / count if count > 0 else 0.0
    
    def _jaccard_similarity(self, vec_i: Dict[str, Any], vec_j: Dict[str, Any]) -> float:
        """Jaccard相似度"""
        total_similarity = 0.0
        count = 0
        
        for key in vec_i.keys():
            if key in vec_j:
                val_i = vec_i[key]
                val_j = vec_j[key]
                
                if isinstance(val_i, set) and isinstance(val_j, set):
                    if len(val_i) > 0 or len(val_j) > 0:
                        intersection = len(val_i & val_j)
                        union = len(val_i | val_j)
                        if union > 0:
                            total_similarity += intersection / union
                            count += 1
        
        return total_similarity / count if count > 0 else 0.0
    
    def _get_top_k_similar_users(self, user_id: str, similarities: Dict[Tuple[str, str], float], k: int) -> List[Tuple[str, float]]:
        """获取K个最相似的用户"""
        similar_users = []
        for (uid_i, uid_j), similarity in similarities.items():
            if uid_i == user_id:
                similar_users.append((uid_j, similarity))
        similar_users.sort(key=lambda x: x[1], reverse=True)
        return similar_users[:k]
    
    
    def _build_implicit_interactions(self, user_personas: List[Dict[str, Any]], virtual_tasks: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """
        基于用户画像推断用户对任务的兴趣
        
        核心逻辑：
        1. 从用户画像提取 preferred_targets（偏好目标）
        2. 找到所有包含这些目标的虚拟任务
        3. 建立映射：用户 → 感兴趣的任务集合
        
        :param user_personas: 用户画像列表
        :param virtual_tasks: 虚拟任务列表
        :return: {user_id: {task_id集合}} 映射
        """
        interactions = {}
        
        for user_persona in user_personas:
            user_id = self._get_user_id(user_persona)
            persona_tags = user_persona.get('persona_tags', {})
            
            # 步骤1：提取用户偏好目标
            preferred_targets = set()
            for target in persona_tags.get('preferred_targets', []):
                target_id = target.get('target_id')
                if target_id:
                    preferred_targets.add(target_id)
            
            # 步骤2：找到包含这些目标的虚拟任务
            task_ids = set()
            for task in virtual_tasks:
                task_target_id = task.get('targetId')
                if task_target_id in preferred_targets:
                    task_id = task.get('generateTaskId')
                    if task_id:
                        task_ids.add(task_id)
            
            # 步骤3：建立用户-任务映射
            interactions[user_id] = task_ids
        
        return interactions
    
    
    def _get_user_id(self, user_persona: Dict[str, Any]) -> str:
        """获取用户唯一标识"""
        user_id = user_persona.get('user_id', {})
        return f"{user_id.get('req_unit', '')}_{user_id.get('req_group', '')}"
    
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
