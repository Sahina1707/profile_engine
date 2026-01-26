from .models import PromptVersion

def get_prompt(name: str) -> str:
    prompt = PromptVersion.objects.filter(name=name, is_active=True).first()
    if not prompt:
        raise ValueError(f"No active prompt found for {name}")
    return prompt.content
