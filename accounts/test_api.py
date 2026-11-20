import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import DatabaseError, connection
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from profiles.models import Profile


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountsAPITests(TestCase):
    password = "Kain-Lama!9472-segar"

    def setUp(self):
        self.client = self.browser()

    def browser(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/accounts/login/")
        return client

    def post(self, endpoint, data=None, client=None):
        client = client or self.client
        return client.post(
            f"/api/v1/accounts/{endpoint}/", data=json.dumps({} if data is None else data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )

    def register(self, client=None, **overrides):
        data = {
            "username": "nina.arum", "email": "nina@example.com",
            "password": self.password, "password_confirmation": self.password,
        }
        data.update(overrides)
        return self.post("register", data, client)

    def test_guest_registers_and_starts_incomplete_account_session(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()), {"account", "profile_complete", "next"})
        self.assertEqual(set(response.json()["account"]), {"id", "username", "email"})
        self.assertEqual(response.json()["account"]["username"], "nina.arum")
        self.assertEqual(response.json()["account"]["email"], "nina@example.com")
        self.assertIs(response.json()["profile_complete"], False)
        self.assertEqual(response.json()["next"], "/api/v1/profiles/")
        self.assertIn("sessionid", self.client.cookies)
        self.assertNotIn(self.password, response.content.decode())

    def test_registered_account_can_login_and_existing_session_is_not_replaced(self):
        registered = self.register().json()
        browser = self.browser()
        response = self.post("login", {"username": "nina.arum", "password": self.password,
                                       "next": "https://evil.example/"}, browser)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), registered)
        response = self.post("login", {"username": "other", "password": "wrong"}, browser)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), registered)

    def test_logout_ends_only_current_session_and_also_accepts_guest(self):
        registered = self.register().json()
        other = self.browser()
        self.post("login", {"username": "nina.arum", "password": self.password}, other)
        response = self.post("logout")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.post("logout").status_code, 204)
        self.assertEqual(self.post("login", {}, other).json(), registered)
        self.assertEqual(self.post("login").status_code, 401)

    def test_delete_revokes_all_sessions_and_credentials_for_incomplete_account(self):
        self.register()
        other = self.browser()
        self.post("login", {"username": "nina.arum", "password": self.password}, other)
        response = self.post("delete", {"username": "nina.arum", "password": self.password,
                                        "user_id": 999})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.post("delete").status_code, 401)
        self.assertEqual(self.post("delete", client=other).status_code, 401)
        self.assertEqual(self.post("login", {"username": "nina.arum",
                                            "password": self.password}).status_code, 401)

    def test_database_failure_during_registration_returns_safe_json(self):
        def fail_insert(execute, sql, params, many, context):
            if sql.startswith('INSERT INTO "auth_user"'):
                raise DatabaseError("private registration detail")
            return execute(sql, params, many, context)

        with connection.execute_wrapper(fail_insert):
            response = self.register()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "server_error")
        self.assertNotIn("private registration detail", response.content.decode())

    def test_api_rejects_csrf_and_unsupported_methods_as_json(self):
        for endpoint in ("register", "login", "logout", "delete"):
            url = f"/api/v1/accounts/{endpoint}/"
            for browser in (Client(enforce_csrf_checks=True), self.client):
                response = browser.post(url, {}, content_type="application/json")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "csrf_failed")
            response = self.client.get(url)
            self.assertEqual(response.status_code, 405)
            self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_registration_enforces_django_validation_and_guest_only_access(self):
        cases = [({"username": "bad name"}, "username"),
                 ({"username": "x" * 151}, "username"),
                 ({"email": "invalid"}, "email"),
                 ({"password_confirmation": "wrong"}, "password_confirmation")]
        for password in ("short", "password", "123456789012", "nina.arum"):
            cases.append(({"password": password, "password_confirmation": password},
                          "password_confirmation"))
        for values, field in cases:
            with self.subTest(values=values):
                response = self.register(**values)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()["error"]["fields"])
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register(username="another").status_code, 403)
        response = self.register(client=self.browser())
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json()["error"]["fields"])

    def test_login_failure_is_identical_for_unknown_inactive_and_wrong_password(self):
        User.objects.create_user("inactive", password=self.password, is_active=False)
        User.objects.create_user("active", password=self.password)
        expected = {"error": {"code": "invalid_credentials", "message": "Username atau kata sandi salah."}}
        for data in ({}, {"username": "unknown", "password": self.password},
                     {"username": "inactive", "password": self.password},
                     {"username": "active", "password": "wrong"}):
            response = self.post("login", data)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), expected)

    def test_login_rejects_non_string_credentials(self):
        User.objects.create_user("123", password=self.password)
        response = self.post("login", {"username": 123, "password": self.password})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "invalid_credentials")

    def test_non_object_and_malformed_json_return_json_errors(self):
        for endpoint, code in (("register", "validation_error"), ("login", "invalid_credentials")):
            for data in ([], "", False, 0):
                response = self.post(endpoint, data)
                self.assertEqual(response.status_code, 401 if endpoint == "login" else 400)
                self.assertEqual(response.json()["error"]["code"], code)
            response = self.client.generic(
                "POST", f"/api/v1/accounts/{endpoint}/", b"{", content_type="application/json",
                HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error"]["code"], "parse_error")

    def test_complete_member_login_returns_local_profile_destination(self):
        user = User.objects.create_user("member", password=self.password)
        Profile.objects.create(user=user, display_name="  Nina  ")
        response = self.post("login", {"username": "member", "password": self.password})
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["profile_complete"], True)
        self.assertEqual(response.json()["next"], "/api/v1/profiles/me/")

    def test_staff_and_superuser_cannot_delete_themselves(self):
        for flags in ({"is_staff": True}, {"is_superuser": True}):
            user = User.objects.create_user("admin" + str(len(flags)) + str(flags),
                                            password=self.password, **flags)
            browser = self.browser()
            browser.force_login(user)
            response = self.post("delete", {"username": user.username, "password": self.password}, browser)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"]["code"], "self_deletion_forbidden")
            self.assertEqual(self.post("login", {}, browser).json()["account"]["id"], user.pk)

    def test_database_failure_rolls_back_deletion_and_preserves_other_sessions(self):
        registered = self.register().json()
        other = self.browser()
        self.post("login", {"username": "nina.arum", "password": self.password}, other)

        def fail_user_delete(execute, sql, params, many, context):
            if sql.startswith('DELETE FROM "auth_user"'):
                raise DatabaseError("private database detail")
            return execute(sql, params, many, context)

        with connection.execute_wrapper(fail_user_delete):
            response = self.post("delete", {"username": "nina.arum", "password": self.password})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private database detail", response.content.decode())
        self.assertEqual(self.post("login", {}, other).json(), registered)
        self.assertEqual(self.post("login").json(), registered)

    def test_registration_rejects_non_string_fields_without_creating_session(self):
        for field in ("username", "email", "password", "password_confirmation"):
            for value in (True, 123456789, ["valid-string"], {"value": "text"}, None):
                with self.subTest(field=field, value=value):
                    response = self.register(**{field: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.json()["error"]["fields"])
        self.assertEqual(self.register().status_code, 201)

    def test_non_string_confirmation_never_matches_string_credentials(self):
        user = User.objects.create_user("123", password="{'key': 'secret'}")
        self.client.force_login(user)
        for data in ({"username": 123, "password": "{'key': 'secret'}"},
                     {"username": "123", "password": {"key": "secret"}}):
            response = self.post("delete", data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error"]["code"], "confirmation_failed")
        for _ in range(3):
            self.assertEqual(self.post("delete").status_code, 400)
        self.assertEqual(self.post("delete").status_code, 429)

    def test_malformed_confirmation_counts_toward_cross_session_limit(self):
        self.register()
        other = self.browser()
        self.post("login", {"username": "nina.arum", "password": self.password}, other)
        for data in ({}, {"username": []}, {"password": {}}, "{", {"username": "wrong"}):
            if data == "{":
                response = self.client.generic(
                    "POST", "/api/v1/accounts/delete/", b"{", content_type="application/json",
                    HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
                )
            else:
                response = self.post("delete", data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error"]["code"], "confirmation_failed")
        self.assertEqual(self.post("delete", {"username": "nina.arum", "password": self.password},
                                   other).status_code, 429)
        with patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(minutes=16)):
            self.assertEqual(self.post("delete", {"username": "nina.arum",
                                                   "password": self.password}, other).status_code, 204)
