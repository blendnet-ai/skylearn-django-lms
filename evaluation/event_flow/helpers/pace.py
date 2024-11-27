import logging
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
import numpy as np
from storage_service.azure_storage import AzureStorageService
import io
from datetime import datetime

logger = logging.getLogger(__name__)

def evaluate_pace(*, audio_blob_path, storage_container_name, timed_words, window_duration, full_transcript):


    # Extract the spoken words and their start times
    # for i in user_input['segments']:
    #     for j in i['words']:
    #         spoken_words.append(j)

    # Initialize variables
    word_count = 0
    window_start = 0
    word_pace_in_window = []

    # Iterate through the spoken words and calculate the speaking pace in 10-second windows
    for word in timed_words:
        word_start = word['start']

        # Check if the word is within the current window
        if word_start <= window_start + window_duration:
            word_count += 1
        else:
            # Calculate pace for the completed window and store it
            pace_in_window_wpm = (word_count / window_duration) * 60
            word_pace_in_window.append((window_start, pace_in_window_wpm))

            # Move the window start to the next window
            window_start += window_duration
            word_count = 1  # Reset the word count for the new window

    # Plot the speaking pace in 10-second windows
    window_starts, window_pace = zip(*word_pace_in_window)

    # Create a plot
    plt.figure(figsize=(12, 6))
    smoothed_pitch_values = gaussian_filter1d(window_pace, sigma=3)
    smoothed_pitch_values = smoothed_pitch_values.tolist()
    window_starts = list(window_starts)
    smoothed_pitch_values.insert(0,50)
    window_starts.insert(0,0)
    plt.plot(window_starts, smoothed_pitch_values)
    # plt.plot(window_starts, smoothed_pitch_values, label='Speaking Pace in 10-Second Windows (WPM)')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Pace (WPM)')
    # plt.title('Speaking Pace in 10-Second Windows')

    # Add horizontal lines to divide the graph into different pace ranges
    pace_ranges = [50, 100, 140, 160, 200, 250]  # Define your pace ranges here
    for pace in pace_ranges:
        # plt.axhline(y=pace, color='r', linestyle='--', label=f'{pace} WPM')
        plt.axhline(y=pace, color='r', linestyle='--')

    # Fill the space between the pace ranges
    # Fill the space between the pace ranges
    color = ["red","yellow","green"]
    plt.fill_between(window_starts, pace_ranges[0], pace_ranges[1], color=color[0], alpha=0.5)
    plt.fill_between(window_starts, pace_ranges[1], pace_ranges[2], color=color[1], alpha=0.5)
    plt.fill_between(window_starts, pace_ranges[2], pace_ranges[3], color=color[2], alpha=0.5)
    plt.fill_between(window_starts, pace_ranges[3], pace_ranges[4], color=color[1], alpha=0.5)
    plt.fill_between(window_starts, pace_ranges[4], pace_ranges[5], color=color[0], alpha=0.5)

    # plt.legend(loc='best')
    image_stream = io.BytesIO()
    plt.savefig(image_stream, format='jpeg')
    image_stream.seek(0)
    plot_name = audio_blob_path.split(".")[0] + "_pace_result_" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".jpg"

    azure_obj = AzureStorageService()
    url = azure_obj.upload_blob(storage_container_name, plot_name, image_stream)

    return (url, np.ceil(len(full_transcript.split()) / ((timed_words[-1]["end"]) - timed_words[0]["start"]) * 60))
