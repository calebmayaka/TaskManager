import re

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from main.models import UserApproval, UserApprovalAuditLog


User = get_user_model()


def _split_full_name(full_name):
    normalized = " ".join((full_name or "").split())
    if not normalized:
        return "", ""
    first_name, _, last_name = normalized.partition(" ")
    return first_name, last_name


def _normalize_username_base(email):
    local_part = (email.split("@", 1)[0] if email else "").strip().lower()
    cleaned = re.sub(r"[^\w.@+-]", "", local_part)
    return cleaned[:150] or "user"


def _generate_unique_username(email):
    base = _normalize_username_base(email)
    candidate = base
    suffix = 1

    while User.objects.filter(username__iexact=candidate).exists():
        suffix_text = f"-{suffix}"
        candidate = f"{base[: 150 - len(suffix_text)]}{suffix_text}"
        suffix += 1

    return candidate


@transaction.atomic
def register_user(*, email, password, full_name, username=None):
    first_name, last_name = _split_full_name(full_name)
    resolved_username = username or _generate_unique_username(email)
    user = User.objects.create_user(
        username=resolved_username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_active=False,
    )
    UserApproval.objects.create(user=user, status=UserApproval.Status.PENDING)
    UserApprovalAuditLog.objects.create(
        target_user=user,
        actor=None,
        action=UserApprovalAuditLog.Action.REGISTERED,
    )
    return user


@transaction.atomic
def approve_user(*, target_user, reviewer, notes=""):
    approval, _ = UserApproval.objects.select_for_update().get_or_create(
        user=target_user,
        defaults={"status": UserApproval.Status.PENDING},
    )
    is_noop = (
        approval.status == UserApproval.Status.APPROVED
        and target_user.is_active
        and approval.review_notes == (notes or "")
    )
    if is_noop:
        return approval

    now = timezone.now()
    approval.status = UserApproval.Status.APPROVED
    approval.reviewed_by = reviewer
    approval.reviewed_at = now
    approval.review_notes = notes or ""
    approval.rejection_reason = ""
    approval.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "rejection_reason",
            "updated_at",
        ]
    )

    if not target_user.is_active:
        target_user.is_active = True
        target_user.save(update_fields=["is_active"])

    UserApprovalAuditLog.objects.create(
        target_user=target_user,
        actor=reviewer,
        action=UserApprovalAuditLog.Action.APPROVED,
        notes=notes or "",
    )
    return approval


@transaction.atomic
def reject_user(*, target_user, reviewer, reason="", notes=""):
    approval, _ = UserApproval.objects.select_for_update().get_or_create(
        user=target_user,
        defaults={"status": UserApproval.Status.PENDING},
    )
    normalized_reason = reason or ""
    normalized_notes = notes or ""
    is_noop = (
        approval.status == UserApproval.Status.REJECTED
        and not target_user.is_active
        and approval.rejection_reason == normalized_reason
        and approval.review_notes == normalized_notes
    )
    if is_noop:
        return approval

    now = timezone.now()
    approval.status = UserApproval.Status.REJECTED
    approval.reviewed_by = reviewer
    approval.reviewed_at = now
    approval.review_notes = normalized_notes
    approval.rejection_reason = normalized_reason
    approval.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "rejection_reason",
            "updated_at",
        ]
    )

    if target_user.is_active:
        target_user.is_active = False
        target_user.save(update_fields=["is_active"])

    audit_notes = normalized_notes
    if normalized_reason:
        audit_notes = f"{normalized_notes}\nReason: {normalized_reason}".strip()
    UserApprovalAuditLog.objects.create(
        target_user=target_user,
        actor=reviewer,
        action=UserApprovalAuditLog.Action.REJECTED,
        notes=audit_notes,
    )
    return approval
