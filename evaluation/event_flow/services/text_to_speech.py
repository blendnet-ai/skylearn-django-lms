import dataclasses
import typing

from .base_rest_service import BaseRestService
from elevenlabs import Voice, VoiceSettings, generate
from elevenlabs.api import API
from elevenlabs.api.base import api_base_url_v1
import tempfile
from pathlib import Path
import subprocess

class CaptionGenerator:

    @staticmethod
    def generate_srt(captions:typing.List[str],caption_durations:typing.List[float]):
        if len(captions)!=len(caption_durations):
            raise ValueError(f"Captions list length must be equal to caption durations list's lenght. {len(captions)}!={len(caption_durations)} ")
        srt_content = ""
        start_time = 0.0  # Initial start time

        for index, (caption,duration) in enumerate(zip(captions, caption_durations), start=1):
            end_time = start_time + duration
            # Format the start and end times
            start_time_str = CaptionGenerator.format_time(start_time)
            end_time_str = CaptionGenerator.format_time(end_time)
            # Append the formatted caption to the SRT content
            srt_content += f"{index}\n{start_time_str} --> {end_time_str}\n{caption}\n\n"
            # Update the start time for the next caption
            start_time = end_time

        return srt_content

    @staticmethod
    def format_time(seconds):
        """Converts time in seconds to SRT time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:06.3f}".replace('.', ',')



class TextToSpeech:

    def __init__(self):
        self.api_key = "9afbb0837baf22b36a91a47ad36f9b9d"
        self._voice_configs = {
            "default_hindi": Voice(voice_id="7oEtCApkOEauyLUlYmr0",
                                   settings=VoiceSettings(stability=0.31, similarity_boost=0.85, style=0.48,
                                                          use_speaker_boost=True))
        }

    def _get_voice_settings_using_name(self, voice_name: str):
        return self._voice_configs.get(voice_name)

    @staticmethod
    def run_command_and_get_output(cmdlist:typing.List, use_shell=False):
        try:
            if not use_shell:
                byteOutput = subprocess.check_output(cmdlist, stderr=subprocess.STDOUT)
            else:
                byteOutput = subprocess.check_output(" ".join(cmdlist), stderr=subprocess.STDOUT,shell=True)
            return byteOutput.decode('UTF-8').rstrip()
        except subprocess.CalledProcessError as e:
            if e.output.strip():
                ValueError(f"Error in command - {cmdlist}.\n Error is following - \n. {e.output}")
            raise e

    def get_voice(self, voice_id: str):
        url = f"{api_base_url_v1}/voices/{voice_id}?with_settings=true"
        return Voice(**API.get(url, api_key=self.api_key).json())



    @staticmethod
    def _combine_audios_and_return_lengths_in_seconds(*, audios_list: typing.List[typing.ByteString],
                                                      directory_path: str) -> typing.List[float]:
        wav_lengths = []


        combined_file_names_text = ""
        for i, audio in enumerate(audios_list):
            tempfile_name = f"to_combine_audio_{i}.wav"
            with open(f"{directory_path}/{tempfile_name}", "wb") as fil:
                fil.write(audio)
            wav_length = TextToSpeech.run_command_and_get_output(
                ["ffmpeg", "-y","-f", "concat", "-safe", "0", "-i", combined_filenames_path, "-c", "copy",
                    f"{directory_path}/audio.wav"],use_shell=True)
            wav_lengths.append(float(wav_length))
            combined_file_names_text+=f"file '{tempfile_name}'\n"
        combined_filenames_path = f"{directory_path}/combined_files.txt"
        with open(combined_filenames_path, "w") as fil:
            fil.write(combined_file_names_text)

        TextToSpeech.run_command_and_get_output(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", combined_filenames_path,
             "-c", "libmp3lame", f"{directory_path}/audio.mp3"], use_shell=True)

            # if result.returncode != 0:
            #     output = result.stdout.decode()
            #     raise ValueError(f"Got error while getting audio from video. FFMPEG output =  {output}")

        return wav_lengths

    def generate_audio_and_captions_from_text_list(self, *,
                                                   text_list: typing.List[str],
                                                   voice_name: str,
                                                   directory_path:str,
                                                   ):
        audio_list = []
        for text in text_list:
            audio_list.append(self._get_audio_using_text(text=text, voice_name=voice_name))
        wav_lengths = self._combine_audios_and_return_lengths_in_seconds(audios_list=audio_list,
                                                                         directory_path=directory_path)
                                                                         # final_audio_path=f"{directory_path}/audio.wav")
        caption_text = CaptionGenerator.generate_srt(text_list,wav_lengths)
        with open(f"{directory_path}/subtitles.srt",'w') as fil:
            fil.write(caption_text)
        return audio_list

    def _get_audio_using_text(self, *, text: str, voice_name: str, model: str = "eleven_multilingual_v2") -> bytes:
        # with open("to_combine_audio_0.wav",'rb') as fil:
        #     return fil.read()

        audio = generate(
            text=text,
            api_key=self.api_key,
            model=model,
            voice=self._get_voice_settings_using_name(voice_name)
        )

        return audio

    def get_audio_and_store_to_file(self, *, text: str, filepath: str, voice_name: str):
        audio = generate(
            text=text,
            api_key=self.api_key,
            model="eleven_multilingual_v2",
            voice=self._get_voice_settings_using_name(voice_name)
        )

        with open(filepath, "wb") as part_file:
            part_file.write(audio)

    @staticmethod
    def generate_audio_and_subtitles(text_list, folder_name):
        try:
            for text in text_list:
                with open(f"{folder_name}/audio_text.txt",'w',encoding="utf-8") as fil:
                        fil.write(text)
            audio_list = TextToSpeech().generate_audio_and_captions_from_text_list(text_list=text_list,
                                                                            voice_name="default_hindi",
                                                                            directory_path=f"{folder_name}")
            return "subtitles.srt"
        except subprocess.CalledProcessError as e:
            print("err",e.output)
            raise e
    
    @staticmethod
    def generate_audio_as_mp3(text, folder_name):
        try:
            audio=TextToSpeech()._get_audio_using_text(text=text, voice_name="default_hindi")
            file_name = "audio.mp3"
            with open(f"{folder_name}/{file_name}", "wb") as fil:
                fil.write(audio)
        except subprocess.CalledProcessError as e:
            print("err",e.output)
            raise e
        