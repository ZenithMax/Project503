"""侦察周期/频率标签工具模块"""

from dataclasses import dataclass
from typing import Optional, Tuple


def _parse_cycle_interval(req_cycle: Optional[str]) -> Optional[float]:
    """
    将 req_cycle 字符串转换为"天"单位的间隔长度。
    
    支持形式：
    - "30天" / "3个月" / "2年" / "12小时"
    - "单次"、"一次" → None
    - 中文数字（如"三个月"）会被转换
    """
    
    if not req_cycle:
        return None
    
    req_cycle = req_cycle.strip()
    if req_cycle in {"单次", "一次", "临时"}:
        return None
    
    cn_digits = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "半": 0.5,
    }
    
    def _to_number(text: str) -> Optional[float]:
        if not text:
            return None
        if text.isdigit():
            return float(text)
        value = 0.0
        temp = 0.0
        for ch in text:
            if ch == "十":
                temp = max(temp, 1.0)
                value += temp * 10
                temp = 0.0
            elif ch in cn_digits:
                temp += cn_digits[ch]
            else:
                return None
        return value + temp
    
    number_part = ""
    unit_part = ""
    for ch in req_cycle:
        if ch.isdigit() or ch == ".":
            number_part += ch
        elif ch in cn_digits or ch == "十":
            number_part += ch
        else:
            unit_part += ch
    
    number_value = _to_number(number_part)
    if number_value is None or number_value <= 0:
        return None
    
    unit_part = unit_part or "天"
    if "年" in unit_part:
        return number_value * 365
    if "月" in unit_part:
        return number_value * 30
    if "周" in unit_part or "星期" in unit_part:
        return number_value * 7
    if "时" in unit_part:
        return number_value / 24
    # 默认按天处理
    return number_value


def _safe_positive_int(value: Optional[object]) -> Optional[int]:
    """安全地转换正整数。"""
    
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _build_cycle_label(req_cycle: Optional[str], req_cycle_time: Optional[object]) -> Tuple[float, str]:
    """返回 (频率值, 文字标签)。标签直接拼接周期与次数。"""
    
    cycle_count = _safe_positive_int(req_cycle_time)
    if not req_cycle or not cycle_count:
        return 0.0, "无周期需求"
    
    cycle_text = req_cycle.strip()
    normalized = _normalize_cycle_text(cycle_text)
    label = f"{normalized}{cycle_count}次"
    return float(cycle_count), label


def _normalize_cycle_text(cycle_text: str) -> str:
    """将周期文本转换为标准格式（如"1月""3周"），未知值保持原样。"""
    
    mapping = {
        "一周": "1周",
        "两周": "2周",
        "三周": "3周",
        "一个月": "1月",
        "一月": "1月",
        "两个月": "2月",
        "两月": "2月",
        "三个月": "3月",
        "三月": "3月",
        "四个月": "4月",
        "半年": "6月",
        "六个月": "6月",
        "一年": "12月",
        "两年": "24月",
    }
    return mapping.get(cycle_text, cycle_text)


def _build_req_times_label(req_times: Optional[object], cycle_freq_value: float) -> Tuple[float, str]:
    """根据 req_times 生成标签，并转换为可与周期频率比较的数值。"""
    
    req_times_val = _safe_positive_int(req_times)
    if not req_times_val:
        return cycle_freq_value, "频率未指定"
    
    freq_value = float(req_times_val)
    label = f"周期频次为{req_times_val}"
    return freq_value, label


@dataclass(frozen=True)
class ScoutFrequencyLabels:
    """同时返回侦察周期型与侦察频次标签。"""
    
    cycle_label: str
    frequency_label: str


def build_scout_frequency_labels(
    req_cycle: Optional[str],
    req_cycle_time: Optional[object],
    req_times: Optional[object],
) -> ScoutFrequencyLabels:
    """综合生成侦察周期型与侦察频次标签。"""
    
    cycle_label = _build_cycle_label(req_cycle, req_cycle_time)
    req_times_label = _build_req_times_label(req_times, cycle_label[0])
    return ScoutFrequencyLabels(cycle_label=cycle_label[1], frequency_label=req_times_label[1])


__all__ = ["ScoutFrequencyLabels", "build_scout_frequency_labels"]
