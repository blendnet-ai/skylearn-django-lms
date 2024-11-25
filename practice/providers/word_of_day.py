import json
import random
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class WordOfTheDayProvider:

    CACHE_KEY = "word_of_the_day"

    @staticmethod
    def fetch_words_from_file(file_name):
        with open(file_name, 'r', encoding="utf-8") as file:
            words_dict = json.load(file)
        return words_dict

    @staticmethod
    def word_of_the_day_set_cache(word_data):
        cache.set('word_of_the_day', json.dumps(word_data), settings.WORD_OF_DAY_CACHE_TTL)
        logger.info(f"[WordOfTheDayProvider] Cached word of the day: {word_data}")

    @staticmethod
    def fetch_word_of_the_day():
        file_name = "evaluation/vocab/wordOfTheDayData.json"
        all_words_data = WordOfTheDayProvider.fetch_words_from_file(file_name)
        word_data = random.choice(all_words_data)
        logger.info(f"[WordOfTheDayProvider] Fetched word of the day: {word_data}")
        return word_data

    @staticmethod
    def get_word_of_the_day():
        word_data = cache.get(WordOfTheDayProvider.CACHE_KEY)

        if word_data is not None:
            # If word of the day is in cache, return it
            return json.loads(word_data)

        # If word of the day is not in cache, try fetching a new one
        word_data = WordOfTheDayProvider.fetch_word_of_the_day()
        WordOfTheDayProvider.word_of_the_day_set_cache(word_data)

        return word_data
