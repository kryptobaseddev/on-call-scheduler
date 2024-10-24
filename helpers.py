import re

def format_phone_number(phone_number):
    if not phone_number:
        return ''
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone_number))
    # Check if we have a 10-digit number
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    else:
        # Return original if not 10 digits
        return phone_number