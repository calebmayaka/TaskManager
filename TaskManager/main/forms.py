import re

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from main.models import UserApproval, UserProfile


User = get_user_model()

PENDING_APPROVAL_MESSAGE = _(
    "Your account is pending approval. Please wait for admin approval."
)


class RegistrationForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "class": "auth-input",
            }
        ),
    )
    full_name = forms.CharField(
        label=_("Full Name"),
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "name",
                "class": "auth-input",
            }
        ),
    )
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "auth-input",
            }
        ),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "auth-input",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("A user with this email already exists."))
        return email

    def clean_full_name(self):
        full_name = " ".join(self.cleaned_data["full_name"].split())
        if not full_name:
            raise ValidationError(_("Full name is required."))
        return full_name

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", _("The two password fields didn't match."))
            return cleaned_data

        if password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error("password2", exc)
        return cleaned_data


class AccountProfileForm(forms.Form):
    COUNTRY_PREFIX_CHOICES = [
        ("+1", "+1 (US/CA)"),
        ("+7", "+7 (RU/KZ)"),
        ("+20", "+20 (EG)"),
        ("+27", "+27 (ZA)"),
        ("+30", "+30 (GR)"),
        ("+31", "+31 (NL)"),
        ("+32", "+32 (BE)"),
        ("+33", "+33 (FR)"),
        ("+34", "+34 (ES)"),
        ("+36", "+36 (HU)"),
        ("+39", "+39 (IT)"),
        ("+40", "+40 (RO)"),
        ("+41", "+41 (CH)"),
        ("+43", "+43 (AT)"),
        ("+44", "+44 (UK)"),
        ("+45", "+45 (DK)"),
        ("+46", "+46 (SE)"),
        ("+47", "+47 (NO)"),
        ("+48", "+48 (PL)"),
        ("+49", "+49 (DE)"),
        ("+51", "+51 (PE)"),
        ("+52", "+52 (MX)"),
        ("+54", "+54 (AR)"),
        ("+55", "+55 (BR)"),
        ("+56", "+56 (CL)"),
        ("+57", "+57 (CO)"),
        ("+58", "+58 (VE)"),
        ("+60", "+60 (MY)"),
        ("+61", "+61 (AU)"),
        ("+62", "+62 (ID)"),
        ("+63", "+63 (PH)"),
        ("+64", "+64 (NZ)"),
        ("+65", "+65 (SG)"),
        ("+66", "+66 (TH)"),
        ("+81", "+81 (JP)"),
        ("+82", "+82 (KR)"),
        ("+84", "+84 (VN)"),
        ("+86", "+86 (CN)"),
        ("+90", "+90 (TR)"),
        ("+91", "+91 (IN)"),
        ("+92", "+92 (PK)"),
        ("+93", "+93 (AF)"),
        ("+94", "+94 (LK)"),
        ("+95", "+95 (MM)"),
        ("+98", "+98 (IR)"),
        ("+211", "+211 (SS)"),
        ("+212", "+212 (MA)"),
        ("+213", "+213 (DZ)"),
        ("+216", "+216 (TN)"),
        ("+218", "+218 (LY)"),
        ("+220", "+220 (GM)"),
        ("+221", "+221 (SN)"),
        ("+223", "+223 (ML)"),
        ("+225", "+225 (CI)"),
        ("+230", "+230 (MU)"),
        ("+233", "+233 (GH)"),
        ("+234", "+234 (NG)"),
        ("+250", "+250 (RW)"),
        ("+251", "+251 (ET)"),
        ("+254", "+254 (KE)"),
        ("+255", "+255 (TZ)"),
        ("+256", "+256 (UG)"),
        ("+260", "+260 (ZM)"),
        ("+263", "+263 (ZW)"),
        ("+264", "+264 (NA)"),
        ("+267", "+267 (BW)"),
        ("+298", "+298 (FO)"),
        ("+351", "+351 (PT)"),
        ("+352", "+352 (LU)"),
        ("+353", "+353 (IE)"),
        ("+354", "+354 (IS)"),
        ("+355", "+355 (AL)"),
        ("+356", "+356 (MT)"),
        ("+357", "+357 (CY)"),
        ("+358", "+358 (FI)"),
        ("+359", "+359 (BG)"),
        ("+370", "+370 (LT)"),
        ("+371", "+371 (LV)"),
        ("+372", "+372 (EE)"),
        ("+373", "+373 (MD)"),
        ("+374", "+374 (AM)"),
        ("+375", "+375 (BY)"),
        ("+380", "+380 (UA)"),
        ("+381", "+381 (RS)"),
        ("+385", "+385 (HR)"),
        ("+386", "+386 (SI)"),
        ("+387", "+387 (BA)"),
        ("+420", "+420 (CZ)"),
        ("+421", "+421 (SK)"),
        ("+500", "+500 (FK)"),
        ("+501", "+501 (BZ)"),
        ("+502", "+502 (GT)"),
        ("+503", "+503 (SV)"),
        ("+504", "+504 (HN)"),
        ("+505", "+505 (NI)"),
        ("+506", "+506 (CR)"),
        ("+507", "+507 (PA)"),
        ("+590", "+590 (GP/BL/MF)"),
        ("+591", "+591 (BO)"),
        ("+592", "+592 (GY)"),
        ("+593", "+593 (EC)"),
        ("+595", "+595 (PY)"),
        ("+597", "+597 (SR)"),
        ("+598", "+598 (UY)"),
        ("+852", "+852 (HK)"),
        ("+853", "+853 (MO)"),
        ("+855", "+855 (KH)"),
        ("+856", "+856 (LA)"),
        ("+880", "+880 (BD)"),
        ("+886", "+886 (TW)"),
        ("+960", "+960 (MV)"),
        ("+961", "+961 (LB)"),
        ("+962", "+962 (JO)"),
        ("+963", "+963 (SY)"),
        ("+964", "+964 (IQ)"),
        ("+965", "+965 (KW)"),
        ("+966", "+966 (SA)"),
        ("+967", "+967 (YE)"),
        ("+968", "+968 (OM)"),
        ("+970", "+970 (PS)"),
        ("+971", "+971 (UAE)"),
        ("+972", "+972 (IL)"),
        ("+973", "+973 (BH)"),
        ("+974", "+974 (QA)"),
        ("+975", "+975 (BT)"),
        ("+976", "+976 (MN)"),
        ("+977", "+977 (NP)"),
        ("+992", "+992 (TJ)"),
        ("+993", "+993 (TM)"),
        ("+994", "+994 (AZ)"),
        ("+995", "+995 (GE)"),
        ("+996", "+996 (KG)"),
        ("+998", "+998 (UZ)"),
    ]

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    email = forms.EmailField(
        required=True,
        disabled=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone_number = forms.CharField(
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "tel"}),
    )
    country_prefix = forms.CharField(
        max_length=8,
        required=False,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "maxlength": "8",
                "aria-label": "Country prefix",
            }
        ),
    )
    secondary_email = forms.EmailField(required=False)
    profile_picture = forms.FileField(required=False)
    remove_profile_picture = forms.BooleanField(required=False)

    def __init__(self, *args, user, profile, **kwargs):
        self.user = user
        self.profile = profile
        super().__init__(*args, **kwargs)

        self.country_prefix_suggestions = [
            code for code, _label in self.COUNTRY_PREFIX_CHOICES[:24]
        ]
        self.fields["country_prefix"].widget.attrs["list"] = "country-prefix-options"
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email
        self.fields["country_prefix"].initial = profile.country_prefix or "+1"
        self.fields["phone_number"].initial = profile.phone_number
        self.fields["secondary_email"].initial = profile.secondary_email
        self.fields["profile_picture"].widget.attrs["accept"] = "image/*"

    def clean_first_name(self):
        first_name = " ".join(self.cleaned_data["first_name"].split())
        if not first_name:
            raise ValidationError(_("First name is required."))
        return first_name

    def clean_last_name(self):
        last_name = " ".join(self.cleaned_data["last_name"].split())
        if not last_name:
            raise ValidationError(_("Last name is required."))
        return last_name

    def clean_email(self):
        return self.user.email

    def clean_country_prefix(self):
        country_prefix = self.cleaned_data.get("country_prefix", "").strip()
        if not country_prefix:
            return "+1"
        if not re.fullmatch(r"\+[0-9]{1,4}", country_prefix):
            raise ValidationError(_("Select a valid country prefix."))
        return country_prefix

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number", "").strip()
        if not phone_number:
            return ""
        if not re.fullmatch(r"[0-9\-() ]{7,32}", phone_number):
            raise ValidationError(_("Enter a valid phone number."))
        return phone_number

    def clean_secondary_email(self):
        secondary_email = self.cleaned_data.get("secondary_email", "").strip()
        if not secondary_email:
            return ""
        if User.objects.filter(email__iexact=secondary_email).exclude(
            pk=self.user.pk
        ).exists():
            raise ValidationError(_("This email is already used as a primary email."))
        if UserProfile.objects.filter(secondary_email__iexact=secondary_email).exclude(
            user=self.user
        ).exists():
            raise ValidationError(_("This secondary email is already in use."))
        return secondary_email

    def clean_profile_picture(self):
        profile_picture = self.cleaned_data.get("profile_picture")
        if not profile_picture:
            return None
        content_type = getattr(profile_picture, "content_type", "")
        if not content_type.startswith("image/"):
            raise ValidationError(_("Upload a valid image file."))
        max_size = 5 * 1024 * 1024
        if profile_picture.size > max_size:
            raise ValidationError(_("Image must be 5 MB or smaller."))
        return profile_picture

    def clean(self):
        cleaned_data = super().clean()
        primary = cleaned_data.get("email", "").strip().lower()
        secondary = cleaned_data.get("secondary_email", "").strip().lower()
        if primary and secondary and primary == secondary:
            self.add_error(
                "secondary_email",
                _("Secondary email must be different from primary email."),
            )
        return cleaned_data


class PendingAwareAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
                "class": "auth-input",
            },
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "auth-input",
            }
        ),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive_pending": PENDING_APPROVAL_MESSAGE,
    }

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email is None or password is None:
            return self.cleaned_data

        candidate_users = User._default_manager.filter(email__iexact=email.strip())
        user_count = candidate_users.count()
        if user_count != 1:
            raise self.get_invalid_login_error()

        user = candidate_users.select_related("approval").first()
        self.user_cache = authenticate(
            self.request,
            username=getattr(user, User.USERNAME_FIELD),
            password=password,
        )
        if self.user_cache is None:
            self._validate_pending_user(user=user, password=password)
            raise self.get_invalid_login_error()

        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def _validate_pending_user(self, *, user, password):
        if user and not user.is_active and user.check_password(password):
            approval = getattr(user, "approval", None)
            if approval and approval.status == UserApproval.Status.PENDING:
                raise ValidationError(
                    self.error_messages["inactive_pending"],
                    code="inactive_pending",
                )
