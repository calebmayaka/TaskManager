from django.conf import settings
from django.db import models


def profile_picture_upload_to(instance, filename):
    return f"profile_pictures/{instance.user_id}/{filename}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    country_prefix = models.CharField(max_length=8, default="+1")
    phone_number = models.CharField(max_length=32, blank=True)
    secondary_email = models.EmailField(blank=True)
    profile_picture = models.FileField(
        upload_to=profile_picture_upload_to,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user.username}>"


class UserApproval(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_user_approvals",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("can_review_user_approvals", "Can review user approvals"),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.status})"


class UserApprovalAuditLog(models.Model):
    class Action(models.TextChoices):
        REGISTERED = "registered", "Registered"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_actions_taken",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.target_user.username} - {self.action}"
            f" ({self.created_at.isoformat()})"
        )
