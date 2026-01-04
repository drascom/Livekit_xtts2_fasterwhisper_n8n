"""Formatting utilities for TTS and speech-friendly output."""

import re
from datetime import datetime


def strip_markdown_for_tts(text: str) -> str:
    """Strip markdown formatting that TTS would read aloud.

    Removes asterisks, underscores, and other markdown syntax while preserving
    the actual content for clean TTS output.
    """
    if not text:
        return text

    # Remove bold/italic markers: **text**, *text*, __text__, _text_
    # Handle bold first (** or __), then italic (* or _)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'__(.+?)__', r'\1', text)       # __bold__
    text = re.sub(r'\*(.+?)\*', r'\1', text)       # *italic*
    text = re.sub(r'_(.+?)_', r'\1', text)         # _italic_

    # Remove inline code backticks
    text = re.sub(r'`(.+?)`', r'\1', text)

    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove any remaining standalone asterisks or underscores used as emphasis
    # (in case of unclosed markdown)
    text = re.sub(r'(?<!\w)\*(?!\w)', '', text)  # standalone *
    text = re.sub(r'(?<!\w)_(?!\w)', '', text)   # standalone _

    # Convert score patterns (30-23) to "30 to 23" so TTS doesn't say "minus"
    text = re.sub(r'(\d+)-(\d+)', r'\1 to \2', text)

    return text


def number_to_ordinal_word(n: int) -> str:
    """Convert a number to its ordinal word form (e.g., 1 -> 'first', 7 -> 'seventh')."""
    # Special cases for 1-31 (days of the month)
    ordinals = {
        1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth',
        6: 'sixth', 7: 'seventh', 8: 'eighth', 9: 'ninth', 10: 'tenth',
        11: 'eleventh', 12: 'twelfth', 13: 'thirteenth', 14: 'fourteenth',
        15: 'fifteenth', 16: 'sixteenth', 17: 'seventeenth', 18: 'eighteenth',
        19: 'nineteenth', 20: 'twentieth', 21: 'twenty-first', 22: 'twenty-second',
        23: 'twenty-third', 24: 'twenty-fourth', 25: 'twenty-fifth',
        26: 'twenty-sixth', 27: 'twenty-seventh', 28: 'twenty-eighth',
        29: 'twenty-ninth', 30: 'thirtieth', 31: 'thirty-first'
    }

    if n in ordinals:
        return ordinals[n]

    # For numbers beyond 31, construct the ordinal (shouldn't happen for dates, but handle it)
    # Since dates are 1-31, this is just a safety fallback
    if n < 100:
        tens = n // 10
        ones = n % 10
        tens_words = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        if ones == 0:
            return f"{tens_words[tens]}th"
        else:
            # Get the ordinal for the ones place (should always be in dict for 1-9)
            ones_ordinal = ordinals.get(ones, f"{ones}th")
            return f"{tens_words[tens]}-{ones_ordinal}"

    # For larger numbers, use numeric form (unlikely for dates, but handle gracefully)
    return f"{n}th"


def format_date_speech_friendly(dt: datetime) -> str:
    """Format a datetime in a speech-friendly way with ordinal words."""
    day_name = dt.strftime('%A')
    month_name = dt.strftime('%B')
    day_number = dt.day
    year = dt.year

    day_ordinal = number_to_ordinal_word(day_number)

    return f"{day_name}, {month_name} {day_ordinal}, {year}"


def format_time_speech_friendly(dt: datetime) -> str:
    """Format a time in a speech-friendly way for TTS.

    Examples:
        3:00 PM -> "3 PM"
        3:30 PM -> "3:30 PM"
        12:00 PM -> "noon"
        12:00 AM -> "midnight"
    """
    hour = dt.hour
    minute = dt.minute

    # Special cases for noon and midnight
    if hour == 12 and minute == 0:
        return "noon"
    elif hour == 0 and minute == 0:
        return "midnight"

    # Convert to 12-hour format
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12

    # Determine AM/PM
    period = "AM" if hour < 12 else "PM"

    # Format based on whether there are minutes
    if minute == 0:
        # On the hour: "3 PM" instead of "3:00 PM"
        return f"{hour_12} {period}"
    else:
        # With minutes: "3:30 PM"
        return f"{hour_12}:{minute:02d} {period}"
