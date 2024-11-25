import typing

import numpy as np

def evaluate_awkwardPauses_old(user_input, awkward_pause_threshold):
    # Extract segments
    segments = user_input["segments"]
    count = 0
    # Initialize variables to track pauses
    previous_end_time = None
    awkward_pauses = []

    words = []

    # Iterate through segments and calculate pauses
    for segment in segments:
        words.extend(temp for temp in segment["words"] if temp["text"] != "[*]")

    # Handle case where first word is missing in output
    if words:
        awkward_pauses.append(words[0])
    
    for i in range(1, len(words)):
        current_start_time = words[i]["start"]
        previous_end_time = words[i - 1]["end"]
        pause_duration = current_start_time - previous_end_time

        # Check if the pause duration exceeds the threshold
        if pause_duration >= 2 and words[i-1]["text"][-1] == ".":
            awkward_pauses.append({
                "text": "**--**",
                "start": np.round(previous_end_time,2),
                "end": np.round(current_start_time,2),
                "duration": np.round(pause_duration,2)
            })
            count += 1
            
        elif pause_duration >= awkward_pause_threshold:
            awkward_pauses.append({
                "text": "**--**",
                "start": np.round(previous_end_time,2),
                "end": np.round(current_start_time,2),
                "duration": np.round(pause_duration,2)
            })
            count += 1

        else:
            awkward_pauses.append(words[i])
            
    awkward_pauses_text = ""
    for i in awkward_pauses:
        awkward_pauses_text += i["text"] + " "
         
    return user_input["text"], count, awkward_pauses_text

def evaluate_awkwardPauses(*, timed_words:typing.List, awkward_pause_threshold:float):
    # Extract segments

    count = 0
    # Initialize variables to track pauses
    previous_end_time = None
    awkward_pauses = []

    # Handle case where first word is missing in output
    if timed_words:
        awkward_pauses.append({"text":timed_words[0]["word"],
                               "start": timed_words[0]["start"],
                               "end": timed_words[0]["end"],
                               })

    for i in range(1, len(timed_words)):
        current_start_time = timed_words[i]["start"]
        previous_end_time = timed_words[i - 1]["end"]
        pause_duration = current_start_time - previous_end_time

        # Check if the pause duration exceeds the threshold
        if pause_duration >= 2 and timed_words[i - 1]["word"][-1] == ".":
            awkward_pauses.append({
                "text": "**--**",
                "start": np.round(previous_end_time, 2),
                "end": np.round(current_start_time, 2),
                "duration": np.round(pause_duration, 2)
            })
            count += 1

        elif pause_duration >= awkward_pause_threshold:
            awkward_pauses.append({
                "text": "**--**",
                "start": np.round(previous_end_time, 2),
                "end": np.round(current_start_time, 2),
                "duration": np.round(pause_duration, 2)
            })
            count += 1

        else:
            awkward_pauses.append({"text":timed_words[i]["word"],
                               "start": timed_words[i]["start"],
                               "end": timed_words[i]["end"],
                               })

    awkward_pauses_text = ""
    for i in awkward_pauses:
        awkward_pauses_text += i["text"] + " "

    return count, awkward_pauses_text
