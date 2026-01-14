from datetime import UTC, datetime

from django.core import mail
from pytest_django.asserts import assertFormError

from tests.base import BaseUnitTest
from virtuallibrarycard.models import LibraryCard


class TestPasswordResetView(BaseUnitTest):
    def test_reset_post(self):
        response = self.client.post(
            "/account/reset-password/", {"email": self._default_user.email}
        )

        assert response.context.get("token") is not None
        assert len(mail.outbox) == 1

        reset_mail = mail.outbox[0]
        assert reset_mail.to == [self._default_user.email]
        assert reset_mail.subject == "Virtual Library Card | Password Reset"

    def test_bad_email(self):
        response = self.client.post(
            "/account/reset-password/", {"email": "nosuchemail@email.com"}
        )
        assertFormError(
            response.context["form"],
            "email",
            [
                "There is no user registered with the specified email address nosuchemail@email.com"
            ],
        )

        response = self.client.post("/account/reset-password/")
        assertFormError(
            response.context["form"],
            "email",
            ["This field is required."],
        )

    def test_reset_email_with_no_cards(self):
        """Test password reset email when user has no library cards"""
        # Create a user without any cards
        user = self.create_user(self._default_library, email="nocards@example.com")
        
        # Delete the default card if it exists
        LibraryCard.objects.filter(user=user).delete()
        
        response = self.client.post(
            "/account/reset-password/", {"email": user.email}
        )
        
        assert response.status_code == 302
        assert len(mail.outbox) == 1
        
        reset_mail = mail.outbox[0]
        assert reset_mail.to == [user.email]
        assert reset_mail.subject == "Virtual Library Card | Password Reset"
        
        # Check that barcode section is not in the email
        assert "library card barcodes" not in reset_mail.body.lower()
        
        # Check HTML content if available
        if hasattr(reset_mail, 'alternatives') and reset_mail.alternatives:
            html_content = reset_mail.alternatives[0][0]
            assert "library card barcodes" not in html_content.lower()

    def test_reset_email_with_one_card(self):
        """Test password reset email when user has one library card"""
        user = self.create_user(self._default_library, email="onecard@example.com")
        
        # Delete any existing cards and create one new card
        LibraryCard.objects.filter(user=user).delete()
        card = self.create_library_card(user, self._default_library, number="123456789")
        self._default_library.barcode_text = "Barcode"
        self._default_library.save()
        
        response = self.client.post(
            "/account/reset-password/", {"email": user.email}
        )
        
        assert response.status_code == 302
        assert len(mail.outbox) == 1
        
        reset_mail = mail.outbox[0]
        assert reset_mail.to == [user.email]
        
        # Check plain text content
        body = reset_mail.body
        assert "library card barcodes" in body.lower()
        assert card.number in body
        assert self._default_library.barcode_text in body
        assert self._default_library.name in body
        
        # Check HTML content if available
        if hasattr(reset_mail, 'alternatives') and reset_mail.alternatives:
            html_content = reset_mail.alternatives[0][0]
            assert "library card barcodes" in html_content.lower()
            assert card.number in html_content
            assert self._default_library.barcode_text in html_content
            assert self._default_library.name in html_content

    def test_reset_email_with_two_cards(self):
        """Test password reset email when user has two library cards"""
        user = self.create_user(self._default_library, email="twocards@example.com")
        
        # Create a second library
        library2 = self.create_library(
            name="Second Library",
            identifier="second",
            prefix="02",
            barcode_text="Card Number"
        )
        
        # Delete any existing cards and create two new cards
        LibraryCard.objects.filter(user=user).delete()
        card1 = self.create_library_card(user, self._default_library, number="111111111")
        card2 = self.create_library_card(user, library2, number="222222222")
        
        self._default_library.barcode_text = "Barcode"
        self._default_library.save()
        
        response = self.client.post(
            "/account/reset-password/", {"email": user.email}
        )
        
        assert response.status_code == 302
        assert len(mail.outbox) == 1
        
        reset_mail = mail.outbox[0]
        assert reset_mail.to == [user.email]
        
        # Check plain text content
        body = reset_mail.body
        assert "library card barcodes" in body.lower()
        assert card1.number in body
        assert card2.number in body
        assert self._default_library.barcode_text in body
        assert library2.barcode_text in body
        assert self._default_library.name in body
        assert library2.name in body
        
        # Check HTML content if available
        if hasattr(reset_mail, 'alternatives') and reset_mail.alternatives:
            html_content = reset_mail.alternatives[0][0]
            assert "library card barcodes" in html_content.lower()
            assert card1.number in html_content
            assert card2.number in html_content
            assert self._default_library.barcode_text in html_content
            assert library2.barcode_text in html_content
            assert self._default_library.name in html_content
            assert library2.name in html_content

    def test_reset_email_excludes_canceled_cards(self):
        """Test that canceled library cards are not included in the email"""
        user = self.create_user(self._default_library, email="canceled@example.com")
        
        # Delete any existing cards
        LibraryCard.objects.filter(user=user).delete()
        
        # Create one active card and one canceled card
        active_card = self.create_library_card(user, self._default_library, number="ACTIVE123")
        canceled_card = self.create_library_card(user, self._default_library, number="CANCELED456")
        canceled_card.canceled_date = datetime.now(UTC)
        canceled_card.save()
        
        response = self.client.post(
            "/account/reset-password/", {"email": user.email}
        )
        
        assert response.status_code == 302
        assert len(mail.outbox) == 1
        
        reset_mail = mail.outbox[0]
        body = reset_mail.body
        
        # Active card should be in email
        assert active_card.number in body
        
        # Canceled card should NOT be in email
        assert canceled_card.number not in body
        
        # Check HTML content if available
        if hasattr(reset_mail, 'alternatives') and reset_mail.alternatives:
            html_content = reset_mail.alternatives[0][0]
            assert active_card.number in html_content
            assert canceled_card.number not in html_content


class TestPasswordChangeView(BaseUnitTest):
    def test_password_change_form(self):
        old_password = "apassword"
        new_password = "jalasd8838383"

        user = self._default_user
        user.set_password(old_password)
        user.save()
        self.client.force_login(user)

        response = self.client.post(
            f"/account/change-password/{self._default_user.first_name}/",
            {
                "old_password": old_password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        assert response.status_code == 302
        assert response.url == "password_change_done"

        assert (
            self.client.login(username=self._default_user.email, password=old_password)
            == False
        )
        assert (
            self.client.login(username=self._default_user.email, password=new_password)
            == True
        )

    def test_required_fields(self):
        self.client.force_login(self._default_user)
        response = self.client.post(
            f"/account/change-password/{self._default_user.first_name}/"
        )

        assert response.status_code == 200
        assertFormError(
            response.context["form"], "old_password", ["This field is required."]
        )
        assertFormError(
            response.context["form"], "new_password1", ["This field is required."]
        )
        assertFormError(
            response.context["form"], "new_password2", ["This field is required."]
        )

    def test_login_required(self):
        response = self.client.post(
            f"/account/change-password/{self._default_user.first_name}/"
        )

        assert response.status_code == 302
        assert "/login" in response.url
