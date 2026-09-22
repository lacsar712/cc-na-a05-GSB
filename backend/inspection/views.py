from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from inspection.models import Inspection, Receipt
from inspection.receipts import new_serial, render_body
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
@require_http_methods(["POST"])
def correct_view(request, pk):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅持灯账号可改正实测")
    row = get_object_or_404(Inspection, pk=pk)
    try:
        measured = float(request.POST["measured_cd"])
    except (KeyError, ValueError):
        return render(
            request,
            "detail.html",
            {"row": row, "error": "改正亮度要填数值"},
            status=400,
        )
    row.measured_cd = measured
    row.verdict, row.note = judge(measured, row.required_cd, row.bearing_error_deg)
    row.save()
    return redirect("detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def issue_receipt(request, pk):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅持灯账号可签发回执")
    row = get_object_or_404(Inspection, pk=pk)
    issued_at = timezone.now()
    serial = new_serial()
    body, checksum = render_body(
        serial=serial,
        aid_code=row.aid_code,
        measured_cd=row.measured_cd,
        required_cd=row.required_cd,
        bearing_error_deg=row.bearing_error_deg,
        verdict=row.verdict,
        note=row.note,
        issued_by=request.user.username,
        issued_at=issued_at,
    )
    receipt = Receipt.objects.create(
        inspection=row,
        serial=serial,
        aid_code=row.aid_code,
        measured_cd=row.measured_cd,
        required_cd=row.required_cd,
        bearing_error_deg=row.bearing_error_deg,
        verdict=row.verdict,
        note=row.note,
        body=body,
        checksum=checksum,
        issued_by=request.user.username,
        issued_at=issued_at,
    )
    return redirect("receipt_detail", pk=receipt.pk)


@login_required
def receipt_book(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "receipts.html", {"row": row, "receipts": row.receipts.all()})


@login_required
def receipt_detail(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    return render(request, "receipt_detail.html", {"receipt": receipt})


@login_required
def receipt_download(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    response = HttpResponse(receipt.body, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{receipt.serial}.txt"'
    return response
