import ast
from .models import PromptTemplates
from string import Template
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
import json
import secrets
from django.contrib.auth import get_user_model
User = get_user_model()
import random
from custom_auth.models import UserProfile

import datetime

def fetch_relevant_text(transcript, timestamp):
    transcript = ast.literal_eval(transcript)
    closest_index = 0
    min_difference = float('inf')
    
    for i, entry in enumerate(transcript):
        difference = abs(entry['start'] - timestamp)
        if difference < min_difference:
            min_difference = difference
            closest_index = i
    
    return_string =""
    for i in range(closest_index - 10, closest_index + 10):
        if 0 <= i < len(transcript):
            return_string += transcript[i]['text'] + " "
    exact_string = transcript[closest_index]['text']
    print("RETURN STRING")
    print(return_string)
    print("EXACT STRING")
    print(exact_string)
    return return_string, exact_string

def extract_summary(transcript, exact_string, return_string):
    highlight_prompt = PromptTemplates.objects.get(name='highlight_prompt')
    if not highlight_prompt:
        return None
    try:
        src = Template(highlight_prompt.prompt)
        result = src.substitute(exact_string=exact_string, return_string=return_string)
        llm = OpenAIService()
        print("RESULT IS")
        print(result)
        messages = [{'role': 'system', 'content': result}]
        result_messages = llm.get_completion_from_messages(messages)
        print("RESULT MESSAGES")
        print(result_messages)
        print(type(result_messages))
        response = json.loads(result_messages)
        print(type(response))
        print("GPT RESPONSE")
        print(response)
        return response
    except Exception as e:
        print(e)
        return None
    
def generate_6_digit_hex_id():
    random_bytes = secrets.token_bytes(3)
    hex_id = random_bytes.hex()
    hex_id_6_digit = hex_id[:6]
    return hex_id_6_digit
    
def generate_12_digit_random_id():
    min_num = 10**11  
    max_num = (10**12) - 1  
    return random.randint(min_num, max_num)


def update_daily_streak(user_id):
    user = UserProfile.objects.get(user_id=user_id)
    if user.last_task_date:
        last_task_date = user.last_task_date
        today = datetime.datetime.now().date()
        if last_task_date == today - datetime.timedelta(days=1):
            user.daily_streak += 1
        else:
            user.daily_streak = 1
    else:
        user.daily_streak = 1
    if user.daily_streak > user.longest_streak:
        user.longest_streak = user.daily_streak
    user.last_task_date = datetime.datetime.now().date()
    user.save()

def fetch_prompt(prompt_name):
    prompt = PromptTemplates.objects.get(name=prompt_name)
    return prompt.prompt

def chat_prompt_template(conversational_history, transcript, title, timestamp):
    prompt = fetch_prompt('chat_prompt')
    src = Template(prompt)
    result = src.substitute(conversational_history=conversational_history, transcript=transcript, title=title, timestamp=timestamp)
    return result

def format_updated_at(updated_at):
    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    day = updated_at.strftime('%d')
    day_suffix = 'th' if 11 <= int(day) % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(int(day) % 10, 'th')
    formatted_day = f"{day}{day_suffix}"
    month = month_names[updated_at.month - 1]  # month_names is 0-indexed
    year = updated_at.strftime('%Y')
    
    formatted_date = f"{formatted_day} {month} {year}"
    
    return formatted_date

def format_duration(duration):
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60
    if hours == 0:
        formatted_duration = f"{minutes} mins {seconds} secs"
    else:
        formatted_duration = f"{hours} hrs {minutes} mins {seconds} secs"
    
    return formatted_duration

def list_chapters_data(chapters_data):
    for chapter in chapters_data:
        questions_data = chapters_data[chapter].get('ques', None)
        if questions_data:
            ques = list(questions_data.values())
            chapters_data[chapter]['ques'] = ques
    return list(chapters_data.values())

def convert_timestamp(timestamp):
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    hours = timestamp // 3600
    mins = (timestamp % 3600) // 60
    secs = timestamp % 60
    if hours > 0:
    # add hours, mins and secs string to the timestamp
        return f"{hours} hours: {mins} mins : {secs} seconds"
    return f"{mins} mins : {secs} seconds"