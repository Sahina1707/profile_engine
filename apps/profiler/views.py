import uuid
import json
import docx
import fitz  
from django.db import transaction
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ChatSession, GeneratedOutput
from apps.core.utils import generate_profile_pdf
import ollama

EXTRACTION_PROMPT = """
You are a Precision Data Extractor.

Analyze the text and extract only concrete, verifiable facts.
Do NOT interpret, summarize, explain, or infer.

Rules:
- Preserve factual accuracy.
- Separate financial performance from valuation or reputation.
- Keep exact wording only when criticism or claims are specific.
- Remove marketing language and subjective praise unless quoted.

Extract factual signals such as:
- Subject type (person, company, place, service, institution)
- Role, function, or operational purpose
- Location or scope of operation
- Time-based changes or pivots (facts only)
- Quantitative data (revenue, valuation, scale, experience)
- Named individuals and their roles
- Explicit risks, failures, limitations, or criticisms

Output as short bullet points only.
"""


SYNTHESIS_PROMPT = """
You are operating in PROFILING MODE.

This is an internal analytical profile, not a summary, explanation, or rewrite.

You are given extracted factual signals about a subject.
The subject may be a person, company, place, service, institution, or role.

Your task is to infer:
- operating posture
- structural strengths
- systemic constraints
- decision-relevant implications

DO NOT use chronological phrasing:
- Avoid references like "in 2018" or "from X to Y"
- Do not narrate events, timelines, or historical sequences
- Do not imply past → present order

MANDATORY BEHAVIOR:
- Convert facts into behavioral tendencies, leverage points, and risks
- Focus on present-state characteristics
- Use events or individuals only as evidence for inferred patterns
- Treat unknowns as unknowns; do not speculate

STRICT PROHIBITIONS:
- No summarization or paraphrasing of source text
- No history, founding, or chronological narration
- No product, service, or feature listings unless they illustrate constraints
- No encyclopedic tone, explanations, or public-facing language
- No headings, bullets, labels, or templates
- No praise, marketing, or generic descriptions
- No sentences starting with definitions (e.g., "X is…")

OUTPUT REQUIREMENTS:
- Short, dense analytical paragraphs or compact lines
- Neutral, professional, decision-facing tone
- Output must read as an internal intelligence or diligence note

SELF-CHECK:
If the output implies timeline progression or historical narrative, rewrite to remove it, keeping only operational posture, structural strengths, constraints, and decision implications.

"""


VALIDATOR_PROMPT = """
You are an Output Validator for a Profiling Engine.

Review the generated profile below.

Determine whether it violates profiling rules by behaving like
a summary, rewrite, or descriptive explanation.

Violations include:
- Restating or paraphrasing source facts
- Encyclopedic or educational tone
- Historical or chronological narration
- Product, service, or feature listing
- Headings, bullets, labels, or templates
- Public-facing descriptive language

If NO violations are found:
Return exactly:
APPROVED

If ANY violation is found:
Rewrite the content so it fully complies with PROFILING MODE.
Return ONLY the corrected profile text.
Do NOT explain what was changed.
"""


def clean_input(text: str) -> str:
    text = text.replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def chunk_text(text: str, max_chars=12000, overlap=500):
    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap

    return chunks

class ProfileEngineAPI(APIView):

    def post(self, request):
        session_id = request.data.get("session_id") or str(uuid.uuid4())
        session, _ = ChatSession.objects.get_or_create(session_id=session_id)

        text_data = request.data.get("text_data", "")
        uploaded_file = request.FILES.get("file")
        extracted_text = ""

        # ---- Text ingestion ----
        if isinstance(text_data, dict):
            extracted_text = json.dumps(text_data)
        else:
            extracted_text = str(text_data)

        if uploaded_file:
            try:
                if uploaded_file.name.lower().endswith(".docx"):
                    doc = docx.Document(uploaded_file)
                    extracted_text = " ".join(
                        p.text for p in doc.paragraphs if p.text.strip()
                    )
                elif uploaded_file.name.lower().endswith(".pdf"):
                    with fitz.open(
                        stream=uploaded_file.read(), filetype="pdf"
                    ) as pdf:
                        extracted_text = " ".join(
                            page.get_text() for page in pdf
                        )
            except Exception as e:
                return Response(
                    {"error": f"File extraction failed: {str(e)}"},
                    status=500
                )

        extracted_text = clean_input(extracted_text)

        if not extracted_text:
            return Response({"error": "No valid input provided."}, status=400)

        # ---- Extraction phase ----
        chunks = chunk_text(extracted_text)
        extracted_notes = []

        for i, chunk in enumerate(chunks):
            try:
                response = ollama.chat(
                    model="llama3.2",
                    messages=[
                        {"role": "system", "content": EXTRACTION_PROMPT},
                        {"role": "user", "content": chunk}
                    ],
                    options={"temperature": 0.2}
                )
                extracted_notes.append(response["message"]["content"])
            except Exception as e:
                print(f"Extraction failed for chunk {i}: {e}")

        raw_facts = "\n".join(extracted_notes)

        if not raw_facts.strip():
            return Response(
                {"error": "Fact extraction failed."},
                status=500
            )

        # ---- Profiling (synthesis) ----
        try:
            profiling_response = ollama.chat(
                model="llama3.2",
                messages=[
                    {"role": "system", "content": SYNTHESIS_PROMPT},
                    {
                        "role": "user",
                        "content": f"Extracted factual notes:\n\n{raw_facts}"
                    }
                ],
                options={"temperature": 0.3}
            )
            final_profile = profiling_response["message"]["content"]
        except Exception as e:
            return Response(
                {"error": f"Profiling failed: {str(e)}"},
                status=500
            )

        # ---- Validation & enforcement ----
        try:
            validator_response = ollama.chat(
                model="llama3.2",
                messages=[
                    {"role": "system", "content": VALIDATOR_PROMPT},
                    {"role": "user", "content": final_profile}
                ],
                options={"temperature": 0.0}
            )

            validated = validator_response["message"]["content"].strip()
            if validated != "APPROVED":
                final_profile = validated

        except Exception as e:
            return Response(
                {"error": f"Validation failed: {str(e)}"},
                status=500
            )

        # ---- Persist output ----
        with transaction.atomic():
            GeneratedOutput.objects.create(
                session=session,
                output_type="profile_text",
                content=final_profile
            )

        # ---- Optional PDF ----
        if request.data.get("format") == "pdf":
            pdf_file = generate_profile_pdf(final_profile, "Profile Report")
            return FileResponse(
                pdf_file,
                as_attachment=True,
                filename=f"profile_{session_id}.pdf"
            )

        return Response(
            {
                "session_id": session_id,
                "response": final_profile
            },
            status=200
        )
