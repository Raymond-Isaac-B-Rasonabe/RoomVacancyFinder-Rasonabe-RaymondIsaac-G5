from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.decorators import role_required
from .forms import ReportForm
from .models import Building, Room, VacancyReport

@login_required
def search(request):
    now = timezone.localtime()
    building = request.GET.get("building") or None
    floor = request.GET.get("floor") or None
    room_type = request.GET.get("room_type") or None

    rooms = Room.objects.filter(building__is_active=True, is_accessible=True)
    if building:
        rooms = rooms.filter(building_id=building)
    if floor and floor.isdigit():
        rooms = rooms.filter(floor=int(floor))
    if room_type:
        rooms = rooms.filter(room_type=room_type)

    reports = (VacancyReport.objects
               .filter(room__in=rooms, created_at__date=now.date(),
                       slot_start__lte=now.time(), slot_end__gte=now.time())
               .select_related("room__building", "reporter")
               .order_by("room_id", "-created_at"))

    latest = {}
    for r in reports:                       # newest first, so the first one seen is the latest
        latest.setdefault(r.room_id, r)
    results = [r for r in latest.values() if r.is_vacant]

    return render(request, "search.html", {
        "results": results,
        "buildings": Building.objects.filter(is_active=True),
        "room_types": Room.RoomType.choices,
    })

@role_required("student", "staff")
def report_create(request):
    form = ReportForm(request.POST or None)
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
    form = ReportForm(request.POST or None, instance=report)
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

# Create your views here.
