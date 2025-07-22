from datetime import datetime

def convert_date(date_str):
    """
    Convert a date string (e.g., 'dd.mm.yyyy' or 'yyyy-mm-dd') to a Python datetime.date object.
    Handles multiple formats.
    """
    formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")
