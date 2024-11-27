import json 
from channels.generic.websocket import WebsocketConsumer 

from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
from .utility import convert_timestamp, chat_prompt_template, generate_12_digit_random_id
from .models import UserConsumedVideos
from custom_auth.authentication import FirebaseAuthentication

def call_gpt(user_input, transcript, conversational_history, title, timestamp):
	llm = OpenAIService()
	messages = [
	{'role': 'system', 'content': chat_prompt_template(conversational_history, transcript, title, timestamp)},
	{'role': 'user', 'content': user_input}
	]
	completion = llm.get_completion_from_messages(messages)
	return completion

def response_handler(user_input, user_id, video_id, timestamp):
	user_data = UserConsumedVideos.objects.get(user_id=user_id, video_id=video_id)
	conversational_history = user_data.chat_history
	user_message_saver = {
		"message" : user_input,
		"id" : generate_12_digit_random_id(),
		"type": "user"
	}
	transcript = user_data.video_id.timestamped_transcript

	title = user_data.video_id.title
	response = call_gpt(user_input, transcript, conversational_history, title, timestamp)
	response = json.loads(response)['answer']
	bot_message_saver = {
		"message" : response,
		"id" : generate_12_digit_random_id(),
		"type": "bot"
	}
	conversational_history.append(user_message_saver)
	conversational_history.append(bot_message_saver)
	user_data.chat_history = conversational_history
	user_data.chat_count += 1
	user_data.save()
	return response


class SocketClass(WebsocketConsumer): 
        
	def connect(self): 
		self.accept()

	def disconnect(self, close_code): 
		self.close() 

	def receive(self, text_data): 
		text_data_json = json.loads(text_data) 
		user_input = text_data_json['message'] 
		video_id = text_data_json['video_id']
		token = text_data_json['token']
		timestamp = text_data_json.get('timestamp', None)
		timestamp_converted = convert_timestamp(timestamp)
		user,_ = FirebaseAuthentication.authenticate_token(token)
		user_id = user.id
		try: 
			response = response_handler(user_input, user_id, video_id, timestamp_converted)
		except Exception as e: 
			response = "Could not process the input. Please try again."
		self.send(text_data=json.dumps({
			'message': response
		}))
