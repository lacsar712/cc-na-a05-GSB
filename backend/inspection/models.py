from django.db import models
from django.utils import timezone


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class Receipt(models.Model):
    """签发即冻结的回执存档：正文与校验短串落库后不再改动。"""

    inspection = models.ForeignKey(
        Inspection,
        verbose_name="实测",
        related_name="receipts",
        on_delete=models.CASCADE,
    )
    serial = models.CharField("回执编号", max_length=20, unique=True)
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    body = models.TextField("回执正文")
    checksum = models.CharField("校验短串", max_length=16)
    issued_by = models.CharField("签发人", max_length=64)
    issued_at = models.DateTimeField("签发时刻", default=timezone.now)

    class Meta:
        ordering = ["-id"]
