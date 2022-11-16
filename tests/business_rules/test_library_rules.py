from unittest.mock import patch

from tests.base import BaseUnitTest
from VirtualLibraryCard.business_rules.library import LibraryRules


class TestLibraryRules(BaseUnitTest):
    def setup_method(self, request):
        self._mock_checker_patch = patch(
            "VirtualLibraryCard.business_rules.library.AddressChecker"
        )
        self.mock_checker = self._mock_checker_patch.start()
        self.mock_checker.is_valid_zipcode.return_value = True
        return super().setup_method(request)

    def teardown_method(self, request):
        self._mock_checker_patch.stop()

    def test_validate_address_valid_state(self):
        library = self.create_library(places=["NY", "AL"])
        result = LibraryRules.validate_user_address_fields(library, place="AL")
        assert result.state_valid == True
        assert result.zip_valid == True  # by default

    def test_validate_address_invalid_state(self):
        library = self.create_library(places=["NY", "AL"])
        result = LibraryRules.validate_user_address_fields(library, place="HI")
        assert result.state_valid == False
        assert result.zip_valid == True  # by default

    def test_validate_address_valid_zip(self):
        self.mock_checker.is_valid_zipcode.return_value = True
        library = self.create_library(places=["NY", "AL"])
        result = LibraryRules.validate_user_address_fields(
            library, place="AL", zip=99999, city="somecity"
        )
        assert result.zip_valid == True

    def test_validate_address_invalid_zip(self):
        self.mock_checker.is_valid_zipcode.return_value = False
        library = self.create_library(places=["NY", "AL"])
        result = LibraryRules.validate_user_address_fields(
            library, place="AL", zip=99999, city="somecity"
        )
        assert result.zip_valid == False
