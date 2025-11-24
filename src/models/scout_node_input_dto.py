#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
侦察节点输入DTO数据模型
"""

from typing import Optional, Dict, Any


class ScoutNodeInputDto:
    """侦察节点输入DTO数据模型"""
    
    def __init__(self,
                 satellite: str = None,
                 guide_satellite: str = None,
                 resolution: str = None,
                 work_mode: str = None,
                 sensor_id: str = None,
                 sensor_mode: str = None,
                 scout_start_time: str = None,
                 scout_end_time: str = None,
                 req_cycle: str = None,
                 req_cycle_times: int = None,
                 req_times: str = None,
                 req_interval_min: str = None,
                 req_interval_max: str = None,
                 target_preprocess: str = None,
                 is_onboard: str = None,
                 receiving_ant: str = None,
                 receiving_station: str = None):
        """
        初始化侦察节点输入DTO
        
        :param satellite: 卫星代号
        :param guide_satellite: 引导卫星
        :param resolution: 分辨率要求
        :param work_mode: 工作模式要求
        :param sensor_id: 传感器代号要求
        :param sensor_mode: 传感器模式要求
        :param scout_start_time: 侦察开始时间
        :param scout_end_time: 侦察结束时间
        :param req_cycle: 需求侦察频次周期间隔时间
        :param req_cycle_times: 需求侦察频次周期间隔次数
        :param req_times: 侦察次数
        :param req_interval_min: 最小侦察间隔时间
        :param req_interval_max: 最大侦察间隔时间
        :param target_preprocess: 目标侦察时长要求
        :param is_onboard: 目标是否广播分发
        :param receiving_ant: 接收天线名要求
        :param receiving_station: 接收站要求
        """
        self.satellite = satellite
        self.guide_satellite = guide_satellite
        self.resolution = resolution
        self.work_mode = work_mode
        self.sensor_id = sensor_id
        self.sensor_mode = sensor_mode
        self.scout_start_time = scout_start_time
        self.scout_end_time = scout_end_time
        self.req_cycle = req_cycle
        self.req_cycle_times = req_cycle_times
        self.req_times = req_times
        self.req_interval_min = req_interval_min
        self.req_interval_max = req_interval_max
        self.target_preprocess = target_preprocess
        self.is_onboard = is_onboard
        self.receiving_ant = receiving_ant
        self.receiving_station = receiving_station
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        :return: 字典格式的数据
        """
        return {
            'satellite': self.satellite,
            'guideSatellite': self.guide_satellite,
            'resolution': self.resolution,
            'workMode': self.work_mode,
            'sensorId': self.sensor_id,
            'sensorMode': self.sensor_mode,
            'scoutStartTime': self.scout_start_time,
            'scoutEndTime': self.scout_end_time,
            'reqCycle': self.req_cycle,
            'reqCycleTimes': self.req_cycle_times,
            'reqTimes': self.req_times,
            'reqIntervalMin': self.req_interval_min,
            'reqIntervalMax': self.req_interval_max,
            'targetPreprocess': self.target_preprocess,
            'isOnboard': self.is_onboard,
            'receivingAnt': self.receiving_ant,
            'receivingStation': self.receiving_station
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScoutNodeInputDto':
        """
        从字典创建对象（支持驼峰命名和下划线命名）
        :param data: 字典数据
        :return: ScoutNodeInputDto对象
        """
        # 支持驼峰命名格式的字段名
        return cls(
            satellite=data.get('satellite') or data.get('satellite'),
            guide_satellite=data.get('guideSatellite') or data.get('guide_satellite'),
            resolution=data.get('resolution') or data.get('resolution'),
            work_mode=data.get('workMode') or data.get('work_mode'),
            sensor_id=data.get('sensorId') or data.get('sensor_id'),
            sensor_mode=data.get('sensorMode') or data.get('sensor_mode'),
            scout_start_time=data.get('scoutStartTime') or data.get('scout_start_time'),
            scout_end_time=data.get('scoutEndTime') or data.get('scout_end_time'),
            req_cycle=data.get('reqCycle') or data.get('req_cycle'),
            req_cycle_times=data.get('reqCycleTimes') or data.get('req_cycle_times'),
            req_times=data.get('reqTimes') or data.get('req_times'),
            req_interval_min=data.get('reqIntervalMin') or data.get('req_interval_min'),
            req_interval_max=data.get('reqIntervalMax') or data.get('req_interval_max'),
            target_preprocess=data.get('targetPreprocess') or data.get('target_preprocess'),
            is_onboard=data.get('isOnboard') or data.get('is_onboard'),
            receiving_ant=data.get('receivingAnt') or data.get('receiving_ant'),
            receiving_station=data.get('receivingStation') or data.get('receiving_station')
        )
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (f"ScoutNodeInputDto(satellite={self.satellite}, "
                f"guide_satellite={self.guide_satellite}, "
                f"resolution={self.resolution}, "
                f"work_mode={self.work_mode}, "
                f"scout_start_time={self.scout_start_time}, "
                f"scout_end_time={self.scout_end_time})")
    
    def __str__(self) -> str:
        """用户友好的字符串表示"""
        return self.__repr__()


__all__ = ["ScoutNodeInputDto"]
