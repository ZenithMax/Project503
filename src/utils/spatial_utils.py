"""空间密度（DBSCAN 聚类）工具模块"""

import math
from typing import Dict, Iterable, List, Optional, Tuple

from ..models import TargetInfo, Trajectory

try:
    from sklearn.cluster import DBSCAN
except ImportError as exc:
    raise ImportError(
        "需要安装 scikit-learn 以运行空间密度聚类：pip install scikit-learn"
    ) from exc


EARTH_RADIUS_KM = 6371.0


def _extract_target_coordinate(target: TargetInfo) -> Optional[Tuple[float, float]]:
    """从 target 的 trajectory_list 中提取第一个合法的经纬度坐标。"""
    
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


def _haversine_coord(coord: Tuple[float, float]) -> Tuple[float, float]:
    """将经纬度（度）转换为弧度，供 haversine 度量使用。"""
    
    lon, lat = coord
    return math.radians(lon), math.radians(lat)


def compute_spatial_density_labels(
    target_info_list: Iterable[TargetInfo],
    eps_km: float = 80.0,
    min_samples: int = 3,
    auto_tune: bool = True,
    desired_min_clusters: int = 5,
    max_attempts: int = 10,
    noise_ratio_threshold: float = 0.45,
) -> Dict[str, int]:
    """
    使用 DBSCAN 对目标经纬度进行聚类，返回 target_id → cluster_id 的映射。
    
    - eps_km: 聚类的邻域半径（单位：公里），默认 80km。
    - min_samples: 构成核心点所需的最小数量。
    """
    
    coordinates: List[Tuple[float, float]] = []
    target_ids: List[str] = []
    
    for target in target_info_list:
        coord = _extract_target_coordinate(target)
        if coord is None:
            continue
        coordinates.append(coord)
        target_ids.append(target.target_id)
    
    if not coordinates:
        return {}
    
    coords_rad = [_haversine_coord(coord) for coord in coordinates]
    eps = eps_km / EARTH_RADIUS_KM
    min_samples = max(1, min(min_samples, len(coords_rad) // 2 or 1))
    
    def _apply_dbscan(cur_eps: float, cur_min_samples: int) -> List[int]:
        clustering = DBSCAN(
            eps=cur_eps,
            min_samples=cur_min_samples,
            metric="haversine",
        )
        return clustering.fit_predict(coords_rad).tolist()
    
    attempts: List[Tuple[float, int, List[int], float, int]] = []
    best_score = float("-inf")
    best_labels: Optional[List[int]] = None
    
    if auto_tune:
        eps_scales = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2][:max_attempts]
    else:
        eps_scales = [1.0]
    
    for attempt_idx, scale in enumerate(eps_scales):
        cur_eps = eps * scale
        cur_min_samples = max(
            1,
            min_samples
            - max(0, attempt_idx - len(eps_scales) // 3),
        )
        cur_min_samples = min(cur_min_samples, len(coords_rad))
        labels = _apply_dbscan(cur_eps, cur_min_samples)
        
        unique_clusters = {label for label in labels if label != -1}
        noise_ratio = labels.count(-1) / len(labels)
        
        cluster_count = len(unique_clusters)
        score = (
            cluster_count
            - abs(cluster_count - desired_min_clusters) * 0.7
            - noise_ratio
        )
        
        attempts.append((cur_eps, cur_min_samples, labels, noise_ratio, cluster_count))
        
        if len(unique_clusters) >= desired_min_clusters or (
            unique_clusters and noise_ratio <= noise_ratio_threshold
        ):
            best_labels = labels
            break
        
        if score > best_score:
            best_score = score
            best_labels = labels
    
    if best_labels is None and attempts:
        best_labels = max(attempts, key=lambda item: item[4])[2]
    elif best_labels is None:
        best_labels = [-1] * len(coords_rad)
    
    label_map: Dict[int, int] = {}
    next_label = 0
    result: Dict[str, int] = {}
    for target_id, raw_label in zip(target_ids, best_labels):
        if raw_label == -1:
            result[target_id] = -1
            continue
        if raw_label not in label_map:
            label_map[raw_label] = next_label
            next_label += 1
        result[target_id] = label_map[raw_label]
    return result


__all__ = ["compute_spatial_density_labels"]
