import logging
from datetime import datetime, timedelta

from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateformat import DateFormat
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponseBadRequest
from django.db.models import Sum
from custom_auth.authentication import FirebaseAuthentication
from .models import PromptTemplates, Video, UserConsumedVideos
from django.contrib.auth import get_user_model
User = get_user_model()

from custom_auth.models import UserProfile
from django.conf import settings
logger = logging.getLogger(__name__)
from .tasks import task1
from .utility import list_chapters_data, fetch_relevant_text, extract_summary, generate_6_digit_hex_id, update_daily_streak, format_duration, format_updated_at

class ProcessURL(APIView):
    def get(self, request, format=None):
        youtube_url = request.query_params.get('url', None)
        task1.delay(youtube_url)
        return Response({"data": youtube_url}, status=status.HTTP_200_OK)

class HandlePrompts(APIView):
    def post(self, request, format=None):
        data = request.data
        name = data.get('name', None)
        prompt = data.get('prompt', None)
        type = data.get('type', None)
        if not name or not prompt or not type:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        
        if PromptTemplates.objects.filter(name=name).exists():
            return Response({"error": "Prompt already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        prompt_obj = PromptTemplates(name=name, prompt=prompt, type=type)
        prompt_obj.save()
        
        return Response({"data": "Prompt Added"}, status=status.HTTP_200_OK)
    
    def get(self, request, format=None):
        prompts = PromptTemplates.objects.all()
        data = []
        for prompt in prompts:
            data.append({
                "name": prompt.name,
                "prompt": prompt.prompt,
                "type": prompt.type,
                "created_at": DateFormat(prompt.created_at).format('Y-m-d H:i:s'),
                "updated_at": DateFormat(prompt.updated_at).format('Y-m-d H:i:s')
            })
        return Response({"Prompts": data}, status=status.HTTP_200_OK)
    
class VideoList(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user_id = request.user.id
        userModel = User.objects.get(id=user_id)
        if not UserProfile.objects.filter(user_id=userModel).exists():
            user_profile = UserProfile(user_id=userModel)
            user_profile.save()
            
        logger.info(f"VideoListAPI. Getting video list {datetime.now()}")
        video_list = Video.objects.all().order_by('-created_at').values('video_id', 'url', 'title')
        logger.info(f"VideoListAPI. First video {video_list}")
        return Response({"data": video_list}, status=status.HTTP_200_OK)
    
class VideoData(APIView):   

    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user_id = request.user.id
        inputed_video_id = request.query_params.get('video_id', None)

        if not inputed_video_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not Video.objects.filter(video_id=inputed_video_id).exists():
            return Response({"error": "Invalid video_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        video_id=Video.objects.get(video_id=inputed_video_id)
        user_video_object = None
        try:
            user_video_object = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_id)
            update_daily_streak(user_id)
        except UserConsumedVideos.DoesNotExist:
            user_video_object = UserConsumedVideos(user_id=user_id, video_id=video_id)
            user_video_object.chapters_data = video_id.chapters_data
            user_video_object.questions_data = video_id.questions_data
            user_video_object.save()
            
        data = {
            "video_id": inputed_video_id,
            "chapters": list_chapters_data(user_video_object.chapters_data),
            "questions": list(user_video_object.questions_data.values()),
            "url": video_id.url,
            "title": video_id.title,
            "transcript": video_id.transcript,
            "thumbnail": video_id.thumbnail,
        }
        return Response({"data": data}, status=status.HTTP_200_OK)
    
class SubmitQuestionResponse(APIView):
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        user_id = request.user.id
        data = request.data
        type = request.query_params.get('type', None)
        question_id = request.query_params.get('question_id', None)
        video_id = request.query_params.get('video_id', None)

        marked_answer = data.get('response', None)
        video_instance = Video.objects.get(video_id=video_id)
        if not user_id or not video_id or not question_id or not type:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_video = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_instance)
        except UserConsumedVideos.DoesNotExist:
            return Response({"error": "Invalid user or video ID"}, status=status.HTTP_400_BAD_REQUEST)

        if type == 'assessment':
            question_data = user_video.questions_data
            
            question_fetched = question_data.get(question_id)
            if question_fetched is None:
                return Response({"error": "Invalid question_id"}, status=status.HTTP_400_BAD_REQUEST)
            
            answer = question_fetched['answer']
            score = question_fetched['score']
                        
            if answer == marked_answer:
                user_score = score
                user_video.total_points_scored += user_score
            else:
                user_score = 0

            question_data[question_id]['user_score'] = user_score
            question_data[question_id]['attempted'] = True
            question_data[question_id]['marked_answer'] = marked_answer
            user_video.questions_data = question_data
            
        if type == 'in-video':
            chapter_id = request.query_params.get('chapter_id', None)
            fetched_chapter_data = user_video.chapters_data.get(chapter_id)            
            if not fetched_chapter_data:
                return Response({"error": "Invalid chapter_id"}, status=status.HTTP_400_BAD_REQUEST)
            question_fetched = fetched_chapter_data['ques'][question_id]
            if question_fetched is None:
                return Response({"error": "Invalid question_id"}, status=status.HTTP_400_BAD_REQUEST)
            
            answer = question_fetched['answer']
            score = question_fetched['score']
                        
            if answer == marked_answer:
                user_score = score
                user_video.total_points_scored += user_score
            else:
                user_score = 0
            
            fetched_chapter_data['ques'][question_id]['user_score'] = user_score
            fetched_chapter_data['ques'][question_id]['attempted'] = True
            fetched_chapter_data['ques'][question_id]['marked_answer'] = marked_answer
            user_video.chapters_data[chapter_id] = fetched_chapter_data
            
        user_video.save()    
        
        return Response({"data": {"score_added":user_score}}, status=status.HTTP_200_OK)
    
    
class MarkChapterComplete(APIView):
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        user_id = request.user.id
        video_id = request.query_params.get('video_id', None)
        chapter_id = request.query_params.get('chapter_id', None)
        if not user_id or not video_id or not chapter_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_video = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_id)
        chapter_data = user_video.chapters_data.get(chapter_id)
        if not chapter_data:
            return Response({"error": "Invalid chapter_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not chapter_data.get('watched') == True:
            chapter_data['watched'] = True
            current_time_watched = user_video.time_spent
            start_time, end_time = chapter_data['start_time'], chapter_data['end_time']
            start_time = sum(x * int(t) for x, t in zip([3600, 60, 1], start_time.split(":")))
            end_time = sum(x * int(t) for x, t in zip([3600, 60, 1], end_time.split(":")))
            chapter_duration = end_time - start_time
            user_video.time_spent = current_time_watched + chapter_duration
            user_video.chapters_data[chapter_id] = chapter_data

        update_daily_streak(user_id)
        user_video.save()
        
        return Response({"data": "Chapter marked as complete"}, status=status.HTTP_200_OK)
    
class MarkQuizComplete(APIView):
        
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        user_id = request.user.id
        video_id = request.query_params.get('video_id', None)
        chapter_id = request.query_params.get('chapter_id', None)
        type = request.query_params.get('type', None)
        if not user_id or not video_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_video = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_id)
        
        if type == 'in-video':
            chapter_data = user_video.chapters_data.get(chapter_id)
            if not chapter_data:
                return Response({"error": "Invalid chapter_id"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not chapter_data.get('quiz_completed') == True:
                chapter_data['quiz_completed'] = True
                user_video.quizzes_attempted += 1
                user_video.chapters_data[chapter_id] = chapter_data
                
        if type == 'assessment':
            if not user_video.questions_data.get('quiz_completed') == True:
                user_video.questions_data['quiz_completed'] = True
                user_video.quizzes_attempted += 1

        user_video.save()
        
        return Response({"data": "Quiz marked as complete"}, status=status.HTTP_200_OK)
    
class Highlight(APIView):    
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        logger.info(f"Entered Highlight API {datetime.now()}")
        user_id = request.user.id
        video_id = request.query_params.get('video_id', None)
        highlight_data = request.data
        if not user_id or not video_id or not highlight_data:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        timestamp = highlight_data.get('timestamp', None)
        logger.info(f"Timestamp {timestamp}")

        if not timestamp:
            return Response({"error": "Timestamp not found"}, status=status.HTTP_400_BAD_REQUEST)
        user_video = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_id)
        logger.info(f"User Video {user_video}")
        if not user_video:
            return Response({"error": "Invalid user or video ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            fetched_highlight = user_video.highlights[str(timestamp)]
            return Response({"data": fetched_highlight}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f"Timestamp {timestamp} not found. {e}")
            pass
        
        timestamped_transcript = user_video.video_id.timestamped_transcript
        texts, exact_text = fetch_relevant_text(timestamped_transcript, timestamp)
        response = extract_summary(timestamped_transcript, exact_text, texts)
        user_highlights = user_video.highlights

        highlight_id = generate_6_digit_hex_id()
        user_highlights = user_video.highlights
        user_highlights[timestamp]={
            "highlight_id": highlight_id,
            "timestamp": timestamp,
            "start_time": timestamp,
            "summary": response['summary'],
            "key_points": response['key_points'],
            "duration": 10
        }
        user_video.highlights = user_highlights
        user_video.save()
        return Response({"data": user_highlights[timestamp]}, status=status.HTTP_200_OK)
    
    def get(self, request, format=None):
        user_id = "2"
        video_id = request.query_params.get('video_id', None)
        if not user_id or not video_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_video = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_id)
        if not user_video:
            return Response({"error": "Invalid user or video ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"data": user_video.highlights}, status=status.HTTP_200_OK)
                                               
class UserHighlights(APIView):
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):
        user_id = request.user.id
        if not user_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        user_highlights = UserConsumedVideos.objects.filter(user_id=user_id).values('video_id', 'highlights')
        return Response({"data": user_highlights}, status=status.HTTP_200_OK)
    
class UserData(APIView):
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def post(self, request, format=None):
        data = request.data
        user_id = request.user.id
        userModel = User.objects.get(id=user_id)
        if not user_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_data = UserProfile.objects.get(user_id=userModel)
            if not user_data:
                user_data = UserProfile(user_id=userModel)
                user_data.save()
            for key, value in data.items():
                if key == 'name' or key == 'email' or key == 'age' or key == 'languages' or key == 'gender' or key == 'phone' or key == 'city' or key == 'country' or key == 'interests': 
                    if hasattr(user_data, key):
                        setattr(user_data, key, value)
            user_data.save()
        except Exception as e:
            logger.error(f"Error in fetching user data or creating new user {e}")
            return Response({"error": "Error in fetching user data or creating new user"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"data": "User data updated"}, status=status.HTTP_200_OK)
        
        
    def get(self, request, format=None):
        user_id = request.user.id
        if not user_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        userModel = User.objects.get(id=user_id)
        if not UserProfile.objects.filter(user_id=userModel).exists():
            return Response({"error": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)
                
        user_profile = UserProfile.objects.get(user_id=userModel)

        data = {
            "name": user_profile.name,
            "email": user_profile.email,
            "age": user_profile.age,
            "gender": user_profile.gender,
            "languages": user_profile.languages,
            "phone": user_profile.phone,
            "city": user_profile.city,
            "country": user_profile.country,
            "interests": user_profile.interests,
            "telegram_link":f"tg://resolve?domain=@{settings.AI_BOT_USERNAME}&start={user_profile.otp}--{settings.DEFAULT_AGENT_CONFIG_NAME}"
        }
        
        return Response({"data": data}, status=status.HTTP_200_OK)
        
    
class DashboardData(APIView):
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
        
    def get(self, request, format=None):
        user_id = request.user.id
        if not user_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
        userModel = User.objects.get(id=user_id)
        if not UserProfile.objects.filter(user_id=userModel).exists():
            return Response({"error": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        number_of_vids_watched = UserConsumedVideos.objects.filter(user_id=user_id).count()
        time_spent_sum = UserConsumedVideos.objects.filter(user_id=user_id).aggregate(total_time_spent=Sum('time_spent'))['total_time_spent']
        time_spent_string = ""
        hours = time_spent_sum // 3600
        minutes = (time_spent_sum % 3600) // 60
        if hours > 0:
            time_spent_string = f"{hours} hrs {minutes} mins"
        else:
            time_spent_string = f"{minutes} mins"
        
        user_profile = UserProfile.objects.get(user_id=userModel)
        daily_streak = user_profile.daily_streak
        longest_streak = user_profile.longest_streak
        quizzes_attempted = UserConsumedVideos.objects.filter(user_id=user_id).aggregate(total_quizzes_attempted=Sum('quizzes_attempted'))['total_quizzes_attempted']
        total_chat_count = UserConsumedVideos.objects.filter(user_id=user_id).aggregate(total_chat_count=Sum('chat_count'))['total_chat_count']
        total_points_scored = UserConsumedVideos.objects.filter(user_id=user_id).aggregate(total_points_scored=Sum('total_points_scored'))['total_points_scored']
        data ={
            "videos_watched": number_of_vids_watched,
            "daily_streak": daily_streak,
            "longest_streak": longest_streak,
            "time_spent": time_spent_string,
            "quizzes_attempted": quizzes_attempted,
            "chat_count": total_chat_count,
            "total_points_scored": total_points_scored
        }
        
        return Response({"data": data}, status=status.HTTP_200_OK)
    

class ChatHistory(APIView):
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):
        user_id = request.user.id
        video_id = request.query_params.get('video_id', None)
        if not video_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        if not UserConsumedVideos.objects.filter(user_id=user_id, video_id=video_id).exists():
            return Response({"error": "User video item does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        user_data = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_id)
        chat_history = user_data.chat_history
        return Response({"data": chat_history}, status=status.HTTP_200_OK)
    
class VideosWatchedHistory(APIView):
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):
        user_id = request.user.id
        if not user_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        video_history = UserConsumedVideos.objects.filter(user_id=user_id)
        video_history_list = []
        for video in video_history:
            video_history_list.append({
                "video_id": video.video_id.video_id,
                "title": video.video_id.title,
                "url": video.video_id.url,
                "duration": format_duration(video.video_id.duration),
                "updated_at": format_updated_at(video.updated_at),
                "thumbnail": video.video_id.thumbnail,
            })
        return Response({"data": video_history_list}, status=status.HTTP_200_OK)