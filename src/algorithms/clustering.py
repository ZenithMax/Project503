"""DBSCAN 空间聚类模块

提供通用的 DBSCAN 聚类功能，支持多种输入格式，可用于目标画像和用户画像。
完全独立的聚类模块，包含从 TargetInfo 和 Mission 中提取坐标的功能。
"""

import math
from typing import Dict, Iterable, List, Optional, Tuple, Union, Any, Callable

try:
    from sklearn.cluster import DBSCAN
except ImportError as exc:
    raise ImportError(
        "需要安装 scikit-learn 以运行空间密度聚类：pip install scikit-learn"
    ) from exc

# 注意：模型类在函数内部延迟导入，避免循环依赖


# 地球半径（公里）
EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    计算两个经纬度坐标之间的 Haversine 距离（公里）
    
    :param coord1: (经度, 纬度) 元组，单位为度
    :param coord2: (经度, 纬度) 元组，单位为度
    :return: 距离（公里）
    """
    lon1, lat1 = math.radians(coord1[0]), math.radians(coord1[1])
    lon2, lat2 = math.radians(coord2[0]), math.radians(coord2[1])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS_KM * c


def _to_radians(coord: Tuple[float, float]) -> Tuple[float, float]:
    """将经纬度（度）转换为弧度，供 haversine 度量使用"""
    lon, lat = coord
    return math.radians(lon), math.radians(lat)


class DBSCANClustering:
    """DBSCAN 空间聚类器
    
    支持自动调参和多种输入格式，可用于地理坐标聚类。
    """
    
    def __init__(self,
                 eps_km: float = 80.0,
                 min_samples: int = 3,
                 auto_tune: bool = True,
                 desired_min_clusters: int = 5,
                 max_attempts: int = 10,
                 noise_ratio_threshold: float = 0.45):
        """
        初始化 DBSCAN 聚类器
        
        :param eps_km: 聚类的邻域半径（单位：公里），默认 80.0
        :param min_samples: 构成核心点所需的最小样本数，默认 3
        :param auto_tune: 是否自动调参，默认 True
        :param desired_min_clusters: 期望的最小簇数，默认 5
        :param max_attempts: 自动调参的最大尝试次数，默认 10
        :param noise_ratio_threshold: 噪声点比例阈值，默认 0.45
        """
        self.eps_km = eps_km
        self.min_samples = min_samples
        self.auto_tune = auto_tune
        self.desired_min_clusters = desired_min_clusters
        self.max_attempts = max_attempts
        self.noise_ratio_threshold = noise_ratio_threshold
    
    def fit_predict(self,
                    coordinates: List[Tuple[float, float]],
                    item_ids: Optional[List[Any]] = None) -> Dict[Any, int]:
        """
        对坐标列表进行 DBSCAN 聚类
        
        :param coordinates: 坐标列表，每个元素为 (经度, 纬度) 元组，单位为度
        :param item_ids: 可选的标识符列表，与 coordinates 一一对应。如果为 None，则使用索引
        :return: 标识符到簇ID的映射字典。噪声点（-1）会被保留，有效簇从 0 开始编号
        """
        if not coordinates:
            return {}
        
        # 转换坐标到弧度
        coords_rad = [_to_radians(coord) for coord in coordinates]
        
        # 计算 eps（弧度）
        eps = self.eps_km / EARTH_RADIUS_KM
        
        # 调整 min_samples
        min_samples = max(1, min(self.min_samples, len(coords_rad) // 2 or 1))
        
        # 如果没有提供 item_ids，使用索引
        if item_ids is None:
            item_ids = list(range(len(coordinates)))
        
        # 执行聚类
        labels = self._cluster_with_auto_tune(coords_rad, eps, min_samples)
        
        # 重新映射簇ID（从0开始连续编号，保留-1作为噪声）
        label_map: Dict[int, int] = {}
        next_label = 0
        result: Dict[Any, int] = {}
        
        for item_id, raw_label in zip(item_ids, labels):
            if raw_label == -1:
                result[item_id] = -1
                continue
            if raw_label not in label_map:
                label_map[raw_label] = next_label
                next_label += 1
            result[item_id] = label_map[raw_label]
        
        return result
    
    def _cluster_with_auto_tune(self,
                                coords_rad: List[Tuple[float, float]],
                                base_eps: float,
                                base_min_samples: int) -> List[int]:
        """
        执行 DBSCAN 聚类，支持自动调参
        
        :param coords_rad: 弧度坐标列表
        :param base_eps: 基础 eps 值（弧度）
        :param base_min_samples: 基础 min_samples 值
        :return: 聚类标签列表
        """
        def _apply_dbscan(cur_eps: float, cur_min_samples: int) -> List[int]:
            """应用 DBSCAN 算法"""
            clustering = DBSCAN(
                eps=cur_eps,
                min_samples=cur_min_samples,
                metric="haversine",
            )
            return clustering.fit_predict(coords_rad).tolist()
        
        # 如果不自动调参，直接使用默认参数
        if not self.auto_tune:
            return _apply_dbscan(base_eps, base_min_samples)
        
        # 自动调参：尝试不同的参数组合
        attempts: List[Tuple[float, int, List[int], float, int]] = []
        best_score = float("-inf")
        best_labels: Optional[List[int]] = None
        
        eps_scales = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2][:self.max_attempts]
        
        for attempt_idx, scale in enumerate(eps_scales):
            cur_eps = base_eps * scale
            cur_min_samples = max(
                1,
                base_min_samples - max(0, attempt_idx - len(eps_scales) // 3),
            )
            cur_min_samples = min(cur_min_samples, len(coords_rad))
            
            labels = _apply_dbscan(cur_eps, cur_min_samples)
            
            unique_clusters = {label for label in labels if label != -1}
            noise_ratio = labels.count(-1) / len(labels)
            cluster_count = len(unique_clusters)
            
            # 计算评分：簇数越多越好，但接近期望值更好，噪声越少越好
            score = (
                cluster_count
                - abs(cluster_count - self.desired_min_clusters) * 0.7
                - noise_ratio
            )
            
            attempts.append((cur_eps, cur_min_samples, labels, noise_ratio, cluster_count))
            
            # 如果满足条件，直接返回
            if len(unique_clusters) >= self.desired_min_clusters or (
                unique_clusters and noise_ratio <= self.noise_ratio_threshold
            ):
                best_labels = labels
                break
            
            # 更新最佳结果
            if score > best_score:
                best_score = score
                best_labels = labels
        
        # 如果没有找到最佳结果，从尝试中选择簇数最多的
        if best_labels is None and attempts:
            best_labels = max(attempts, key=lambda item: item[4])[2]
        elif best_labels is None:
            best_labels = [-1] * len(coords_rad)
        
        return best_labels


def cluster_coordinates(coordinates: List[Tuple[float, float]],
                       item_ids: Optional[List[Any]] = None,
                       eps_km: float = 80.0,
                       min_samples: int = 3,
                       auto_tune: bool = True,
                       desired_min_clusters: int = 5,
                       max_attempts: int = 10,
                       noise_ratio_threshold: float = 0.45) -> Dict[Any, int]:
    """
    便捷函数：对坐标列表进行 DBSCAN 聚类
    
    :param coordinates: 坐标列表，每个元素为 (经度, 纬度) 元组，单位为度
    :param item_ids: 可选的标识符列表，与 coordinates 一一对应。如果为 None，则使用索引
    :param eps_km: 聚类的邻域半径（单位：公里），默认 80.0
    :param min_samples: 构成核心点所需的最小样本数，默认 3
    :param auto_tune: 是否自动调参，默认 True
    :param desired_min_clusters: 期望的最小簇数，默认 5
    :param max_attempts: 自动调参的最大尝试次数，默认 10
    :param noise_ratio_threshold: 噪声点比例阈值，默认 0.45
    :return: 标识符到簇ID的映射字典
    """
    clustering = DBSCANClustering(
        eps_km=eps_km,
        min_samples=min_samples,
        auto_tune=auto_tune,
        desired_min_clusters=desired_min_clusters,
        max_attempts=max_attempts,
        noise_ratio_threshold=noise_ratio_threshold,
    )
    return clustering.fit_predict(coordinates, item_ids)


def _extract_target_coordinate(target: Any) -> Optional[Tuple[float, float]]:
    """
    从 target 的 trajectory_list 中提取第一个合法的经纬度坐标。
    
    :param target: TargetInfo 对象
    :return: (经度, 纬度) 元组，如果无法提取则返回 None
    """
    # 延迟导入，避免循环依赖
    from ..models import Trajectory
    
    for trajectory in target.trajectory_list:
        if not isinstance(trajectory, Trajectory):
            continue
        try:
            lon = float(trajectory.lon)
            lat = float(trajectory.lat)
        except (TypeError, ValueError):
            continue
        return lon, lat
    return None


def _extract_coordinate_from_mission(
    mission: Any,
    target_info_dict: Dict[Union[str, int], Any]
) -> Optional[Tuple[float, float]]:
    """
    从 mission 中提取坐标（通过 target_id 查找对应的 TargetInfo）。
    
    :param mission: Mission 对象
    :param target_info_dict: target_id 到 TargetInfo 的映射字典
    :return: (经度, 纬度) 元组，如果无法提取则返回 None
    """
    target_id = mission.target_id
    target_info = target_info_dict.get(target_id)
    if target_info is None:
        return None
    return _extract_target_coordinate(target_info)


def compute_spatial_density_labels(
    target_info_list: Iterable[Any],
    eps_km: float = 80.0,
    min_samples: int = 3,
    auto_tune: bool = True,
    desired_min_clusters: int = 5,
    max_attempts: int = 10,
    noise_ratio_threshold: float = 0.45,
) -> Dict[Union[str, int], int]:
    """
    使用 DBSCAN 对目标经纬度进行聚类，返回 target_id → cluster_id 的映射。
    
    此函数专门用于处理 TargetInfo 对象。
    
    :param target_info_list: 目标信息列表
    :param eps_km: 聚类的邻域半径（单位：公里），默认 80.0
    :param min_samples: 构成核心点所需的最小数量，默认 3
    :param auto_tune: 是否自动调参，默认 True
    :param desired_min_clusters: 期望的最小簇数，默认 5
    :param max_attempts: 自动调参的最大尝试次数，默认 10
    :param noise_ratio_threshold: 噪声点比例阈值，默认 0.45
    :return: target_id 到 cluster_id 的映射字典（target_id 保持原始类型）
    """
    
    coordinates: List[Tuple[float, float]] = []
    target_ids: List[Union[str, int]] = []
    
    # 提取坐标和目标ID（保持原始类型）
    for target in target_info_list:
        coord = _extract_target_coordinate(target)
        if coord is None:
            continue
        coordinates.append(coord)
        # 保持 target_id 的原始类型（可能是 str 或 int）
        target_ids.append(target.target_id)
    
    if not coordinates:
        return {}
    
    # 使用聚类模块进行聚类
    result = cluster_coordinates(
        coordinates=coordinates,
        item_ids=target_ids,
        eps_km=eps_km,
        min_samples=min_samples,
        auto_tune=auto_tune,
        desired_min_clusters=desired_min_clusters,
        max_attempts=max_attempts,
        noise_ratio_threshold=noise_ratio_threshold,
    )
    
    return result


def compute_spatial_clustering_from_missions(
    missions: Iterable[Any],
    target_info_list: Iterable[Any],
    item_id_extractor: Optional[Callable[[Any], Any]] = None,
    eps_km: float = 80.0,
    min_samples: int = 3,
    auto_tune: bool = True,
    desired_min_clusters: int = 5,
    max_attempts: int = 10,
    noise_ratio_threshold: float = 0.45,
) -> Dict[Any, int]:
    """
    从 Mission 列表中提取坐标进行 DBSCAN 聚类，返回 item_id → cluster_id 的映射。
    
    统一的聚类接口，目标画像和用户画像都可以使用。
    通过 mission.target_id 查找对应的 TargetInfo，然后提取坐标进行聚类。
    
    :param missions: Mission 列表
    :param target_info_list: 目标信息列表（用于查找坐标）
    :param item_id_extractor: 可选的函数，用于从 mission 中提取标识符。
                             如果为 None，则使用 mission.req_id 作为标识符。
                             例如：lambda m: m.target_id 或 lambda m: (m.req_unit, m.req_group)
    :param eps_km: 聚类的邻域半径（单位：公里），默认 80.0
    :param min_samples: 构成核心点所需的最小数量，默认 3
    :param auto_tune: 是否自动调参，默认 True
    :param desired_min_clusters: 期望的最小簇数，默认 5
    :param max_attempts: 自动调参的最大尝试次数，默认 10
    :param noise_ratio_threshold: 噪声点比例阈值，默认 0.45
    :return: item_id 到 cluster_id 的映射字典
    """
    
    # 构建 target_info 字典，便于快速查找
    target_info_dict = {target.target_id: target for target in target_info_list}
    
    coordinates: List[Tuple[float, float]] = []
    item_ids: List[Any] = []
    
    # 默认使用 req_id 作为标识符
    if item_id_extractor is None:
        item_id_extractor = lambda m: m.req_id
    
    # 从 missions 中提取坐标和标识符
    for mission in missions:
        coord = _extract_coordinate_from_mission(mission, target_info_dict)
        if coord is None:
            continue
        coordinates.append(coord)
        item_ids.append(item_id_extractor(mission))
    
    if not coordinates:
        return {}
    
    # 使用聚类模块进行聚类
    result = cluster_coordinates(
        coordinates=coordinates,
        item_ids=item_ids,
        eps_km=eps_km,
        min_samples=min_samples,
        auto_tune=auto_tune,
        desired_min_clusters=desired_min_clusters,
        max_attempts=max_attempts,
        noise_ratio_threshold=noise_ratio_threshold,
    )
    
    return result


__all__ = [
    "DBSCANClustering",
    "cluster_coordinates",
    "haversine_distance_km",
    "EARTH_RADIUS_KM",
    "compute_spatial_density_labels",
    "compute_spatial_clustering_from_missions",
]

