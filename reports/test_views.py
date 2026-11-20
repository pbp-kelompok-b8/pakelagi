from unittest import mock

from django.template import Context, Template
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from listings.models import Listing
from listings.test_detail import create_listing, make_user
from reports.forms import ReportForm
from reports.models import Report
from reports.test_models import REASON, create_report

SECRET = "RAHASIA-CATATAN-MODERATOR"


def valid_data(**overrides):
    data = {"reason": REASON, "description": "Foto tidak sesuai dengan barang aslinya."}
    data.update(overrides)
    return data


class ReportViewBase(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.member = make_user("budi", "Budi")
        self.other = make_user("dewi", "Dewi")
        self.listing = create_listing(self.seller, title="Kemeja flanel kotak")
        self.create_url = reverse("reports:create", args=[self.listing.pk])
        self.list_url = reverse("reports:list")
        self.client.force_login(self.member)


class UrlPatternTests(ReportViewBase):
    def test_url_patterns(self):
        report = create_report(self.member, self.listing)
        self.assertEqual(self.list_url, "/reports/")
        self.assertEqual(self.create_url, f"/reports/create/{self.listing.pk}/")
        self.assertEqual(reverse("reports:edit", args=[report.pk]), f"/reports/{report.pk}/edit/")
        self.assertEqual(reverse("reports:delete", args=[report.pk]), f"/reports/{report.pk}/delete/")


class AccessControlTests(ReportViewBase):
    def setUp(self):
        super().setUp()
        self.report = create_report(self.member, self.listing)
        self.urls = [
            self.list_url, self.create_url,
            reverse("reports:edit", args=[self.report.pk]),
            reverse("reports:delete", args=[self.report.pk]),
        ]

    def test_guest_is_sent_to_login(self):
        self.client.logout()
        for url in self.urls:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f"/accounts/login/?next={url}", fetch_redirect_response=False)

    def test_guest_cannot_post(self):
        self.client.logout()
        for url in (self.create_url, self.urls[2], self.urls[3]):
            with self.subTest(url=url):
                response = self.client.post(url, valid_data())
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith("/accounts/login/"))
        self.assertEqual(Report.objects.count(), 1)
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_member_without_complete_profile_is_sent_to_onboarding(self):
        self.client.force_login(make_user("tanpaprofil"))
        for url in self.urls:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f"/profile/create/?next={url}", fetch_redirect_response=False)

    def test_member_without_complete_profile_cannot_create_a_report(self):
        self.client.force_login(make_user("tanpaprofil"))
        self.client.post(self.create_url, valid_data())
        self.assertEqual(Report.objects.count(), 1)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        other_listing = create_listing(self.seller, title="Barang lain yang berbeda")
        response = client.post(reverse("reports:create", args=[other_listing.pk]), valid_data())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Report.objects.count(), 1)
        response = client.post(reverse("reports:delete", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_list_only_accepts_get(self):
        self.assertEqual(self.client.post(self.list_url).status_code, 405)


class ListViewTests(ReportViewBase):
    def test_empty_state_and_template(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/list.html")
        self.assertContains(response, "Kamu belum membuat laporan")
        self.assertContains(response, "0 laporan")
        self.assertIsNone(response.context["form"])

    def test_shows_only_the_members_own_reports(self):
        create_report(self.member, self.listing)
        other_listing = create_listing(self.seller, title="Barang yang dilaporkan orang lain")
        create_report(self.other, other_listing)
        response = self.client.get(self.list_url)
        self.assertContains(response, "Kemeja flanel kotak")
        self.assertNotContains(response, "Barang yang dilaporkan orang lain")
        self.assertEqual(response.context["counts"]["total"], 1)

    def test_counts_total_and_open(self):
        for number, status in enumerate(("open", "reviewing", "resolved")):
            create_report(self.member, create_listing(self.seller, title=f"Barang nomor {number}"), status=status)
        counts = self.client.get(self.list_url).context["counts"]
        self.assertEqual((counts["total"], counts["open"]), (3, 1))
        self.assertContains(self.client.get(self.list_url), "3 laporan · 1 masih terbuka")

    def test_status_is_shown_as_text_and_actions_only_for_open_reports(self):
        open_listing = create_listing(self.seller, title="Barang laporan terbuka")
        done_listing = create_listing(self.seller, title="Barang laporan selesai")
        open_report = create_report(self.member, open_listing)
        done_report = create_report(self.member, done_listing, status="resolved")
        response = self.client.get(self.list_url)
        self.assertContains(response, open_report.get_status_display())
        self.assertContains(response, done_report.get_status_display())
        self.assertContains(response, reverse("reports:edit", args=[open_report.pk]))
        self.assertContains(response, reverse("reports:delete", args=[open_report.pk]))
        self.assertNotContains(response, reverse("reports:edit", args=[done_report.pk]))
        self.assertNotContains(response, reverse("reports:delete", args=[done_report.pk]))

    # def test_moderator_note_is_never_shown_to_the_reporter(self):
    #     report = create_report(self.member, self.listing, moderator_note=SECRET)
    #     pages = [self.list_url, reverse("reports:edit", args=[report.pk]), self.create_url]
    #     for url in pages:
    #         with self.subTest(url=url):
    #             self.assertNotContains(self.client.get(url), SECRET)

    def test_report_on_a_deleted_listing_still_shows_its_title(self):
        create_report(self.member, self.listing)
        self.listing.delete()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kemeja flanel kotak")
        self.assertContains(response, "Listing dihapus")

    def test_user_text_is_escaped(self):
        listing = create_listing(self.seller, title="<script>alert(1)</script> kemeja")
        create_report(self.member, listing, description="<img src=x onerror=alert(2)> deskripsi panjang")
        response = self.client.get(self.list_url)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertNotContains(response, "<img src=x")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_pagination_is_ten_per_page_and_bad_pages_do_not_crash(self):
        for number in range(12):
            create_report(self.member, create_listing(self.seller, title=f"Barang nomor {number:02d}"))
        self.assertEqual(len(self.client.get(self.list_url).context["page"].object_list), 10)
        self.assertEqual(len(self.client.get(self.list_url + "?page=2").context["page"].object_list), 2)
        for page in ("abc", "0", "-1", "999", ""):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(f"{self.list_url}?page={page}").status_code, 200)


class CreateViewTests(ReportViewBase):
    def test_form_page_shows_the_listing_and_all_reasons(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/list.html")
        self.assertEqual(response.context["listing"], self.listing)
        self.assertContains(response, "Kemeja flanel kotak")
        self.assertContains(response, 'name="reason"', count=len(Report._meta.get_field("reason").choices))
        self.assertContains(response, 'name="description"')

    def test_valid_post_creates_an_open_report_for_the_logged_in_member(self):
        response = self.client.post(self.create_url, valid_data())
        self.assertRedirects(response, self.list_url)
        report = Report.objects.get()
        self.assertEqual(report.reporter, self.member)
        self.assertEqual(report.listing, self.listing)
        self.assertEqual(report.status, "open")
        # self.assertEqual(report.moderator_note, "")
        self.assertEqual(report.listing_title, "Kemeja flanel kotak")

    def test_success_message_is_shown_after_redirect(self):
        response = self.client.post(self.create_url, valid_data(), follow=True)
        self.assertContains(response, "Laporan terkirim")

    def test_protected_fields_in_post_are_ignored(self):
        self.client.post(self.create_url, valid_data(
            status="resolved", reporter=self.other.pk, listing=999999,
        ))
        report = Report.objects.get()
        self.assertEqual(report.status, "open")
        # self.assertEqual(report.moderator_note, "")
        self.assertEqual(report.reporter, self.member)
        self.assertEqual(report.listing, self.listing)

    def test_invalid_post_creates_nothing_and_keeps_input(self):
        response = self.client.post(self.create_url, valid_data(description="pendek"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Report.objects.count(), 0)
        self.assertIn("description", response.context["form"].errors)
        self.assertContains(response, "pendek")

    def test_missing_or_unknown_reason_is_rejected(self):
        for reason in ("", "ngawur"):
            with self.subTest(reason=reason):
                response = self.client.post(self.create_url, valid_data(reason=reason))
                self.assertEqual(response.status_code, 200)
                self.assertIn("reason", response.context["form"].errors)
        self.assertEqual(Report.objects.count(), 0)

    def test_own_listing_cannot_be_reported(self):
        self.client.force_login(self.seller)
        response = self.client.post(self.create_url, valid_data())
        self.assertRedirects(response, reverse("listings:detail", args=[self.listing.pk]))
        self.assertEqual(Report.objects.count(), 0)
        response = self.client.get(self.create_url, follow=True)
        self.assertContains(response, "tidak bisa melaporkan listing milikmu sendiri")

    def test_hidden_and_unknown_listings_are_404(self):
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        self.assertEqual(self.client.get(self.create_url).status_code, 404)
        self.assertEqual(self.client.post(self.create_url, valid_data()).status_code, 404)
        self.assertEqual(self.client.get("/reports/create/999999/").status_code, 404)
        self.assertEqual(Report.objects.count(), 0)

    def test_sold_listing_can_still_be_reported(self):
        self.listing.status = Listing.Status.SOLD
        self.listing.save()
        self.assertRedirects(self.client.post(self.create_url, valid_data()), self.list_url)
        self.assertEqual(Report.objects.count(), 1)

    def test_duplicate_active_report_shows_a_form_error(self):
        for status in ("open", "reviewing"):
            with self.subTest(status=status):
                Report.objects.all().delete()
                create_report(self.member, self.listing, status=status)
                response = self.client.post(self.create_url, valid_data())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "laporannya masih diproses")
                self.assertEqual(Report.objects.count(), 1)

    def test_new_report_is_allowed_after_the_previous_one_is_resolved(self):
        create_report(self.member, self.listing, status="resolved")
        self.assertRedirects(self.client.post(self.create_url, valid_data()), self.list_url)
        self.assertEqual(Report.objects.count(), 2)

    def test_race_condition_is_a_form_error_not_a_server_error(self):
        # clean() dimatikan supaya cek duplikat lolos, jadi yang menolak adalah constraint database.
        create_report(self.member, self.listing)
        with mock.patch.object(Report, "clean"):
            response = self.client.post(self.create_url, valid_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "laporannya masih diproses")
        self.assertEqual(Report.objects.count(), 1)

    def test_form_page_also_lists_the_members_history(self):
        other_listing = create_listing(self.seller, title="Barang yang sudah pernah dilaporkan")
        create_report(self.member, other_listing)
        self.assertContains(self.client.get(self.create_url), "Barang yang sudah pernah dilaporkan")


class EditViewTests(ReportViewBase):
    def setUp(self):
        super().setUp()
        self.report = create_report(self.member, self.listing, description="Deskripsi lama yang cukup panjang.")
        self.url = reverse("reports:edit", args=[self.report.pk])

    def test_owner_sees_a_prefilled_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["report"], self.report)
        self.assertContains(response, "Deskripsi lama yang cukup panjang.")
        self.assertContains(response, "Simpan perubahan")

    def test_owner_can_update_and_keeps_status_and_listing(self):
        response = self.client.post(self.url, valid_data(description="Deskripsi baru yang sudah diperbarui."))
        self.assertRedirects(response, self.list_url)
        self.report.refresh_from_db()
        self.assertEqual(self.report.description, "Deskripsi baru yang sudah diperbarui.")
        self.assertEqual(self.report.status, "open")
        self.assertEqual(self.report.listing, self.listing)
        self.assertEqual(Report.objects.count(), 1)

    def test_success_message_is_shown(self):
        response = self.client.post(self.url, valid_data(), follow=True)
        self.assertContains(response, "Laporan diperbarui")

    def test_editing_an_open_report_is_not_blocked_as_a_duplicate_of_itself(self):
        response = self.client.post(self.url, valid_data(description="Deskripsi baru yang sudah diperbarui."))
        self.assertEqual(response.status_code, 302)

    def test_invalid_update_changes_nothing(self):
        response = self.client.post(self.url, valid_data(description="pendek"))
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.description, "Deskripsi lama yang cukup panjang.")

    def test_protected_fields_in_post_are_ignored(self):
        self.client.post(self.url, valid_data(
            status="resolved", reporter=self.other.pk,
        ))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "open")
        # self.assertEqual(self.report.moderator_note, "")
        self.assertEqual(self.report.reporter, self.member)

    def test_other_member_gets_404_and_cannot_change_data(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, valid_data(description="Dibajak orang lain, ya.")).status_code, 404)
        self.report.refresh_from_db()
        self.assertEqual(self.report.description, "Deskripsi lama yang cukup panjang.")

    def test_staff_cannot_edit_someone_elses_report_either(self):
        staff = make_user("mod", "Moderator")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_unknown_report_is_404(self):
        self.assertEqual(self.client.get("/reports/999999/edit/").status_code, 404)

    def test_report_that_left_open_status_cannot_be_edited(self):
        for status in ("reviewing", "resolved", "rejected"):
            with self.subTest(status=status):
                Report.objects.filter(pk=self.report.pk).update(status=status)
                for response in (self.client.get(self.url), self.client.post(self.url, valid_data(description="Percobaan ubah laporan."))):
                    self.assertRedirects(response, self.list_url)
                self.report.refresh_from_db()
                self.assertEqual(self.report.description, "Deskripsi lama yang cukup panjang.")
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, "sudah ditinjau moderator")

    def test_report_can_still_be_edited_after_the_listing_is_hidden(self):
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        response = self.client.post(self.url, valid_data(description="Deskripsi baru setelah disembunyikan."))
        self.assertRedirects(response, self.list_url)

    def test_report_on_a_deleted_listing_can_still_be_edited(self):
        self.listing.delete()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        response = self.client.post(self.url, valid_data(description="Deskripsi baru setelah listing dihapus."))
        self.assertRedirects(response, self.list_url)


class DeleteViewTests(ReportViewBase):
    def setUp(self):
        super().setUp()
        self.report = create_report(self.member, self.listing)
        self.url = reverse("reports:delete", args=[self.report.pk])

    def test_get_shows_confirmation_and_never_deletes(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/confirm_delete.html")
        self.assertContains(response, "Kemeja flanel kotak")
        self.assertContains(response, "Ya, hapus")
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_owner_post_deletes_and_redirects_to_the_list(self):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, self.list_url)
        self.assertFalse(Report.objects.filter(pk=self.report.pk).exists())
        self.assertContains(response, "dihapus")

    def test_deleting_a_report_keeps_the_listing(self):
        self.client.post(self.url)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_other_member_cannot_delete(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_staff_cannot_delete_someone_elses_report(self):
        staff = make_user("mod", "Moderator")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_report_that_left_open_status_cannot_be_deleted(self):
        for status in ("reviewing", "resolved", "rejected"):
            with self.subTest(status=status):
                Report.objects.filter(pk=self.report.pk).update(status=status)
                self.assertRedirects(self.client.post(self.url), self.list_url)
                self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_deleting_a_report_on_a_deleted_listing_works(self):
        self.listing.delete()
        self.client.post(self.url)
        self.assertFalse(Report.objects.filter(pk=self.report.pk).exists())

    def test_unknown_report_is_404(self):
        self.assertEqual(self.client.post("/reports/999999/delete/").status_code, 404)


class ReportFormTests(SimpleTestCase):
    def test_only_reason_and_description_are_user_input(self):
        self.assertEqual(list(ReportForm().fields), ["reason", "description"])

    def test_reason_choices_have_no_blank_option(self):
        values = [value for value, _ in ReportForm().fields["reason"].choices]
        self.assertNotIn("", values)
        self.assertEqual(len(values), len(Report._meta.get_field("reason").choices))