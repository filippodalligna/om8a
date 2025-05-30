# climbing_app_backend/app/utils/difficulty.py

# Basic V-scale mapping. This can be expanded or made more complex.
# Maps grade string to a numerical value for sorting/comparison.
# Higher number means harder grade.
V_SCALE_MAPPING = {
    "VB": 0, "V0": 1, "V1": 2, "V2": 3, "V3": 4, "V4": 5,
    "V5": 6, "V6": 7, "V7": 8, "V8": 9, "V9": 10,
    "V10": 11, "V11": 12, "V12": 13, "V13": 14,
    "V14": 15, "V15": 16, "V16": 17, "V17": 18 # Hypothetical extension
    # Add other scales or conversions if necessary later (e.g., Fontainebleau)
}

# Reverse mapping to get grade string from numerical value
V_SCALE_REVERSE_MAPPING = {v: k for k, v in V_SCALE_MAPPING.items()}

def get_grade_numerical_value(grade_str):
    if not grade_str: # Handle None or empty string
        return -1
    return V_SCALE_MAPPING.get(grade_str.upper(), -1) # Return -1 for unknown/unsortable grades

def get_grade_from_numerical_value(grade_val):
    return V_SCALE_REVERSE_MAPPING.get(grade_val, "Unknown")
