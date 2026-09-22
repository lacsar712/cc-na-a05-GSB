"""回执正文与校验短串的生成。

只在签发那一刻调用一次，结果随回执一起存档；
下载时直接取存档正文，不重新拼装。
"""

import hashlib

CHECKSUM_LEN = 12


def make_checksum(
    *,
    aid_code: str,
    measured_cd: float,
    required_cd: float,
    bearing_error_deg: float,
    verdict: str,
    note: str,
    issued_by: str,
    issued_at_text: str,
) -> str:
    raw = "|".join(
        str(part)
        for part in (
            aid_code,
            measured_cd,
            required_cd,
            bearing_error_deg,
            verdict,
            note,
            issued_by,
            issued_at_text,
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:CHECKSUM_LEN]


def render_body(
    *,
    aid_code: str,
    measured_cd: float,
    required_cd: float,
    bearing_error_deg: float,
    verdict: str,
    note: str,
    issued_by: str,
    issued_at_text: str,
    checksum: str,
) -> str:
    lines = [
        "航标灯光巡检回执",
        f"航标编号：{aid_code}",
        f"实测光强：{measured_cd} cd",
        f"要求光强：{required_cd} cd",
        f"方位偏差：{bearing_error_deg} 度",
        f"结论：{verdict}",
        f"说明：{note}",
        f"签发人：{issued_by}",
        f"签发时刻：{issued_at_text}",
        f"校验短串：{checksum}",
    ]
    return "\n".join(lines) + "\n"
