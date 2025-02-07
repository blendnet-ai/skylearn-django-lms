from datetime import datetime, timedelta

def get_feedback_intervals(start_date, end_date, interval_days=7):
    """
    Generate intervals between start_date and end_date with given gap in days
    Returns list of (start_date, end_date) tuples
    """
    intervals = []
    current_date = start_date
    
    while current_date < end_date:
        interval_end = min(current_date + timedelta(days=interval_days), end_date)
        intervals.append((current_date, interval_end))
        current_date = interval_end
    
    return intervals