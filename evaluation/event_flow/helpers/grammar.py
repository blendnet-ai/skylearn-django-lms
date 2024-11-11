import json
from data_repo.models import QuestionBank
from textblob import TextBlob

def evaluate_grammar(user_answer, llm_object, question_type):
    system_message = f"""
    You are an AI tutor, tasked with analyzing a student's answer for grammatical errors and ignoring punctuation errors.
    Identify clear and obvious grammatical errors from the STANDARD LIST OF ERRORS added below in the each sentence in the answer. 

    Important Notes:
    - Do not evaluate clarity or completeness.
    - Do not attempt to rephrase sentences.
    - Overlook any logical errors, spelling mistakes, and punctuation errors.

    STANDARD LIST OF ERRORS:
    1. Subject-Verb Agreement: Ensuring the subject and verb agree in number and person.
        - Incorrect: "The team are playing well."
        - Correct: "The team is playing well."

    2. Run-on Sentences: Joining two independent clauses without proper punctuation or conjunctions.
        - Incorrect: "I went to the store I bought some milk."
        - Correct: "I went to the store, and I bought some milk."

    4. Misplaced Modifiers: Ensuring that descriptive words or phrases are placed next to the words they modify.
        - Incorrect: "I found a gold ring in the garden with a metal detector."
        - Correct: "I found with a metal detector a gold ring in the garden."

    5. Dangling Modifiers: Clarifying the subject that a modifier is supposed to modify.
        - Incorrect: "Rushing to the bus, my phone fell out of my pocket."
        - Correct: "While I was rushing to the bus, my phone fell out of my pocket."

    6. Double Negatives: Avoiding the use of double negatives, which can create confusion.
        - Incorrect: "I don't want no dessert."
        - Correct: "I don't want any dessert."

    7. Ambiguous Pronoun Reference: Ensuring that pronouns have clear antecedents.
        - Incorrect: "She told her sister she would visit her."
        - Correct: "She told her sister that she would visit."

    9. Redundancy: Avoiding repetition of the same ideas using different words.
        - Incorrect: "The reason why he left is because of a disagreement."
        - Correct: "He left because of a disagreement."

    10. Incomplete Comparisons: Ensuring that comparisons are complete and logical.
        - Incorrect: "She is taller than her sister."
        - Correct: "She is taller than her sister is."

    11. Improper Preposition Usage: Using the correct preposition for a specific context.
        - Incorrect: "I'm good in math."
        - Correct: "I'm good at math."

    12. Improper Pronoun Case: Using the correct form of pronouns (e.g., subject vs. object).
        - Incorrect: "Me and him went to the store."
        - Correct: "He and I went to the store."

    13. Fused Sentences: Combining two independent clauses without proper punctuation or conjunctions.
        - Incorrect: "I'm tired I'm going to bed."
        - Correct: "I'm tired, so I'm going to bed."

    14. Tense Shift: Maintaining consistency in verb tense within a sentence.
        - Incorrect: "She will finish her homework, then she was watching TV."
        - Correct: "She will finish her homework, then she will watch TV."

    15. Parallel Structure: Ensuring that items in a list or elements in a sentence have a consistent grammatical structure.
    Do not check for commas or punctuation here. 
        - Incorrect: "She likes swimming, hiking, and to read."
        - Correct: "She likes swimming, hiking, and reading."

    16. Improper Use of Adjectives and Adverbs: Using adjectives to modify nouns and adverbs to modify verbs or adjectives.
        - Incorrect: "He ran quick to catch the bus."
        - Correct: "He ran quickly to catch the bus."

    17. Singular vs. Plural Nouns: Making sure nouns and their modifiers agree in number.
        - Incorrect: "The book on the table are interesting."
        - Correct: "The books on the table are interesting."

    18. Improper Article Usage: Using articles (a, an, the) appropriately.
        - Incorrect: "I want a apple."
        - Correct: "I want an apple."

    19. Incorrect Verb Forms: Using the correct verb forms (e.g., past tense, past participle).
        - Incorrect: "I have saw that movie before."
        - Correct: "I have seen that movie before."

    20. Confusing Homophones: Differentiating between words that sound the same but have different meanings and spellings.
        - Incorrect: "Their going to the park."
        - Correct: "They're going to the park."

    Student answer =  {llm_object.delimiter}{user_answer}{llm_object.delimiter}
    Generate a JSON that contains the error outputs,
    containing a error phrase, corrected phrase, grammatical error from the standard list and reason which is an explanation of the wrong usage.
    The output should NOT contain any extra text but a json with the following format:
    {{
        "errors": [
            {{
                "incorrect": "error phrase",
                "correct": "corrected phrase",
                "grammatical_error" : "grammatical error from the standard list (make this key visible only if the error exists. If the error is No Error then also do not display",
                "reason": "reason"
            }}
        ]
    }}
    
    If there are no grammatical errors, then the output should be in the following (empty errors json):
    {{
        "errors": []
    }}
    """
    messages = [
        {'role': 'system', 'content': system_message},
    ]
    response = llm_object.get_completion_from_messages(messages)
    try:
        response_json = json.loads(response)
    except json.JSONDecodeError:
        response_json = response
        
    errors = response_json.get("errors") if isinstance(response_json, dict) else response_json

    error_count = {}
    final_error_response = []
    for item in errors:
        if (item.get("grammatical_error")).lower() != "no error" and item.get("grammatical_error"):
            final_error_response.append(item)
            error_count[item.get("grammatical_error")] = error_count.get(item.get("grammatical_error"), 0) + 1

    total_errors = len(final_error_response)    
    blob = TextBlob(user_answer)
    total_words = len(blob.words)
    sentences = blob.sentences
    average_sentence_length = total_words / len(sentences) if len(sentences) != 0 else 0
    error_density = (total_errors / total_words) * 100

    
    sentence_length_score_ranges = {
        QuestionBank.QuestionType.IELTS: {10: 2, 15: 4.5, 20: 6.5, float('inf'): 8.5},
        QuestionBank.QuestionType.INTERVIEW_PREP: {10: 4, 15: 6, 20: 8, float('inf'): 10},
    }
    sentence_length_score = calculate_score(sentence_length_score_ranges, average_sentence_length, question_type)

    error_density_score_ranges = {
        QuestionBank.QuestionType.IELTS: {1: 9, 5: 8, 10: 6.5, float('inf'): 3},
        QuestionBank.QuestionType.INTERVIEW_PREP: {1: 10, 5: 8, 10: 4, float('inf'): 2},
    }
    error_density_score = calculate_score(error_density_score_ranges, error_density, question_type)
        
    score = 0.7*sentence_length_score + 0.3*error_density_score
    
    return score, final_error_response, error_count, error_density_score

def calculate_score(score_ranges, param, question_type):
    for length, score in score_ranges[question_type].items():
        if param < length:
            return score
