from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.views.generic import DeleteView, TemplateView, UpdateView

from virtual_library_card.user_session import UserSessionManager
from VirtualLibraryCard.forms.forms_profile import ProfileEditForm
from VirtualLibraryCard.models import CustomUser, LibraryCard


class CustomLoginView(LoginView):
    form_class = AuthenticationForm

    def get_form_kwargs(self):
        kwargs = super(CustomLoginView, self).get_form_kwargs()
        url_parts = self.request.path.split("/")[:-1]
        identifier = str(url_parts.pop())
        UserSessionManager.set_session_identifier_info(self, identifier)
        return kwargs


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def render_to_response(self, context, **response_kwargs):
        UserSessionManager.set_context_library_cards(context, self.request.user)
        return super().render_to_response(context, **response_kwargs)


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileEditForm
    template_name = "accounts/edit_profile.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse("profile")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ProfileDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomUser
    success_url = "delete_profile_success"
    template_name = "accounts/customer_confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        custom_user = self.get_object()
        # I SET SESSION FOR DISPLAYING LIBRARY LOGO BEFORE DELETING USER
        UserSessionManager.set_request_session_library(request, custom_user.library)
        library_cards = LibraryCard.objects.filter(user=custom_user)
        if library_cards:
            for card in library_cards:
                card.delete()
        return super().delete(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def render_to_response(self, context, **response_kwargs):
        UserSessionManager.set_context_library_cards(context, self.request.user)
        return super().render_to_response(context, **response_kwargs)
