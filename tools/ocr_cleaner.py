# tools/ocr_cleaner.py
"""
FitForge AI — OCR Text Cleaner Tool (ADK Compatible)
=====================================================
Heuristic cleaner for noisy OCR text from workout screenshots.
Fixes common OCR recognition errors and normalizes formatting.

This is a pure text-processing tool (no AI required).

ADK Tool Format: Function with docstring + type hints + dict return
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime


# =============================================================================
# CHARACTER SUBSTITUTION MAPS
# =============================================================================

# Common OCR digit misreads
DIGIT_SUBSTITUTIONS = {
    # Characters that look like 1
    "I": "1", "l": "1", "|": "1",
    # Characters that look like 0
    "O": "0",
    # Characters that look like 5
    "S": "5",
    # Characters that look like 8
    "B": "8",
    # Characters that look like 6
    "G": "6",
}

# Contextual unit fixes (common OCR misreads)
UNIT_FIXES = {
    "krn": "km",
    "knn": "km",
    "bprn": "bpm",
    "bpnn": "bpm",
    "rnin": "min",
    "m1n": "min",
    "rn": "m",  # meters
}

# Fitness-specific terms to preserve
FITNESS_TERMS = [
    "km", "mi", "miles", "meters", "m",
    "min", "sec", "hr", "hours", "minutes", "seconds",
    "bpm", "heart", "rate",
    "cal", "kcal", "calories",
    "watts", "power",
    "pace", "speed", "avg", "max",
    "elevation", "elev", "gain", "ft", "feet",
    "cadence", "rpm", "spm",
    "distance", "duration", "time",
    "run", "ride", "swim", "walk", "cycle",
]


# =============================================================================
# MAIN ADK TOOL: clean_ocr_text
# =============================================================================

def clean_ocr_text(
    text: str,
    fix_digits: bool = True,
    fix_spacing: bool = True,
    remove_garbage: bool = True
) -> Dict[str, Any]:
    """
    Clean and normalize noisy OCR text from workout screenshots.
    
    Applies multiple cleaning passes to fix common OCR recognition errors:
    1. Removes garbage/unprintable characters (optional)
    2. Fixes digit misreads in numeric contexts (O→0, I→1, etc.)
    3. Fixes spacing in decimal numbers and times
    4. Normalizes whitespace
    
    Args:
        text: Raw OCR text to clean. Can be messy output from image recognition.
        fix_digits: If True, fixes common digit misreads (O→0, I→1, etc.)
        fix_spacing: If True, fixes spacing issues in numbers and times.
        remove_garbage: If True, removes non-alphanumeric characters 
                       except common punctuation (:, ., -, /).
    
    Returns:
        Dictionary with cleaning results:
        - status: "success" or "error"
        - cleaned_text: The cleaned text
        - original_length: Character count of input
        - cleaned_length: Character count of output
        - changes_made: List of cleaning operations applied
        - confidence: Confidence in cleaning quality (0.0 to 1.0)
    
    Example:
        >>> result = clean_ocr_text("5 . O2 km in 28 : 3O min")
        >>> print(result["cleaned_text"])
        "5.02 km in 28:30 min"
    """
    
    # -------------------------------------------------------------------------
    # Input Validation
    # -------------------------------------------------------------------------
    if text is None:
        return {
            "status": "error",
            "error_message": "Input text is None"
        }
    
    if not isinstance(text, str):
        return {
            "status": "error",
            "error_message": f"Expected string, got {type(text).__name__}"
        }
    
    original_text = text
    original_length = len(text)
    changes_made = []
    
    if not text.strip():
        return {
            "status": "success",
            "cleaned_text": "",
            "original_length": original_length,
            "cleaned_length": 0,
            "changes_made": [],
            "confidence": 1.0
        }
    
    result = text
    
    # -------------------------------------------------------------------------
    # Step 1: Remove garbage characters (keep fitness-relevant punctuation)
    # -------------------------------------------------------------------------
    if remove_garbage:
        before = result
        # Keep: letters, numbers, spaces, and : . - / , % ' "
        result = re.sub(r'[^\w\s:\-.,/%\'\"°]', ' ', result)
        if result != before:
            changes_made.append("removed_garbage_characters")
    
    # -------------------------------------------------------------------------
    # Step 2: Fix spacing in decimals and times ONLY
    # -------------------------------------------------------------------------
    if fix_spacing:
        before = result
        
        # Fix spaced decimals: "5 . 02" -> "5.02"
        result = re.sub(r'(\d)\s+\.\s+(\d)', r'\1.\2', result)
        result = re.sub(r'(\d)\s+\.(\d)', r'\1.\2', result)
        result = re.sub(r'(\d)\.\s+(\d)', r'\1.\2', result)
        
        # Fix spaced time colons: "28 : 30" -> "28:30"
        result = re.sub(r'(\d)\s+:\s+(\d)', r'\1:\2', result)
        result = re.sub(r'(\d)\s+:(\d)', r'\1:\2', result)
        result = re.sub(r'(\d):\s+(\d)', r'\1:\2', result)
        
        # Fix split unit words: "k m" -> "km", "b p m" -> "bpm"
        result = re.sub(r'\bk\s+m\b', 'km', result, flags=re.I)
        result = re.sub(r'\bm\s+i\b', 'mi', result, flags=re.I)
        result = re.sub(r'\bb\s+p\s+m\b', 'bpm', result, flags=re.I)
        result = re.sub(r'\bm\s+i\s+n\b', 'min', result, flags=re.I)
        
        if result != before:
            changes_made.append("fixed_spacing")
    
    # -------------------------------------------------------------------------
    # Step 3: Fix digit substitutions in numeric contexts
    # -------------------------------------------------------------------------
    if fix_digits:
        before = result
        
        # Only fix characters that appear between/near digits
        # Fix O between digits: "1O5" -> "105"
        result = re.sub(r'(\d)O(\d)', r'\g<1>0\2', result)
        result = re.sub(r'(\d)o(\d)', r'\g<1>0\2', result)
        
        # Fix I/l at start of number followed by digits: "I52" -> "152"
        result = re.sub(r'\bI(\d)', r'1\1', result)
        result = re.sub(r'\bl(\d)', r'1\1', result)
        
        # Fix O/I in time context: "I2:3O" -> "12:30"
        result = re.sub(r'\bI(\d):(\d)', r'1\1:\2', result)
        result = re.sub(r'(\d):(\d)O\b', r'\1:\g<2>0', result)
        result = re.sub(r'(\d)O:(\d)', r'\g<1>0:\2', result)
        
        # Fix common unit OCR errors
        for wrong, correct in UNIT_FIXES.items():
            result = re.sub(r'\b' + wrong + r'\b', correct, result, flags=re.I)
        
        if result != before:
            changes_made.append("fixed_digit_errors")
    
    # -------------------------------------------------------------------------
    # Step 4: Normalize whitespace
    # -------------------------------------------------------------------------
    before = result
    result = re.sub(r'\s+', ' ', result).strip()
    if result != before:
        changes_made.append("normalized_whitespace")
    
    # -------------------------------------------------------------------------
    # Calculate Confidence
    # -------------------------------------------------------------------------
    if original_length > 0:
        change_ratio = abs(len(result) - original_length) / original_length
    else:
        change_ratio = 0
    
    if change_ratio < 0.1:
        confidence = 0.95
    elif change_ratio < 0.25:
        confidence = 0.8
    elif change_ratio < 0.4:
        confidence = 0.6
    else:
        confidence = 0.4
    
    return {
        "status": "success",
        "cleaned_text": result,
        "original_length": original_length,
        "cleaned_length": len(result),
        "changes_made": changes_made,
        "confidence": round(confidence, 2),
        "cleaned_at": datetime.now().isoformat()
    }


# =============================================================================
# ADDITIONAL TOOL: Extract Numbers from OCR Text
# =============================================================================

def extract_numbers_from_ocr(text: str) -> Dict[str, Any]:
    """
    Extract all numbers from OCR text after cleaning.
    
    Useful for quickly pulling out all numeric values from a workout screenshot.
    Handles decimals, times (HH:MM:SS), and numbers attached to units.
    
    Args:
        text: OCR text to extract numbers from (will be cleaned first)
    
    Returns:
        Dictionary with extraction results:
        - status: "success" or "error"
        - numbers: List of extracted number values
        - time_values: List of detected time values (MM:SS or HH:MM:SS format)
        - count: Total numbers found
        - cleaned_text: The cleaned text used for extraction
    
    Example:
        >>> result = extract_numbers_from_ocr("Ran 5.2km in 28:30, avg HR 152")
        >>> print(result["numbers"])
        [5.2, 28, 30, 152]
    """
    
    if not text:
        return {
            "status": "error",
            "error_message": "No text provided"
        }
    
    # Clean the text first
    clean_result = clean_ocr_text(text)
    if clean_result["status"] != "success":
        return clean_result
    
    cleaned = clean_result["cleaned_text"]
    
    # Extract time values first (special format)
    time_pattern = r'(\d{1,2}):(\d{2})(?::(\d{2}))?'
    time_matches = re.findall(time_pattern, cleaned)
    time_values = []
    for match in time_matches:
        if match[2]:  # HH:MM:SS
            time_values.append(f"{match[0]}:{match[1]}:{match[2]}")
        else:  # MM:SS
            time_values.append(f"{match[0]}:{match[1]}")
    
    # Extract ALL numbers (including those attached to units like "5.2km")
    # This pattern finds any sequence of digits optionally followed by decimal
    all_numbers_pattern = r'(\d+\.\d+|\d+)'
    number_matches = re.findall(all_numbers_pattern, cleaned)
    
    numbers = []
    for match in number_matches:
        try:
            if '.' in match:
                val = float(match)
            else:
                val = int(match)
            numbers.append(val)
        except ValueError:
            continue
    
    # Remove duplicates while preserving order
    seen = set()
    unique_numbers = []
    for num in numbers:
        if num not in seen:
            seen.add(num)
            unique_numbers.append(num)
    
    return {
        "status": "success",
        "numbers": unique_numbers,
        "time_values": time_values,
        "count": len(unique_numbers),
        "cleaned_text": cleaned
    }


# =============================================================================
# ADDITIONAL TOOL: Validate OCR Quality
# =============================================================================

def assess_ocr_quality(text: str) -> Dict[str, Any]:
    """
    Assess the quality of OCR text and identify potential issues.
    
    Analyzes text for common OCR problems and provides a quality score.
    Useful for deciding whether to trust OCR output or request manual input.
    
    Args:
        text: OCR text to assess
    
    Returns:
        Dictionary with quality assessment:
        - status: "success" or "error"
        - quality_score: Overall quality (0.0 to 1.0)
        - quality_label: "good", "acceptable", "poor", "unusable"
        - issues_found: List of detected problems
        - recommendations: Suggestions for handling the text
        - fitness_content_detected: Whether fitness-related content was found
    """
    
    if not text:
        return {
            "status": "error",
            "error_message": "No text provided"
        }
    
    issues = []
    score = 1.0
    
    # Check for garbage characters
    garbage_count = len(re.findall(r'[^\w\s:\-.,/%]', text))
    garbage_ratio = garbage_count / max(len(text), 1)
    if garbage_ratio > 0.2:
        issues.append("High proportion of garbage characters")
        score -= 0.25
    elif garbage_ratio > 0.1:
        issues.append("Some garbage characters present")
        score -= 0.1
    
    # Check for spaced numbers (OCR artifact)
    spaced_numbers = len(re.findall(r'\d\s+\d', text))
    if spaced_numbers > 3:
        issues.append("Multiple spaced number sequences")
        score -= 0.15
    
    # Check for fitness content
    text_lower = text.lower()
    fitness_terms_found = [term for term in FITNESS_TERMS if term in text_lower]
    has_fitness_content = len(fitness_terms_found) >= 2
    
    if not has_fitness_content:
        issues.append("Limited fitness-related content")
        score -= 0.1
    
    # Check for valid numbers
    valid_numbers = len(re.findall(r'\d+\.?\d*', text))
    if valid_numbers == 0:
        issues.append("No numbers found")
        score -= 0.2
    
    # Clamp score
    score = max(0.0, min(1.0, score))
    
    # Determine label
    if score >= 0.8:
        label = "good"
        recommendations = ["Text quality is good."]
    elif score >= 0.6:
        label = "acceptable"
        recommendations = ["Consider cleaning before extraction."]
    elif score >= 0.4:
        label = "poor"
        recommendations = ["Manual verification recommended."]
    else:
        label = "unusable"
        recommendations = ["Please provide a clearer image."]
    
    return {
        "status": "success",
        "quality_score": round(score, 2),
        "quality_label": label,
        "issues_found": issues,
        "recommendations": recommendations,
        "fitness_content_detected": has_fitness_content,
        "fitness_terms_found": fitness_terms_found[:10],
        "assessed_at": datetime.now().isoformat()
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "clean_ocr_text",
    "extract_numbers_from_ocr",
    "assess_ocr_quality",
    "DIGIT_SUBSTITUTIONS",
    "FITNESS_TERMS",
]