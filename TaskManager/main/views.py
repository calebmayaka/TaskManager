from django.contrib import messages
from django.contrib.auth import get_user_model, views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, RedirectView, TemplateView

from main.forms import AccountProfileForm, PendingAwareAuthenticationForm, RegistrationForm
from main.models import UserApproval, UserApprovalAuditLog, UserProfile
from main.rate_limit import RateLimitMixin
from main.services import (
    approve_user,
    register_user,
    reject_user,
    update_account_profile,
)


User = get_user_model()


def user_can_access_admin_dashboard(user):
    return user.is_staff and user.has_perm("main.can_review_user_approvals")


class StaffPermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "main.can_review_user_approvals"

    def has_permission(self):
        return user_can_access_admin_dashboard(self.request.user) and super().has_permission()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class RegisterView(RateLimitMixin, FormView):
    template_name = "registration/register.html"
    form_class = RegistrationForm
    rate_limit_count = 10
    rate_limit_window = 3600  # 1 hour

    def form_valid(self, form):
        register_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password1"],
            full_name=form.cleaned_data["full_name"],
        )
        return super().form_valid(form)

    def get_success_url(self):
        return f"{reverse('main:register')}?pending=1"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_approval"] = self.request.GET.get("pending") == "1"
        return context


class LoginView(RateLimitMixin, auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = PendingAwareAuthenticationForm
    rate_limit_count = 5
    rate_limit_window = 900  # 15 minutes


class DashboardEntryView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if user_can_access_admin_dashboard(request.user):
            return redirect("main:admin-dashboard")
        return redirect("main:user-dashboard")


class PendingApprovalInfoView(TemplateView):
    template_name = "registration/pending_approval.html"


class AdminDashboardEntryView(StaffPermissionRequiredMixin, RedirectView):
    pattern_name = "main:admin-dashboard-tasks"
    permanent = False


class AdminTasksLandingView(StaffPermissionRequiredMixin, TemplateView):
    template_name = "dashboard/admin_tasks_landing.html"


class AdminUsersDashboardView(StaffPermissionRequiredMixin, TemplateView):
    template_name = "dashboard/admin_users_dashboard.html"
    recent_events_limit = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_approvals = UserApproval.objects.all()
        pending_approvals = all_approvals.filter(
            status=UserApproval.Status.PENDING
        ).select_related("user").order_by("created_at")
        status_totals = dict(
            all_approvals.values_list("status").annotate(total=Count("id"))
        )
        recent_events = UserApprovalAuditLog.objects.select_related(
            "actor",
            "target_user",
        ).order_by("-created_at")[: self.recent_events_limit]

        context["pending_approvals"] = pending_approvals
        context["pending_count"] = status_totals.get(UserApproval.Status.PENDING, 0)
        context["approved_count"] = status_totals.get(UserApproval.Status.APPROVED, 0)
        context["rejected_count"] = status_totals.get(UserApproval.Status.REJECTED, 0)
        context["recent_events"] = recent_events
        return context


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/user_dashboard.html"


class AccountProfileView(LoginRequiredMixin, FormView):
    template_name = "dashboard/account_profile.html"
    form_class = AccountProfileForm

    def get_profile(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["profile"] = self.get_profile()
        return kwargs

    def form_valid(self, form):
        update_account_profile(
            user=self.request.user,
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            country_prefix=form.cleaned_data["country_prefix"],
            phone_number=form.cleaned_data["phone_number"],
            secondary_email=form.cleaned_data["secondary_email"],
            profile_picture=form.cleaned_data["profile_picture"],
            remove_profile_picture=form.cleaned_data["remove_profile_picture"],
        )
        messages.success(self.request, "Account profile updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("main:account-profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = self.get_profile()
        context["is_admin_dashboard_user"] = user_can_access_admin_dashboard(
            self.request.user
        )
        return context


class PendingUsersListView(RedirectView):
    pattern_name = "main:admin-dashboard-users"
    permanent = False


class ReviewUserApprovalView(StaffPermissionRequiredMixin, View):
    def post(self, request, user_id, action):
        target_user = get_object_or_404(User, pk=user_id)
        notes = request.POST.get("notes", "").strip()

        if action == "approve":
            approve_user(target_user=target_user, reviewer=request.user, notes=notes)
            messages.success(request, f"{target_user.username} was approved.")
        elif action == "reject":
            reason = request.POST.get("reason", "").strip()
            reject_user(
                target_user=target_user,
                reviewer=request.user,
                reason=reason,
                notes=notes,
            )
            messages.success(request, f"{target_user.username} was rejected.")
        else:
            raise Http404("Invalid action")

        return redirect("main:admin-dashboard-users")
