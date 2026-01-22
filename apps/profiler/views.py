import uuid
import json
import docx
import fitz
from collections import defaultdict
from django.db import transaction
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ChatSession, GeneratedOutput
from apps.core.utils import generate_profile_pdf
import ollama


SYSTEM_PROMPT = """
You are a professional profiling engine capable of creating concise, accurate, and structured profiles for ANY subject.

Rules:
- Output must be plain text only
- No markdown symbols
- No bullets, dashes, numbering, or emojis
- No slashes or escape characters
- Section titles must be plain words followed by a colon
- Do not use filler phrases
- Do not hallucinate information
- Use paragraphs only

Allowed sections:
Key Achievements
Early Life Origins
Education Training
Career Contributions
Products Services
Recognition Awards
Timeline
Key Roles Key Facts
Additional Notes
"""


def clean_input(text):
    text = text.replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def chunk_text(text, max_chars=6000):
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]


def merge_chunks(chunks):
    sections = defaultdict(list)
    current_section = None

    for chunk in chunks:
        lines = chunk.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers conservatively
            if line.endswith(":") and len(line.split()) <= 4:
                current_section = line
                continue

            # Fallback when model does not emit headers
            if current_section:
                sections[current_section].append(line)
            else:
                sections["Additional Notes:"].append(line)

    final_blocks = []
    for section, content in sections.items():
        if not content:
            continue
        final_blocks.append(section + "\n" + " ".join(content))

    return "\n\n".join(final_blocks)


def normalize_headers(text):
    replacements = {
        "Early Life  Origins:": "Early Life Origins:",
        "Education  Training:": "Education Training:",
        "Career  Contributions:": "Career Contributions:",
        "Products  Services:": "Products Services:",
        "Recognition  Awards:": "Recognition Awards:",
        "Key Roles  Key Facts:": "Key Roles Key Facts:"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def remove_list_symbols(text):
    cleaned = []
    for line in text.split("\n"):
        line = line.lstrip("-•– ").strip()
        cleaned.append(line)
    return "\n".join(cleaned)


def remove_empty_sections(text):
    blocks = text.split("\n\n")
    valid_blocks = []

    for block in blocks:
        lines = block.split("\n")
        if len(lines) == 1 and lines[0].endswith(":"):
            continue
        valid_blocks.append(block)

    return "\n\n".join(valid_blocks)


def final_normalize(text):
    for ch in ["*", "`", "_", "#", "/", "\\", "-"]:
        text = text.replace(ch, "")
    text = normalize_headers(text)
    text = remove_list_symbols(text)
    text = remove_empty_sections(text)
    return text.strip()


class ProfileEngineAPI(APIView):

    def post(self, request):
        session_id = request.data.get("session_id") or str(uuid.uuid4())
        session, _ = ChatSession.objects.get_or_create(session_id=session_id)

        text_data = request.data.get("text_data", "")
        uploaded_file = request.FILES.get("file")
        extracted_text = ""

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
                    pdf = fitz.open(
                        stream=uploaded_file.read(),
                        filetype="pdf"
                    )
                    extracted_text = " ".join(page.get_text() for page in pdf)
                    pdf.close()

            except Exception as e:
                return Response(
                    {"error": f"File extraction failed: {str(e)}"},
                    status=500
                )

        extracted_text = clean_input(extracted_text)
        if not extracted_text:
            return Response(
                {"error": "No valid input data provided."},
                status=400
            )

        chunks = chunk_text(extracted_text)
        ai_outputs = []

        try:
            for chunk in chunks:
                response = ollama.chat(
                    model="llama3.2",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": chunk}
                    ],
                    options={"temperature": 0.6}
                )
                ai_outputs.append(response["message"]["content"])
        except Exception as e:
            return Response(
                {"error": f"AI processing failed: {str(e)}"},
                status=500
            )

        final_content = merge_chunks(ai_outputs)
        final_content = final_normalize(final_content)

        if not final_content.strip():
            final_content = (
                "Additional Notes:\n"
                "No structured information could be extracted from the input."
            )

        with transaction.atomic():
            GeneratedOutput.objects.create(
                session=session,
                output_type="profile_text",
                content=final_content
            )

        if request.data.get("format") == "pdf":
            pdf_file = generate_profile_pdf(
                final_content,
                "Profile Report"
            )
            return FileResponse(
                pdf_file,
                as_attachment=True,
                filename=f"profile_{session_id}.pdf",
                content_type="application/pdf"
            )

        return Response(
            {
                "session_id": session_id,
                "response": final_content
            },
            status=200
        )
