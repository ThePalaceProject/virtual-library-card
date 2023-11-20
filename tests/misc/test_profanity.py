from better_profanity.varying_string import VaryingString

from tests.base import BaseUnitTest
from virtual_library_card.profanity import ProfanityWordList


class TestProfanityWordList(BaseUnitTest):
    def test__generate_word_variations(self):
        vstr = VaryingString(
            "news", char_map={"e": ("e", "3"), "s": ("s", "5"), "n": ("n", "m")}
        )
        variations = ProfanityWordList._generate_word_variations(vstr)
        # Assert the length, and no repetitions
        assert len(variations) == 8
        assert len(set(variations)) == 8

        # Special characters ignored
        vstr = VaryingString("00", char_map={"0": ("0", "1", "2", "*")})
        variations = ProfanityWordList._generate_word_variations(vstr)
        assert set(variations) == {"00", "10", "20", "01", "11", "21", "02", "12", "22"}

    def test_contains_profanity(self):
        ProfanityWordList._generate_wordlist(custom_words=["bard", "gent"])
        assert ProfanityWordList.contains_profanity("Bard") == True
        assert ProfanityWordList.contains_profanity("B4RD") == True
        assert ProfanityWordList.contains_profanity("g3n7") == True
