import random
from datetime import date
import logging

from common.utilities import convert_to_float, round_to_pt5

from practice.models import UserQuestionAttempt
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

class TransformResponse:

    @staticmethod
    def transform_evaluation_response(evaluation_data, audio_url):
        coherence_data = evaluation_data.get("coherence_details")
        coherence_score = None
        if coherence_data is not None:
            coherence_response_data = coherence_data.get("response")
            if coherence_response_data is not None:
                coherence_score = TransformResponse.calculate_coherence_score(coherence_response_data)
            else:
                logger.info("Coherence Response data not found")
        else:
            logger.info("Coherence data not found")

        emotion_data = evaluation_data.get("sentiment_details")
        emotion_score = None
        if emotion_data is not None:
            emotion_score = TransformResponse.calculate_emotion_score(emotion_data)
        else:
            logger.info("Emotion data not found")


        transformed_response = {
            "status": evaluation_data.get("status_text"),
            "summary": (evaluation_data["summary"] or {}).get("text"),
            "overall_performance": (evaluation_data["summary"] or {}).get("overall_performance"),
            "overall_score": convert_to_float(evaluation_data["score"]),
            "evaluation_response": {
                "Fluency": {
                    "score": round_to_pt5(convert_to_float(evaluation_data["fluency"]))
                },
                "Pronunciation": {
                    "score": round_to_pt5(convert_to_float(evaluation_data["pronunciation"]))
                },
                "Grammar": {
                    "score": convert_to_float(evaluation_data["grammar"])
                },
                "Vocab": {
                    "score": evaluation_data["vocab"]
                },
                "Coherence": {
                    "score": coherence_score
                },
                "Emotion": {
                    "score": emotion_score
                },
                "Ideal": {
                    "isComputed": evaluation_data["ideal_response_details"] is not None
                }
            },
            "audio_url": audio_url
        }
        return transformed_response

    @staticmethod
    def transform_grammar_response(grammar_data, grammar_score):
        # score, errors, error_count, incorrect_speech_percentage
        score = convert_to_float(grammar_score)
        errors = grammar_data.get("sentence_correction")
        error_count = grammar_data.get("common_mistakes")
        incorrect_speech_percentage = grammar_data.get("incorrect_speech_percentage")

        data = {
            "Subject-Verb Agreement": "Ensuring the subject and verb agree in number and person.",
            "Run-on Sentences": "Joining two independent clauses without proper punctuation or conjunctions.",
            "Misplaced Modifiers": "Ensuring that descriptive words or phrases are placed next to the words they modify.",
            "Dangling Modifiers": "Clarifying the subject that a modifier is supposed to modify.",
            "Double Negatives": "Avoiding the use of double negatives, which can create confusion.",
            "Ambiguous Pronoun Reference": "Ensuring that pronouns have clear antecedents.",
            "Redundancy": "Avoiding repetition of the same ideas using different words.",
            "Incomplete Comparisons": "Ensuring that comparisons are complete and logical.",
            "Improper Preposition Usage": "Using the correct preposition for a specific context.",
            "Improper Pronoun Case": "Using the correct form of pronouns (e.g., subject vs. object).",
            "Fused Sentences": "Combining two independent clauses without proper punctuation or conjunctions.",
            "Tense Shift": "Maintaining consistency in verb tense within a sentence.",
            "Parallel Structure": "Ensuring that items in a list or elements in a sentence have a consistent grammatical structure.",
            "Improper Use Of Adjectives And Adverbs": "Using adjectives to modify nouns and adverbs to modify verbs or adjectives.",
            "Singular Vs Plural Nouns": "Making sure nouns and their modifiers agree in number.",
            "Improper Article Usage": "Using articles (a, an, the) appropriately.",
            "Incorrect Verb Forms": "Using the correct verb forms (e.g., past tense, past participle).",
            "Confusing Homophones": "Differentiating between words that sound the same but have different meanings and spellings."
            }
        common_mistakes = []
        for rule, mistake_count in error_count.items():
            common_mistakes.append({
                "rule": rule,
                "content": data.get(rule, "Rule description not found"),
                "mistake": mistake_count
            })
        common_mistakes = sorted(common_mistakes, key=lambda x: x["mistake"], reverse=True)
        performance_remark, summary = TransformResponse.generate_grammar_summary(score)
        transformed_response = {
            "score": score,
            "performance_remark": performance_remark,
            "sentence_correction": errors,
            "incorrect_speech_percentage": incorrect_speech_percentage,
            "common_mistakes": common_mistakes,
            "summary": summary
        }
        return transformed_response

    @staticmethod
    def transform_pronunciation_response(pronunciation_data, pronunciation_score, audio_url):
        pronunciation_score = convert_to_float(pronunciation_score)
        mispronounced_words = pronunciation_data.get("words_test", [])
        performance_remark, summary = TransformResponse.generate_pronunciation_summary(pronunciation_score)
        transformed_response = {
            "summary": summary,
            "score": pronunciation_score,
            "performance_remark": performance_remark,
            "words_test": mispronounced_words,
            "audio_uri": audio_url
        }
        return transformed_response

    @staticmethod
    def transform_vocab_response(vocab_data):
        pass

    @staticmethod
    def transform_fluency_response(fluency_data, fluency_score, user_id, practice_question_id):
        score = convert_to_float(fluency_score)
        performance_remark, description = TransformResponse.generate_fluency_summary(score)
        # Pace score is not sent to FE
        pace_score = None
        pace_overall_comment = "NA"
        pace_summary = "NA"
        pace_score = convert_to_float(fluency_data.get("pace_score"))
        if pace_score is not None:
            pace_overall_comment, pace_summary = TransformResponse.get_pace_score_details(pace_score)
        else:
            logger.info(f"[Fluency Transformer] - Pace score not found for user {user_id} and question {practice_question_id}")

        # Fillerword percentage for historical data can be empty
        fillerword_percentage = None
        fillerword_desc = "NA"
        fillerwords_summary = "NA"
        fillerword_percentage = convert_to_float(fluency_data.get("fillerwords_percentage"))
        if fillerword_percentage is not None:
            fillerword_desc, fillerwords_summary = TransformResponse.generate_fillerwords_summary(fillerword_percentage)
        else:
            logger.info(f"[Fluency Transformer] - Fillerword percentage not found for user {user_id} and question {practice_question_id}")

        transform_response = {
            "score": score,
            "summary": description,
            "performance_remark": performance_remark,
            "pitch_image_url": fluency_data.get("pitch_image_url"),
            "pitch_summary": fluency_data.get("pitch_summary"),
            "pace_image_url": fluency_data.get("pace_image_url"),
            "pace_summary": pace_summary,
            "pace_overall_comment": pace_overall_comment,
            "fillerwords": fillerwords_summary,
            "fillerwords_percentage": fillerword_percentage,
            "fillerwords_overall_comment": fillerword_desc,
            "transcript": fluency_data.get("transcript")
        }

        return transform_response

    @staticmethod
    def generate_grammar_summary(grammar_score):
        score_details = {
            "segments": [
            {
                "description": "Novice",
                "grammar_score_range": [0, 4],
                "details": "You're making a good effort, but there are many mistakes in your sentences. Keep practicing and try to focus on basic sentence structures."
            },
            {
                "description": "Beginner",
                "grammar_score_range": [4, 6],
                "details": "Your sentence formations are getting better, but they can be hard to understand due to frequent grammar errors. Keep practicing and aim for more accuracy in your speech."
            },
            {
                "description": "Intermediate",
                "grammar_score_range": [6, 8],
                "details": "Your speech is comprehensible, but you tend to make grammatical mistakes in certain parts of speech. Keep practicing to further improve your accuracy."
            },
            {
                "description": "Expert",
                "grammar_score_range": [8, 10],
                "details": "Top-notch grammar skills! You communicate with great clarity and minimal errors. Keep up the excellent work."
            }
        ]
        }

        segments = score_details["segments"]

        for segment in segments:
            score_range = segment["grammar_score_range"]
            if score_range[0] <= grammar_score < score_range[1]:
                return segment["description"], segment["details"]

        return "Unknown", "Grammar score outside the specified range."

    @staticmethod
    def generate_fluency_summary(fluency_score):
        score_details = {
            "segments": [
                {
                    "description": "Good",
                    "fluency_score_range": [85, 100],
                    "details": "Impressive fluency! Your ability to express yourself with ease is remarkable. You come across as a confident and fluent speaker."
                },
                {
                    "description": "Average",
                    "fluency_score_range": [60, 85],
                    "details": "Your fluency is decent, but there's room for improvement. Work on reducing hesitations and improving the overall flow of your speech."
                },
                {
                    "description": "Bad",
                    "fluency_score_range": [0, 60],
                    "details": "Your fluency needs significant improvement. Hesitations and disruptions in your speech make it challenging to follow. Practice speaking more confidently and working on transitions between ideas. "
                },
        ]
        }

        segments = score_details["segments"]

        for segment in segments:
            score_range = segment["fluency_score_range"]
            if score_range[0] <= fluency_score < score_range[1]:
                return segment["description"], segment["details"]

        return "Unknown", "Fluency score outside the specified range."


    @staticmethod
    def generate_pronunciation_summary(pronunication_score):
        score_details = {
            "segments": [
                {
                    "description": "Good",
                    "pronunication_score_range": [85, 100],
                    "details": "You've nailed it! Your words are crisp and well-articulated, enhancing your overall communication."
                },
                {
                    "description": "Average",
                    "pronunication_score_range": [60, 85],
                    "details": "Your pronunciation is decent, but some words may be a bit unclear. Focus on practicing specific sounds that pose challenges."
                },
                {
                    "description": "Bad",
                    "pronunication_score_range": [0, 60],
                    "details": "Your pronunciation is challenging to follow. Frequent pronunciation errors hinder understanding. Refer to the errors highlighted below and their respective correct pronunciations."
                },
            ]
        }

        segments = score_details["segments"]

        for segment in segments:
            score_range = segment["pronunication_score_range"]
            if score_range[0] <= pronunication_score < score_range[1]:
                return segment["description"], segment["details"]

        return "Unknown", "Pronunciation score outside the specified range."

    @staticmethod
    def get_pace_score_details(pace_score):
        score_details = {
            "segments": [
                {
                    "description": "Bad",
                    "pace_score_range": [0, 100],
                    "details": "Your pace was too slow and hence challenging to follow; it lacked a natural rhythm. Focus on pacing that matches the content and audience's needs."
                },
                {
                    "description": "Average",
                    "pace_score_range": [100, 140],
                    "details": "Your pace was slightly slower than the normal pace of speaking, with some moments of inconsistency. Work on maintaining a steady flow for better delivery."
                },
                {
                    "description": "Good",
                    "pace_score_range": [140, 160],
                    "details": "Your pace was excellent, well-balanced, and easy to follow. Keep up the great tempo."
                },
                {
                    "description": "Average",
                    "pace_score_range": [160, 200],
                    "details": "Your pace was slightly faster than the normal pace of speaking, making your speech somewhat difficult to follow. Practice maintaining a consistent tempo throughout."
                },
                {
                    "description": "Bad",
                    "pace_score_range": [200, 500],
                    "details": "Your pace needs improvement as it was too fast to follow. Aim for a more consistent and balanced delivery."
                },
            ]
        }
        segments = score_details["segments"]

        for segment in segments:
            score_range = segment["pace_score_range"]
            if score_range[0] <= pace_score < score_range[1]:
                return segment["description"], segment["details"]

        return "Unknown", "Pace score outside the specified range."


    @staticmethod
    def generate_fillerwords_summary(fillerword_percentage):
        score_details = {
            "segments": [
                {
                    "description": "Good",
                    "fillerword_score_range": [0, 5],
                    "details": "Great job! Your use of filler words was minimal, allowing your message to come across clearly."
                },
                {
                    "description": "Average",
                    "fillerword_score_range": [5, 15],
                    "details": "Your speech was decent, but there were moments when filler words were distracting. Practice speaking more confidently and with fewer hesitations."
                },
                {
                    "description": "Bad",
                    "fillerword_score_range": [15, 100],
                    "details": "You used too many filler words, disrupting the overall flow of your speech. Practice speaking slowly and thinking ahead to reduce the use of filler words."
                },
            ]
        }

        segments = score_details["segments"]

        for segment in segments:
            score_range = segment["fillerword_score_range"]
            if score_range[0] <= fillerword_percentage < score_range[1]:
                return segment["description"], segment["details"]

        return "Unknown", "Fillerword score outside the specified range."

    @staticmethod
    def transform_coherence_response(coherence_data):
        coherence_response_data = coherence_data.get("response")
        score = TransformResponse.calculate_coherence_score(coherence_response_data)

        transform_response = {
            "overall": coherence_response_data.get("Overall"),
            "completeness": coherence_response_data.get("Completeness", "NA").upper(),
            "logical": coherence_response_data.get("Logical", "NA").upper(),
            "relevance": coherence_response_data.get("Relevance", "NA").upper(),
            "relevance_reason": coherence_response_data.get("Relevance_Reason"),
            "completeness_reason": coherence_response_data.get("Completeness_Reason"),
            "logical_reason": coherence_response_data.get("Logical_Reason"),
            "overall_reason": coherence_response_data.get("Overall_Reason"),
            "score": score
        }

        return transform_response

    @staticmethod
    def calculate_coherence_score(coherence_response_data):
        weight_relevance = {'high': 6, 'medium': 3, 'low': 1}
        weight_logical_flow = {'high': 2, 'medium': 1, 'low': 0}
        weight_completeness = {'yes': 2, 'no': 1}

        relevance = coherence_response_data.get("Relevance")
        logical = coherence_response_data.get("Logical")
        completeness = coherence_response_data.get("Completeness")

        # If any value is Not preset return None
        if relevance is None or logical is None or completeness is None:
            logger.info(f"Relevance: {relevance} - Logical: {logical} - Completeness: {completeness} is None")
            return None

        relevance = relevance.lower()
        logical = logical.lower()
        completeness = completeness.lower()

        score = (weight_relevance[relevance] + weight_logical_flow[logical] + weight_completeness[completeness])
        return score

    @staticmethod
    def transform_emotion_response(emotion_data):

        score = TransformResponse.calculate_emotion_score(emotion_data)
        emotion_data = {
            "sentiment": emotion_data.get("sentiment", "negative").upper(),
            "confidence": emotion_data.get("confidence", "low").upper(),
            "overall_score": score,
            "overall_remark": emotion_data.get("overall_remark", "neutral"),
        }
        return emotion_data

    @staticmethod
    def calculate_emotion_score(emotion_data):
        # Define the weights for confidence and sentiment
        confidence_weights = {"high": 8, "moderate": 4, "low": 2}
        sentiment_weights = {"negative": 0, "neutral": 1, "positive": 2}

        confidence = emotion_data.get("confidence")
        sentiment = emotion_data.get("sentiment")

        if confidence is None or sentiment is None:
            logger.info(f"Confidence: {confidence} -- Sentiment: {sentiment} is None")
            return None
        # Convert input values to lowercase to make it case-insensitive
        confidence = confidence.lower()
        sentiment = sentiment.lower()

        # Calculate the overall score
        overall_score = confidence_weights[confidence] + sentiment_weights[sentiment]

        return overall_score


class StreakUtility:
    @staticmethod
    def get_streak(user_id):
        today = date.today()
        try:
            latest_attempt = UserQuestionAttempt.objects.filter(user_id=user_id).latest('created_at')
            if latest_attempt.created_at.date() == today:
                return latest_attempt.daily_streak
            else:
                return 1

        except ObjectDoesNotExist:
            return 0

class AudioURLProvider:
    @staticmethod
    def get_storage_container_name():
        """ Returns the container name """
        CONTAINER_NAME = "tst"
        return CONTAINER_NAME