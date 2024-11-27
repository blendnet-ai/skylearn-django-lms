from django.core.exceptions import ObjectDoesNotExist

from storage_service.azure_storage import AzureStorageService

from ..models import UserAttemptResponseEvaluation


class EvaluationUtility:
    @staticmethod
    def get_evaluation_by_id(evaluation_id):
        try:
            evaluation = UserAttemptResponseEvaluation.objects.get(id=evaluation_id)
            return evaluation
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_evaluation_score_by_id(evaluation_id):
        try:
            evaluation = UserAttemptResponseEvaluation.objects.get(id=evaluation_id)
            return evaluation.score if evaluation else None
        except UserAttemptResponseEvaluation.DoesNotExist:
            return None

    @staticmethod
    def create_evaluation_and_return_id():

        # TODO: Remove this hardcoding, once no longer required
        fluency_details = {
                "score": 80,
                "summary": "Your might want to slow down the pace to increase clarity of speech",
                "pitch_image_url": "https://stspeechaistage.blob.core.windows.net/misc/pitch_image.jpg",
                "pitch_score": "Your overall pitch was good. Try stressing more on important parts of the speech to get audience’s attention",
                "pace_image_url": "https://stspeechaistage.blob.core.windows.net/tst/pace_image.png",
                "pace_score": "160",
                "fillerwords_summary": "Bad: You used 6 filler words during your 1 minute speech!",
                "transcript": "I am Rahul, ~~um~~ I am an aspiring engineering student hailing **--** from the diverse and culturally rich landscape of India. ~~Basically~~ my relentless curiosity and passion for innovation drive me as I **--** embark on this exciting journey in pursuit of engineering knowledge.I’m ~~uh~~, looking for a **--** developer job."
        }

        pronunciation_details = {
            "score": 60,
            "summary": "You pronounced 20% of the words incorrectly",
            "audio_uri": "",
            "words_test": [
                {
                    "word": "refulgent",
                    "phonetic": "/reːfləgənt/",
                    "start_time": 10,
                    "duration": 5,
                },
                {
                    "word": "word 2",
                    "phonetic": "/reːfləgənt/",
                    "start_time": 10,
                    "duration": 5,
                },
            ]
        }

        grammar_details = {
                "score": 6,
                "summary": "You made grammatical errors in 80% of your speech",
                "sentence_correction": [
                    {
                        "incorrect": "He say he likes to go for a run every morning.",
                        "correct": "He says that he likes to go for a run every morning."
                    },
                    {
                        "incorrect": "Incorrect Sentence",
                        "correct": "Correct Sentence"
                    }
                ],
                "common_mistakes": {
                       'Parallel Structure': 4,
                       'Misplaced Modifiers': 1,
                       'Improper Article Usage': 2
                    }

            }

        vocab_details = {
                "score": "A2",
                "cefr_breakdown": {
                    "A1": 45,
                    "A2": 21,
                    "B1": 16,
                    "B2": 15,
                    "C1": 2,
                    "C2": 1
                },
                "vocal_insights": {
                    "rare_words": 12,
                    "unique_words": 20,
                    "frequently_used": 60
                    },
                "boost_vocab": [
                    {
                        "word": "full",
                        "level": "A2",
                        "synonyms": ["adequate", "big", "chock-full"]
                    },
                    {
                        "word": "easy",
                        "level": "A1",
                        "synonyms": ["accessible", "clear", "effortless"]
                    },
                    {
                        "word": "convenient",
                        "level": "B1",
                        "synonyms": ["acceptable", "advantageous", "agreeable"]
                    }
                ]
             }
        coherence_details = {
            "score": 7.10,
            "summary": "You used 5 filler words during your 1 minute speech!"
        }

        summary = {
            "text": "Keep it Up!!! Your overall score improved by 15% in last 7 days.",
            "achievement_text": "VOCAB KING Active vocabulary better than 50% of the users",
            "improvement_text": "LOW CONFIDENCE Use of too many filler words make you sound less confident",
            "observations": [{
                    "title": "Observation 1",
                    "content": "Fear not, for I am the Lorem Ipsum Whisperer, and I comprehend the secrets that lay within this mystic script. Read and marvel at my linguistic prowess!",
                },
                {
                    "title": "Observation 2",
                    "content": "Lorem ipsum some dummy data here, you can read this I know!",
                }
            ]
        }

        evaluation = UserAttemptResponseEvaluation.objects.create()
        return evaluation.id