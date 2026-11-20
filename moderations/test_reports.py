"""Tes moderasi laporan: python manage.py test moderations.test_reports"""
import uuid
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from listings.models import Listing
from listings.test_detail import create_listing, make_user
from profiles.models import Profile
from reports.models import Report, ReportModeratorNote

DESCRIPTION = "Foto tidak sesuai dengan barang aslinya."


def make_report(reporter, listing, **overrides):
    data = {"reporter": reporter, "listing": listing, "reason": "Misleading", "description": DESCRIPTION}
    data.update(overrides)
    return Report.objects.create(**data)


def msgs(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


class ModerationReportBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin1", "admin1@example.com", "Strong!9382")
        self.staff = User.objects.create_user("staff1", is_staff=True)
        self.seller = make_user("sari", "Sari")
        self.reporter = make_user("budi", "Budi")
        self.listing = create_listing(self.seller, title="Kemeja flanel kotak")
        self.report = make_report(self.reporter, self.listing)
        self.client.force_login(self.admin)
        self.list_url = reverse("moderations:reports_list")

    # --- helpers
    def review_url(self, report=None):
        return reverse("moderations:report_review", args=[(report or self.report).pk])

    def action_url(self, report=None):
        return reverse("moderations:report_listing_action", args=[(report or self.report).pk])

    def notes_url(self, report=None):
        return reverse("moderations:report_notes_popover", args=[(report or self.report).pk])

    def another_report(self, status="open", **overrides):
        title = f"Barang laporan {Report.objects.count()}"
        return make_report(self.reporter, create_listing(self.seller, title=title), status=status, **overrides)

    def set_status(self, status, report=None):
        report = report or self.report
        Report.objects.filter(pk=report.pk).update(status=status)

    def fresh(self, report=None):
        return Report.objects.get(pk=(report or self.report).pk)


class ModerationReportAccessTests(ModerationReportBase):
    def endpoints(self):
        return [
            ("get", self.list_url), ("post", self.review_url()),
            ("post", self.action_url()), ("get", self.notes_url()),
        ]

    def test_guest_is_sent_to_login(self):
        self.client.logout()
        for method, url in self.endpoints():
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertRedirects(response, f"/accounts/login/?next={url}", fetch_redirect_response=False)

    def test_members_and_non_superuser_staff_are_sent_to_login(self):
        for viewer in (self.reporter, self.seller, self.staff):
            self.client.force_login(viewer)
            for method, url in self.endpoints():
                with self.subTest(viewer=viewer.username, url=url):
                    response = getattr(self.client, method)(url)
                    self.assertRedirects(response, f"/accounts/login/?next={url}", fetch_redirect_response=False)

    def test_non_admins_cannot_change_anything(self):
        for viewer in (self.reporter, self.seller, self.staff):
            self.client.force_login(viewer)
            self.client.post(self.review_url(), {"status": "resolved", "moderator_note": "Coba ubah laporan."})
            self.client.post(self.action_url(), {"action": "hide"})
        self.assertEqual(self.fresh().status, "open")
        self.assertEqual(Listing.objects.get(pk=self.listing.pk).status, Listing.Status.AVAILABLE)
        self.assertFalse(ReportModeratorNote.objects.exists())

    def test_wrong_http_methods_are_rejected_for_admin(self):
        self.assertEqual(self.client.post(self.list_url).status_code, 405)
        self.assertEqual(self.client.get(self.review_url()).status_code, 405)
        self.assertEqual(self.client.get(self.action_url()).status_code, 405)
        self.assertEqual(self.client.post(self.notes_url()).status_code, 405)
        self.assertEqual(self.fresh().status, "open")

    def test_state_changing_posts_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.review_url(), {"status": "resolved"}).status_code, 403)
        self.assertEqual(client.post(self.action_url(), {"action": "hide"}).status_code, 403)
        self.assertEqual(self.fresh().status, "open")
        self.assertEqual(Listing.objects.get(pk=self.listing.pk).status, Listing.Status.AVAILABLE)

    def test_unknown_report_is_404(self):
        missing = uuid.uuid4()
        self.assertEqual(self.client.post(reverse("moderations:report_review", args=[missing])).status_code, 404)
        self.assertEqual(self.client.post(reverse("moderations:report_listing_action", args=[missing])).status_code, 404)
        self.assertEqual(self.client.get(reverse("moderations:report_notes_popover", args=[missing])).status_code, 404)

    def test_non_uuid_ids_do_not_match_any_route(self):
        self.assertEqual(self.client.post("/moderation/reports/123/review/").status_code, 404)
        self.assertEqual(self.client.get("/moderation/reports/abc/notes/").status_code, 404)


class ModerationReportListTests(ModerationReportBase):
    def test_default_page_uses_open_tab_and_template(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "moderations/reports.html")
        self.assertEqual(response.context["active_tab"], "open")
        self.assertEqual(list(response.context["page"].object_list), [self.report])

    def test_unknown_tab_falls_back_to_open_and_tab_is_case_insensitive(self):
        resolved = self.another_report(status="resolved")
        self.assertEqual(self.client.get(self.list_url, {"tab": "ngawur"}).context["active_tab"], "open")
        response = self.client.get(self.list_url, {"tab": "RESOLVED"})
        self.assertEqual(response.context["active_tab"], "resolved")
        self.assertEqual(list(response.context["page"].object_list), [resolved])

    def test_counts_per_status(self):
        for status in ("open", "reviewing", "reviewing", "resolved", "rejected"):
            self.another_report(status=status)
        context = self.client.get(self.list_url).context
        self.assertEqual(
            (context["count_open"], context["count_reviewing"], context["count_resolved"], context["count_rejected"]),
            (2, 2, 1, 1),
        )

    def test_each_tab_only_lists_its_own_status(self):
        for status in ("reviewing", "resolved", "rejected"):
            self.another_report(status=status)
        for tab in ("open", "reviewing", "resolved", "rejected"):
            with self.subTest(tab=tab):
                page = self.client.get(self.list_url, {"tab": tab}).context["page"]
                self.assertEqual(len(page.object_list), 1)
                self.assertEqual({r.status for r in page.object_list}, {tab})

    def test_oldest_update_comes_first(self):
        newer = self.report
        older = self.another_report()
        base = timezone.now() + timedelta(hours=1)
        Report.objects.filter(pk=newer.pk).update(updated_at=base + timedelta(hours=2))
        Report.objects.filter(pk=older.pk).update(updated_at=base + timedelta(hours=1))
        page = self.client.get(self.list_url).context["page"]
        self.assertEqual(list(page.object_list), [older, newer])

    def test_pagination_is_ten_per_page_and_bad_pages_do_not_crash(self):
        for _ in range(11):
            self.another_report()
        self.assertEqual(len(self.client.get(self.list_url).context["page"].object_list), 10)
        self.assertEqual(len(self.client.get(self.list_url, {"page": 2}).context["page"].object_list), 2)
        for page in ("abc", "0", "-1", "999", ""):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(self.list_url, {"page": page}).status_code, 200)

    def test_first_report_of_the_tab_is_selected_by_default(self):
        self.assertEqual(self.client.get(self.list_url).context["selected_report"], self.report)

    def test_selected_report_can_come_from_another_tab(self):
        resolved = self.another_report(status="resolved")
        response = self.client.get(self.list_url, {"tab": "open", "id": resolved.pk})
        self.assertEqual(response.context["selected_report"], resolved)
        self.assertEqual(list(response.context["page"].object_list), [self.report])

    def test_invalid_or_unknown_id_falls_back_without_error(self):
        for value in ("bukan-uuid", "123", str(uuid.uuid4()), ""):
            with self.subTest(value=value):
                response = self.client.get(self.list_url, {"id": value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["selected_report"], self.report)

    def test_empty_tab_shows_empty_states_and_no_selection(self):
        response = self.client.get(self.list_url, {"tab": "rejected"})
        self.assertIsNone(response.context["selected_report"])
        self.assertContains(response, "Belum ada laporan dipilih")
        self.assertContains(response, "Tidak ada laporan")

    def test_panel_shows_report_details(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, "Kemeja flanel kotak")
        self.assertContains(response, DESCRIPTION)
        self.assertContains(response, "Budi")
        self.assertContains(response, f"#RPT-{str(self.report.pk)[:4].upper()}")
        self.assertContains(response, self.notes_url())

    def test_open_report_offers_all_four_statuses(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, 'name="status"', count=4)
        self.assertNotContains(response, "mr-status-blocked")

    def test_closed_report_cannot_offer_reopening(self):
        for status in ("resolved", "rejected"):
            with self.subTest(status=status):
                self.set_status(status)
                response = self.client.get(self.list_url, {"tab": status})
                self.assertContains(response, 'name="status"', count=2)
                self.assertContains(response, "mr-status-blocked", count=2)

    def test_hide_and_restore_buttons_follow_listing_status(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, 'value="hide"')
        self.assertNotContains(response, 'value="restore"')
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
        response = self.client.get(self.list_url)
        self.assertContains(response, 'value="restore"')
        self.assertContains(response, "Listing sedang disembunyikan")
        self.assertNotContains(response, 'value="hide"')

    def test_report_on_deleted_listing_keeps_title_and_has_no_listing_actions(self):
        self.listing.delete()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kemeja flanel kotak")
        self.assertContains(response, "Listing sudah dihapus penjual.")
        self.assertNotContains(response, self.action_url())

    def test_user_text_is_escaped(self):
        listing = create_listing(self.seller, title="<script>alert(1)</script> kemeja")
        report = make_report(
            make_user("dewi", "Dewi"), listing, description="<img src=x onerror=alert(2)> deskripsi panjang",
        )
        response = self.client.get(self.list_url, {"id": report.pk})
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertNotContains(response, "<img src=x")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertContains(response, "&lt;img src=x onerror=alert(2)&gt;")

    def test_reporter_without_profile_falls_back_to_username(self):
        report = make_report(make_user("tanpaprofil"), create_listing(self.seller, title="Barang tanpa profil"))
        self.assertContains(self.client.get(self.list_url, {"id": report.pk}), "tanpaprofil")


class ModerationReviewActionTests(ModerationReportBase):
    def post_review(self, report=None, **data):
        return self.client.post(self.review_url(report), data)

    def assert_redirect(self, response, tab, report=None):
        report = report or self.report
        self.assertRedirects(response, f"{self.list_url}?tab={tab}&id={report.pk}", fetch_redirect_response=False)

    def test_forward_transitions_are_saved_and_redirect_to_the_new_tab(self):
        for before, after in (("open", "reviewing"), ("open", "resolved"), ("reviewing", "resolved")):
            with self.subTest(before=before, after=after):
                self.set_status(before)
                response = self.post_review(status=after)
                self.assert_redirect(response, after)
                self.assertEqual(self.fresh().status, after)
                self.assertTrue("Keputusan tersimpan." in msgs(response))

    def test_updated_at_is_refreshed(self):
        before = self.fresh().updated_at
        self.post_review(status="reviewing")
        self.assertGreater(self.fresh().updated_at, before)

    def test_decision_without_note_creates_no_note(self):
        self.post_review(status="reviewing", moderator_note="")
        self.post_review(status="resolved", moderator_note="   \n ")
        self.assertFalse(ReportModeratorNote.objects.exists())

    def test_note_is_stripped_and_attached_to_report_and_moderator(self):
        self.post_review(status="resolved", moderator_note="  Sudah dicek, listing diperbaiki.  ")
        note = ReportModeratorNote.objects.get()
        self.assertEqual(note.note, "Sudah dicek, listing diperbaiki.")
        self.assertEqual(note.report_id, self.report)
        self.assertEqual(note.moderator_id, self.admin)

    def test_note_is_cut_to_one_thousand_characters(self):
        self.post_review(status="reviewing", moderator_note="a" * 1500)
        self.assertEqual(len(ReportModeratorNote.objects.get().note), 1000)

    def test_notes_accumulate_across_decisions(self):
        self.post_review(status="reviewing", moderator_note="Mulai ditinjau moderator.")
        self.post_review(status="resolved", moderator_note="Sudah selesai ditangani.")
        self.assertEqual(ReportModeratorNote.objects.filter(report_id=self.report).count(), 2)

    def test_rejecting_requires_a_note(self):
        for note in ("", "   ", None):
            with self.subTest(note=note):
                data = {"status": "rejected"}
                if note is not None:
                    data["moderator_note"] = note
                response = self.client.post(self.review_url(), data)
                self.assert_redirect(response, "open")
                
                storage = get_messages(response.wsgi_request)
                messages_list = [str(m) for m in storage]
                
                self.assertTrue("Catatan moderator wajib diisi bila laporan ditolak." in messages_list)
                self.assertEqual(self.fresh().status, "open")
                storage = []
        self.assertFalse(ReportModeratorNote.objects.exists())

    def test_rejecting_with_a_note_works(self):
        response = self.post_review(status="rejected", moderator_note="Laporan tidak terbukti.")
        self.assert_redirect(response, "rejected")
        self.assertEqual(self.fresh().status, "rejected")
        self.assertEqual(ReportModeratorNote.objects.count(), 1)

    def test_invalid_status_is_rejected(self):
        for data in ({"status": "ngawur"}, {"status": ""}, {}):
            with self.subTest(data=data):
                response = self.client.post(self.review_url(), data)
                self.assert_redirect(response, "open")
                self.assertTrue("Status tidak valid." in msgs(response))
                self.assertEqual(self.fresh().status, "open")

    def test_closed_reports_cannot_be_reopened(self):
        for closed in ("resolved", "rejected"):
            for target in ("open", "reviewing"):
                with self.subTest(closed=closed, target=target):
                    self.set_status(closed)
                    response = self.post_review(status=target, moderator_note="Coba buka lagi laporan.")
                    self.assert_redirect(response, closed)
                    self.assertTrue("Laporan yang sudah diproses tidak dapat dibuka kembali" in msgs(response))
                    self.assertEqual(self.fresh().status, closed)
        self.assertFalse(ReportModeratorNote.objects.exists())

    def test_closed_report_can_switch_between_closed_statuses(self):
        self.set_status("resolved")
        self.assert_redirect(self.post_review(status="rejected", moderator_note="Ternyata tidak terbukti."), "rejected")
        self.assertEqual(self.fresh().status, "rejected")
        self.assert_redirect(self.post_review(status="resolved"), "resolved")
        self.assertEqual(self.fresh().status, "resolved")

    def test_only_status_changes_other_fields_in_post_are_ignored(self):
        other = make_user("dewi", "Dewi")
        self.post_review(status="resolved", description="Dibajak.", reporter=other.pk, reason="Other")
        report = self.fresh()
        self.assertEqual(report.description, DESCRIPTION)
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.reason, "Misleading")

    def test_decision_does_not_touch_the_listing(self):
        self.post_review(status="resolved", moderator_note="Selesai ditinjau.")
        self.assertEqual(Listing.objects.get(pk=self.listing.pk).status, Listing.Status.AVAILABLE)

    def test_integrity_error_on_save_is_reported_without_a_note(self):
        with mock.patch.object(Report, "save", side_effect=IntegrityError):
            response = self.post_review(status="reviewing", moderator_note="Catatan yang tidak jadi disimpan.")
        self.assert_redirect(response, "reviewing")
        self.assertEqual(msgs(response), ["Pelapor telah membuat laporan baru pada listing yang sama"])
        self.assertEqual(self.fresh().status, "open")
        self.assertFalse(ReportModeratorNote.objects.exists())

    def test_full_flow_shows_confirmation_on_the_next_page(self):
        response = self.client.post(
            self.review_url(), {"status": "resolved", "moderator_note": "Selesai ditinjau."}, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Keputusan tersimpan.")
        self.assertEqual(response.context["active_tab"], "resolved")
        self.assertEqual(response.context["selected_report"], self.fresh())


class ModerationListingActionTests(ModerationReportBase):
    def act(self, action=None, report=None):
        data = {} if action is None else {"action": action}
        return self.client.post(self.action_url(report), data)

    def listing_status(self):
        return Listing.objects.get(pk=self.listing.pk).status

    def test_hide_makes_listing_hidden_and_redirects_to_the_report(self):
        response = self.act("hide")
        self.assertRedirects(
            response, f"{self.list_url}?tab=open&id={self.report.pk}", fetch_redirect_response=False,
        )
        self.assertEqual(self.listing_status(), Listing.Status.HIDDEN)
        self.assertEqual(msgs(response), ["Listing disembunyikan."])

    def test_restore_makes_listing_available_again(self):
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
        response = self.act("restore")
        self.assertEqual(self.listing_status(), Listing.Status.AVAILABLE)
        self.assertEqual(msgs(response), ["Listing dipulihkan."])

    def test_hiding_twice_is_harmless(self):
        self.act("hide")
        self.act("hide")
        self.assertEqual(self.listing_status(), Listing.Status.HIDDEN)

    def test_unknown_or_missing_action_changes_nothing(self):
        for action in ("delete", "", "HIDE", None):
            with self.subTest(action=action):
                response = self.act(action)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.listing_status(), Listing.Status.AVAILABLE)
                self.assertEqual(msgs(response), [])

    def test_listing_action_does_not_change_report_status(self):
        self.set_status("reviewing")
        response = self.act("hide")
        self.assertIn("tab=reviewing", response.url)
        self.assertEqual(self.fresh().status, "reviewing")

    def test_report_without_listing_redirects_quietly(self):
        self.listing.delete()
        response = self.act("hide")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(msgs(response), [])
        self.assertEqual(Report.objects.filter(pk=self.report.pk).count(), 1)

    def test_only_the_reported_listing_is_affected(self):
        other = create_listing(self.seller, title="Barang yang aman")
        self.act("hide")
        self.assertEqual(Listing.objects.get(pk=other.pk).status, Listing.Status.AVAILABLE)

    def test_hidden_listing_leaves_public_site_but_seller_still_sees_it(self):
        self.act("hide")
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("listings:list")), "Kemeja flanel kotak")
        self.assertEqual(self.client.get(reverse("listings:detail", args=[self.listing.pk])).status_code, 404)
        self.client.force_login(self.seller)
        mine = self.client.get(reverse("listings:mine"), {"status": "disembunyikan"})
        self.assertContains(mine, "Kemeja flanel kotak")

    def test_restored_listing_returns_to_the_catalog(self):
        self.act("hide")
        self.act("restore")
        self.client.logout()
        self.assertContains(self.client.get(reverse("listings:list")), "Kemeja flanel kotak")

    def test_full_flow_shows_confirmation_on_the_next_page(self):
        response = self.client.post(self.action_url(), {"action": "hide"}, follow=True)
        self.assertContains(response, "Listing disembunyikan.")
        self.assertContains(response, 'value="restore"')


class ModerationNotesPopoverTests(ModerationReportBase):
    def add_note(self, text, moderator=None, report=None):
        return ReportModeratorNote.objects.create(
            report_id=report or self.report, moderator_id=moderator or self.admin, note=text,
        )

    def test_empty_state(self):
        response = self.client.get(self.notes_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "moderations/components/notes_popover.html")
        self.assertContains(response, "Belum ada catatan moderasi.")
        self.assertContains(response, f"#RPT-{str(self.report.pk)[:4].upper()}")

    def test_partial_response_not_a_full_page(self):
        self.assertTemplateNotUsed(self.client.get(self.notes_url()), "base.html")

    def test_notes_are_listed_newest_first(self):
        old = self.add_note("Catatan paling lama.")
        new = self.add_note("Catatan paling baru.")
        base = timezone.now()
        ReportModeratorNote.objects.filter(pk=old.pk).update(created_at=base - timedelta(hours=2))
        ReportModeratorNote.objects.filter(pk=new.pk).update(created_at=base - timedelta(hours=1))
        content = self.client.get(self.notes_url()).content.decode()
        self.assertLess(content.index("Catatan paling baru."), content.index("Catatan paling lama."))

    def test_only_notes_of_this_report_are_shown(self):
        other = self.another_report()
        self.add_note("Catatan laporan ini.")
        self.add_note("Catatan laporan lain.", report=other)
        response = self.client.get(self.notes_url())
        self.assertContains(response, "Catatan laporan ini.")
        self.assertNotContains(response, "Catatan laporan lain.")

    def test_moderator_name_uses_display_name_then_username(self):
        self.add_note("Dari admin tanpa profil.")
        self.assertContains(self.client.get(self.notes_url()), "admin1")
        Profile.objects.create(user=self.admin, display_name="Tim Moderasi")
        self.assertContains(self.client.get(self.notes_url()), "Tim Moderasi")

    def test_note_text_is_escaped(self):
        self.add_note("<script>alert(1)</script> catatan")
        response = self.client.get(self.notes_url())
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_review_note_shows_up_in_popover(self):
        self.client.post(self.review_url(), {"status": "rejected", "moderator_note": "Tidak terbukti melanggar."})
        self.assertContains(self.client.get(self.notes_url()), "Tidak terbukti melanggar.")

    def test_review_action_preserves_page_parameter(self):
            # Buat laporan agar mencapai 2 halaman
            for _ in range(11):
                self.another_report()
            
            # Eksekusi review pada laporan di halaman 2
            response = self.client.post(
                f"{self.review_url()}?tab=open&page=2",
                {"status": "reviewing", "moderator_note": "Tinjau dari hal 2."}
            )
            self.assertRedirects(
                response, 
                f"{self.list_url}?tab=reviewing&id={self.report.pk}", 
                fetch_redirect_response=False
            )
            
    def test_notes_modal_only_endpoint_returns_modal_partial(self):
        modal_url = reverse("moderations:report_notes_popover", args=[self.report.pk])
        response = self.client.get(modal_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catatan Moderasi")
        self.assertNotContains(response, "<html")