from datetime import datetime, timedelta
from models import User, Schedule, Team
from sqlalchemy import func

def generate_advanced_schedule(team_id, start_date, end_date):
    """
    Generate an advanced schedule for a team considering various factors.
    
    :param team_id: ID of the team to generate the schedule for
    :param start_date: Start date of the scheduling period
    :param end_date: End date of the scheduling period
    :return: List of generated schedules
    """
    team = Team.query.get(team_id)
    users = User.query.filter_by(team_id=team_id).all()
    
    if not users:
        return []
    
    # Get the current on-call hours for each user
    user_hours = {user.id: get_user_on_call_hours(user.id, start_date, end_date) for user in users}
    
    # Sort users by their current on-call hours (ascending)
    sorted_users = sorted(users, key=lambda u: user_hours[u.id])
    
    schedules = []
    current_date = start_date
    
    while current_date <= end_date:
        # Select the user with the least on-call hours
        selected_user = sorted_users[0]
        
        # Create a new schedule
        new_schedule = Schedule(
            user_id=selected_user.id,
            start_time=current_date,
            end_time=current_date + timedelta(days=1)
        )
        schedules.append(new_schedule)
        
        # Update the user's on-call hours
        user_hours[selected_user.id] += 24
        
        # Re-sort the users based on updated hours
        sorted_users = sorted(sorted_users, key=lambda u: user_hours[u.id])
        
        current_date += timedelta(days=1)
    
    return schedules

def get_user_on_call_hours(user_id, start_date, end_date):
    """
    Calculate the total on-call hours for a user within a given date range.
    
    :param user_id: ID of the user
    :param start_date: Start date of the range
    :param end_date: End date of the range
    :return: Total on-call hours
    """
    schedules = Schedule.query.filter(
        Schedule.user_id == user_id,
        Schedule.start_time >= start_date,
        Schedule.end_time <= end_date
    ).all()
    
    total_hours = sum((s.end_time - s.start_time).total_seconds() / 3600 for s in schedules)
    return total_hours
