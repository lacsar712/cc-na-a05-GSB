import hashlib
import uuid

from django.utils import timezone


def new_serial() -> str:
    return "R-" + uuid.uuid4().hex[:8].upper()


def render_body(
    *,
    serial: str,
    aid_code: str,
    measured_cd: float,
    required_cd: float,
    bearing_error_deg: float,
    verdict: str,
    note: str,
    issued_by: str,
    issued_at,
) -> tuple[str, str]:
    """签发当时把正文一次拼好并算出校验短串，之后存档原文不再改动。"""
    content = "\n".join(
        [
            "航标灯光巡检回执",
            f"回执编号：{serial}",
            f"灯号：{aid_code}",
            f"实测光强：{measured_cd} cd",
            f"要求光强：{required_cd} cd",
            f"方位偏差：{bearing_error_deg} 度",
            f"判词：{verdict}",
            f"附言：{note}",
            f"签发人：{issued_by}",
            f"签发时刻：{timezone.localtime(issued_at).isoformat(timespec='seconds')}",
        ]
    )
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    body = content + f"\n校验短串：{checksum}\n"
    return body, checksum
