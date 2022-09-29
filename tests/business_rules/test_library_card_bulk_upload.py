from io import BytesIO
from unittest.mock import patch

import pytest
from django.core import mail

from tests.base import BaseUnitTest, MockThread
from VirtualLibraryCard.business_rules.library_card import (
    BulkUploadBadHeadersException,
    BulkUploadDuplicatesException,
    BulkUploadLibraryException,
    LibraryCardBulkUpload,
)
from VirtualLibraryCard.models import CustomUser, LibraryCard


class TestLibraryCardBulkUpload(BaseUnitTest):
    def test_bulk_upload_csv(self):
        csv_bytes = b"""id,first_name,email
                        111,name111,111@example.org
                        222,name222,222@example.org
                        333,name333,333@example.org
                        444,name444,444@example.org"""

        uploaded = BytesIO(csv_bytes)
        library = self.create_library(allow_bulk_card_uploads=True)
        LibraryCardBulkUpload.bulk_upload_csv(
            library, uploaded, admin_user=self._default_user
        )
        users = CustomUser.objects.filter(library=library).order_by("first_name").all()
        assert len(users) == 4
        cards = LibraryCard.objects.filter(library=library).all()
        assert len(cards) == 4

        for ix, email_num in enumerate([111, 222, 333, 444]):
            assert users[ix].email == f"{email_num}@example.org"

        # Welcome email per user, and one result email
        assert len(mail.outbox) == 5
        for ix in range(0, len(mail.outbox) - 1):
            welcome = mail.outbox[ix]
            assert "Welcome" in welcome.subject

        result_email = mail.outbox[-1]
        assert result_email.subject == f"Bulk Upload Results | {library.name}"
        assert len(result_email.attachments) == 1

    def test_bad_headers(self):
        self._default_library.allow_bulk_card_uploads = True
        csv_bytes = b"""notid,first_name,email
                        someid,somename,someemail"""

        uploaded = BytesIO(csv_bytes)
        with pytest.raises(BulkUploadBadHeadersException) as e:
            LibraryCardBulkUpload.bulk_upload_csv(self._default_library, uploaded)

    def test_duplicate_rows(self):
        self._default_library.allow_bulk_card_uploads = True

        # Duplicate IDs check
        csv_bytes = b"""id,first_name,email
                        111,name111,111@example.org
                        111,name111,112@example.org
                        """

        uploaded = BytesIO(csv_bytes)
        with pytest.raises(BulkUploadDuplicatesException) as e:
            LibraryCardBulkUpload.bulk_upload_csv(self._default_library, uploaded)

        assert e.value.duplicates["ids"] == {
            "111",
        }

        # Duplicate emails check
        csv_bytes = b"""id,first_name,email
                        111,name111,111@example.org
                        112,name111,111@example.org
                        """

        uploaded = BytesIO(csv_bytes)
        with pytest.raises(BulkUploadDuplicatesException) as e:
            LibraryCardBulkUpload.bulk_upload_csv(self._default_library, uploaded)

        assert e.value.duplicates["emails"] == {
            "111@example.org",
        }

    def test_library_exceptions(self):
        library = self.create_library()
        library.allow_bulk_card_uploads = False
        library.bulk_upload_prefix = "Something"

        with pytest.raises(BulkUploadLibraryException) as ex:
            LibraryCardBulkUpload.bulk_upload_csv(library, BytesIO())
        assert ex.match("Library does not allow bulk uploads")

        library.allow_bulk_card_uploads = True
        library.bulk_upload_prefix = None

        with pytest.raises(BulkUploadLibraryException) as ex:
            LibraryCardBulkUpload.bulk_upload_csv(library, BytesIO())
        assert ex.match("Library has no upload prefix")

    def test_optional_columns(self):
        self._default_library.allow_bulk_card_uploads = True
        csv_bytes = b"""id,first_name,email,last_name,city,us_state,zip
                        111,name111,111@example.org,000,New York,NY,10001"""
        uploaded = BytesIO(csv_bytes)

        LibraryCardBulkUpload.bulk_upload_csv(
            self._default_library, uploaded, admin_user=self._default_user
        )
        user = CustomUser.objects.get(email="111@example.org")

        assert user.last_name == "000"
        assert user.city == "New York"
        assert user.us_state == "NY"
        assert user.zip == "10001"
        assert len(mail.outbox) == 2

    @patch("VirtualLibraryCard.business_rules.library_card.Thread", new=MockThread)
    def test_async_mode(self):
        csv_bytes = b"""id,first_name,email
                        111,name111,111@example.org
                        222,name222,222@example.org
                        333,name333,333@example.org
                        444,name444,444@example.org"""

        uploaded = BytesIO(csv_bytes)
        library = self.create_library(allow_bulk_card_uploads=True)
        bulk = LibraryCardBulkUpload.bulk_upload_csv(
            library, uploaded, admin_user=self._default_user, _async=True
        )

        assert type(bulk._async_thread) == MockThread
        assert bulk._async_thread.daemon == False
        assert type(bulk._async_thread.args[0]) == str  # filename not fileio

        assert CustomUser.objects.filter(library=library).count() == 4
        assert len(mail.outbox) == 5

        # Did we clean up the file
        assert not bulk.storage_class().exists(bulk._async_thread.args[0])
