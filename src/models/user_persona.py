class UserPersona:
    def __init__(self,
                 user_id: dict,
                 persona_tags: dict,
                 generation_time: str):
        """
        用户画像结果数据模型（简化版 - 基于统计规则）
        :param user_id: 用户身份信息字典 {'req_unit': 部门, 'req_group': 区组}
        :param persona_tags: 画像标签字典，包含各种分类结果
        :param generation_time: 生成时间
        """
        self.user_id = user_id
        self.persona_tags = persona_tags
        self.generation_time = generation_time

    def to_dict(self):
        """转换为字典格式"""
        return {
            'user_id': self.user_id,
            'persona_tags': self.persona_tags,
            'generation_time': self.generation_time
        }
