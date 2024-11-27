from django.urls import path
from .views import ProcessURL, HandlePrompts, VideoList, VideoData, SubmitQuestionResponse,UserData, Highlight,UserHighlights, MarkChapterComplete, MarkQuizComplete, VideosWatchedHistory, ChatHistory, DashboardData

urlpatterns = [
    path('process-youtube-url', ProcessURL.as_view(), name='process_youtube_url'),
    path('handle-prompts', HandlePrompts.as_view(), name='handle_prompts'),
    path('video-list', VideoList.as_view(), name='video_list'),
    path('video-data',VideoData.as_view(), name='video_data'),
    path('submit-question-response',SubmitQuestionResponse.as_view(), name='submit_question_response'),
    path('mark-chapter-complete',MarkChapterComplete.as_view(), name='mark_chapter_complete'),
    path('mark-quiz-complete',MarkQuizComplete.as_view(), name='mark_quiz_complete'),
    path('highlight',Highlight.as_view(), name='highlight'),
    path('highlights',UserHighlights.as_view(), name='highlights'),
    path('chat-history', ChatHistory.as_view(), name='chat_history'),
    path('videos-watched-history', VideosWatchedHistory.as_view(), name='videos_watched_history'),
    path('user-data',UserData.as_view(), name='user_data'),
    path('dashboard-data',DashboardData.as_view(), name='dashboard_data'),
]

