from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import monotonic, sleep
from unittest import skipUnless

from django.db import connection, transaction
from django.test import Client, TransactionTestCase

from favorites.models import Favorite
from listings.models import Listing
from listings.test_detail import create_listing, make_user


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class FavoriteAPIConcurrencyTests(TransactionTestCase):
    url = "/api/v1/favorites/"

    def setUp(self):
        self.member = make_user("member", "Member")
        self.listing = create_listing(make_user("seller"))
        self.client.force_login(self.member)

    def request_while_hiding_listing(self, method, url, data):
        backend_pid = Queue()

        def send_request():
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_pid.put(cursor.fetchone()[0])
                client = Client()
                client.cookies.update(self.client.cookies)
                return getattr(client, method)(url, data, content_type="application/json")
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
                response = executor.submit(send_request)
                pid = backend_pid.get(timeout=5)
                deadline = monotonic() + 5
                # Release moderation's lock only after the request either finishes or waits on it.
                while not response.done():
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_blocking_pids(%s)", [pid])
                        if cursor.fetchone()[0]:
                            break
                    if monotonic() >= deadline:
                        self.fail("The favorite request neither finished nor waited on the listing lock.")
                    sleep(0.01)
            return response.result(timeout=5)

    def test_cannot_add_favorite_when_concurrent_hide_commits_first(self):
        response = self.request_while_hiding_listing("post", self.url, {"listing_id": self.listing.pk})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Favorite.objects.exists())

    def test_repeated_post_after_concurrent_hide_does_not_return_listing(self):
        Favorite.objects.create(user=self.member, listing=self.listing)
        response = self.request_while_hiding_listing("post", self.url, {"listing_id": self.listing.pk})
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("listing", response.json())

    def test_cannot_edit_note_when_concurrent_hide_commits_first(self):
        favorite = Favorite.objects.create(user=self.member, listing=self.listing, note="Catatan lama")
        url = f"{self.url}{favorite.pk}/"
        response = self.request_while_hiding_listing("patch", url, {"note": "Catatan baru"})
        self.assertEqual(response.status_code, 404)
        favorite.refresh_from_db()
        self.assertEqual(favorite.note, "Catatan lama")
