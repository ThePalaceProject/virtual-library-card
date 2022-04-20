from base import BaseUnitTest


class TestSeedData(BaseUnitTest):
    def test_seed_data(self):
        assert self._default_library is not None
        assert self._default_library.name == "Default"
        assert self._default_user is not None
        assert self._default_user.first_name == "Default"
        assert self._default_user.library == self._default_library
        assert self._default_card.library == self._default_library
        assert self._default_card.user == self._default_user

    def test_random_names(self):
        assert len(self._random_name(length=5)) == 5
        random_name = self._random_name(length=50)
        for ch in random_name:
            assert ch in self.VALID_CHARS
