"""Utility functions for executor module."""

import json
import re
from typing import Optional


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text.

    This removes color codes, cursor movement, and other terminal control sequences.

    Args:
        text: Text potentially containing ANSI escape codes.

    Returns:
        Clean text without ANSI codes.
    """
    # Pattern matches:
    # - \x1b (ESC) followed by [ and any parameters ending with a letter
    # - \x1b (ESC) followed by other escape sequences
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b[^[[]?")
    return ansi_pattern.sub("", text)


def extract_final_json(text: str) -> Optional[str]:
    """Extract final JSON from agent response.
    
    Looks for JSON in markdown code blocks (```json ... ```) or as raw JSON.
    Returns the last JSON found in the text, or None if no valid JSON found.
    
    Args:
        text: Full text response from agent.
        
    Returns:
        JSON string if found, None otherwise.
    """
    if not text:
        return None
    
    # Try to find JSON in markdown code blocks first
    json_block_pattern = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
    json_matches = json_block_pattern.findall(text)
    if json_matches:
        # Return the last JSON block found
        try:
            json.loads(json_matches[-1])  # Validate it's valid JSON
            return json_matches[-1].strip()
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON blocks (``` ... ``` without json label)
    code_block_pattern = re.compile(r"```\s*\n(.*?)\n```", re.DOTALL)
    code_matches = code_block_pattern.findall(text)
    for match in reversed(code_matches):  # Check from end to start
        try:
            parsed = json.loads(match.strip())
            # If it's a dict or list, it's likely JSON
            if isinstance(parsed, (dict, list)):
                return match.strip()
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON at the end of the text (common pattern)
    # Look for { ... } or [ ... ] patterns
    json_object_pattern = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
    json_array_pattern = re.compile(r"\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]", re.DOTALL)
    
    # Try object first
    object_matches = json_object_pattern.findall(text)
    for match in reversed(object_matches):
        try:
            json.loads(match)
            return match.strip()
        except json.JSONDecodeError:
            continue
    
    # Try array
    array_matches = json_array_pattern.findall(text)
    for match in reversed(array_matches):
        try:
            json.loads(match)
            return match.strip()
        except json.JSONDecodeError:
            continue
    
    return None
