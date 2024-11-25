DAG = {
    "default": {
        "processors": {
            "SpeechToText": {"depends_on": []},
            "Sentiment": {"depends_on": ["SpeechToText"]},
            "AwkwardPauses": {"depends_on": ["SpeechToText"]},
            "Pace": {"depends_on": ["SpeechToText"]},
            "FillerWords": {"depends_on": ["SpeechToText"]},
            "Pitch": {"depends_on": ["SpeechToText"]},
            "Fluency": {"depends_on": ["Pitch", "FillerWords", "Pace", "Pronunciation", "AwkwardPauses", ]},
            "Pronunciation": {"depends_on": ["SpeechToText"]},
            "Vocab": {"depends_on": ["SpeechToText"]},
            "SentimentSaver": {"depends_on": ["Sentiment"]},
            "Grammar": {"depends_on": ["SpeechToText"]},
            "Coherence": {"depends_on": ["SpeechToText"]},
            "PronunciationSaver": {"depends_on": ["Pronunciation"]},
            "VocabSaver": {"depends_on": ["Vocab"]},
            "IELTSGrammarSaver": {"depends_on": ["Grammar"]},
            "CoherenceSaver": {"depends_on": ["Coherence"]},
            "FluencySaver": {"depends_on": ["Fluency"]},
            "IELTSReportGenerator": {
                "depends_on": ["Grammar", "Vocab", "Coherence", "Fluency", "Pronunciation", "FillerWords", "Pace", ]
            },
            "IELTSEvaluationSaver": {"depends_on": ["IELTSReportGenerator", "IELTSIdealResponse"]},
            "IELTSIdealResponse": {"depends_on": ["SpeechToText"]},
            "IELTSIdealResponseSaver": {"depends_on": ["IELTSIdealResponse"]},
        },
        "termination_processor": {
            "AbortHandler": {}
        }
    },
    "interview_prep": {
        "processors": {
            "SpeechToText": {"depends_on": []},
            "Sentiment": {"depends_on": ["SpeechToText"]},
            "AwkwardPauses": {"depends_on": ["SpeechToText"]},
            "Pace": {"depends_on": ["SpeechToText"]},
            "FillerWords": {"depends_on": ["SpeechToText"]},
            "Pitch": {"depends_on": ["SpeechToText"]},
            "Fluency": {"depends_on": ["Pitch", "FillerWords", "Pace", "Pronunciation", "AwkwardPauses", ]},
            "Pronunciation": {"depends_on": ["SpeechToText"]},
            "Vocab": {"depends_on": ["SpeechToText"]},
            "SentimentSaver": {"depends_on": ["Sentiment"]},
            "InterviewPrepGrammar": {"depends_on": ["SpeechToText"]},
            "Coherence": {"depends_on": ["SpeechToText"]},
            "PronunciationSaver": {"depends_on": ["Pronunciation"]},
            "VocabSaver": {"depends_on": ["Vocab"]},
            "InterviewPrepGrammarSaver": {"depends_on": ["InterviewPrepGrammar"]},
            "CoherenceSaver": {"depends_on": ["Coherence"]},
            "FluencySaver": {"depends_on": ["Fluency"]},
            "InteviewPrepReportGenerator": {
                "depends_on": ["InterviewPrepGrammar", "Vocab", "Coherence", "Fluency", "Pronunciation", "FillerWords", "Pace", "Sentiment",]
            },
            "InterviewEvaluationSaver": {"depends_on": ["InteviewPrepReportGenerator", "InterviewPrepIdealResponse"]},
            "InterviewPrepIdealResponse": {"depends_on": ["SpeechToText"]},
            "InterviewPrepIdealResponseSaver": {"depends_on": ["InterviewPrepIdealResponse"]},
        },
        "termination_processor": {
            "AbortHandler": {}
        }
    },
    "speaking": {
        "processors": {
            "SpeechToText": {"depends_on": []},
            "Sentiment": {"depends_on": ["SpeechToText"]},
            "AwkwardPauses": {"depends_on": ["SpeechToText"]},
            "Pace": {"depends_on": ["SpeechToText"]},
            "FillerWords": {"depends_on": ["SpeechToText"]},
            "Pitch": {"depends_on": ["SpeechToText"]},
            "Fluency": {"depends_on": ["Pitch", "FillerWords", "Pace", "Pronunciation", "AwkwardPauses", ]},
            "Pronunciation": {"depends_on": ["SpeechToText"]},
            "Vocab": {"depends_on": ["SpeechToText"]},
            "InterviewPrepGrammar": {"depends_on": ["SpeechToText"]},
            "Coherence": {"depends_on": ["SpeechToText"]},
            "SpeakingFinalScore": {"depends_on": ["SpeechToText", "Sentiment", "Pronunciation", "Vocab", "InterviewPrepGrammar", "Coherence", "Fluency"]},
            "SpeakingSaver": {"depends_on": ["SpeechToText", "Sentiment", "Pronunciation", "Vocab", "InterviewPrepGrammar", "Coherence", "Fluency", "SpeakingFinalScore"]},
            "AssessmentEvaluatorProcessor": {"depends_on": ["SpeakingSaver"]},
        },
        "termination_processor": {
            "AbortHandler": {}
        }
    },
    
    "mock_behavioural": {
        "processors": {
            "SpeechToText": {"depends_on": []},
            "Sentiment": {"depends_on": ["SpeechToText"]},
            "AwkwardPauses": {"depends_on": ["SpeechToText"]},
            "Pace": {"depends_on": ["SpeechToText"]},
            "FillerWords": {"depends_on": ["SpeechToText"]},
            "Pitch": {"depends_on": ["SpeechToText"]},
            "Fluency": {"depends_on": ["Pitch", "FillerWords", "Pace", "Pronunciation", "AwkwardPauses"]},
            "Pronunciation": {"depends_on": ["SpeechToText"]},
            "Coherence": {"depends_on": ["SpeechToText"]},
            "InterviewPrepIdealResponse": {"depends_on": ["SpeechToText"]},
            "MockBehaviourFinalScore": {"depends_on": ["SpeechToText", "Sentiment", "Pronunciation", "Coherence", "Fluency"]},
            "MockBehaviouralSaver": {"depends_on": ["SpeechToText", "Sentiment", "Pronunciation", "InterviewPrepIdealResponse", "Coherence", "Fluency", "MockBehaviourFinalScore"]},
            "AssessmentEvaluatorProcessor": {"depends_on": ["MockBehaviouralSaver"]}
        },
        "termination_processor": {
            "AbortHandler": {}
        }
    },

    "writing": {
        "processors": {
            "Vocab": {"depends_on": []},
            "InterviewPrepGrammar": {"depends_on": []},
            "Coherence": {"depends_on": []},
            "WritingFinalScore": {"depends_on": ["Vocab", "InterviewPrepGrammar", "Coherence"]},
            "WritingSaver": {"depends_on": ["Vocab", "InterviewPrepGrammar", "Coherence", "WritingFinalScore"]},
            "AssessmentEvaluatorProcessor": {"depends_on": ["WritingSaver"]},
        },
        "termination_processor": {
            "AbortHandler": {}
        }
    },
    "coding": {
        "processors": {
            "CodeEfficiencyProcessor": { 
                "depends_on": [] 
            },
            "CodeQualityProcessor": { 
                "depends_on": [] 
            },
            "CodeImprovementProcessor": { 
                "depends_on": [] 
            },
            "CodeRevisionTopicProcessor": { 
                "depends_on": [] 
            },
            "CodeSummaryProcessor": {
                "depends_on": [
                    "CodeEfficiencyProcessor", 
                    "CodeQualityProcessor",
                    "CodeImprovementProcessor",
                    "CodeRevisionTopicProcessor"
                ]
            },
            "DSAResponseSaverEfficiency": {
                "depends_on": ["CodeEfficiencyProcessor"]
            },
            "DSAResponseSaverQuality": {
                "depends_on": ["CodeQualityProcessor"]
            },
            "DSAResponseSaverImprovement": {
                "depends_on": ["CodeImprovementProcessor"]
            },
            "DSAResponseSaverRevision": {
                "depends_on": ["CodeRevisionTopicProcessor"]
            },
            "DSAResponseSaverSummary": {
                "depends_on": ["CodeSummaryProcessor"]
            },
            "DSAMarkAsCompleteSaver":{
                  "depends_on": [
                    "DSAResponseSaverEfficiency", 
                    "DSAResponseSaverQuality",
                    "DSAResponseSaverImprovement",
                    "DSAResponseSaverRevision",
                    "DSAResponseSaverSummary"]
            },
            "AssessmentEvaluatorProcessor": {
                "depends_on": [
                    "DSAMarkAsCompleteSaver"
                ]
            }
        },
        "termination_processor": {
            "AbortHandler": {}
        }
    },
    "testing":{
        "processors":
            {
                "TestingProcessor":{"depends_on": []}
            }
    }
}

# Which celery queue to assign to.
# If the mapping doesn't exist, it will assigned to default queue

PROCESSOR_QUEUE_MAPPING = {
    "SpeechToText":"whisper-timestamped"
}