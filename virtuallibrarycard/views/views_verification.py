from typing import Any, Dict
from urllib.request import Request

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from virtual_library_card.api.dynamic_links import (
    DynamicLinksSetting,
    FirebaseDynamicLinksAPI,
)
from virtual_library_card.logging import LoggingMixin
from virtual_library_card.sender import Sender
from virtual_library_card.tokens import (
    TokenDecodeError,
    TokenExpiredError,
    Tokens,
    TokenTypes,
)
from virtuallibrarycard.models import CustomUser, LibraryCard


class EmailVerificationTokenView(LoggingMixin, TemplateView):
    template_name: str = "verification/email_success.html"

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.user:
            context["user"] = self.user

            # Should the user set their password?
            if not self.user.password:
                context["form"] = self._password_form(self.user)
            else:
                # If the user has been setup completely, redirect to the App link
                # Fetch the library card for this user
                card = LibraryCard.objects.filter(
                    user=self.user, library=self.user.library
                ).first()

                if (
                    card
                    and (dl_settings := getattr(settings, "DYNAMIC_LINKS", None))
                    and (
                        signup_url := getattr(
                            settings, "DYNAMIC_LINKS_SIGNUP_URL", None
                        )
                    )
                ):
                    api = FirebaseDynamicLinksAPI(DynamicLinksSetting(**dl_settings))
                    link = api.create_signup_short_link(
                        signup_url,
                        card.number,
                        self.user.library.identifier,
                    )
                    context["redirect_link"] = link
        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        token = self.request.GET.get("token")
        redirect = None
        try:
            decoded = Tokens.verify(token)
            if (
                decoded["type"] != TokenTypes.EMAIL_VERIFICATION
                or "email" not in decoded
            ):
                raise Exception("Token format is incorrect")
            user: CustomUser = CustomUser.objects.get(email=decoded["email"])
            if not user:
                raise Exception("Email does not exist")

            self.user = user
            user.email_verified = True
            user.save()

        except TokenExpiredError as e:
            email = e.data.get("email")
            if not email:
                redirect = reverse("email_token_error")
            else:
                user: CustomUser = CustomUser.objects.filter(email=email).first()
                if not user:
                    redirect = reverse("email_token_error")
                elif user.email_verified:  # We are already verified
                    redirect = None
                    self.user = user
                else:
                    self.request.session["verification_email_address"] = email
                    redirect = reverse("email_token_resend")
        except TokenDecodeError as e:
            self.log.error(f"Email verification: Exception decoding token: {e}")
            redirect = reverse("email_token_error")
        except Exception as e:
            self.log.error(f"Email verification: Exception decoding token: {e}")
            redirect = reverse("email_token_error")

        if redirect:
            return HttpResponseRedirect(redirect)

        return super().get(request, *args, **kwargs)

    def post(self, request: Request) -> HttpResponse:
        token = self.request.GET.get("token")
        # A POST form submit is only going to come through a
        # successful page load above, we don't need to do more error
        # handling for the token here
        decoded = Tokens.verify(token)
        email = decoded.get("email")
        user: CustomUser = CustomUser.objects.get(email=email)
        form = self._password_form(user, data=request.POST)
        if form.is_valid():
            user.set_password(request.POST["new_password1"])
            user.save()
            return self.render_to_response(
                {"user": user, "form": None, "did_set_password": True}
            )
        else:
            return self.render_to_response({"form": form, "user": user})

    def _password_form(self, user, data=None):
        form = SetPasswordForm(user, data=data)
        form.helper = FormHelper()
        form.helper.add_input(Submit("submit", "save"))
        return form


class EmailVerificationResendToken(FormView):
    template_name: str = "verification/email_resend.html"
    form_class = forms.Form
    success_url = None

    def __init__(self, **kwargs: Any) -> None:
        self.email_missing = False
        super().__init__(**kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        success = self.request.GET.get("success", None)

        if success is not None:
            context["email_missing"] = success == "f"
            context["send_success"] = success == "t"

        return context

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.success_url = request.get_full_path()  # Redirect to self
        email = request.session.get("verification_email_address")
        success = True

        if not email:
            success = False
        else:
            user: CustomUser = CustomUser.objects.filter(
                email__iexact=email.lower()
            ).first()
            if user:
                # Only send the verification part of the email
                Sender.send_user_welcome(user.library, user)
                request.session.pop("verification_email_address")
            else:
                success = False

        self.success_url = f"{self.success_url}?success={'t' if success else 'f'}"
        return super().post(request, *args, **kwargs)


class EmailVerificationErrorView(TemplateView):
    template_name: str = "verification/email_error.html"
