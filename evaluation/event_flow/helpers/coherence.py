
def evaluate_coherence(question, user_answer, llm_object):
        system_message =  f"""
        You are a communication coach training students for professional interviews.
        Evaluate the user response to the question on the below parameters:
       1. Check the answer for Completeness:
        Is the information provided by the answer complete and detailed and informative and answer all questions posed to it directly?
        The answer must specifically answer every question and subquestions posted to it in detail, if not then the answer is incomplete.
        
       2. Relevance to the question: 
       Does the answer intend to answer the question and does it address the question posed?
       Does the answer address the question or does it veer off-topic or not related to the question at all?       
       Rate relevance on a 3 point scale - low/medium/high
       
       3. Logical Flow:
       Assess if the candidate's response follows a logical sequence and structure. 
       Is the information presented in a coherent and organized manner, allowing for clear understanding? 
       Rate logical on a 3 point scale - low/medium/high
        
        Generate a overall score on the basis of these two questions (Unsatisfactory, Good or Excellent)
        You are not to find any logical errors or fallacies in the answer.

        
        Question : {question}
        Student answer =  {llm_object.delimiter}{user_answer}{llm_object.delimiter}
        
        Your response must be in a JSON dictionary format with the following elements.
        
            {{"Completeness" : "Yes/No",
            "Completeness_Reason" : Reason for the completeness score,
            "Relevance" : High/medium/low,
            "Relevance_Reason" : Reason for the completeness score,
            "Logical" : "High/medium/low",
            "Logical_Reason": Reason for the logical flow score,
            "Overall" : Unsatisfactory/ Good/ Excellent,
            "Overall_Reason" : 50 word feedback based on relevance, logical flow, completeness ratings}}            
    
        The output must always be a JSON dictionary.
        """

        messages = [
            {'role': 'system', 'content': system_message},
        ]

        response = llm_object.get_completion_from_messages(messages)
        return response