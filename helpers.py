def remove_smartquotes(text: str) -> str:
    return text.replace('’', "'").replace('“', '"').replace('”', '"')
