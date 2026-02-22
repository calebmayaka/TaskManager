from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from main.views import (
    AccountProfileView,
    AdminDashboardEntryView,
    AdminTasksLandingView,
    AdminUsersDashboardView,
    DashboardEntryView,
    LoginView,
    PendingApprovalInfoView,
    PendingUsersListView,
    RegisterView,
    ReviewUserApprovalView,
    UserDashboardView,
)

app_name = "main"

urlpatterns = [
    path(
        "",
        RedirectView.as_view(pattern_name="main:login", permanent=False),
        name="root",
    ),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(next_page="main:login"), name="logout"),
    path("account/profile/", AccountProfileView.as_view(), name="account-profile"),
    path("dashboard/", DashboardEntryView.as_view(), name="dashboard-entry"),
    path("dashboard/admin/", AdminDashboardEntryView.as_view(), name="admin-dashboard"),
    path(
        "dashboard/admin/tasks/",
        AdminTasksLandingView.as_view(),
        name="admin-dashboard-tasks",
    ),
    path(
        "dashboard/admin/users/",
        AdminUsersDashboardView.as_view(),
        name="admin-dashboard-users",
    ),
    path("dashboard/my/", UserDashboardView.as_view(), name="user-dashboard"),
    path(
        "auth/pending-approval/",
        PendingApprovalInfoView.as_view(),
        name="pending-approval",
    ),
    path(
        "approvals/users/pending/",
        PendingUsersListView.as_view(),
        name="pending-users",
    ),
    path(
        "approvals/users/<int:user_id>/<str:action>/",
        ReviewUserApprovalView.as_view(),
        name="review-user-approval",
    ),
]
