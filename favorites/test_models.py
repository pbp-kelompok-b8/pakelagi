from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from favorites.models import Favorite
from listings.test_detail import create_listing, make_user


class FavoriteModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("seller", "Penjual")
        cls.member = make_user("member", "Member")
        cls.listing = create_listing(cls.seller)

    def test_valid_favorite_allows_blank_note_and_has_timestamps(self):
        favorite = Favorite(user=self.member, listing=self.listing)
        favorite.full_clean()
        favorite.save()
        self.assertEqual(favorite.note, "")
        self.assertIsNotNone(favorite.created_at)
        self.assertIsNotNone(favorite.updated_at)

    def test_user_listing_pair_is_unique_in_database(self):
        Favorite.objects.create(user=self.member, listing=self.listing)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=self.member, listing=self.listing)

    def test_different_users_can_save_the_same_listing(self):
        other = make_user("other", "Lain")
        for user in (self.member, other):
            Favorite.objects.create(user=user, listing=self.listing)
        self.assertEqual(Favorite.objects.count(), 2)

    def test_note_length_is_limited_to_one_thousand_characters(self):
        favorite = Favorite(user=self.member, listing=self.listing, note="a" * 1000)
        favorite.full_clean()
        favorite.note += "a"
        with self.assertRaises(ValidationError):
            favorite.full_clean()

    def test_deleting_listing_cascades_to_favorites(self):
        Favorite.objects.create(user=self.member, listing=self.listing)
        self.listing.delete()
        self.assertFalse(Favorite.objects.exists())

    def test_deleting_user_cascades_to_favorites(self):
        Favorite.objects.create(user=self.member, listing=self.listing)
        self.member.delete()
        self.assertFalse(Favorite.objects.exists())
