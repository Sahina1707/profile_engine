from .models import PromptVersion
import hashlib
import requests
import re
import json

def get_prompt_safe(name: str) -> str:
    """Retrieves the active prompt version from the database."""
    qs = PromptVersion.objects.filter(name=name, is_active=True)
    if qs.count() != 1:
        raise RuntimeError(f"Prompt misconfiguration for {name}: {qs.count()} active")
    return qs.first().content

def hash_text(text: str) -> str:
    """Generates a SHA-256 hash for content tracking."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_ollama_alive():
    """Checks if the Ollama AI server is reachable."""
    try:
        response = requests.get("http://localhost:11434/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

# HARD FAILURE: Ensures system reliability before startup
if not is_ollama_alive():
    raise RuntimeError("Ollama Server is offline! Please run 'ollama serve'")

def parse_bullets(text: str):
    """Fallback parser to extract list items from raw text if JSON fails."""
    bullets = []
    if not text:
        return bullets
    for line in text.splitlines():
        line = line.strip()
        if re.match(r'^(\*|-|\d+\.)\s+', line):
            bullets.append(re.sub(r'^(\*|-|\d+\.)\s+', '', line))
        elif line:  
            bullets.append(line)
    return bullets

def normalize_structured_output(raw_json: str, fallback_profile: str, fallback_rating: str):
    """
    Final optimized normalization logic. 
    Flattens output and strips hallucinated JSON syntax from observations.
    """
    structured = {
        "profile_points": {"domain": "UNKNOWN", "avg_confidence": 0, "observations": []},
        "analyst_insights": {"avg_confidence": 0, "observations": []},
        "executive_overview": fallback_profile[:500] if fallback_profile else "",
        "evaluation": {"rating": 5, "risk_level": "UNKNOWN", "recommendations": []},
    }

    if not raw_json:
        return structured

    # 1. CLEANING: Remove markdown decorators
    clean_text = re.sub(r'```python|```json|```', '', raw_json).strip()
    
    try:
        # 2. ISOLATION: Locate the JSON object
        start, end = clean_text.find('{'), clean_text.rfind('}')
        if start != -1 and end != -1:
            data = json.loads(clean_text[start:end+1])

            # --- FLATTEN PROFILE POINTS ---
            raw_p = data.get("profile_points", [])
            if isinstance(raw_p, list) and raw_p:
                valid = [p for p in raw_p if isinstance(p, dict)]
                if valid:
                    structured["profile_points"]["domain"] = valid[0].get("domain", "General")
                    
                    # Calculate Confidence
                    scores = [float(p.get("score", 0)) * (1 if float(p.get("score", 0)) > 10 else 10) for p in valid]
                    structured["profile_points"]["avg_confidence"] = round(sum(scores) / len(valid))
                    
                    # CLEAN OBSERVATIONS: Strip stray JSON artifacts found in ID 91
                    clean_obs = []
                    for p in valid:
                        val = p.get("description", p.get("text", ""))
                        # Regex to strip backticks, braces, quotes, and square brackets
                        sanitized = re.sub(r'```json|```|{|}|"|\[|\]', '', str(val)).strip()
                        if len(sanitized) > 3:
                            clean_obs.append(sanitized)
                    structured["profile_points"]["observations"] = clean_obs

            # --- FLATTEN ANALYST INSIGHTS ---
            raw_ins = data.get("analyst_insights", [])
            if isinstance(raw_ins, list) and raw_ins:
                obs, total, seen = [], 0, set()
                for i in raw_ins:
                    if isinstance(i, dict):
                        txt = i.get("insight", i.get("description", "")).strip()
                        # Sanitize insights as well
                        sanitized_ins = re.sub(r'```json|```|{|}|"|\[|\]', '', str(txt)).strip()
                        if sanitized_ins and sanitized_ins not in seen:
                            obs.append(sanitized_ins)
                            seen.add(sanitized_ins)
                            total += float(i.get("score", 0)) * (1 if float(i.get("score", 0)) > 10 else 10)
                
                structured["analyst_insights"]["observations"] = obs
                if obs:
                    structured["analyst_insights"]["avg_confidence"] = round(total / len(obs))

            # --- MAP OVERVIEW & EVALUATION (Fixed space typo) ---
            structured["executive_overview"] = data.get("executive_overview", structured["executive_overview"])
            ev = data.get("evaluation", {})
            structured["evaluation"]["rating"] = ev.get("rating", 5)
            
            risk = str(ev.get("risk_level", "UNKNOWN")).upper()
            if risk in ["LOW", "MEDIUM", "HIGH"]:
                structured["evaluation"]["risk_level"] = risk
                
            recs = ev.get("recommendations", [])
            structured["evaluation"]["recommendations"] = [
                r.get("description", r) if isinstance(r, dict) else r for r in recs
            ]

    except Exception as e:
        print(f"Sanitization Error: {e}")
        structured["profile_points"]["observations"] = parse_bullets(raw_json)[:5]
        
    return structured