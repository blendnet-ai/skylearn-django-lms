import json
import logging
from json import JSONDecodeError

from evaluation.event_flow.processors.expections import ProcessorEvaluationException

logger = logging.getLogger(__name__)

def evaluate_fillerWords(user_input, llm_object):
    system_message = f'''
            IGNORE ALL PREVIOUS INSTRUCTIONS:
            You are a Filler word Checker: your job is to identify any Filler words or repeated words in the text. 
            Assess whether these repetitions disrupt the text's flow. Pay attention to any patterns or
            excessive repetitions that may disrupt fluency. Correct the text only by fixing the filler words and nothing else.
            A few examples fo the filler words are below 
                Actually
                Almost
                Basically
                For what it’s worth
                In my (humble) opinion
                It goes without saying
                Only
                Really
                very
                Ah
                Er
                I think
                like
                Literally
                OK
                Right
                So
                Uh
                Um
                Well
                Um
                Ummm
                Aah
                Ah 
                Ahh
                Er 
                Uh 
                Uhh
                You know (what I mean)

            A few examples of sentences with filler words.
                Text : "It was a sunny day, so so beautiful."
                Corrected Text: "It was a sunny beautiful day."
                Filler Words: "so so"

                Text: "The new employee quickly adapted to the new work environment."
                Corrected Text: "The new employee quickly adapted to the work environment."
                Filler Words: "new"

                Text: "Just, like, take your time to finish the report."
                Corrected Text: "Take your time to finish the report."
                Filler Words: "Just, like"

                Text: "In my humble opinion, this movie is excellent."
                Corrected Text: "In my opinion, this movie is excellent."
                Filler Words: "humble"

                Text: "Basically, you need to follow these steps."
                Corrected Text: "You need to follow these steps."
                Filler Words: "Basically"

                Text: Um, well, I think we should, you know, go to the museum today.
                Corrected Text: I think we should go to the museum today.
                Filler Words: "Um, well"

                Text: I, like, literally can't believe what just happened
                Corrected Text: I literally can't believe what just happened.
                Filler Words: "like, literally"

                Text: I was literally so tired after the long day at work, and I just wanted to go home and sleep.
                Corrected Text: I was so tired after the long day at work, and I just wanted to go home and sleep.
                Filler Words: "literally"

                Text: Um.. can we go there?
                Corrected Text: Can we go there?
                Filler Words: "Um"

                Text: Ummm.. we can catch a flight at noon.
                Corrected Text: We can catch a flight at noon.
                Filler Words: "Umm"

            Student answer =  {llm_object.delimiter}{user_input}{llm_object.delimiter}

            Identify the filler words in the below paragraph
            Iterate the paragraph by one sentence at a time and report the FULL Corrected Text by removing the filler words.
            The format of the output should be json dictionary with below keys:        
            {{
                "Corrected Text": "",
                "Filler words":[]
            }}
            
            If there are no filler words, then the output should be (empty array for filler words):
            {{
                "Corrected Text": "student's exact answer",
                "Filler words":[]
            }}

            Remember, the output should NOT contain any extra text than the specified json.
            '''
    
    messages = [
        {'role': 'system', 'content': system_message}
    ]

    response = llm_object.get_completion_from_messages(messages)
    fillerWords_list, corrected_text = [], None

    try:
        response_json = json.loads(response)
        fillerWords_list = response_json["Filler words"]
        corrected_text = response_json["Corrected Text"]
    except (JSONDecodeError, KeyError) as e:
        logger.error(f"[evaluate_fillerWords] Some of the key are missing, err: {e}. LLM Response was {response}")
        raise ProcessorEvaluationException("Error while evaluating fillerword") from e
    
    return (user_input, len(fillerWords_list), corrected_text, fillerWords_list)
