import json
import re
import docx
import fitz
import ollama
from django.db import transaction
from .models import GeneratedOutput
from .utils import get_prompt_safe, parse_bullets, normalize_structured_output
import time
import requests

def clean_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def normalize_input(data) -> str:
    if isinstance(data, dict):
        return "\n".join(f"{k}: {v}" for k, v in data.items())
    if isinstance(data, list):
        return "\n".join(str(x) for x in data)
    return str(data)

def chunk_text(text: str, max_chars=12000, overlap=500):
    chunks, start = [], 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

def safe_ollama_chat(messages, temperature=0.2, retries=3):
    for i in range(retries):
        try:
            resp = ollama.chat(
                model="llama3.2",
                messages=messages,
                options={"temperature": temperature},
            )
            return resp["message"]["content"]
        except (requests.exceptions.ConnectionError, Exception) as e:
            if i < retries - 1:
                time.sleep(2)  # Wait 2 seconds and try again
                continue
            return f"Error: Model connection failed after {retries} attempts."

def run_profile_engine(profile_input: dict, session):
    """
    Full updated Profiling Engine with Domain Detection, 
    Confidence Scores, and 1-10 Rating Logic.
    """
    extracted_text = ""
    file_obj = profile_input.get("file")
    text_data = profile_input.get("text_data", "")

    # 1. Extraction from Files
    if file_obj:
        if file_obj.name.endswith(".docx"):
            import docx
            doc = docx.Document(file_obj)
            extracted_text = "\n".join([p.text for p in doc.paragraphs])
        elif file_obj.name.endswith(".pdf"):
            import fitz
            with fitz.open(stream=file_obj.read(), filetype="pdf") as doc:
                extracted_text = "\n".join([page.get_text() for page in doc])
    else:
        extracted_text = text_data

    # 2. Multi-Step AI Pipeline
    # Step A: EXTRACTION with Domain Detection & Confidence
    extraction_prompt = get_prompt_safe("EXTRACTION")
    raw_facts = []
    detected_domains = []

    for chunk in chunk_text(extracted_text):
        resp = safe_ollama_chat([
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": chunk},
        ], temperature=0.3)
        
        if resp:
            # Domain Detection Logic
            domain_match = re.search(r"DOMAIN:\s*(.*)", resp, re.IGNORECASE)
            if domain_match:
                detected_domains.append(domain_match.group(1).strip())
            raw_facts.append(resp)

    combined_facts = "\n".join(raw_facts)

    # Update session domain if found
    if detected_domains and not session.detected_domain:
        from collections import Counter
        session.detected_domain = Counter(detected_domains).most_common(1)[0][0]
        session.save()

    # Step B: SYNTHESIS
    synthesis_prompt = get_prompt_safe("SYNTHESIS")
    profile_text = safe_ollama_chat([
        {"role": "system", "content": synthesis_prompt},
        {"role": "user", "content": combined_facts},
    ], temperature=0.4)

    # Step C: RATING (Enforcing 1-10 Scale)
    rating_prompt = get_prompt_safe("RATING")
    rating_text = safe_ollama_chat([
        {"role": "system", "content": rating_prompt},
        {"role": "user", "content": profile_text},
    ], temperature=0.2)

    # Step D: PROFILING (JSON Structuring)
    profiling_prompt = get_prompt_safe("PROFILING")
    structured_resp = safe_ollama_chat([
        {"role": "system", "content": profiling_prompt},
        {"role": "user", "content": f"Facts: {combined_facts}\nProfile: {profile_text}\nRating: {rating_text}"},
    ], temperature=0.1)

    # 3. Normalization & Rating Scale Enforcement (1-10)
    structured_data = normalize_structured_output(structured_resp, profile_text, rating_text)

    # 4. Save to Database
    with transaction.atomic():
        output = GeneratedOutput.objects.create(
            session=session,
            raw_content=extracted_text,
            structured_content=structured_data
        )

    return {
        "id": output.id,
        "domain": session.detected_domain,
        "structured_content": structured_data
    }