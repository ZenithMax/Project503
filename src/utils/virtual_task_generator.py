#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟任务生成器
生成模拟的虚拟任务数据用于推荐系统测试
"""

import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
from ..models import VirtualTask, VirtualTaskAndUser, ScoutNodeInputDto


class VirtualTaskGenerator:
    """虚拟任务生成器"""
    
    def __init__(self):
        # 卫星列表
        self.satellites = ['GF-2', 'GF-3', 'GF-4', 'GF-5', 'GF-6', 'ZY-3', 'GJ-1', 'GJ-2']
        
        # 工作模式
        self.work_modes = ['Strip', 'Spotlight', 'Push-broom', 'Stare', 'Scan']
        
        # 分辨率选项
        self.resolutions = ['0.5m', '0.8m', '1.0m', '1.5m', '2.0m', '2.5m', '3.0m']
        
        # 网格编码前缀
        self.grid_prefixes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        
        # 侦察类型
        self.scout_types = ['光学侦察', '雷达侦察', '电子侦察', '信号情报', '红外侦察']
        
    def generate_virtual_tasks(self,
                               target_ids: List[str],
                               num_tasks: int = 50,
                               start_date: str = None,
                               end_date: str = None) -> List[VirtualTask]:
        """
        生成虚拟任务列表
        
        :param target_ids: 目标ID列表
        :param num_tasks: 生成的任务数量
        :param start_date: 开始日期 (YYYY-MM-DD)
        :param end_date: 结束日期 (YYYY-MM-DD)
        :return: 虚拟任务列表
        """
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        virtual_tasks = []
        
        for i in range(num_tasks):
            # 随机选择目标
            target_id = random.choice(target_ids)
            
            # 生成任务ID
            task_id = f'VTASK{i+1:04d}'
            
            # 生成时间范围
            task_start = start_dt + timedelta(
                days=random.randint(0, (end_dt - start_dt).days)
            )
            task_duration = random.randint(1, 30)  # 1-30天
            task_end = task_start + timedelta(days=task_duration)
            
            # 生成网格编码列表
            grid_codes = self._generate_grid_codes()
            
            # 生成侦察节点（1-3个）
            num_scouts = random.randint(1, 3)
            scout_nodes = [
                self._generate_scout_node(task_start, task_end)
                for _ in range(num_scouts)
            ]
            
            # 创建虚拟任务
            virtual_task = VirtualTask(
                generate_task_id=task_id,
                target_id=target_id,
                req_start_time=task_start.strftime('%Y-%m-%d %H:%M:%S'),
                req_end_time=task_end.strftime('%Y-%m-%d %H:%M:%S'),
                grid_code_list=grid_codes,
                scout_node_input_dto=scout_nodes
            )
            
            virtual_tasks.append(virtual_task)
        
        return virtual_tasks
    
    def generate_virtual_tasks_and_users(self,
                                        target_ids: List[str],
                                        user_groups: List[str],
                                        user_units: List[str],
                                        num_tasks: int = 50,
                                        start_date: str = None,
                                        end_date: str = None) -> List[VirtualTaskAndUser]:
        """
        生成虚拟任务和用户列表
        
        :param target_ids: 目标ID列表
        :param user_groups: 用户组列表
        :param user_units: 用户单位列表
        :param num_tasks: 生成的任务数量
        :param start_date: 开始日期 (YYYY-MM-DD)
        :param end_date: 结束日期 (YYYY-MM-DD)
        :return: 虚拟任务和用户列表
        """
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        virtual_tasks_users = []
        
        for i in range(num_tasks):
            # 随机选择目标
            target_id = random.choice(target_ids)
            
            # 生成任务ID
            task_id = f'VTASK_USER{i+1:04d}'
            
            # 生成时间范围
            task_start = start_dt + timedelta(
                days=random.randint(0, (end_dt - start_dt).days)
            )
            task_duration = random.randint(1, 30)
            task_end = task_start + timedelta(days=task_duration)
            
            # 随机选择用户组和单位
            req_group = random.choice(user_groups)
            req_unit = random.choice(user_units)
            
            # 生成侦察节点（1-3个）
            num_scouts = random.randint(1, 3)
            scout_nodes = [
                self._generate_scout_node(task_start, task_end)
                for _ in range(num_scouts)
            ]
            
            # 创建虚拟任务和用户
            virtual_task_user = VirtualTaskAndUser(
                generate_task_id=task_id,
                target_id=target_id,
                req_start_time=task_start.strftime('%Y-%m-%d %H:%M:%S'),
                req_end_time=task_end.strftime('%Y-%m-%d %H:%M:%S'),
                req_group=req_group,
                req_unit=req_unit,
                scout_node_input_dto=scout_nodes
            )
            
            virtual_tasks_users.append(virtual_task_user)
        
        return virtual_tasks_users
    
    def _generate_grid_codes(self) -> str:
        """生成网格编码列表"""
        num_grids = random.randint(1, 5)
        grid_codes = []
        
        for _ in range(num_grids):
            prefix = random.choice(self.grid_prefixes)
            number = random.randint(1, 999)
            grid_codes.append(f'{prefix}{number:03d}')
        
        return ','.join(grid_codes)
    
    def _generate_scout_node(self,
                            task_start: datetime,
                            task_end: datetime) -> ScoutNodeInputDto:
        """生成侦察节点"""
        # 在任务时间范围内随机选择侦察时间
        scout_duration = (task_end - task_start).days
        if scout_duration > 0:
            scout_day = random.randint(0, scout_duration)
            scout_start = task_start + timedelta(days=scout_day)
        else:
            scout_start = task_start
        
        # 侦察持续时间（1-12小时）
        scout_hours = random.randint(1, 12)
        scout_end = scout_start + timedelta(hours=scout_hours)
        
        # 随机选择参数
        satellite = random.choice(self.satellites)
        resolution = random.choice(self.resolutions)
        work_mode = random.choice(self.work_modes)
        req_cycle_times = random.randint(1, 10)
        
        # 是否添加引导卫星（30%概率）
        guide_satellite = None
        if random.random() < 0.3:
            guide_satellite = f'GUIDE-{random.randint(1, 5):02d}'
        
        # 是否添加传感器要求（40%概率）
        sensor_id = None
        sensor_mode = None
        if random.random() < 0.4:
            sensor_id = f'SENSOR-{random.randint(1, 10):03d}'
            sensor_mode = random.choice(['Panchromatic', 'Multispectral', 'SAR', 'Infrared'])
        
        # 是否添加接收站要求（30%概率）
        receiving_station = None
        receiving_ant = None
        if random.random() < 0.3:
            stations = ['北京站', '喀什站', '三亚站', '昆明站', '佳木斯站']
            receiving_station = random.choice(stations)
            receiving_ant = f'ANT-{random.randint(1, 5):02d}'
        
        return ScoutNodeInputDto(
            satellite=satellite,
            guide_satellite=guide_satellite,
            resolution=resolution,
            work_mode=work_mode,
            sensor_id=sensor_id,
            sensor_mode=sensor_mode,
            scout_start_time=scout_start.strftime('%Y-%m-%d %H:%M:%S'),
            scout_end_time=scout_end.strftime('%Y-%m-%d %H:%M:%S'),
            req_cycle_times=req_cycle_times,
            req_times=str(random.randint(1, 10)),
            req_interval_min=f'{random.randint(1, 6)}hours',
            req_interval_max=f'{random.randint(12, 48)}hours',
            target_preprocess=f'{random.randint(10, 60)}min',
            is_onboard='true' if random.random() < 0.5 else 'false',
            receiving_ant=receiving_ant,
            receiving_station=receiving_station
        )


__all__ = ["VirtualTaskGenerator"]
