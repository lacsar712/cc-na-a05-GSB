from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from inspection.models import Inspection, Receipt
from inspection.rules import judge


def _make_dim_seed() -> Inspection:
    verdict, note = judge(800, 1200, 0.2)
    return Inspection.objects.create(
        aid_code="LH-09",
        measured_cd=800,
        required_cd=1200,
        bearing_error_deg=0.2,
        verdict=verdict,
        note=note,
        created_by="keeper",
    )


class ReceiptFlowTests(TestCase):
    """交卷流程：偏暗种子签发 -> 下载含光强不足 -> 改高亮度 -> 旧回执正文不变。"""

    @classmethod
    def setUpTestData(cls):
        group = Group.objects.create(name="inspector")
        keeper = User.objects.create_user(username="keeper", password="light123456")
        keeper.groups.add(group)
        User.objects.create_user(username="watch", password="watch123456")

    def setUp(self):
        self.seed = _make_dim_seed()

    def _login(self, username):
        passwords = {"keeper": "light123456", "watch": "watch123456"}
        self.client.login(username=username, password=passwords[username])

    def test_issue_download_then_correct_keeps_frozen_body(self):
        self._login("keeper")

        # 先给偏暗种子签发一张回执
        response = self.client.post(reverse("issue_receipt", args=[self.seed.pk]))
        receipt = Receipt.objects.get()
        self.assertRedirects(response, reverse("receipt_detail", args=[receipt.pk]))
        self.assertEqual(receipt.measured_cd, 800)
        self.assertEqual(receipt.verdict, "不合格")

        # 下载文本里要有 光强不足
        response = self.client.get(reverse("receipt_download", args=[receipt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        text = response.content.decode("utf-8")
        self.assertIn("光强不足", text)
        self.assertIn("800", text)
        self.assertEqual(text, receipt.body)

        # 再把该条亮度改高，实测记录随之更新
        response = self.client.post(
            reverse("correct", args=[self.seed.pk]), {"measured_cd": "1500"}
        )
        self.assertRedirects(response, reverse("detail", args=[self.seed.pk]))
        self.seed.refresh_from_db()
        self.assertEqual(self.seed.measured_cd, 1500)
        self.assertEqual(self.seed.verdict, "合格")

        # 详情页能渲染：改正表单、签发入口、已签发的回执列表
        response = self.client.get(reverse("detail", args=[self.seed.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "签发回执")
        self.assertContains(response, "改正亮度")
        self.assertContains(response, receipt.checksum)

        # 打开刚才那张：正文仍是改之前的亮度，校验短串不变
        receipt.refresh_from_db()
        self.assertEqual(receipt.measured_cd, 800)
        self.assertIn("实测光强：800.0 cd", receipt.body)
        self.assertIn("光强不足", receipt.body)
        response = self.client.get(reverse("receipt_download", args=[receipt.pk]))
        self.assertEqual(response.content.decode("utf-8"), receipt.body)

        # 再签发一次才产生新的一张，新回执是改后的亮度
        self.client.post(reverse("issue_receipt", args=[self.seed.pk]))
        self.assertEqual(Receipt.objects.count(), 2)
        newest = Receipt.objects.first()
        self.assertEqual(newest.measured_cd, 1500)
        self.assertNotEqual(newest.checksum, receipt.checksum)

    def test_readonly_can_download_but_not_issue_or_correct(self):
        self._login("keeper")
        self.client.post(reverse("issue_receipt", args=[self.seed.pk]))
        receipt = Receipt.objects.get()
        self.client.logout()
        self._login("watch")

        # 只读账号能进回执册、能下载存档
        self.assertEqual(self.client.get(reverse("receipt_book")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("receipt_detail", args=[receipt.pk])).status_code, 200
        )
        response = self.client.get(reverse("receipt_download", args=[receipt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("光强不足", response.content.decode("utf-8"))

        # 详情页对只读账号隐藏签发与改正入口
        response = self.client.get(reverse("detail", args=[self.seed.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "改正亮度")
        self.assertNotContains(response, 'type="submit">签发回执')

        # 不能签发，也不能改正实测
        self.assertEqual(
            self.client.post(reverse("issue_receipt", args=[self.seed.pk])).status_code, 403
        )
        self.assertEqual(
            self.client.post(
                reverse("correct", args=[self.seed.pk]), {"measured_cd": "1500"}
            ).status_code,
            403,
        )
        self.seed.refresh_from_db()
        self.assertEqual(self.seed.measured_cd, 800)
        self.assertEqual(Receipt.objects.count(), 1)

    def test_anonymous_is_redirected_to_login(self):
        self.assertRedirects(
            self.client.get(reverse("receipt_book")),
            f"{reverse('login')}?next={reverse('receipt_book')}",
        )
