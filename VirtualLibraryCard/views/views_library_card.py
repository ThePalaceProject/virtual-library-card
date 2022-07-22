from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from virtual_library_card.geoloc import Geolocalize
from virtual_library_card.logging import LoggingMixin
from virtual_library_card.user_session import UserSessionManager
from VirtualLibraryCard.forms.forms_library_card import (
    LibraryCardDeleteForm,
    RequestLibraryCardForm,
    SignupCardForm,
)
from VirtualLibraryCard.models import CustomUser, Library, LibraryCard


class LibraryCardsView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def render_to_response(self, context, **response_kwargs):
        context["delete_cards"] = True
        UserSessionManager.set_context_library_cards(context, self.request.user)
        return super().render_to_response(context, **response_kwargs)


class LibraryCardDeleteView(LoginRequiredMixin, UpdateView):
    model = LibraryCard
    template_name = "accounts/customer_confirm_delete.html"
    form_class = LibraryCardDeleteForm

    def get_success_url(self):
        return reverse(
            "card_deleted_success", kwargs={"delete_cards": True, "success": True}
        )

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def render_to_response(self, context, **response_kwargs):
        UserSessionManager.set_request_session_library(
            self.request, self.request.user.library
        )
        UserSessionManager.set_context_library_cards(context, self.request.user)
        return super().render_to_response(context, **response_kwargs)


class LibraryCardRequestSuccessView(LoggingMixin, TemplateView):
    template_name = "library_card/library_card_request_success.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        email = kwargs["email"]
        try:
            user = CustomUser.objects.filter(email=email).first()
            UserSessionManager.set_context_library_cards(context, user)
            context["user"] = user

        except Exception as e:
            self.log.error(f"Exception getting context data {e}")

        return context


class LibraryCardRequestView(LoggingMixin, CreateView):
    model = CustomUser
    form_class = RequestLibraryCardForm
    template_name = "library_card/library_card_request.html"

    def render_to_response(self, context, **response_kwargs):
        if "identifier" not in self.request.session:
            raise Http404(_("You are not allowed to access this page"))

        identifier = self.request.session["identifier"]
        if not identifier:
            raise Http404(_("You are not allowed to access this page"))

        identifier_from_url_param = self.request.GET.get("identifier", None)
        self.log.debug(f"================== identifier_from_session: {identifier}")
        self.log.debug(
            f"================== identifier_from_url_param: {identifier_from_url_param}"
        )

        if identifier != identifier_from_url_param:
            self.request.session.flush()
            self.request.session.modified = True
            raise Http404(_("You are not allowed to access this page"))

        library = Library.objects.filter(identifier=identifier).first()
        if not library:
            raise Http404(_("Library does not exist"))
        else:
            UserSessionManager.set_session_library(self, library)
            context.update(
                {
                    "library": library,
                }
            )
        return super().render_to_response(context, **response_kwargs)

    def get_form_kwargs(self):
        kwargs = super(LibraryCardRequestView, self).get_form_kwargs()
        if "identifier" not in self.request.session:
            raise Http404(_("You are not allowed to access this page"))

        identifier = self.request.session["identifier"]
        if identifier:
            identifier = self.request.session["identifier"]
            state = self.request.session["state"]
            city = self.request.session["city"]
            zipcode = self.request.session["zipcode"]
            #  Not Working (Err 500):
            #            del self.request.session['identifier']
            #            del self.request.session['state']
            #            del self.request.session['city']
            #            del self.request.session['zipcode']
            self.request.session.modified = True

            try:
                self.model = CustomUser()
                library = Library.objects.filter(identifier=identifier).first()
                self.model.library = library
                self.model.us_state = state
                self.model.city = city
                self.model.zip = zipcode
                self.model.username = ""
                self.model.first_name = ""
                self.model.last_name = ""
                self.model.email = ""
                self.model.street_address_line1 = ""
                self.model.street_address_line2 = ""
                self.model.existing_library_card = ""
                self.model.is_superuser = False
                self.model.is_staff = False
                self.model.is_active = True

                # Default for age verification should be false
                if library.age_verification_mandatory is False:
                    self.model.over13 = False

                kwargs["instance"] = self.model
                # kwargs['prefix'] = 'FR'

            except Exception as e:
                self.log.error(e)

        return kwargs

    def get_context(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self):
        return reverse(
            "library_card_request_success", kwargs={"email": self.model.email}
        )


class CardSignupView(FormView):
    template_name = "library_card/library_card_signup.html"
    form_class = SignupCardForm
    success_url = "/account/library_card_request/"

    def dispatch(self, request, *args, **kwargs):
        UserSessionManager.clean_session_data(request)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        context = self.get_context_data()
        identifier = form.cleaned_data.get("identifier")
        if not identifier:
            raise Http404(_("Identifier parameter is mandatory"))
        library = Library.objects.filter(identifier=identifier).first()
        if not library:
            raise Http404(_("Library does not exist"))
        lat = form.cleaned_data.get("lat")
        long = form.cleaned_data.get("long")

        # FOR TESTING FROM FRANCE
        # lat = "40.7539033"
        # long = "-73.9757635"

        result = Geolocalize.get_user_location(lat, long)

        if result:
            first_result = result["results"]
            location = first_result[0]["locations"][0]
            state = location["adminArea3"]
            country = location["adminArea1"]
            city = location["adminArea5"]
            zipcode = location["postalCode"]

            context.update(
                {
                    "identifier": library.identifier,
                    "library": library,
                    "state_names": ", ".join(library.get_us_states()),
                }
            )

            if country != "US":
                return render(
                    self.request,
                    "library_card/library_card_request_denied_country.html",
                    context,
                )

            if state not in library.get_us_states():
                return render(
                    self.request,
                    "library_card/library_card_request_denied.html",
                    context,
                )

            # We put the informations into the session only after checking the access is allowed
            UserSessionManager.set_session_library(self, library)
            UserSessionManager.set_session_user_location(
                self.request, state, city, zipcode
            )

            # We add the library identifier to the URL in order to allow comapring it with the one which can
            # be present in the session. This allows preventing circumventing the geolocation barrier by
            # first logging into a local library
            self.success_url += "?identifier=" + identifier

        return super().form_valid(form)
