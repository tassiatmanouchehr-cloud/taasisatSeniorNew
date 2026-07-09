"""
Tests for Module 21A — UserAccount authentication UX fix.

Covers: USERNAME_FIELD/REQUIRED_FIELDS configuration, email uniqueness
(including the null-not-blank multi-account allowance), Django admin login
using email instead of the UUID primary key, and createsuperuser no longer
prompting for the id field.
"""

import io
import uuid

from django.contrib.auth import authenticate
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings

from apps.kernel.models import Person, Tenant, UserAccount


@override_settings(ALLOWED_HOSTS=["*"])
class UsernameFieldConfigurationTest(TestCase):
    def test_username_field_is_email_not_id(self):
        self.assertEqual(UserAccount.USERNAME_FIELD, "email")

    def test_required_fields_no_longer_include_email(self):
        # USERNAME_FIELD must never appear in REQUIRED_FIELDS (Django auth.E002).
        self.assertNotIn("email", UserAccount.REQUIRED_FIELDS)

    def test_email_field_attribute_is_set(self):
        self.assertEqual(UserAccount.EMAIL_FIELD, "email")


class EmailUniquenessTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")

    def test_duplicate_email_is_rejected(self):
        UserAccount.objects.create_user(email="dup@example.com", password="x", tenant=self.tenant)
        with self.assertRaises(IntegrityError):
            UserAccount.objects.create_user(email="dup@example.com", password="x", tenant=self.tenant)

    def test_multiple_phone_only_accounts_with_no_email_do_not_collide(self):
        user1 = UserAccount.objects.create_user(phone="09121111111", tenant=self.tenant)
        user2 = UserAccount.objects.create_user(phone="09122222222", tenant=self.tenant)
        self.assertIsNone(user1.email)
        self.assertIsNone(user2.email)


@override_settings(ALLOWED_HOSTS=["*"])
class SeededAdminAuthenticationTest(TestCase):
    """seeded admin can authenticate with email/password (Django's authenticate())."""

    def setUp(self):
        call_command("seed_tenant")

    def test_authenticate_with_email_and_password_succeeds(self):
        user = authenticate(email="admin@marketplace.local", password="admin123456")
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "admin@marketplace.local")

    def test_authenticate_with_wrong_password_fails(self):
        user = authenticate(email="admin@marketplace.local", password="wrong-password")
        self.assertIsNone(user)


@override_settings(ALLOWED_HOSTS=["*"])
class DjangoAdminLoginUsesEmailTest(TestCase):
    """Django admin login form must ask for email, not the UUID id field."""

    def setUp(self):
        call_command("seed_tenant")
        self.client = Client()

    def test_login_form_label_is_not_id(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn(">Id:</label>", content)
        self.assertNotIn('for="id_username">Id', content)

    def test_login_form_label_mentions_email(self):
        response = self.client.get("/admin/login/")
        content = response.content.decode()
        self.assertIn("Email", content)

    def test_login_with_email_and_password_redirects_into_admin(self):
        response = self.client.post(
            "/admin/login/",
            {"username": "admin@marketplace.local", "password": "admin123456", "next": "/admin/"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/")

    def test_login_with_uuid_id_no_longer_works(self):
        user = UserAccount.objects.get(email="admin@marketplace.local")
        response = self.client.post(
            "/admin/login/",
            {"username": str(user.id), "password": "admin123456", "next": "/admin/"},
        )
        self.assertEqual(response.status_code, 200)  # re-renders form with an error, no redirect
        self.assertIn('class="errornote"', response.content.decode())


class CreateSuperuserTest(TestCase):
    """createsuperuser must no longer ask for the id field as the login identifier."""

    def test_noinput_creation_only_needs_email(self):
        call_command(
            "createsuperuser",
            interactive=False,
            email="root@example.com",
            stdout=io.StringIO(),
        )
        user = UserAccount.objects.get(email="root@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_username_field_used_by_command_is_email(self):
        # The command reads UserModel.USERNAME_FIELD to decide what to prompt for.
        self.assertEqual(UserAccount.USERNAME_FIELD, "email")


@override_settings(ALLOWED_HOSTS=["*"])
class UserAccountAdminFormsTest(TestCase):
    """UserAccountAdmin.form/add_form must be bound to UserAccount, not auth.User."""

    def setUp(self):
        call_command("seed_tenant")
        self.client = Client()
        self.client.login(email="admin@marketplace.local", password="admin123456")

    def test_add_user_page_renders_without_error(self):
        response = self.client.get("/admin/kernel/useraccount/add/")
        self.assertEqual(response.status_code, 200)

    def test_change_user_page_renders_without_error(self):
        user = UserAccount.objects.get(email="admin@marketplace.local")
        response = self.client.get(f"/admin/kernel/useraccount/{user.id}/change/")
        self.assertEqual(response.status_code, 200)
