"""统一数据模型模块"""

# 基础数据模型
from .mission import Mission
from .target_info import TargetInfo, Group, Trajectory

# 画像模型
from .user_persona import UserPersona
from .target_profile import TargetProfile

# DTO模型
from .scout_node_input_dto import ScoutNodeInputDto
from .virtual_task import VirtualTask

__all__ = [
    "Mission", 
    "TargetInfo", 
    "Group", 
    "Trajectory",
    "UserPersona",
    "TargetProfile",
    "ScoutNodeInputDto",
    "VirtualTask",
]
