import re

def compress_prompt(prompt: str) -> str:
    """
    Autonomous Prompt Compression:
    Removes redundant whitespace, filler words, and distills the prompt to save token costs.
    """
    original_len = len(prompt)
    
    # Strip excess whitespace
    compressed = re.sub(r'\s+', ' ', prompt).strip()
    
    # Strip common conversational filler that LLMs don't need
    fillers = [
        r'\bplease\b', r'\bcould you\b', r'\bwould you mind\b',
        r'\bI was wondering if\b', r'\bcan you\b'
    ]
    for filler in fillers:
        compressed = re.sub(filler, '', compressed, flags=re.IGNORECASE).strip()
    
    # Ensure we don't return an empty string
    if not compressed:
        return prompt
        
    return compressed
