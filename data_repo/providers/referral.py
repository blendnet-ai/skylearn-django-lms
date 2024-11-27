from django.conf import settings

class ReferralProvider:
    @staticmethod
    def get_referral_url():
        """Returns the referral URL"""
        URL = settings.REFERRAL_URL
        return URL

    @staticmethod
    def get_referral_message():
        """Returns the referral message"""
        message = """ELEVATE YOUR COMMUNICATION GAME WITH COMUNIQA!\nAce your IELTS and interviews with our AI-powered communication coach.\nPractice with COMUNIQA to get comprehensive and actionable feedback on your speaking skills, and improve your overall communication.\nDownload Now!\n"""
        return message
