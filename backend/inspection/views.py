from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from inspection.models import Inspection, Receipt
from inspection.receipts import make_checksum, render_body
from inspection.rules import judge


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = Inspection.objects.all()
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "detail.html", {"row": row})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


@login_required
@require_POST
def correct_view(request, pk):
    """持灯账号事后改正这条实测的亮度，结论随之重判。

    只改实测记录本身；已签发的回执存档不受影响。
    """
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可改正实测")
    row = get_object_or_404(Inspection, pk=pk)
    try:
        measured = float(request.POST["measured_cd"])
    except (KeyError, ValueError):
        return render(request, "detail.html", {"row": row, "error": "请填正确的实测光强数值"})
    row.measured_cd = measured
    row.verdict, row.note = judge(measured, row.required_cd, row.bearing_error_deg)
    row.save(update_fields=["measured_cd", "verdict", "note"])
    return redirect("detail", pk=row.pk)


@login_required
@require_POST
def issue_receipt_view(request, pk):
    """按实测当前状态签发一张回执，冻结存档；再签发一次就再存一张。"""
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可签发回执")
    row = get_object_or_404(Inspection, pk=pk)
    now = timezone.localtime()
    issued_at_text = now.strftime("%Y-%m-%d %H:%M:%S %z")
    checksum = make_checksum(
        aid_code=row.aid_code,
        measured_cd=row.measured_cd,
        required_cd=row.required_cd,
        bearing_error_deg=row.bearing_error_deg,
        verdict=row.verdict,
        note=row.note,
        issued_by=request.user.username,
        issued_at_text=issued_at_text,
    )
    body = render_body(
        aid_code=row.aid_code,
        measured_cd=row.measured_cd,
        required_cd=row.required_cd,
        bearing_error_deg=row.bearing_error_deg,
        verdict=row.verdict,
        note=row.note,
        issued_by=request.user.username,
        issued_at_text=issued_at_text,
        checksum=checksum,
    )
    receipt = Receipt.objects.create(
        inspection=row,
        aid_code=row.aid_code,
        measured_cd=row.measured_cd,
        required_cd=row.required_cd,
        bearing_error_deg=row.bearing_error_deg,
        verdict=row.verdict,
        note=row.note,
        body=body,
        checksum=checksum,
        issued_by=request.user.username,
        issued_at=now,
    )
    return redirect("receipt_detail", pk=receipt.pk)


@login_required
def receipt_book_view(request):
    rows = Receipt.objects.select_related("inspection").all()
    return render(request, "receipt_book.html", {"rows": rows})


@login_required
def receipt_detail_view(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    return render(request, "receipt_detail.html", {"receipt": receipt})


@login_required
def receipt_download_view(request, pk):
    """下载签发时存档的正文原文，不重新拼装。"""
    receipt = get_object_or_404(Receipt, pk=pk)
    response = HttpResponse(receipt.body, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="receipt-{receipt.pk}.txt"'
    return response
