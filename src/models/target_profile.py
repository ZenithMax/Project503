"""目标画像数据模型"""

from datetime import datetime
from typing import Dict, Any


class TargetProfile:
    """目标画像数据模型"""
    
    def __init__(self,
                 target_id: str,
                 profile_tags: Dict[str, Any],
                 generation_time: str = None):
        """
        初始化目标画像
        :param target_id: 目标标识号
        :param profile_tags: 目标画像标签（包含多个维度的标签）
        :param generation_time: 画像生成时间
        """
        self.target_id = target_id
        self.profile_tags = profile_tags
        self.generation_time = generation_time or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将目标画像转换为字典格式
        :return: 字典格式的目标画像
        """
        return {
            'target_id': self.target_id,
            'profile_tags': self.profile_tags,
            'generation_time': self.generation_time
        }


__all__ = ["TargetProfile"]
