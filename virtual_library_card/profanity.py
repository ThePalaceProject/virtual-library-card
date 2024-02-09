import itertools

from better_profanity import profanity
from better_profanity.varying_string import VaryingString

from virtual_library_card.logging import log


class ProfanityWordList:
    """
    We generate a list of all censored word permutations from the better_profanity library
    since it matches our need for basic censorship with common replacements but not the need to do partial string matches
    """

    _ALL_CENSORED_WORDS: list[str] = []

    @classmethod
    def contains_profanity(cls, word: str) -> bool:
        """Do a partial match to check if any profanity is contained within a string"""
        lower_word = word.lower()
        for profane in cls.wordlist():
            if profane in lower_word:
                return True
        return False

    @classmethod
    def wordlist(cls) -> list[str]:
        if not cls._ALL_CENSORED_WORDS:
            cls._generate_wordlist()
        return cls._ALL_CENSORED_WORDS

    @classmethod
    def _generate_wordlist(cls, custom_words: list[str] | None = None):
        # setup and cache the profanity list
        profanity.load_censor_words(custom_words=custom_words)
        cls._ALL_CENSORED_WORDS = []
        for word in profanity.CENSOR_WORDSET:
            cls._ALL_CENSORED_WORDS.extend(cls._generate_word_variations(word))

        log.info(
            f"Generated profanity wordlist with {len(cls._ALL_CENSORED_WORDS)} words"
        )

    @classmethod
    def _generate_word_variations(cls, vstr: VaryingString) -> list[str]:
        """Generate all possible variations for a given word"""
        variations = []
        combos = []
        # Don't need special character checks
        for chars in vstr._char_combos:
            combos.append(tuple(c for c in chars if c.isalnum()))

        # Create the universe of possible words for the replacement letters
        products = list(itertools.product(*combos))
        for word in products:
            variations.append("".join(word))
        return variations
