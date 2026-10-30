from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from listings.models import Listing
from listings.test_detail import create_listing, make_user
from reports.models import Report

# Nilai alasan pertama dari choices model, supaya tes tidak bergantung pada huruf besar-kecil
REASON = Report._meta.get_field("reason").choices[0][0]


def make_report(reporter, listing, **overrides):
    data = {
        "reporter": reporter, "listing": listing, "reason": REASON,
        "description": "Foto tidak sesuai dengan barang aslinya.",
    }
    data.update(overrides)
    return Report(**data)


def create_report(reporter, listing, **overrides):
    # save() tidak memanggil clean(), jadi helper ini juga bisa membuat data yang sengaja "kotor"
    report = make_report(reporter, listing, **overrides)
    report.save()
    return report


class ReportModelTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.reporter = make_user("budi", "Budi")
        self.listing = create_listing(self.seller, title="Kemeja flanel kotak")

    def test_valid_report_gets_defaults_and_title_snapshot(self):
        report = make_report(self.reporter, self.listing)
        report.full_clean()
        report.save()
        self.assertEqual(report.status, "open")
        # self.assertEqual(report.moderator_note, "")
        self.assertEqual(report.listing_title, "Kemeja flanel kotak")
        self.assertTrue(report.is_editable)

    def test_str_uses_the_snapshot_title(self):
        report = create_report(self.reporter, self.listing)
        self.assertIn("Kemeja flanel kotak", str(report))
        self.assertIn(f"#{report.pk}", str(report))

    def test_snapshot_is_taken_once_and_survives_a_title_change(self):
        report = create_report(self.reporter, self.listing)
        self.listing.title = "Judul baru yang berbeda"
        self.listing.save()
        report.description = "Penjelasan yang sudah diperbarui."
        report.save()
        report.refresh_from_db()
        self.assertEqual(report.listing_title, "Kemeja flanel kotak")

    def test_report_survives_listing_deletion_with_its_title(self):
        report = create_report(self.reporter, self.listing)
        self.listing.delete()
        report.refresh_from_db()
        self.assertIsNone(report.listing)
        self.assertEqual(report.listing_title, "Kemeja flanel kotak")
        self.assertIn("Kemeja flanel kotak", str(report))

    def test_deleting_the_reporter_removes_their_reports(self):
        create_report(self.reporter, self.listing)
        self.reporter.delete()
        self.assertEqual(Report.objects.count(), 0)

    def test_unknown_reason_and_short_description_are_rejected(self):
        for field, value in (("reason", "Ngawur"), ("description", "pendek")):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    make_report(self.reporter, self.listing, **{field: value}).full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_description_and_reason_are_required(self):
        for field in ("reason", "description"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    make_report(self.reporter, self.listing, **{field: ""}).full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            make_report(self.reporter, self.listing, status="ngawur").full_clean()
        self.assertIn("status", ctx.exception.message_dict)

    def test_cannot_report_own_listing(self):
        with self.assertRaises(ValidationError):
            make_report(self.seller, self.listing).full_clean()

    def test_cannot_report_hidden_listing(self):
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        with self.assertRaises(ValidationError):
            make_report(self.reporter, self.listing).full_clean()

    def test_available_and_sold_listings_can_be_reported(self):
        for status in (Listing.Status.AVAILABLE, Listing.Status.SOLD):
            with self.subTest(status=status):
                self.listing.status = status
                self.listing.save()
                make_report(self.reporter, self.listing).full_clean()

    def test_report_without_a_listing_is_rejected_when_created(self):
        with self.assertRaises(ValidationError):
            make_report(self.reporter, None).full_clean()

    def test_hiding_the_listing_does_not_block_editing_the_report(self):
        report = create_report(self.reporter, self.listing)
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        report.refresh_from_db()
        report.description = "Penjelasan yang diperbarui oleh pelapor."
        report.full_clean()

    def test_editing_an_active_report_is_not_flagged_as_its_own_duplicate(self):
        report = create_report(self.reporter, self.listing)
        report.description = "Penjelasan baru yang cukup panjang."
        report.full_clean()


class ReportDuplicateRuleTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.reporter = make_user("budi", "Budi")
        self.listing = create_listing(self.seller)

    def test_another_reporter_may_report_the_same_listing(self):
        create_report(self.reporter, self.listing)
        make_report(make_user("dewi", "Dewi"), self.listing).full_clean()

    def test_same_reporter_may_report_a_different_listing(self):
        create_report(self.reporter, self.listing)
        make_report(self.reporter, create_listing(self.seller, title="Barang kedua yang berbeda")).full_clean()

    def test_finished_reports_do_not_block_a_new_one(self):
        for status in ("resolved", "rejected"):
            with self.subTest(status=status):
                Report.objects.all().delete()
                create_report(self.reporter, self.listing, status=status)
                make_report(self.reporter, self.listing).full_clean()

    def test_database_constraint_blocks_duplicates_that_skip_validation(self):
        create_report(self.reporter, self.listing)
        with self.assertRaises(IntegrityError), transaction.atomic():
            create_report(self.reporter, self.listing)

    def test_database_constraint_allows_a_new_report_after_the_old_one_finished(self):
        create_report(self.reporter, self.listing, status="resolved")
        create_report(self.reporter, self.listing)
        self.assertEqual(Report.objects.count(), 2)


class ReportEditableTests(TestCase):
    def test_only_open_reports_are_editable_by_the_reporter(self):
        seller = make_user("sari", "Sari")
        reporter = make_user("budi", "Budi")
        listing = create_listing(seller)
        expectations = (("open", True), ("reviewing", False),
                        ("resolved", False), ("rejected", False))
        for status, expected in expectations:
            with self.subTest(status=status):
                self.assertEqual(make_report(reporter, listing, status=status).is_editable, expected)


class ReportOrderingTests(TestCase):
    def test_newest_report_comes_first(self):
        seller = make_user("sari", "Sari")
        reporter = make_user("budi", "Budi")
        first = create_report(reporter, create_listing(seller, title="Listing pertama"))
        second = create_report(reporter, create_listing(seller, title="Listing kedua"))
        self.assertEqual(list(Report.objects.all()), [second, first])