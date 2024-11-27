import pytz

class TimeZone:

    @staticmethod
    def change_timezone(time):
        indian_timezone = pytz.timezone('Asia/Kolkata')
        return time.astimezone(indian_timezone)