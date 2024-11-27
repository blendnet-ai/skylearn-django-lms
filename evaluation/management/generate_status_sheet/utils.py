from collections import defaultdict
from datetime import timedelta, timezone
from typing import Dict, List, Optional

from evaluation.models import AssessmentAttempt


class Utils:
    @staticmethod
    def get_most_recent_completed_attempts(
        attempts: List[AssessmentAttempt],
    ) -> Optional[Dict[str, AssessmentAttempt]]:
        if not attempts:
            return None, 0

        most_recent_attempts = {}
        attempt_counts = defaultdict(int)

        for attempt in attempts:
            attempt_counts[attempt.type] += 1

            if attempt.status == int(AssessmentAttempt.Status.COMPLETED):
                attempt_type = attempt.type
                if attempt_type not in most_recent_attempts:
                    most_recent_attempts[attempt_type] = attempt

        return most_recent_attempts, dict(attempt_counts)

    @staticmethod
    def format_datetime(datetime):
        ist_offset = timedelta(hours=5, minutes=30)
        ist = timezone(ist_offset)

        if datetime:
            if datetime.tzinfo is None:
                datetime = datetime.replace(tzinfo=timezone.utc)
            datetime_ist = datetime.astimezone(ist)
            return datetime_ist.strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            return None
