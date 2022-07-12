from typing import Any, Dict

from django import forms
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from virtual_library_card.logging import LoggingMixin
from virtual_library_card.sender import Sender
from virtual_library_card.tokens import (
    TokenDecodeError,
    TokenExpiredError,
    Tokens,
    TokenTypes,
)
from VirtualLibraryCard.models import CustomUser


class EmailVerificationTokenView(LoggingMixin, TemplateView):

    template_name: str = "verification/email_success.html"

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.user:
            context["user"] = self.user
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
                Sender.send_email_verification(user.library, user)
                request.session.pop("verification_email_address")
            else:
                success = False

        self.success_url = f"{self.success_url}?success={'t' if success else 'f'}"
        return super().post(request, *args, **kwargs)


class EmailVerificationErrorView(TemplateView):
    template_name: str = "verification/email_error.html"
