class TargetInfo:
    def __init__(self,
                 target_id: str,
                 target_name: str,
                 target_type: str,
                 target_category: str,
                 target_priority: float,
                 target_area_type: str,
                 group_list: list,
                 trajectory_list: list):
        """
        目标信息数据列表
        :param target_id: 目标标识号
        :param target_name: 目标名称
        :param target_type: 目标类型
        :param target_category: 目标种类
        :param target_priority: 目标优先级
        :param target_area_type: 目标区域类型
        :param group_list: 分组列表
        :param trajectory_list: 轨迹列表
        """
        self.target_id = target_id
        self.target_name = target_name
        self.target_type = target_type
        self.target_category = target_category
        self.target_priority = target_priority
        self.target_area_type = target_area_type
        self.group_list = group_list
        self.trajectory_list = trajectory_list

class Group:
    def __init__(self,
                 group_name: str,
                 source: str,
                 status: str):
        """
        目标分组数据列表
        :param group_name: 组名称
        :param source: 数据来源
        :param status: 状态
        """
        self.group_name = group_name
        self.source = source
        self.status = status

class Trajectory:
    def __init__(self,
                 lon: str,
                 lat: str,
                 alt: str,
                 point_time: str,
                 speed: str,
                 heading: str,
                 seq: str,
                 elect_silence: str):
        """
        目标轨迹数据列表
        :param lon: 经度
        :param lat: 纬度
        :param alt: 高度
        :param point_time: 时间点
        :param speed: 轨迹速度
        :param heading: 轨迹航向
        :param seq: 序号
        :param elect_silence: 电子静默
        """
        self.lon = lon
        self.lat = lat
        self.alt = alt
        self.point_time = point_time
        self.speed = speed
        self.heading = heading
        self.seq = seq
        self.elect_silence = elect_silence

