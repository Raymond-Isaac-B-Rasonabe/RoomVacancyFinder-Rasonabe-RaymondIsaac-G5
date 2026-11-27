from datetime import time, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .forms import OVERLAP_MSG
from .models import Building, Room, VacancyReport


def make_user(username, role="student"):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com",
        password="Pass12345!x", role=role)


class VacancyTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = make_user("student1")
        cls.other = make_user("student2")
        cls.admin = make_user("admin1", role="admin")
        cls.building = Building.objects.create(name="Main")
        cls.room = Room.objects.create(building=cls.building, floor=2, name="201")
        cls.tomorrow = timezone.localdate() + timedelta(days=1)

    def post_data(self, **overrides):
        data = {
            "room": self.room.pk, "room_type": "aircon", "is_vacant": "on",
            "date_mode": "auto", "date": "",
            "slot_start": "09:00", "slot_end": "10:00", "notes": "",
        }
        data.update(overrides)
        return data

    def make_report(self, reporter=None, **kwargs):
        defaults = dict(room=self.room, reporter=reporter or self.student,
                        room_type="aircon", is_vacant=True, date=self.tomorrow,
                        slot_start=time(9, 0), slot_end=time(10, 0))
        defaults.update(kwargs)
        return VacancyReport.objects.create(**defaults)


class ValidInputTests(VacancyTestBase):
    def test_student_can_create_report_with_automatic_date(self):
        self.client.force_login(self.student)
        resp = self.client.post(reverse("report_create"), self.post_data())
        self.assertRedirects(resp, reverse("dashboard_redirect"), fetch_redirect_response=False)
        report = VacancyReport.objects.get()
        self.assertEqual(report.reporter, self.student)
        self.assertEqual(report.date, timezone.localdate())

    def test_student_can_create_report_with_manual_date(self):
        self.client.force_login(self.student)
        resp = self.client.post(reverse("report_create"), self.post_data(
            date_mode="manual", date=self.tomorrow.isoformat()))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(VacancyReport.objects.get().date, self.tomorrow)

    def test_owner_can_edit_own_report(self):
        report = self.make_report()
        self.client.force_login(self.student)
        resp = self.client.post(reverse("report_edit", args=[report.pk]), self.post_data(
            date_mode="manual", date=self.tomorrow.isoformat(), slot_end="11:00"))
        self.assertEqual(resp.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.slot_end, time(11, 0))

    def test_owner_can_delete_own_report(self):
        report = self.make_report()
        self.client.force_login(self.student)
        resp = self.client.post(reverse("report_delete", args=[report.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(VacancyReport.objects.filter(pk=report.pk).exists())

    def test_search_shows_vacant_room_for_the_chosen_date(self):
        self.make_report()
        self.client.force_login(self.other)
        resp = self.client.get(reverse("search"), {"date": self.tomorrow.isoformat()})
        self.assertContains(resp, "Main 201")

    def test_search_hides_rooms_in_inactive_buildings(self):
        self.make_report()
        self.building.is_active = False
        self.building.save()
        self.client.force_login(self.other)
        resp = self.client.get(reverse("search"), {"date": self.tomorrow.isoformat()})
        self.assertNotContains(resp, "Main 201")


class InvalidInputTests(VacancyTestBase):
    def setUp(self):
        self.client.force_login(self.student)

    def test_end_before_start_is_rejected(self):
        resp = self.client.post(reverse("report_create"),
                                self.post_data(slot_start="10:00", slot_end="09:00"))
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context["form"], None, "Start time must be before end time.")
        self.assertEqual(VacancyReport.objects.count(), 0)

    def test_times_outside_school_hours_are_rejected(self):
        resp = self.client.post(reverse("report_create"),
                                self.post_data(slot_start="07:00", slot_end="09:00"))
        self.assertFormError(resp.context["form"], None, "Times must be between 8:00 AM and 7:00 PM.")
        self.assertEqual(VacancyReport.objects.count(), 0)

    def test_past_date_is_rejected(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        resp = self.client.post(reverse("report_create"),
                                self.post_data(date_mode="manual", date=yesterday))
        self.assertFormError(resp.context["form"], "date", "The date can't be in the past.")
        self.assertEqual(VacancyReport.objects.count(), 0)

    def test_manual_date_is_required_when_chosen(self):
        resp = self.client.post(reverse("report_create"),
                                self.post_data(date_mode="manual", date=""))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(VacancyReport.objects.count(), 0)

    def test_overlapping_report_by_same_user_is_rejected(self):
        self.make_report()
        resp = self.client.post(reverse("report_create"), self.post_data(
            date_mode="manual", date=self.tomorrow.isoformat(),
            slot_start="09:30", slot_end="10:30"))
        self.assertFormError(resp.context["form"], None, OVERLAP_MSG)
        self.assertEqual(VacancyReport.objects.count(), 1)

    def test_invalid_search_filter_shows_error_not_crash(self):
        resp = self.client.get(reverse("search"), {"floor": "-5"})
        self.assertEqual(resp.status_code, 200)


class LoginRequiredTests(VacancyTestBase):
    def test_report_form_requires_login(self):
        url = reverse("report_create")
        resp = self.client.get(url)
        self.assertRedirects(resp, f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def test_search_requires_login(self):
        url = reverse("search")
        resp = self.client.get(url)
        self.assertRedirects(resp, f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def test_delete_requires_login(self):
        report = self.make_report()
        resp = self.client.post(reverse("report_delete", args=[report.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(VacancyReport.objects.filter(pk=report.pk).exists())


class AccessControlTests(VacancyTestBase):
    def test_cannot_open_edit_page_of_another_users_report(self):
        report = self.make_report(reporter=self.student)
        self.client.force_login(self.other)
        resp = self.client.get(reverse("report_edit", args=[report.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_cannot_save_edit_to_another_users_report(self):
        report = self.make_report(reporter=self.student)
        self.client.force_login(self.other)
        resp = self.client.post(reverse("report_edit", args=[report.pk]), self.post_data(
            date_mode="manual", date=self.tomorrow.isoformat(), slot_end="11:00"))
        self.assertEqual(resp.status_code, 404)
        report.refresh_from_db()
        self.assertEqual(report.slot_end, time(10, 0))

    def test_cannot_delete_another_users_report(self):
        report = self.make_report(reporter=self.student)
        self.client.force_login(self.other)
        resp = self.client.post(reverse("report_delete", args=[report.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(VacancyReport.objects.filter(pk=report.pk).exists())

    def test_delete_rejects_get_requests(self):
        report = self.make_report()
        self.client.force_login(self.student)
        resp = self.client.get(reverse("report_delete", args=[report.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(VacancyReport.objects.filter(pk=report.pk).exists())

    def test_unknown_report_id_returns_404(self):
        self.client.force_login(self.student)
        resp = self.client.get(reverse("report_edit", args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_admin_can_delete_any_report(self):
        report = self.make_report(reporter=self.student)
        self.client.force_login(self.admin)
        self.client.post(reverse("report_delete", args=[report.pk]))
        self.assertFalse(VacancyReport.objects.filter(pk=report.pk).exists())

    def test_admin_cannot_create_reports(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("report_create"), self.post_data())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(VacancyReport.objects.count(), 0)

    def test_student_cannot_open_admin_dashboard(self):
        self.client.force_login(self.student)
        resp = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_admin_cannot_open_user_dashboard(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("user_dashboard"))
        self.assertEqual(resp.status_code, 302)