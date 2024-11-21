from meetings.models import MeetingSeries
from meetings.repositories import MeetingRepository, MeetingSeriesRepository
from dateutil.rrule import DAILY, WEEKLY, MONTHLY
from dateutil.rrule import rrule
from django.utils import timezone

from meetings.services.msteams import MSTeamsConferencePlatformService
import logging

logger = logging.getLogger(__name__)


class MeetingSeriesUsecase:
    class WeekdayScheduleNotSet(Exception):
        def __init__(self):
            super().__init__("`weekday_schedule` is required for weekly recurrence")

    class InvalidWeekdaySchedule(Exception):
        def __init__(self):
            super().__init__(
                "`weekday_schedule` must be a list of 7 boolean values (one for each day of the week)"
            )

    class MonthlyDayNotSet(Exception):
        def __init__(self):
            super().__init__("`monthly_day` is required for monthly recurrence")

    class NoRecurringDatesFound(Exception):
        def __init__(self):
            super().__init__("The provided configuration results in no meeting dates")

    class StartDateInPast(Exception):
        def __init__(self):
            super().__init__("Start date must be in the future")

    class EndDateSmallerThanStartDate(Exception):
        def __init__(self):
            super().__init__("End date must be greater than start date")

    @staticmethod
    def renew_meeting_series(
        meeting_series,
        title,
        start_time,
        start_date,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
    ):
        # If recurrence type is changing, we not only need to update the meeting series, but also delete previous meeting occurrences and create new ones
        # Do the same in case of start time and end date changing (for simplicity)
        if (
            recurrence_type != meeting_series.recurrence_type
            or start_time != meeting_series.start_time
            or end_date != meeting_series.end_date
        ):
            # Get old meetings before creating new ones
            old_meetings = list(
                MeetingRepository.get_meetings_by_series_id(meeting_series.id)
            )

            # First create new meetings
            MeetingSeriesUsecase.create_or_update_meeting_series_and_create_occurrences(
                title,
                start_time,
                start_date,
                duration,
                end_date,
                recurrence_type,
                weekday_schedule,
                monthly_day,
                meeting_series,
            )

            # Delete the old meetings that we captured before creating new ones
            for meeting in old_meetings:
                meeting.delete()

        # If not, then only update the meeting series
        else:
            MeetingSeriesRepository.update_meeting_series(
                meeting_series,
                title,
                start_time,
                duration,
                end_date,
                recurrence_type,
                (
                    weekday_schedule
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
                    else None
                ),
                (
                    monthly_day
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
                    else None
                ),
            )

    @staticmethod
    def create_or_update_meeting_series_and_create_occurrences(
        title,
        start_time,
        start_date,
        duration,
        end_date,
        recurrence_type,
        weekday_schedule,
        monthly_day,
        meeting_series=None,
    ):

        if start_date < timezone.now().date():
            raise MeetingSeriesUsecase.StartDateInPast()
        if start_date > end_date:
            raise MeetingSeriesUsecase.EndDateSmallerThanStartDate()

        if (
            recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
            and weekday_schedule is None
        ):
            raise MeetingSeriesUsecase.WeekdayScheduleNotSet()
        elif len(weekday_schedule) != 7 or not all(
            isinstance(element, bool) for element in weekday_schedule
        ):
            raise MeetingSeriesUsecase.InvalidWeekdaySchedule()

        if (
            recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
            and monthly_day is None
        ):
            raise MeetingSeriesUsecase.MonthlyDayNotSet()

        # Generate meeting dates based on recurrence type
        if recurrence_type == MeetingSeries.RECURRENCE_TYPE_NOT_REPEATING:
            recurring_dates = [start_date]
        else:
            # Set up recurrence rules based on type
            if recurrence_type == MeetingSeries.RECURRENCE_TYPE_DAILY:
                freq = DAILY

                recurring_dates = list(
                    rrule(
                        freq=freq,
                        dtstart=start_date,
                        until=end_date,
                    )
                )
            elif recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY:
                freq = WEEKLY
                # Convert weekday_schedule booleans to weekday numbers (0-6)
                byweekday = [i for i, enabled in enumerate(weekday_schedule) if enabled]

                if len(byweekday) == 0:
                    recurring_dates = []
                else:
                    recurring_dates = list(
                        rrule(
                            freq=freq,
                            dtstart=start_date,
                            until=end_date,
                            byweekday=byweekday,
                        )
                    )
            elif recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY:
                freq = MONTHLY
                bymonthday = monthly_day

                recurring_dates = list(
                    rrule(
                        freq=freq,
                        dtstart=start_date,
                        until=end_date,
                        bymonthday=bymonthday,
                    )
                )

        if recurring_dates == []:
            raise MeetingSeriesUsecase.NoRecurringDatesFound()

        if meeting_series is None:
            meeting_series = MeetingSeriesRepository.create_meeting_series(
                title,
                start_time,
                start_date,
                duration,
                end_date,
                recurrence_type,
                (
                    weekday_schedule
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
                    else None
                ),
                (
                    monthly_day
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
                    else None
                ),
            )
        else:
            MeetingSeriesRepository.update_meeting_series(
                meeting_series,
                title,
                start_time,
                duration,
                end_date,
                recurrence_type,
                (
                    weekday_schedule
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_WEEKLY
                    else None
                ),
                (
                    monthly_day
                    if recurrence_type == MeetingSeries.RECURRENCE_TYPE_MONTHLY
                    else None
                ),
            )

        # Create meeting instances for each date
        for meeting_date in recurring_dates:
            MeetingRepository.create_meeting(meeting_series, meeting_date, "")

        return meeting_series

    @staticmethod
    def delete_meeting_series(id):
        meeting_series = MeetingSeriesRepository.get_meeting_series_by_id(id)
        MeetingRepository.get_meetings_by_series_id(id).delete()
        meeting_series.delete()


class MeetingUsecase:
    @staticmethod
    def create_teams_meeting(meeting_id: int) -> None:
        """
        Creates a Teams meeting for a given meeting ID
        """
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)
        if not meeting or not meeting.series.presenter_details:
            return

        try:
            teams_service = MSTeamsConferencePlatformService()

            # Create Teams meeting using model properties
            meeting_details = teams_service.create_meeting(
                presenter=meeting.series.presenter_details,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                subject=meeting.title,
            )

            # Update meeting with Teams details
            meeting.link = meeting_details.join_url
            meeting.conference_metadata = meeting_details.all_details
            meeting.conference_id = meeting_details.id
            meeting.save()

        except Exception as e:
            logger.error(
                f"Failed to create Teams meeting for meeting ID {meeting_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_teams_meeting(meeting_id: int) -> None:
        """
        Deletes a Teams meeting for a given meeting ID
        """
        meeting = MeetingRepository.get_meeting_by_id(meeting_id)
        if not meeting or not meeting.conference_id:
            return

        try:
            teams_service = MSTeamsConferencePlatformService()
            teams_service.delete_meeting(meeting.conference_id)

            # Clear meeting conference details
            meeting.link = ""
            meeting.conference_metadata = None
            meeting.conference_id = None
            meeting.save()

        except Exception as e:
            logger.error(
                f"Failed to delete Teams meeting for meeting ID {meeting_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_meeting(id, start_time_override, duration_override, start_date):
        meeting = MeetingRepository.get_meeting_by_id(id)
        meeting.start_time_override = start_time_override
        meeting.duration_override = duration_override
        meeting.start_date = start_date
        meeting.save()

    @staticmethod
    def delete_meeting(id):
        meeting = MeetingRepository.get_meeting_by_id(id)
        meeting.delete()

    @staticmethod
    def get_meetings_of_series_in_period(series_id, start_date, end_date):
        meetings = MeetingRepository.get_meetings_of_series_in_period(
            series_id, start_date, end_date
        )
        meetings_data = []
        for meeting in meetings:
            meetings_data.append(
                {
                    "meeting_id": meeting.id,
                    "series_id": meeting.series_id,
                    "start_date": meeting.start_date,
                    "start_time": (
                        meeting.start_time_override
                        if meeting.start_time_override
                        else meeting.series.start_time
                    ),
                    "duration": (
                        meeting.duration_override
                        if meeting.duration_override
                        else meeting.series.duration
                    ),
                    "link": meeting.link,
                }
            )
        return meetings_data
