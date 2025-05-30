# climbing_app_backend/app/services/stats_service.py
from app.models.models import db, User, UserAttempt, ClimbingBlock
from app.utils.difficulty import get_grade_numerical_value, get_grade_from_numerical_value
from sqlalchemy import func

def get_user_stats(user_id):
    user = User.query.get(user_id)
    if not user:
        return None # Or raise error

    # Query for all completed attempts by the user, joining with blocks for difficulty
    # This initial query helps get all difficulties for max grade calculation easily
    completed_attempts_with_difficulty_info = db.session.query(
        UserAttempt.block_id, # Keep for potential future use if needed
        ClimbingBlock.difficulty
    ).join(ClimbingBlock, ClimbingBlock.id == UserAttempt.block_id)\
     .filter(UserAttempt.user_id == user_id)\
     .filter(UserAttempt.status == 'completed').all()

    if not completed_attempts_with_difficulty_info:
        return {
            "user_id": user_id,
            "username": user.username,
            "total_completed_unique_climbs": 0,
            "highest_grade_completed": "N/A",
            "completed_grade_distribution": {}
        }

    # Total completed unique climbs
    total_completed_unique_climbs = db.session.query(func.count(func.distinct(UserAttempt.block_id)))\
        .filter(UserAttempt.user_id == user_id)\
        .filter(UserAttempt.status == 'completed').scalar() or 0


    # Highest grade completed
    highest_grade_numerical = -1
    for attempt_info in completed_attempts_with_difficulty_info:
        numerical_val = get_grade_numerical_value(attempt_info.difficulty)
        if numerical_val > highest_grade_numerical:
            highest_grade_numerical = numerical_val

    highest_grade_completed_str = get_grade_from_numerical_value(highest_grade_numerical) if highest_grade_numerical > -1 else "N/A"

    # Distribution of completed unique climbs by difficulty
    grade_distribution = {}
    # Query for distinct block_id and their difficulties for completed attempts
    # This ensures each block is counted once for its difficulty grade in the distribution.
    unique_completed_blocks_difficulty = db.session.query(
        ClimbingBlock.difficulty
    ).join(UserAttempt, UserAttempt.block_id == ClimbingBlock.id)\
     .filter(UserAttempt.user_id == user_id)\
     .filter(UserAttempt.status == 'completed')\
     .distinct(UserAttempt.block_id, ClimbingBlock.difficulty).all() # Distinct on (block_id, difficulty) pairs
                                                                    # then just select difficulty.
                                                                    # Note: distinct() on specific columns might be dialect specific.
                                                                    # A more portable way is to group by difficulty after selecting distinct blocks.

    # A more portable way for grade distribution of unique climbs:
    # First, get all (block_id, difficulty) pairs for completed climbs
    completed_block_difficulties = db.session.query(
            UserAttempt.block_id,
            ClimbingBlock.difficulty
        ).join(ClimbingBlock, ClimbingBlock.id == UserAttempt.block_id)\
         .filter(UserAttempt.user_id == user_id)\
         .filter(UserAttempt.status == 'completed').all()

    # Then, process in Python to count unique blocks per difficulty
    # Store unique block_ids for each difficulty to ensure a block isn't double-counted if logged multiple times
    # (though status 'completed' should ideally be unique per user/block if business logic implies one 'completion')
    # However, the prompt implies "unique climbs", so a block of a certain difficulty counts once.

    # Get unique block_ids and their difficulties
    unique_climbs = {} # block_id -> difficulty
    for attempt_info in completed_attempts_with_difficulty_info:
        if attempt_info.block_id not in unique_climbs:
            unique_climbs[attempt_info.block_id] = attempt_info.difficulty

    for difficulty_str in unique_climbs.values():
        grade_distribution[difficulty_str] = grade_distribution.get(difficulty_str, 0) + 1

    return {
        "user_id": user_id,
        "username": user.username,
        "total_completed_unique_climbs": total_completed_unique_climbs,
        "highest_grade_completed": highest_grade_completed_str,
        "completed_grade_distribution": grade_distribution
    }
