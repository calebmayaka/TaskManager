from django.db import transaction

from main.models import UserProfile


@transaction.atomic
def update_account_profile(
    *,
    user,
    first_name,
    last_name,
    country_prefix="+1",
    phone_number="",
    secondary_email="",
    profile_picture=None,
    remove_profile_picture=False,
):
    profile, _ = UserProfile.objects.select_for_update().get_or_create(user=user)

    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=["first_name", "last_name"])

    profile.country_prefix = country_prefix or "+1"
    profile.phone_number = phone_number
    profile.secondary_email = secondary_email

    if remove_profile_picture and profile.profile_picture:
        profile.profile_picture.delete(save=False)
        profile.profile_picture = None
    elif profile_picture is not None:
        profile.profile_picture = profile_picture

    profile.save()
    return profile
