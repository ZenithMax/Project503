"""算法配置参数"""

# ==================== 用户画像算法配置 ====================

USER_PERSONA_CONFIG = {
    # ========== 基础配置 ==========
    
    # 偏好计算算法
    # 可选值: 'auto', 'percentage', 'zscore', 'tfidf', 'bm25'
    # - auto: 自动选择最优算法（推荐）
    # - percentage: 简单百分比Top-N
    # - zscore: Z-score显著性过滤
    # - tfidf: TF-IDF算法（识别用户独特偏好）
    # - bm25: BM25算法（TF-IDF改进版，带饱和度控制）
    'preference_algorithm': 'auto',
    
    # Top-N结果数量
    'top_n': 3,
    
    # ========== 算法特定参数 ==========
    
    # Z-Score算法参数
    'zscore_threshold': 2.0,        # Z-score阈值（默认2.0，约95%置信度）
                                     # 1.96: 95%置信度
                                     # 2.58: 99%置信度
                                     # 3.0:  99.7%置信度
    
    # BM25算法参数
    'bm25_k1': 1.5,                 # TF饱和度参数（默认1.5）
                                     # 范围: 1.2-2.0
                                     # 值越大，TF权重越高
                                     # 推荐: 1.2(保守), 1.5(标准), 2.0(激进)
    
    'bm25_b': 0.75,                 # 长度归一化参数（默认0.75）
                                     # 范围: 0.0-1.0
                                     # 0.0: 不考虑文档长度
                                     # 1.0: 完全归一化
                                     # 推荐: 0.75(标准)
    
    # ========== 自动选择阈值 ==========
    
    # HHI集中度阈值（用于auto模式）
    'auto_hhi_threshold': 0.05,     # HHI > 0.05 时使用percentage
    
    # 最小数据量要求
    'auto_min_users_tfidf': 10,     # TF-IDF最小用户数
    'auto_min_targets_tfidf': 20,   # TF-IDF最小目标数
    'auto_min_users_bm25': 5,       # BM25最小用户数
    'auto_min_targets_bm25': 10,    # BM25最小目标数
    'auto_min_targets_zscore': 5,   # Z-Score最小目标数
    
    # 变异系数阈值（用于选择BM25 vs TF-IDF）
    'auto_cv_threshold': 1.0,       # CV > 1.0 时优先使用BM25
}

# ==================== 目标画像算法配置 ====================

TARGET_PROFILE_CONFIG = {
    # Top-N结果数量
    'top_n': 3,
    
    # 空间聚类配置（DBSCAN）
    'spatial_eps_km': 60.0,         # 邻域半径（公里）
    'spatial_min_samples': 4,       # 最小样本数
    'spatial_auto_tune': True,      # 是否自动调参
    'spatial_min_clusters': 7,      # 期望的最小簇数
}

# ==================== 数据生成配置 ====================

DATA_GENERATOR_CONFIG = {
    'num_targets': 100,              # 默认目标数量
    'num_missions': 50000,           # 默认任务数量
    'enable_rf_users': False,        # 是否启用随机森林用户模式
    'cluster_spread_deg': 5.0,       # 簇内经纬度扰动幅度（度）
}
