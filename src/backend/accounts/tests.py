from django.test import TestCase
from django.urls import reverse

from .models import User
from .views import PENDING_APPROVAL_USER_SESSION_KEY


class GoogleLogoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password",
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_logout_clears_authenticated_session_and_redirects_home(self):
        session = self.client.session
        session[PENDING_APPROVAL_USER_SESSION_KEY] = self.user.pk
        session["temporary_state"] = "value"
        session.save()

        response = self.client.post(reverse("accounts:google-logout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))
        self.assertFalse(self.client.session.get("_auth_user_id"))
        self.assertNotIn(PENDING_APPROVAL_USER_SESSION_KEY, self.client.session)
        self.assertNotIn("temporary_state", self.client.session)

    def test_logout_requires_post(self):
        self.assertEqual(
            self.client.get(reverse("accounts:google-logout")).status_code,
            405,
        )


class ApprovalPendingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pending@example.com",
            password="password",
            is_active=False,
        )
        session = self.client.session
        session[PENDING_APPROVAL_USER_SESSION_KEY] = self.user.pk
        session.save()

    def test_active_user_is_redirected_to_workspace_entry(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])

        response = self.client.get(reverse("accounts:approval-pending"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workspace:entry"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertNotIn(
            PENDING_APPROVAL_USER_SESSION_KEY,
            self.client.session,
        )

    def test_inactive_user_stays_on_approval_page(self):
        response = self.client.get(reverse("accounts:approval-pending"))

        self.assertEqual(response.status_code, 403)
