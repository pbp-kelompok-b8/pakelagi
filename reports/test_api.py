from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse

from listings.models import Listing
from listings.test_detail import create_listing, make_user
from reports.models import Report, ReportModeratorNote
from reports.test_models import create_report
from reports.test_views import valid_data


class ReportAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("seller", "Seller")
        cls.member = make_user("member", "Member")
        cls.other = make_user("other", "Other")
        cls.listing = create_listing(cls.seller)
        cls.report = create_report(cls.member, cls.listing)

    def setUp(self):
        self.collection = reverse("reports_api:report-list")
        self.detail = reverse("reports_api:report-detail", args=[self.report.pk])

    def test_guest_and_incomplete_profiles_cannot_access_reports(self):
        incomplete = make_user("incomplete")
        blank = make_user("blank", "   ")
        for user in (None, incomplete, blank):
            if user is not None:
                self.client.force_login(user)
            for method, url in (
                ("GET", self.collection), ("HEAD", self.collection), ("POST", self.collection),
                ("GET", self.detail), ("HEAD", self.detail), ("PUT", self.detail),
                ("PATCH", self.detail), ("DELETE", self.detail),
            ):
                with self.subTest(user=user, method=method, url=url):
                    response = self.client.generic(method, url, content_type="application/json")
                    self.assertEqual(response.status_code, 403)

    def test_member_lists_only_own_reports_and_can_read_own_detail(self):
        create_report(self.other, self.listing)
        self.client.force_login(self.member)
        response = self.client.get(self.collection, {"reporter": self.other.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()], [str(self.report.pk)])
        response = self.client.get(self.detail)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reporter"], self.member.pk)
        self.assertIn("no-store", response["Cache-Control"])

    def test_listing_seller_and_staff_cannot_access_another_members_report(self):
        self.other.is_staff = True
        self.other.save(update_fields=["is_staff"])
        for user in (self.seller, self.other):
            self.client.force_login(user)
            for method in ("GET", "HEAD", "PUT", "PATCH", "DELETE"):
                with self.subTest(user=user, method=method):
                    response = self.client.generic(method, self.detail, content_type="application/json")
                    self.assertEqual(response.status_code, 404)
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_superuser_has_cross_report_read_access_not_cross_report_write_access(self):
        self.other.is_superuser = True
        self.other.save(update_fields=["is_superuser"])
        note = ReportModeratorNote.objects.create(
            moderator_id=self.other, report_id=self.report, note="Private audit note.",
        )
        own_report = create_report(self.other, self.listing)
        self.client.force_login(self.other)
        response = self.client.get(self.collection)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["id"] for row in response.json()}, {str(self.report.pk), str(own_report.pk)})
        response = self.client.get(self.detail)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, note.note)
        self.assertNotIn("moderator_note", response.json())
        for method in ("PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                response = self.client.generic(method, self.detail, content_type="application/json")
                self.assertEqual(response.status_code, 404)
        self.assertTrue(ReportModeratorNote.objects.filter(pk=note.pk).exists())

    def test_superuser_reporter_filter_requires_a_valid_id(self):
        self.other.is_superuser = True
        self.other.save(update_fields=["is_superuser"])
        create_report(self.other, self.listing)
        self.client.force_login(self.other)
        response = self.client.get(self.collection, {"reporter": self.member.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()], [str(self.report.pk)])
        for reporter in ("", "nope", "-1", "1.5", "9" * 30):
            with self.subTest(reporter=reporter):
                response = self.client.get(self.collection, {"reporter": reporter})
                self.assertEqual(response.status_code, 400)
                self.assertIn("reporter", response.json())

    def test_reporter_can_read_but_not_change_a_report_after_it_leaves_open(self):
        self.client.force_login(self.member)
        for status in ("reviewing", "resolved", "rejected"):
            Report.objects.filter(pk=self.report.pk).update(status=status)
            with self.subTest(status=status):
                self.assertEqual(self.client.get(self.detail).status_code, 200)
                self.assertEqual(self.client.put(self.detail, valid_data(), content_type="application/json").status_code, 403)
                self.assertEqual(self.client.patch(self.detail, valid_data(), content_type="application/json").status_code, 403)
                self.assertEqual(self.client.delete(self.detail).status_code, 403)

    def post_report(self, **overrides):
        data = valid_data(listing=self.listing.pk)
        data.update(overrides)
        return self.client.post(self.collection, data, content_type="application/json")

    def test_member_can_create_open_report_for_a_sold_listing(self):
        self.listing.status = Listing.Status.SOLD
        self.listing.save()
        self.client.force_login(self.other)
        response = self.post_report(description="  A valid new explanation.  ")
        self.assertEqual(response.status_code, 201)
        report = Report.objects.get(reporter=self.other)
        self.assertEqual(report.status, "open")
        self.assertEqual(report.listing, self.listing)
        self.assertEqual(report.listing_title, self.listing.title)
        self.assertEqual(report.description, "A valid new explanation.")
        self.assertEqual(response.json()["id"], str(report.pk))

    def test_hidden_missing_and_self_owned_listings_cannot_be_reported(self):
        self.client.force_login(self.seller)
        response = self.post_report()
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", response.json())
        self.client.force_login(self.other)
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        for listing_id in (self.listing.pk, 99999):
            with self.subTest(listing_id=listing_id):
                self.assertEqual(self.post_report(listing=listing_id).status_code, 404)
        self.assertEqual(Report.objects.count(), 1)

    def test_create_rejects_invalid_and_missing_fields(self):
        self.client.force_login(self.other)
        for field, value in (
            ("listing", None), ("listing", "not-an-id"), ("listing", True), ("listing", 2**63),
            ("reason", "unknown"), ("description", "    too soon    "), ("description", "x" * 1001),
            ("description", ["Looks like text only when coerced"]), ("description", 1234567890),
        ):
            with self.subTest(field=field, value=value):
                response = self.post_report(**{field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        response = self.client.post(self.collection, {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("listing", response.json())
        response = self.client.post(self.collection, [], content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Report.objects.count(), 1)

    def test_client_cannot_assign_server_managed_fields(self):
        self.client.force_login(self.other)
        changes = {"reporter": self.member.pk, "status": "resolved", "listing_title": "Forged title",
                   "moderator_note": "Forged note"}
        response = self.post_report(**changes)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), set(changes))
        self.assertEqual(Report.objects.count(), 1)

        self.client.force_login(self.member)
        changes.update(reporter=self.other.pk, listing=create_listing(self.seller).pk)
        response = self.client.patch(self.detail, changes, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), set(changes))
        self.report.refresh_from_db()
        self.assertEqual(self.report.listing_id, self.listing.pk)
        self.assertEqual(self.report.reporter_id, self.member.pk)
        self.assertEqual(self.report.listing_title, self.listing.title)
        self.assertEqual(self.report.status, "open")

    def test_owner_can_edit_open_report_after_listing_is_renamed_hidden_or_deleted(self):
        self.client.force_login(self.member)
        snapshot = self.listing.title
        self.listing.title = "A different listing title"
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        response = self.client.patch(self.detail, {"description": "  A revised explanation.  "},
                                     content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.description, "A revised explanation.")
        self.assertEqual(self.report.listing_title, snapshot)

        self.listing.delete()
        response = self.client.put(self.detail, valid_data(reason="Other"), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reason"], "Other")
        self.assertEqual(response.json()["listing_title"], snapshot)
        self.assertIsNone(response.json()["listing"])

    def test_edit_requires_valid_fields_and_put_requires_both(self):
        self.client.force_login(self.member)
        patch = self.client.patch(self.detail, {"description": "x" * 1001}, content_type="application/json")
        self.assertEqual(patch.status_code, 400)
        self.assertIn("description", patch.json())
        put = self.client.put(self.detail, {"description": "A valid explanation."}, content_type="application/json")
        self.assertEqual(put.status_code, 400)
        self.assertIn("reason", put.json())

    def test_owner_can_delete_an_open_report(self):
        self.client.force_login(self.member)
        response = self.client.delete(self.detail)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Report.objects.filter(pk=self.report.pk).exists())
        self.assertEqual(self.client.get(self.detail).status_code, 404)

    def test_open_report_with_moderation_history_cannot_be_deleted_even_by_superuser_owner(self):
        self.member.is_superuser = True
        self.member.save(update_fields=["is_superuser"])
        note = ReportModeratorNote.objects.create(
            moderator_id=self.other, report_id=self.report, note="Private audit note.",
        )
        self.client.force_login(self.member)
        response = self.client.delete(self.detail)
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, note.note, status_code=403)
        self.assertTrue(ReportModeratorNote.objects.filter(pk=note.pk).exists())

    def test_duplicate_is_rejected_until_the_previous_report_is_finished(self):
        self.client.force_login(self.member)
        for status in ("open", "reviewing"):
            with self.subTest(status=status):
                Report.objects.filter(pk=self.report.pk).update(status=status)
                response = self.post_report()
                self.assertContains(response, "laporannya masih diproses", status_code=400)
                self.assertEqual(Report.objects.count(), 1)
        Report.objects.filter(pk=self.report.pk).update(status="resolved")
        self.assertEqual(self.post_report().status_code, 201)
        self.assertEqual(Report.objects.count(), 2)

    def test_duplicate_constraints_after_validation_return_a_form_error(self):
        self.client.force_login(self.member)
        # Simulate a duplicate becoming visible after the preflight check. The DB rejects the insert.
        with mock.patch.object(Report, "clean"):
            response = self.post_report()
        self.assertContains(response, "laporannya masih diproses", status_code=400)
        self.assertEqual(Report.objects.count(), 1)

    def test_session_write_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        login_url = reverse("accounts:login")
        self.other.set_password("test-only-password")
        self.other.save(update_fields=["password"])
        self.assertEqual(client.get(login_url).status_code, 200)
        self.assertEqual(client.post(login_url, {
            "username": self.other.username, "password": "test-only-password",
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        }).status_code, 302)
        payload = valid_data(listing=self.listing.pk)
        self.assertEqual(client.post(self.collection, payload, content_type="application/json").status_code, 403)
        response = client.post(self.collection, payload, content_type="application/json",
                               HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 201)
