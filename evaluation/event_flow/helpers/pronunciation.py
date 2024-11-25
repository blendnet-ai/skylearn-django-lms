import azure.cognitiveservices.speech as speechsdk
import json

def init():
    speech_key="8030b759c9cd43578df9555e906dcb53"
    service_region= "jioindiawest"
    language = "en-US"
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region, speech_recognition_language = language)
    return speech_config

def evaluate_pronunciation(audio_file, user_answer):
    speech_config = init()
    audio_config = speechsdk.audio.AudioConfig(filename=audio_file)

    reference_text = user_answer
    pronunciation_assessment_config = speechsdk.PronunciationAssessmentConfig( reference_text=reference_text, grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark, granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme, enable_miscue=True )

    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config) 
    pronunciation_assessment_config.apply_to(speech_recognizer)
    speech_recognition_result = speech_recognizer.recognize_once()
    pronunciation_assessment_result_json = speech_recognition_result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
    pronunciation_assessment_result_json = json.loads(pronunciation_assessment_result_json)
    pronunciation_assessment = pronunciation_assessment_result_json['NBest'][0]
    words = pronunciation_assessment['Words']
    scores = pronunciation_assessment['PronunciationAssessment']
    total_words_count = 0
    mispronounced_words = []
    mispronounced_words_count = 0
    for word in words:
        if word["PronunciationAssessment"]["ErrorType"]=="Mispronunciation":
            mispronounced_words.append({
                "word": word["Word"],
                "phonetic" : word["Word"],
                "start_time" : word["Offset"] / 10000000,
                "duration": word["Duration"] / 10000000,
            })
            mispronounced_words_count += 1
        total_words_count += 1
    percentage_mispronounced = (mispronounced_words_count / total_words_count) * 100
    percentage_mispronounced = round(percentage_mispronounced, 2)
    pronunciation_score = round(scores["PronScore"]/10, 1)
    return percentage_mispronounced, pronunciation_score, mispronounced_words