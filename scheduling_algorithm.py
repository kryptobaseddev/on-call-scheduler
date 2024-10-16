from datetime import datetime, timedelta
from models import User, Schedule, Team, TimeOffRequest
from sqlalchemy import func
import random

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
    
    # Get time off requests for the period
    time_off_requests = TimeOffRequest.query.filter(
        TimeOffRequest.user_id.in_([user.id for user in users]),
        TimeOffRequest.start_date <= end_date,
        TimeOffRequest.end_date >= start_date,
        TimeOffRequest.status == 'Approved'
    ).all()

    # Create a dictionary of unavailable dates for each user
    unavailable_dates = {user.id: set() for user in users}
    for request in time_off_requests:
        current_date = max(request.start_date, start_date)
        end = min(request.end_date, end_date)
        while current_date <= end:
            unavailable_dates[request.user_id].add(current_date)
            current_date += timedelta(days=1)

    # Sort users by their current on-call hours (ascending)
    sorted_users = sorted(users, key=lambda u: user_hours[u.id])
    
    schedules = []
    current_date = start_date
    rotation_index = 0
    
    while current_date <= end_date:
        # Filter out unavailable users for the current date
        available_users = [user for user in sorted_users if current_date not in unavailable_dates[user.id]]
        
        if not available_users:
            # If no users are available, skip this day
            current_date += timedelta(days=1)
            continue
        
        # Use rotation system to ensure fairness
        selected_user = available_users[rotation_index % len(available_users)]
        
        # Determine the length of the block schedule (aiming for 3-5 day blocks)
        block_length = random.randint(3, 5)
        block_end = min(current_date + timedelta(days=block_length), end_date)
        
        # Check if the selected user is available for the entire block
        while any(date in unavailable_dates[selected_user.id] for date in [current_date + timedelta(days=i) for i in range(block_length)]):
            block_length -= 1
            if block_length < 3:
                # If we can't find a 3-day block, move to the next user
                rotation_index += 1
                selected_user = available_users[rotation_index % len(available_users)]
                block_length = random.randint(3, 5)
            block_end = min(current_date + timedelta(days=block_length), end_date)
        
        # Create a new schedule block
        new_schedule = Schedule(
            user_id=selected_user.id,
            start_time=current_date,
            end_time=block_end
        )
        schedules.append(new_schedule)
        
        # Update the user's on-call hours
        user_hours[selected_user.id] += (block_end - current_date).total_seconds() / 3600
        
        # Move the current date to the end of the block
        current_date = block_end + timedelta(days=1)
        
        # Move to the next user in the rotation
        rotation_index += 1
        
        # Re-sort the users based on updated hours
        sorted_users = sorted(sorted_users, key=lambda u: user_hours[u.id])
    
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
