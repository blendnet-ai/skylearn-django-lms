from abc import ABC, abstractmethod
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags
import requests
from typing import Dict, List
import logging
import asyncio
import aiohttp
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    """Raised when a service's rate limit is exceeded"""
    pass

class NotificationProvider(ABC):
    @abstractmethod
    def send_message(self, messages_data: List[Dict]):
        """Send messages using the provided message data"""
        pass

class EmailNotificationProvider(NotificationProvider):
    # Setting batch size to 550 to stay safely under the 600/minute limit
    BATCH_SIZE = 550  # emails per minute rate limit is 600

    def send_message(self, messages_data: List[Dict]):
        """Send messages in parallel using asyncio and return results"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run our async code in the current loop
        results = loop.run_until_complete(self._send_messages_async(messages_data))
        return results

    async def _send_messages_async(self, messages_data: List[Dict]):
        """Async method to send multiple messages in parallel"""
        async with aiohttp.ClientSession() as session:
            final_results = []
            retry_messages = []
            
            # Process initial batches
            for i in range(0, len(messages_data), self.BATCH_SIZE):
                batch = messages_data[i:i + self.BATCH_SIZE]
                tasks = [self._send_single_email_async(session, message) for message in batch]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for message, result in zip(batch, results):
                    if isinstance(result, dict) and result.get('rate_limited'):
                        retry_messages.append(message)
                    else:
                        final_results.append(result if isinstance(result, dict) else {
                            'success': False,
                            'error': str(result)
                        })
                
                if i + self.BATCH_SIZE < len(messages_data):
                    await asyncio.sleep(60)  # Wait 60 seconds before next batch
            
            # Process retry messages if any
            while retry_messages:
                logger.info(f"Retrying {len(retry_messages)} rate-limited email messages")
                await asyncio.sleep(60)  # Wait before retrying
                
                retry_batch = retry_messages[:self.BATCH_SIZE]
                retry_messages = retry_messages[self.BATCH_SIZE:]
                
                tasks = [self._send_single_email_async(session, message) for message in retry_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for message, result in zip(retry_batch, results):
                    if isinstance(result, dict) and result.get('rate_limited'):
                        retry_messages.append(message)  # Add back to retry queue if still rate limited
                    else:
                        final_results.append(result if isinstance(result, dict) else {
                            'success': False,
                            'error': str(result)
                        })
            
            return final_results

    async def _send_single_email_async(self, session, data: Dict) -> Dict:
        """Send a single email asynchronously"""
        try:
            user_variables = data.get('variables', {})
            subject = user_variables.get('email_subject', 'Notification')
            html_content = data['message']
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[data['recipient']]
            )
            email.attach_alternative(html_content, "text/html")
            await asyncio.to_thread(email.send, fail_silently=False)
            
            return {
                'record_id': data.get('record_id'),
                'success': True,
                'error': ''
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(indicator in error_msg for indicator in ["rate limit", "too many requests", "429"]):
                return {
                    'record_id': data.get('record_id'),
                    'rate_limited': True,
                    'success': False,
                    'error': str(e)
                }
                
            return {
                'record_id': data.get('record_id'),
                'success': False,
                'error': str(e)
            }

class TelegramNotificationProvider(NotificationProvider):
    # Setting batch size to 25 to stay under the 30 messages/second limit
    BATCH_SIZE = 25  # messages per second rate limit is 30

    def send_message(self, messages_data: List[Dict]):
        """Send messages in parallel using asyncio and return results"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run our async code in the current loop
        results = loop.run_until_complete(self._send_messages_async(messages_data))
        return results

    async def _send_messages_async(self, messages_data: List[Dict]):
        """Async method to send multiple messages in parallel"""
        async with aiohttp.ClientSession() as session:
            final_results = []
            retry_messages = []
            
            # Process initial batches
            for i in range(0, len(messages_data), self.BATCH_SIZE):
                batch = messages_data[i:i + self.BATCH_SIZE]
                tasks = [self._send_single_message_async(session, message) for message in batch]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for message, result in zip(batch, results):
                    if isinstance(result, dict) and result.get('rate_limited'):
                        retry_messages.append(message)
                    else:
                        final_results.append(result if isinstance(result, dict) else {
                            'success': False,
                            'error': str(result)
                        })
                
                if i + self.BATCH_SIZE < len(messages_data):
                    await asyncio.sleep(1)  # Wait 1 second before next batch
            
            # Process retry messages if any
            while retry_messages:
                logger.info(f"Retrying {len(retry_messages)} rate-limited Telegram messages")
                await asyncio.sleep(2)  # Wait before retrying
                
                retry_batch = retry_messages[:self.BATCH_SIZE]
                retry_messages = retry_messages[self.BATCH_SIZE:]
                
                tasks = [self._send_single_message_async(session, message) for message in retry_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for message, result in zip(retry_batch, results):
                    if isinstance(result, dict) and result.get('rate_limited'):
                        retry_messages.append(message)  # Add back to retry queue if still rate limited
                    else:
                        final_results.append(result if isinstance(result, dict) else {
                            'success': False,
                            'error': str(result)
                        })
            
            return final_results

    async def _send_single_message_async(self, session, data: Dict) -> Dict:
        """Send a single Telegram message asynchronously"""
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': data['recipient'],
                'text': data['message'],
                'parse_mode': 'HTML'
            }
            
            async with session.post(url, data=payload) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    return {
                        'record_id': data.get('record_id'),
                        'rate_limited': True,
                        'retry_after': retry_after,
                        'success': False,
                        'error': f"Rate limit exceeded. Retry after {retry_after} seconds"
                    }
                
                response.raise_for_status()
                
                return {
                    'record_id': data.get('record_id'),
                    'success': True,
                    'error': ''
                }
            
        except Exception as e:
            return {
                'record_id': data.get('record_id'),
                'success': False,
                'error': str(e)
            }