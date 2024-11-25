from textblob import TextBlob
import json
import re
import spacy


def init():
    with open('evaluation/vocab/most_freq_5000.json', 'r') as json_file:
        most_freq_5000 = json.load(json_file)
    with open('evaluation/vocab/most_freq_2000.json', 'r') as json_file:
        most_freq_2000 = json.load(json_file)

    with open('evaluation/vocab/cefrWords.json', 'r') as json_file:
        word_level_mapping = json.load(json_file)
        
    with open('evaluation/vocab/cefrPhrases.json', 'r') as json_file:
        phrase_level_mapping = json.load(json_file)
        
    return most_freq_5000, most_freq_2000, word_level_mapping, phrase_level_mapping

def evaluate_vocab(user_answer):
    most_freq_5000, most_freq_2000, word_level_mapping, phrase_level_mapping = init()
    blob = TextBlob(user_answer)

    total_words = len(blob.words)
    unique_words = set(blob.words)
    num_unique_words = len(unique_words)

    num_repeated_words = total_words - num_unique_words

    percentage_unique = (num_unique_words / total_words) * 100
    lowercase_unique_words = {word.lower() for word in unique_words}

    common_words = lowercase_unique_words.intersection(most_freq_5000)
    frequently_used_2000 = len(lowercase_unique_words.intersection(most_freq_2000))

    rare_words = num_unique_words - len(common_words)
    percentage_rare_words = (rare_words / num_unique_words) * 100
    percentage_frequently_used_2000 = (frequently_used_2000/num_unique_words) * 100
    level_counts = {}
    words_by_level = {}

    words_not_found = ""
    existing_levels = {'A2', 'B1', 'C2', 'C1', 'A1', 'B2'}
    for word in unique_words:
        cefr_word = word_level_mapping.get(word.lower())
        if cefr_word and cefr_word.get("cefr") in existing_levels:
            level = cefr_word.get("cefr")
            level_counts[level] = level_counts.get(level, 0) + 1
            if level not in words_by_level:
                words_by_level[level] = []
            words_by_level[level].append(word)
        else:
            words_not_found += word + " "   
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(words_not_found)         
    lemmatized_words = [token.lemma_ for token in doc]
    for word in lemmatized_words:
        cefr_word = word_level_mapping.get(word.lower())
        if cefr_word and cefr_word.get("cefr") in existing_levels:
            level = cefr_word.get("cefr")
            level_counts[level] = level_counts.get(level, 0) + 1
            if level not in words_by_level:
                words_by_level[level] = []
            words_by_level[level].append(word)

    sentences = blob.sentences
    sentence_lengths = [len(sentence.words) for sentence in sentences]
    average_sentence_length = sum(sentence_lengths) / len(sentences)

    longest_sentence_length = max(sentence_lengths)

    for phrase in phrase_level_mapping:
        match = re.search(phrase, user_answer, re.IGNORECASE)
        if match:
            exact_phrase = match.group(0)
            level = phrase_level_mapping[phrase]['cefr']
            level_counts[level] = level_counts.get(level, 0) + 1
            if level not in words_by_level:
                words_by_level[level] = []
            words_by_level[level].append(exact_phrase)
    return num_unique_words, num_repeated_words, total_words, frequently_used_2000, percentage_frequently_used_2000, percentage_unique, rare_words, percentage_rare_words, level_counts, words_by_level, average_sentence_length, longest_sentence_length
