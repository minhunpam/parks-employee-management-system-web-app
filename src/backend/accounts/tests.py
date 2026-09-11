from django.test import TestCase, override_settings
from django.urls import reverse

from .models import User
from .views import PENDING_APPROVAL_USER_SESSION_KEY


class NotFoundPageTests(TestCase):
    @override_settings(DEBUG=False)
    def test_unknown_url_renders_branded_page_with_404_status(self):
        response = self.client.get("/this-page-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)
        self.assertContains(
            response,
            "The page you’re looking for doesn’t exist or may have moved.",
            status_code=404,
        )
        self.assertContains(response, 'href="/"', count=2, status_code=404)
        self.assertContains(response, "Go back", status_code=404)


class GoogleLoginPopupTests(TestCase):
    def test_home_loads_google_login_popup_script(self):
        response = self.client.get(reverse("home"))

        self.assertContains(
            response,
            "scripts/accounts/google-login.js",
        )

    def test_approval_page_loads_google_login_popup_script(self):
        user = User.objects.create_user(
            email="pending-popup@example.com",
            password="password",
            is_active=False,
        )
        session = self.client.session
        session[PENDING_APPROVAL_USER_SESSION_KEY] = user.pk
        session.save()

        response = self.client.get(reverse("accounts:approval-pending"))

        self.assertContains(
            response,
            "scripts/accounts/google-login.js",
            status_code=403,
        )


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

    def test_authenticated_active_user_is_redirected_to_workspace(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        self.client.force_login(self.user)

        session = self.client.session
        session.pop(PENDING_APPROVAL_USER_SESSION_KEY, None)
        session.save()

        response = self.client.get(reverse("accounts:approval-pending"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("workspace:entry"))
