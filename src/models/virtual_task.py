#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟任务数据模型
"""

from typing import List, Dict, Any, Optional
from .scout_node_input_dto import ScoutNodeInputDto


class VirtualTask:
    """虚拟任务数据模型"""
    
    def __init__(self,
                 generate_task_id: str = None,
                 target_id: str = None,
                 req_start_time: str = None,
                 req_end_time: str = None,
                 grid_code_list: str = None,
                 scout_node_input_dto: List[ScoutNodeInputDto] = None):
        """
        初始化虚拟任务
        
        :param generate_task_id: 生成虚拟任务标识号
        :param target_id: 目标标识号
        :param req_start_time: 需求开始时间
        :param req_end_time: 需求结束时间
        :param grid_code_list: 网格编码列表
        :param scout_node_input_dto: 侦察要求列表
        """
        self.generate_task_id = generate_task_id
        self.target_id = target_id
        self.req_start_time = req_start_time
        self.req_end_time = req_end_time
        self.grid_code_list = grid_code_list
        self.scout_node_input_dto = scout_node_input_dto if scout_node_input_dto is not None else []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        :return: 字典格式的数据
        """
        return {
            'generateTaskId': self.generate_task_id,
            'targetId': self.target_id,
            'reqStartTime': self.req_start_time,
            'reqEndTime': self.req_end_time,
            'gridCodeList': self.grid_code_list,
            'scoutNodeInputDto': [
                dto.to_dict() if isinstance(dto, ScoutNodeInputDto) else dto
                for dto in self.scout_node_input_dto
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VirtualTask':
        """
        从字典创建对象（支持驼峰命名和下划线命名）
        :param data: 字典数据
        :return: VirtualTask对象
        """
        # 处理侦察要求列表
        scout_list_data = data.get('scoutNodeInputDto') or data.get('scout_node_input_dto') or []
        scout_list = []
        
        for item in scout_list_data:
            if isinstance(item, ScoutNodeInputDto):
                scout_list.append(item)
            elif isinstance(item, dict):
                scout_list.append(ScoutNodeInputDto.from_dict(item))
            else:
                # 如果是其他类型，直接添加
                scout_list.append(item)
        
        return cls(
            generate_task_id=data.get('generateTaskId') or data.get('generate_task_id'),
            target_id=data.get('targetId') or data.get('target_id'),
            req_start_time=data.get('reqStartTime') or data.get('req_start_time'),
            req_end_time=data.get('reqEndTime') or data.get('req_end_time'),
            grid_code_list=data.get('gridCodeList') or data.get('grid_code_list'),
            scout_node_input_dto=scout_list
        )
    
    def add_scout_node(self, scout_node: ScoutNodeInputDto) -> None:
        """
        添加侦察节点
        :param scout_node: 侦察节点输入DTO
        """
        if isinstance(scout_node, ScoutNodeInputDto):
            self.scout_node_input_dto.append(scout_node)
        else:
            raise TypeError("scout_node must be an instance of ScoutNodeInputDto")
    
    def remove_scout_node(self, index: int) -> Optional[ScoutNodeInputDto]:
        """
        移除指定索引的侦察节点
        :param index: 索引位置
        :return: 被移除的侦察节点，如果索引无效则返回None
        """
        if 0 <= index < len(self.scout_node_input_dto):
            return self.scout_node_input_dto.pop(index)
        return None
    
    def get_scout_node_count(self) -> int:
        """
        获取侦察节点数量
        :return: 侦察节点数量
        """
        return len(self.scout_node_input_dto)
    
    def clear_scout_nodes(self) -> None:
        """清空所有侦察节点"""
        self.scout_node_input_dto.clear()
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (f"VirtualTask(generate_task_id={self.generate_task_id}, "
                f"target_id={self.target_id}, "
                f"req_start_time={self.req_start_time}, "
                f"req_end_time={self.req_end_time}, "
                f"grid_code_list={self.grid_code_list}, "
                f"scout_nodes={len(self.scout_node_input_dto)})")
    
    def __str__(self) -> str:
        """用户友好的字符串表示"""
        return self.__repr__()


__all__ = ["VirtualTask"]
