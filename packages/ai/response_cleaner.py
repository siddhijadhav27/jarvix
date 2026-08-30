"""Response cleaner - stub for missing module"""
import re

def clean_response(text: str) -> str:
    """Clean LLM response for frontend display"""
    if not text:
        return ""
    
    # Remove markdown code blocks
    text = re.sub(r'```\w*\n?', '', text)
    text = re.sub(r'```', '', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove thinking tags if present
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    return text.strip()
