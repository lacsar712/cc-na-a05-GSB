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
    """一条实测签发出来的回执存档。

    签发时把实测当时的灯号、亮度、偏角、判词、附言连同正文一起冻结，
    事后改正实测不影响已签发的回执；再签发一次才产生新的一张。
    """

    inspection = models.ForeignKey(
        Inspection,
        related_name="receipts",
        on_delete=models.CASCADE,
    )
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
