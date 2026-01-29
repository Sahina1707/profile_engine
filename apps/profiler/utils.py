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
    structured = {
        "profile_points": {
            "domain": "UNKNOWN", 
            "avg_confidence": 0, 
            "observations": [] 
        },
        "analyst_insights": {
            "avg_confidence": 0, 
            "observations": [] 
        },
        "executive_overview": [], 
        "evaluation": {
            "rating": 5, 
            "risk_level": "UNKNOWN", 
            "recommendations": []
        },
    }

    if not raw_json:
        return structured

    clean_text = re.sub(r'```python|```json|```', '', raw_json).strip()
    
    try:
        # 2. ISOLATION: Locate the JSON object
        start, end = clean_text.find('{'), clean_text.rfind('}')
        if start != -1 and end != -1:
            data = json.loads(clean_text[start:end+1])

            raw_p = data.get("profile_points", [])
            if isinstance(raw_p, list) and raw_p:
                valid = [p for p in raw_p if isinstance(p, dict)]
                if valid:
                    structured["profile_points"]["domain"] = valid[0].get("domain", "General")
                    scores = [float(p.get("score", 0)) * (1 if float(p.get("score", 0)) > 10 else 10) for p in valid]
                    structured["profile_points"]["avg_confidence"] = round(sum(scores) / len(valid))
                    
                    numbered_obs = []
                    count = 1
                    for p in valid:
                        text = str(p.get("description", p.get("text", ""))).strip()
                        if any(k in text.lower() for k in ["import ", "def ", "python code", "snippet", "schema:"]):
                            continue
                        text = re.sub(r'[{}"\[\]]', '', text).strip()
                        text = re.sub(r'^(Point\s*\d+:|Point\s*\d+|^\d+[:.])\s*', '', text, flags=re.IGNORECASE)
                        if len(text) > 5:
                            numbered_obs.append(f"{count} {text}")
                            count += 1
                        if count > 5: break
                    structured["profile_points"]["observations"] = numbered_obs

            raw_ins = data.get("analyst_insights", [])
            if isinstance(raw_ins, list) and raw_ins:
                numbered_ins, total, seen = [], 0, set()
                count = 1
                for i in raw_ins:
                    if isinstance(i, dict):
                        txt = i.get("insight", i.get("description", "")).strip()
                        sanitized = re.sub(r'[{}"\[\]]', '', str(txt)).strip()
                        sanitized = re.sub(r'^(Point\s*\d+:|Point\s*\d+|^\d+[:.])\s*', '', sanitized, flags=re.IGNORECASE)
                        if sanitized and sanitized not in seen and not "import " in sanitized.lower():
                            numbered_ins.append(f"{count} {sanitized}")
                            seen.add(sanitized)
                            total += float(i.get("score", 0)) * (1 if float(i.get("score", 0)) > 10 else 10)
                            count += 1
                        if count > 3: break
                structured["analyst_insights"]["observations"] = numbered_ins
                if numbered_ins:
                    structured["analyst_insights"]["avg_confidence"] = round(total / len(numbered_ins))

            raw_overview = data.get("executive_overview", [])
            items = raw_overview if isinstance(raw_overview, list) else [s.strip() for s in raw_overview.split('.') if len(s) > 10]
            numbered_overview = []
            for idx, item in enumerate(items[:5], 1):
                clean_item = re.sub(r'^(Point\s*\d+:|Point\s*\d+|^\d+[:.])\s*', '', str(item), flags=re.IGNORECASE).strip()
                if clean_item and not any(k in clean_item.lower() for k in ["import ", "def ", "schema"]):
                    numbered_overview.append(f"{idx} {clean_item}")
            structured["executive_overview"] = numbered_overview

            ev = data.get("evaluation", {})
            structured["evaluation"]["rating"] = ev.get("rating", 5)
            risk = str(ev.get("risk_level", "UNKNOWN")).upper()
            if risk in ["LOW", "MEDIUM", "HIGH"]:
                structured["evaluation"]["risk_level"] = risk
            else:
                if structured["evaluation"]["rating"] >= 7:
                    structured["evaluation"]["risk_level"] = "LOW"
                else:
                    structured["evaluation"]["risk_level"] = "UNKNOWN"
            
            # Numbering for Recommendations
            recs = ev.get("recommendations", [])
            numbered_recs = []
            for idx, r in enumerate(recs[:5], 1):
                clean_rec = r.get("description", r) if isinstance(r, dict) else r
                clean_rec = re.sub(r'^(Point\s*\d+:|Point\s*\d+|^\d+[:.])\s*', '', str(clean_rec), flags=re.IGNORECASE).strip()
                numbered_recs.append(f"{idx} {clean_rec}")
            structured["evaluation"]["recommendations"] = numbered_recs

    except Exception:
        structured["profile_points"]["observations"] = [f"{i} {t}" for i, t in enumerate(parse_bullets(raw_json)[:5], 1)]
        
    return structured