from reports.models import UserCourseReport,DailyAggregation

class UserCourseReportRepository:
    @staticmethod
    def get_or_create(user_id, course, defaults):
        report, created = UserCourseReport.objects.get_or_create(
            user_id=user_id,
            course=course,
            defaults=defaults
        )
        
        if not created :
            # Update the existing report by adding incoming values to existing values
            for key, value in defaults.items():
                current_value = getattr(report, key, 0)  # Get current value or default to 0
                setattr(report, key, current_value + value)  # Add incoming value to current value
            report.save()
        
        return report, created
    
    def get_reports_data():
        return UserCourseReport.objects.all()
    
    
    
class DailyAggregationRepository:
    @staticmethod
    def get_or_create_daily_aggregation(user_id,course_id, date, type_of_aggregation, time_spent):
        aggregation, created = DailyAggregation.objects.get_or_create(
            user_id=user_id,
            course_id=course_id,
            date=date,
            type_of_aggregation=type_of_aggregation,
            defaults={'time_spent': time_spent}
        )
        
        if not created:
            # Update the existing record by adding the new time spent
            aggregation.time_spent += time_spent
            aggregation.save()
        
        return aggregation

    
    @staticmethod
    def get_aggregations_by_user_daywise(user_id,date,course_id):
        # Fetch all daily aggregations for the specified user, grouped by date
        return DailyAggregation.objects.filter(user_id=user_id,date=date,course_id=course_id)