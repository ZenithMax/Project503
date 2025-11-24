class UserPersona:
    def __init__(self,
                 user_id: dict,
                 persona_tags: dict,
                 generation_time: str,
                 data_time_range: dict = None):
        """
        用户画像结果数据模型（简化版 - 基于统计规则）
        :param user_id: 用户身份信息字典 {'req_unit': 部门, 'req_group': 区组}
        :param persona_tags: 画像标签字典，包含各种分类结果
        :param generation_time: 生成时间
        :param data_time_range: 数据源时间范围 {'start_time': 开始时间, 'end_time': 结束时间}
        """
        self.user_id = user_id
        self.persona_tags = persona_tags
        self.generation_time = generation_time
        self.data_time_range = data_time_range or {}

    def to_dict(self):
        """转换为字典格式"""
        result = {
            'user_id': self.user_id,
            'persona_tags': self.persona_tags,
            'generation_time': self.generation_time
        }
        if self.data_time_range:
            result['data_time_range'] = self.data_time_range
        return result
