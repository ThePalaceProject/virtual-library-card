from unittest import mock

from django.conf import settings

from tests.base import BaseUnitTest
from virtual_library_card.storage import OverwriteStorage


class TestOverwriteStorage(BaseUnitTest):
    @mock.patch("virtual_library_card.storage.os.remove")
    def test_get_available_name(self, mock_remove: mock.MagicMock):
        storage = OverwriteStorage()
        media_path = f"{settings.MEDIA_ROOT}/anyname"

        # File exists
        storage.exists = mock.MagicMock(return_value=True)
        result = storage.get_available_name("anyname")

        assert storage.exists.call_count == 2
        assert storage.exists.call_args[0] == (media_path,)
        assert mock_remove.call_count == 1
        assert mock_remove.call_args[0] == (media_path,)
        assert result == "anyname"

        # When file does not exist
        mock_remove.reset_mock()
        storage.exists.reset_mock()
        storage.exists.return_value = False

        result = storage.get_available_name("anyname")

        assert storage.exists.call_count == 2
        assert storage.exists.call_args[0] == (media_path,)
        assert mock_remove.call_count == 0
        assert result == "anyname"
