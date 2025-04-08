from tests.base import BaseAdminUnitTest
from virtuallibrarycard.admin import AlphabeticalPlaceTypeFilter, PlaceAdmin
from virtuallibrarycard.models import Place


class TestPlaceAdminView(BaseAdminUnitTest):
    MODEL = Place
    MODEL_ADMIN = PlaceAdmin

    def test_list_filter(self):
        filters = self.admin.get_list_filter(self.mock_request)
        assert AlphabeticalPlaceTypeFilter in filters
