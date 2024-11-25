import io
import parselmouth
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from datetime import datetime

from storage_service.azure_storage import AzureStorageService

TIME_SLICE = 8
def init(audio_file):
    snd = parselmouth.Sound(audio_file)
    return snd


def calculate_pitch(pitch, average_pitch, smoothed_pitch_values):
        upper_bound = average_pitch * 1.25
        lower_bound = average_pitch * 0.75
        above_indices = np.where(smoothed_pitch_values > upper_bound)[0]
        below_indices = np.where(smoothed_pitch_values < lower_bound)[0]
        above = set()
        for i in above_indices:
            if i in above:
                continue
            else:
                above.add(round(pitch.xs()[i]))
        overstressed_words = []
        start = None
        end = None
        for i in above:
            if start is None:
                start = i
            elif end is not None and i != end + 1:
                overstressed_words.append((start, end))
                start = i
                end = None
            end = i

        if start is not None and end is not None:
            overstressed_words.append((start, end))

        below = set()
        for i in below_indices:
            if i in below:
                continue
            else:
                below.add(round(pitch.xs()[i]))
        understressed_words = []
        start = None
        end = None
        for i in below:
            if start is None:
                start = i
            elif end is not None and i != end + 1:
                understressed_words.append((start, end))
                start = i
                end = None
            end = i

        if start is not None and end is not None:
            understressed_words.append((start, end))
        interval_duration = TIME_SLICE  # seconds
        total_duration = pitch.duration
        num_intervals = int(total_duration // interval_duration)
        count_of_less_variation = 0
        for i in range(num_intervals):
            start_time = i * interval_duration
            end_time = (i + 1) * interval_duration
            interval_indices = np.where((pitch.xs() >= start_time) & (pitch.xs() <= end_time))[0]
            interval_pitch_values = smoothed_pitch_values[interval_indices]
            interval_min = np.min(interval_pitch_values)
            interval_max = np.max(interval_pitch_values)

            if interval_max - interval_min < 20:
                count_of_less_variation = count_of_less_variation + 1
        mini = np.min(smoothed_pitch_values)
        maxi = np.max(smoothed_pitch_values)
        return upper_bound, lower_bound, mini, maxi, count_of_less_variation, overstressed_words, understressed_words

def evaluate_pitch(audio_blob_path, storage_container_name, audio_file):
    snd = init(audio_file)
    duration = snd.duration
    pitch = snd.to_pitch()
    sigma = 200
    pitch_values = pitch.selected_array['frequency']
    mask = pitch_values != 0

    pitch_values[~mask] = np.interp(np.flatnonzero(~mask), np.flatnonzero(mask), pitch_values[mask])
    average_pitch = np.mean(pitch_values)
    smoothed_pitch_values = gaussian_filter1d(pitch_values, sigma=sigma)
    upper_bound, lower_bound, mini, maxi, count_of_less_variation, overstressed_words, understressed_words = calculate_pitch(pitch, average_pitch, smoothed_pitch_values)

    fig, ax = plt.subplots()  # Create a new figure and axis

    ax.fill_between(pitch.xs(), smoothed_pitch_values, upper_bound, where=smoothed_pitch_values > upper_bound,
                    color='k', alpha=0.5)
    ax.fill_between(pitch.xs(), smoothed_pitch_values, lower_bound, where=smoothed_pitch_values < lower_bound,
                    color='k', alpha=0.5)

    ax.plot(pitch.xs(), smoothed_pitch_values, linewidth=1, color='r')
    ax.axhline(average_pitch, color='g', linestyle='--')

    ax.grid(True)
    ymin = mini - 30
    ymax = maxi + 30

    remark = ""
    if count_of_less_variation < duration/(3*TIME_SLICE):
        remark = "Your pitch went flat and needs improvement; it was unclear and lacked persuasiveness. Focus on clarity and confidence."
    elif count_of_less_variation >= duration/(3*TIME_SLICE) and count_of_less_variation < (2*duration)/(3*TIME_SLICE):
        remark = "Your pitch was decent, but it could be more engaging. Try adding more enthusiasm and confidence. Work on making your delivery more dynamic."
    else:
        remark = "Your pitch was excellent, clear, and engaging. Keep up the great work!"

    ax.set_ylim(ymin, ymax)
    ax.set_ylabel("fundamental frequency [Hz]")
    ax.legend()
    ax.set_xlim([snd.xmin, snd.xmax])

    fig.savefig('evaluation/pitch_graph.jpg')  # Adjust the filename and options as needed
    image_stream = io.BytesIO()
    fig.savefig(image_stream, format='jpeg')
    image_stream.seek(0)
    plot_name = audio_blob_path + "_pitch_result_" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".jpg"

    azure_obj = AzureStorageService()
    url = azure_obj.upload_blob(storage_container_name, plot_name, image_stream)

    plt.close(fig)  # Close the figure

    return url, plot_name, overstressed_words, understressed_words, remark
