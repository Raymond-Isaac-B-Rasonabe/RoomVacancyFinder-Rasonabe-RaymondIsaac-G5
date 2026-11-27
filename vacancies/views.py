from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone as dj_timezone
from django.views.decorators.http import require_POST
from accounts.decorators import role_required
from .forms import ReportForm, SearchForm
from .models import VacancyReport


@login_required
def search(request):
    form = SearchForm(request.GET or None)
    data = form.cleaned_data if form.is_valid() else {}
    day = data.get("date") or dj_timezone.localdate()
    at = data.get("time")

    reports = VacancyReport.objects.filter(
        date=day,
        room__building__is_active=True,
        room__is_accessible=True,
    ).select_related("room__building", "reporter")

    if data.get("building"):
        reports = reports.filter(room__building=data["building"])
    if data.get("floor") is not None:
        reports = reports.filter(room__floor=data["floor"])
    if data.get("room_type"):
        reports = reports.filter(room_type=data["room_type"])
    if at:
        reports = reports.filter(slot_start__lte=at, slot_end__gte=at)

    reports = reports.order_by("room_id", "-created_at")

    results, seen = [], set()
    for r in reports:                  # newest first
        if at:                         # with a time, only the latest report per room counts
            if r.room_id in seen:
                continue
            seen.add(r.room_id)
        if r.is_vacant:
            results.append(r)
    results.sort(key=lambda r: (r.room.building.name, r.room.floor, r.room.name, r.slot_start))

    return render(request, "search.html", {
        "form": form, "results": results, "day": day, "at": at,
    })


@role_required("student", "staff")
def report_create(request):
    form = ReportForm(request.POST or None, reporter=request.user)
    if request.method == "POST":
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()
            messages.success(request, "Report submitted.")
            return redirect("dashboard_redirect")
        messages.error(request, "Please fix the errors below.")
    return render(request, "form.html", {"form": form, "title": "Report a room"})


@role_required("student", "staff")
def report_edit(request, pk):
    report = get_object_or_404(VacancyReport, pk=pk, reporter=request.user)   # own reports only
    form = ReportForm(request.POST or None, instance=report, reporter=request.user)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Report updated.")
            return redirect("dashboard_redirect")
        messages.error(request, "Please fix the errors below.")
    return render(request, "form.html", {"form": form, "title": "Edit report"})


@login_required
@require_POST
def report_delete(request, pk):
    if request.user.role == "admin":
        qs = VacancyReport.objects.all()
    else:
        qs = VacancyReport.objects.filter(reporter=request.user)
    report = get_object_or_404(qs, pk=pk)
    report.delete()
    messages.success(request, "Report deleted.")
    return redirect("dashboard_redirect")
