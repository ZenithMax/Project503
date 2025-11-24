class Mission:
    def __init__(self,
                 req_id: str,
                 req_unit: str,
                 req_group: str,
                 req_start_time: str,
                 req_end_time: str,
                 task_type: str,
                 target_id: str,
                 country_name: str,
                 target_priority: float,
                 is_emcon: str,
                 scout_type: str,
                 task_scene: str,
                resolution: str,
                req_cycle: str,
                req_cycle_time: int,
                req_times: int,
                 mission_plan_type: str,
                 topic_id: str,
                 is_precise: bool):
        """
        历史需求数据列表
        :param req_id: 需求标识号
        :param topic_id: 专题标识号
        :param req_unit: 提出部门
        :param req_group: 提出区组
        :param req_start_time: 需求有效开始时间
        :param req_end_time: 需求结束时间
        :param task_type: 任务类型
        :param target_id: 目标标识号
        :param country_name: 国家名称
        :param target_priority: 目标优先级
        :param is_emcon: 是否电磁管制
        :param is_precise: 是否精确需求（True/False）
        :param scout_type: 侦察类型
        :param task_scene: 任务场景
        :param resolution: 分辨率（类似"0.5-1.0"这样的区间，字符串）
        :param req_cycle: 需求周期
        :param req_cycle_time: 需求周期次数
        :param req_times: 需求次数
        :param mission_plan_type: 筹划方式
        """
        self.req_id = req_id
        self.req_unit = req_unit
        self.req_group = req_group
        self.req_start_time = req_start_time
        self.req_end_time = req_end_time
        self.task_type = task_type
        self.target_id = target_id
        self.country_name = country_name
        self.target_priority = target_priority
        self.is_emcon = is_emcon
        self.scout_type = scout_type
        self.task_scene = task_scene
        self.resolution = resolution
        self.req_cycle = req_cycle
        self.req_cycle_time = req_cycle_time
        self.req_times = req_times
        self.mission_plan_type = mission_plan_type
        self.topic_id = topic_id
        self.is_precise = is_precise

