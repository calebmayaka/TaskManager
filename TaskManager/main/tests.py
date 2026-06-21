import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase, override_settings

from main.models import UserApproval, UserApprovalAuditLog, UserProfile
from main.services import approve_user, register_user, reject_user


User = get_user_model()


class AuthApprovalFlowTests(TestCase):
    def setUp(self):
        self.review_permission = Permission.objects.get(
            codename="can_review_user_approvals"
        )
        self.reviewer = User.objects.create_user(
            username="reviewer",
            email="reviewer@example.com",
            password="StrongPass!123",
            is_staff=True,
        )
        self.reviewer.user_permissions.add(self.review_permission)

    def _register_pending_user(
        self,
        username="pendinguser",
        email="pending@example.com",
        password="StrongPass!123",
        full_name="Pending User",
    ):
        return register_user(
            email=email,
            password=password,
            full_name=full_name,
            username=username,
        )

    def _create_active_user(
        self,
        username="normaluser",
        email="normal@example.com",
        password="StrongPass!123",
        is_staff=False,
    ):
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True,
            is_staff=is_staff,
        )

    def test_register_creates_inactive_user_and_pending_approval_record(self):
        pending_url = f"{reverse('main:register')}?pending=1"
        response = self.client.post(
            reverse("main:register"),
            data={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password1": "StrongPass!123",
                "password2": "StrongPass!123",
            },
        )

        self.assertRedirects(response, pending_url, fetch_redirect_response=False)
        pending_page_response = self.client.get(pending_url)
        self.assertContains(
            pending_page_response,
            "Your account is pending approval. Please wait for admin approval.",
        )
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(user.username)
        self.assertEqual(user.approval.status, UserApproval.Status.PENDING)
        self.assertTrue(
            UserApprovalAuditLog.objects.filter(
                target_user=user, action=UserApprovalAuditLog.Action.REGISTERED
            ).exists()
        )

    def test_root_redirects_to_login(self):
        response = self.client.get(reverse("main:root"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:login"))

    def test_login_page_get_returns_ok(self):
        response = self.client.get(reverse("main:login"))
        self.assertEqual(response.status_code, 200)

    def test_logout_post_logs_out_and_redirects_to_login(self):
        normal_user = self._create_active_user(
            username="logoutuser",
            email="logout@example.com",
        )
        self.client.force_login(normal_user)

        response = self.client.post(reverse("main:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="StrongPass!123",
            is_active=True,
        )

        response = self.client.post(
            reverse("main:register"),
            data={
                "email": "EXISTING@example.com",
                "full_name": "New User",
                "password1": "StrongPass!123",
                "password2": "StrongPass!123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with this email already exists.")
        self.assertFalse(User.objects.filter(email="newuser@example.com").exists())

    def test_unapproved_user_cannot_login_and_sees_pending_message(self):
        self._register_pending_user(email="pending@example.com")

        response = self.client.post(
            reverse("main:login"),
            data={"username": "pending@example.com", "password": "StrongPass!123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Your account is pending approval. Please wait for admin approval.",
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_approved_user_can_login(self):
        user = self._register_pending_user(
            username="approveduser",
            email="approved@example.com",
        )
        approve_user(target_user=user, reviewer=self.reviewer, notes="Approved")

        response = self.client.post(
            reverse("main:login"),
            data={"username": "approved@example.com", "password": "StrongPass!123"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:dashboard-entry"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_rejected_user_cannot_login(self):
        user = self._register_pending_user(
            username="rejecteduser",
            email="rejected@example.com",
        )
        reject_user(
            target_user=user,
            reviewer=self.reviewer,
            reason="Policy mismatch",
            notes="Rejected",
        )

        response = self.client.post(
            reverse("main:login"),
            data={"username": "rejected@example.com", "password": "StrongPass!123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_entry_routes_admin_to_admin_dashboard(self):
        self.client.force_login(self.reviewer)

        response = self.client.get(reverse("main:dashboard-entry"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:admin-dashboard"))

    def test_dashboard_entry_routes_normal_user_to_user_dashboard(self):
        normal_user = self._create_active_user()
        self.client.force_login(normal_user)

        response = self.client.get(reverse("main:dashboard-entry"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:user-dashboard"))

    def test_admin_dashboard_requires_login(self):
        response = self.client.get(reverse("main:admin-dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("main:login"), response.url)

    def test_admin_dashboard_forbidden_without_permission(self):
        no_permission_staff = User.objects.create_user(
            username="staffnoperm",
            email="staffnoperm@example.com",
            password="StrongPass!123",
            is_staff=True,
        )
        self.client.force_login(no_permission_staff)

        response = self.client.get(reverse("main:admin-dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_entry_redirects_to_tasks_module(self):
        self.client.force_login(self.reviewer)

        response = self.client.get(reverse("main:admin-dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:admin-dashboard-tasks"))

    def test_admin_dashboard_tasks_module_available_for_staff_with_permission(self):
        self.client.force_login(self.reviewer)

        response = self.client.get(reverse("main:admin-dashboard-tasks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task Management")

    def test_admin_dashboard_users_module_available_for_staff_with_permission(self):
        self.client.force_login(self.reviewer)

        response = self.client.get(reverse("main:admin-dashboard-users"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approval Queue")

    def test_pending_users_alias_redirects_to_admin_dashboard(self):
        response = self.client.get(reverse("main:pending-users"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:admin-dashboard-users"))

    def test_user_dashboard_accessible_for_approved_user(self):
        normal_user = self._create_active_user(
            username="dashboarduser",
            email="dashboard@example.com",
        )
        self.client.force_login(normal_user)

        response = self.client.get(reverse("main:user-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task Dashboard Coming Next")

    def test_account_profile_requires_login(self):
        response = self.client.get(reverse("main:account-profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("main:login"), response.url)

    def test_account_profile_page_accessible_for_logged_in_user(self):
        user = self._create_active_user(
            username="profileuser",
            email="profile@example.com",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("main:account-profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account Profile")

    def test_account_profile_updates_names_phone_and_secondary_email(self):
        user = self._create_active_user(
            username="profileedit",
            email="profileedit@example.com",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("main:account-profile"),
            data={
                "first_name": "Profile",
                "last_name": "Editor",
                "email": "profile.editor@example.com",
                "country_prefix": "+1",
                "phone_number": "(212) 555-8877",
                "secondary_email": "backup@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:account-profile"))

        user.refresh_from_db()
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(user.first_name, "Profile")
        self.assertEqual(user.last_name, "Editor")
        self.assertEqual(user.email, "profileedit@example.com")
        self.assertEqual(profile.country_prefix, "+1")
        self.assertEqual(profile.phone_number, "(212) 555-8877")
        self.assertEqual(profile.secondary_email, "backup@example.com")

    def test_account_profile_rejects_secondary_email_equal_to_primary(self):
        user = self._create_active_user(
            username="sameemail",
            email="same@example.com",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("main:account-profile"),
            data={
                "first_name": "Same",
                "last_name": "Email",
                "email": "same@example.com",
                "phone_number": "",
                "secondary_email": "same@example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Secondary email must be different from primary email.",
        )

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_account_profile_rejects_non_image_upload(self):
        user = self._create_active_user(
            username="badimage",
            email="badimage@example.com",
        )
        self.client.force_login(user)

        bad_file = SimpleUploadedFile(
            "not-image.txt",
            b"not image data",
            content_type="text/plain",
        )
        response = self.client.post(
            reverse("main:account-profile"),
            data={
                "first_name": "Bad",
                "last_name": "Image",
                "email": "badimage@example.com",
                "phone_number": "",
                "secondary_email": "",
                "profile_picture": bad_file,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload a valid image file.")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_account_profile_accepts_image_upload(self):
        user = self._create_active_user(
            username="goodimage",
            email="goodimage@example.com",
        )
        self.client.force_login(user)

        image_file = SimpleUploadedFile(
            "avatar.png",
            b"\x89PNG\r\n\x1a\n",
            content_type="image/png",
        )
        response = self.client.post(
            reverse("main:account-profile"),
            data={
                "first_name": "Good",
                "last_name": "Image",
                "email": "goodimage@example.com",
                "phone_number": "",
                "secondary_email": "good.backup@example.com",
                "profile_picture": image_file,
            },
        )

        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=user)
        self.assertIn("profile_pictures", profile.profile_picture.name)
        self.assertTrue(profile.profile_picture.name.endswith(".png"))

    def test_staff_with_permission_can_approve_user(self):
        user = self._register_pending_user(username="approveview")
        self.client.force_login(self.reviewer)

        response = self.client.post(
            reverse(
                "main:review-user-approval", kwargs={"user_id": user.id, "action": "approve"}
            ),
            data={"notes": "Looks good"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:admin-dashboard-users"))
        user.refresh_from_db()
        approval = user.approval
        self.assertTrue(user.is_active)
        self.assertEqual(approval.status, UserApproval.Status.APPROVED)
        self.assertEqual(approval.reviewed_by, self.reviewer)
        self.assertEqual(approval.review_notes, "Looks good")
        self.assertIsNotNone(approval.reviewed_at)
        self.assertLessEqual(approval.reviewed_at, timezone.now())

    def test_staff_with_permission_can_reject_user_and_store_reason(self):
        user = self._register_pending_user(username="rejectview")
        self.client.force_login(self.reviewer)

        response = self.client.post(
            reverse(
                "main:review-user-approval", kwargs={"user_id": user.id, "action": "reject"}
            ),
            data={"reason": "Incomplete profile", "notes": "Missing details"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("main:admin-dashboard-users"))
        user.refresh_from_db()
        approval = user.approval
        self.assertFalse(user.is_active)
        self.assertEqual(approval.status, UserApproval.Status.REJECTED)
        self.assertEqual(approval.reviewed_by, self.reviewer)
        self.assertEqual(approval.rejection_reason, "Incomplete profile")
        self.assertEqual(approval.review_notes, "Missing details")

    def test_approval_actions_write_audit_logs(self):
        user = self._register_pending_user(username="auditeduser")
        approve_user(target_user=user, reviewer=self.reviewer, notes="Approved")
        reject_user(
            target_user=user,
            reviewer=self.reviewer,
            reason="Revoked",
            notes="Follow-up rejection",
        )

        actions = list(
            UserApprovalAuditLog.objects.filter(target_user=user)
            .order_by("created_at")
            .values_list("action", flat=True)
        )
        self.assertEqual(
            actions,
            [
                UserApprovalAuditLog.Action.REGISTERED,
                UserApprovalAuditLog.Action.APPROVED,
                UserApprovalAuditLog.Action.REJECTED,
            ],
        )

    def test_approve_idempotent_no_duplicate_audit_on_noop(self):
        user = self._register_pending_user(username="idempotentuser")

        approve_user(target_user=user, reviewer=self.reviewer, notes="Approved")
        approve_user(target_user=user, reviewer=self.reviewer, notes="Approved")

        approved_logs = UserApprovalAuditLog.objects.filter(
            target_user=user, action=UserApprovalAuditLog.Action.APPROVED
        )
        self.assertEqual(approved_logs.count(), 1)


class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _post_login(self, ip="1.2.3.4"):
        return self.client.post(
            reverse("main:login"),
            data={"username": "nobody@example.com", "password": "wrongpass"},
            REMOTE_ADDR=ip,
        )

    def _post_register(self, email, ip="1.2.3.4"):
        return self.client.post(
            reverse("main:register"),
            data={
                "email": email,
                "full_name": "Rate Test",
                "password1": "StrongPass!123",
                "password2": "StrongPass!123",
            },
            REMOTE_ADDR=ip,
        )

    def test_login_allows_requests_up_to_limit(self):
        for i in range(5):
            response = self._post_login()
            self.assertNotEqual(response.status_code, 429)

    def test_login_blocks_on_attempt_exceeding_limit(self):
        for _ in range(5):
            self._post_login()
        response = self._post_login()
        self.assertEqual(response.status_code, 429)

    def test_login_rate_limit_is_per_ip(self):
        for _ in range(5):
            self._post_login(ip="1.2.3.4")
        response = self._post_login(ip="9.9.9.9")
        self.assertNotEqual(response.status_code, 429)

    def test_login_get_requests_are_never_rate_limited(self):
        for _ in range(10):
            response = self.client.get(reverse("main:login"), REMOTE_ADDR="1.2.3.4")
            self.assertEqual(response.status_code, 200)

    def test_register_allows_requests_up_to_limit(self):
        for i in range(10):
            response = self._post_register(email=f"rl{i}@example.com")
            self.assertNotEqual(response.status_code, 429)

    def test_register_blocks_on_attempt_exceeding_limit(self):
        for i in range(10):
            self._post_register(email=f"rl{i}@example.com")
        response = self._post_register(email="rl10@example.com")
        self.assertEqual(response.status_code, 429)

    def test_register_rate_limit_is_per_ip(self):
        for i in range(10):
            self._post_register(email=f"rl{i}@example.com", ip="1.2.3.4")
        response = self._post_register(email="other@example.com", ip="9.9.9.9")
        self.assertNotEqual(response.status_code, 429)

    def test_rate_limited_response_contains_window_info(self):
        for _ in range(5):
            self._post_login()
        response = self._post_login()
        self.assertContains(response, "15 minutes", status_code=429)
