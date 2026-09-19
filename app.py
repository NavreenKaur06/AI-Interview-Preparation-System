from pathlib import Path
import os
import re
import base64
import json
import html
from io import BytesIO
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import speech_recognition as sr
from gtts import gTTS

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
HISTORY_FILE = BASE_DIR / "interview_history.json"

HERO_SVG = r"""<svg width="520" height="260" viewBox="0 0 520 260" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="520" y2="260" gradientUnits="userSpaceOnUse"><stop stop-color="#4F46E5"/><stop offset="1" stop-color="#9333EA"/></linearGradient>
 <linearGradient id="screen" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#DDE7FF"/><stop offset="1" stop-color="#9AA8FF"/></linearGradient>
 <linearGradient id="shirt" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8B5CF6"/><stop offset="1" stop-color="#4338CA"/></linearGradient>
</defs>
<rect x="0" y="0" width="520" height="260" rx="28" fill="url(#bg)" opacity=".18"/>
<circle cx="421" cy="48" r="25" fill="#A78BFA" opacity=".22"/>
<circle cx="470" cy="91" r="9" fill="#E9D5FF" opacity=".6"/>
<path d="M348 44C348 28 361 15 377 15C393 15 406 28 406 44C406 60 393 73 377 73C361 73 348 60 348 44Z" fill="#8B5CF6" opacity=".65"/>
<text x="365" y="53" font-family="Arial" font-size="23" font-weight="700" fill="white">AI</text>
<!-- person -->
<path d="M359 105C359 82 377 64 400 64C423 64 441 82 441 105V143H359V105Z" fill="#17172B"/>
<path d="M368 96C368 75 382 62 400 62C418 62 432 75 432 96V113C432 132 418 146 400 146C382 146 368 132 368 113V96Z" fill="#F7C8A8"/>
<path d="M366 95C366 72 382 56 402 58C423 60 438 75 435 98C426 87 418 82 404 81C390 80 380 87 366 95Z" fill="#111827"/>
<circle cx="387" cy="103" r="2.5" fill="#1F2937"/><circle cx="414" cy="103" r="2.5" fill="#1F2937"/>
<path d="M393 120C398 124 405 124 410 120" stroke="#9F4E56" stroke-width="2.5" stroke-linecap="round"/>
<path d="M342 154C350 133 370 124 400 124C430 124 450 133 458 154L477 212H323L342 154Z" fill="url(#shirt)"/>
<path d="M399 128L384 168L400 190L416 168L401 128H399Z" fill="#F8FAFC" opacity=".9"/>
<!-- laptop -->
<rect x="210" y="130" width="190" height="104" rx="9" fill="#0F172A" stroke="#A5B4FC" stroke-width="3"/>
<rect x="221" y="141" width="168" height="82" rx="5" fill="url(#screen)"/>
<path d="M188 233H423L448 246C450 248 448 251 444 251H168C164 251 162 248 165 246L188 233Z" fill="#CBD5E1"/>
<circle cx="305" cy="182" r="14" fill="#4F46E5" opacity=".65"/>
<path d="M298 182L303 187L313 176" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="238" y="199" width="55" height="7" rx="3.5" fill="#6366F1" opacity=".55"/>
<rect x="300" y="199" width="70" height="7" rx="3.5" fill="#7C3AED" opacity=".35"/>
<!-- floating card -->
<rect x="40" y="48" width="145" height="72" rx="15" fill="#0F172A" stroke="#A78BFA" stroke-opacity=".35"/>
<circle cx="66" cy="76" r="14" fill="#22C55E" opacity=".9"/>
<path d="M59 76L64 81L74 70" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
<text x="88" y="74" font-family="Arial" font-size="12" font-weight="700" fill="white">Ready to</text>
<text x="88" y="91" font-family="Arial" font-size="12" fill="#CBD5E1">practice</text>
</svg>
"""
HERO_SVG_B64 = base64.b64encode(HERO_SVG.encode("utf-8")).decode("ascii")

load_dotenv(dotenv_path=ENV_FILE)

# ============================================================
# OPENROUTER CONFIGURATION
# ============================================================

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    st.error(
        "OPENROUTER_API_KEY was not found in the .env file. "
        "Please add your OpenRouter API key and restart the app."
    )
    st.stop()

@st.cache_resource
def get_client():
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

client = get_client()

MODEL = "openrouter/free"

st.set_page_config(
    page_title="AI Interview Preparation System",
    page_icon="🎯",
    layout="wide"
)

# Number of questions in each smart interview
TOTAL_QUESTIONS = 5


# ============================================================
# LOCAL STORAGE
# ============================================================

def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history):
    temp_file = HISTORY_FILE.with_suffix(".tmp")

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(history, file, indent=2, ensure_ascii=False)

        temp_file.replace(HISTORY_FILE)
    except OSError as e:
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)
        raise e


# ============================================================
# AI HELPERS
# ============================================================

# Free models used as a small reliability fallback chain.
# OpenRouter's free router can select different free models, including
# reasoning models. A reasoning model can sometimes consume the token budget
# without putting text in message.content, so we explicitly disable reasoning
# where supported and retry with non-thinking free models if needed.
FREE_AI_MODELS = [
    # Start with explicit non-thinking/instruction models, then use the router.
    "qwen/qwen3-235b-a22b-2507:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/free",
]


def ask_ai(prompt, max_tokens=250):
    """Generate text through OpenRouter with retries and model fallbacks."""

    errors = []
    token_limit = max(500, max_tokens)

    for model_name in FREE_AI_MODELS:
        # Try each model twice:
        # 1) with reasoning disabled
        # 2) without extra_body, for providers that reject that parameter
        attempts = [
            {"reasoning": {"effort": "none"}},
            None,
        ]

        for extra_body in attempts:
            try:
                request_kwargs = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": token_limit,
                }

                if extra_body is not None:
                    request_kwargs["extra_body"] = extra_body

                response = client.chat.completions.create(**request_kwargs)

                choices = getattr(response, "choices", None)

                if not choices:
                    errors.append(
                        f"{model_name}: no choices returned"
                    )
                    continue

                message = choices[0].message
                content = getattr(message, "content", None)

                if isinstance(content, str) and content.strip():
                    return content.strip()

                # Some providers may return content in a list of text parts.
                if isinstance(content, list):
                    parts = []
                    for part in content:
                        if isinstance(part, dict):
                            value = part.get("text", "")
                        else:
                            value = getattr(part, "text", "")
                        if isinstance(value, str):
                            parts.append(value)
                    combined = "".join(parts).strip()
                    if combined:
                        return combined

                errors.append(
                    f"{model_name}: empty message content"
                )

            except Exception as exc:
                errors.append(
                    f"{model_name}: {type(exc).__name__}: {str(exc)}"
                )

    details = " | ".join(errors[-6:])
    raise RuntimeError(
        "The AI service did not return usable text. "
        "Please try again in a few seconds. "
        f"Details: {details}"
    )


def generate_question(role, interview_type, difficulty, level):
    prompt = f"""
You are a professional interviewer.

Role: {role}
Experience: {level}
Interview Type: {interview_type}
Difficulty: {difficulty}

Generate exactly ONE interview question.

Rules:
- Relevant to the selected role and interview type.
- Match the difficulty and experience level.
- Do not give an answer.
- Do not explain anything.
- Do not create multiple questions.
- Return ONLY the question.
"""
    return ask_ai(prompt, max_tokens=100)


def generate_adaptive_question(role, interview_type, difficulty, level,
                               previous_question, previous_answer, previous_score):
    prompt = f"""
You are conducting an adaptive interview.

Role: {role}
Experience: {level}
Interview Type: {interview_type}
Difficulty: {difficulty}

Previous Question:
{previous_question}

Previous Answer:
{previous_answer}

Previous Score: {previous_score}/10

Generate exactly ONE NEW interview question.

Rules:
- Do not repeat or simply rephrase the previous question.
- Consider the candidate's previous answer.
- If the answer was strong (8-10), increase depth or complexity.
- If the answer was weak (0-5), make the next question clearer or slightly easier.
- Otherwise keep a similar difficulty.
- Keep it relevant to the selected role.
- Return ONLY the question.
"""
    return ask_ai(prompt, max_tokens=110)


def evaluate_answer(role, interview_type, difficulty, level, question, answer):
    prompt = f"""
You are an expert professional interviewer.

Role: {role}
Experience: {level}
Interview Type: {interview_type}
Difficulty: {difficulty}

Question:
{question}

Candidate Answer:
{answer}

Evaluate the answer.

Return EXACTLY this structure:

Score: x/10

Strengths:
- Point 1
- Point 2

Areas for Improvement:
- Point 1
- Point 2

Ideal Answer:
Give a concise professional ideal answer.

Interviewer's Comment:
Give one short professional comment.

Rules:
- Score must be between 0 and 10.
- Evaluate the actual answer.
- Be constructive.
- Keep the response concise.
"""
    return ask_ai(prompt, max_tokens=400)


def generate_final_analysis(candidate, role, interview_type, average, history):
    interview_text = "\n\n".join(
        f"""Question {i}:
{item['question']}

Answer:
{item['answer']}

Score: {item['score']}/10

Evaluation:
{item['feedback']}"""
        for i, item in enumerate(history, 1)
    )

    prompt = f"""
You are a professional interview coach.

Candidate: {candidate['name']}
Role: {role}
Interview Type: {interview_type}
Average Score: {average:.1f}/10

Interview:
{interview_text}

Give a concise professional analysis using EXACTLY these sections:

Overall Assessment:

Strengths:
- 3 points

Weak Areas:
- 3 points

Communication:

Technical Knowledge:

Improvement Plan:
- 3 specific recommendations

Final Verdict:
Choose exactly one: Ready, Almost Ready, Needs More Practice.
"""
    return ask_ai(prompt, max_tokens=500)


def generate_study_plan(candidate, role, interview_type, level, average, history, final_analysis):
    interview_text = "\n\n".join(
        f"""Question {i}:
{item['question']}

Answer:
{item['answer']}

Score: {item['score']}/10

Evaluation:
{item['feedback']}"""
        for i, item in enumerate(history, 1)
    )

    prompt = f"""
You are an expert interview coach creating a personalized study plan.

Candidate: {candidate['name']}
Target Role: {role}
Interview Type: {interview_type}
Experience Level: {level}
Average Score: {average:.1f}/10

Interview Results:
{interview_text}

Final AI Analysis:
{final_analysis or "Not available"}

Create a practical 7-day improvement plan based ONLY on the candidate's actual performance.

Return EXACTLY these sections:

Weak Skills:
- 3 specific weak skills or areas
- Keep them relevant to the selected role and interview.

7-Day Study Plan:
Day 1: Topic — specific tasks
Day 2: Topic — specific tasks
Day 3: Topic — specific tasks
Day 4: Topic — specific tasks
Day 5: Topic — specific tasks
Day 6: Topic — specific tasks
Day 7: Topic — specific tasks

Practice Goals:
- 3 measurable goals for the next interview

Rules:
- Prioritize the weakest areas.
- Make the plan suitable for the candidate's experience level.
- Keep each day concise and actionable.
- Do not invent skills unrelated to the interview.
"""
    return ask_ai(prompt, max_tokens=600)


# ============================================================
# VOICE HELPERS
# ============================================================

def create_tts_audio(text):
    """Called only when the user explicitly asks to play the question."""
    audio_buffer = BytesIO()
    tts = gTTS(text=text, lang="en", slow=False)
    tts.write_to_fp(audio_buffer)
    return audio_buffer.getvalue()


def count_filler_words(text):
    """Count complete filler-word occurrences instead of substrings."""
    fillers = [
        "um",
        "uh",
        "like",
        "actually",
        "basically",
        "you know",
        "so"
    ]

    text_lower = text.lower()
    count = 0

    for filler in fillers:
        pattern = r"(?<!\w)" + re.escape(filler) + r"(?!\w)"
        count += len(re.findall(pattern, text_lower))

    return count


def transcribe_audio(audio_value):
    recognizer = sr.Recognizer()
    audio_bytes = audio_value.getvalue()

    with BytesIO(audio_bytes) as audio_file:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)

    return recognizer.recognize_google(audio_data)


# ============================================================
# PDF REPORT
# ============================================================

def pdf_text(value):
    return html.escape(str(value or "")).replace("\n", "<br/>")


def create_pdf_report(
    candidate,
    role,
    interview_type,
    difficulty,
    level,
    scores,
    history,
    final_analysis,
    voice_analysis,
    study_plan=""
):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8
    )

    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=6
    )

    story = [
        Paragraph("AI Interview Preparation System", title_style),
        Paragraph("Professional Interview Performance Report", styles["Heading2"]),
        Spacer(1, 10)
    ]

    story.append(Paragraph("1. Candidate Details", heading_style))

    candidate_data = [
        ["Candidate Name", pdf_text(candidate.get("name"))],
        ["Email", pdf_text(candidate.get("email"))],
        ["Education", pdf_text(candidate.get("education"))],
        ["Target Role", pdf_text(role)],
        ["Experience Level", pdf_text(level)]
    ]

    candidate_table = Table(
        candidate_data,
        colWidths=[2.2 * inch, 3.8 * inch]
    )
    candidate_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, "black"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6)
    ]))
    story.append(candidate_table)

    story.append(Paragraph("2. Interview Details", heading_style))

    details = [
        ["Interview Type", pdf_text(interview_type)],
        ["Difficulty", pdf_text(difficulty)],
        ["Number of Questions", str(len(scores))],
        ["Interview Date", datetime.now().strftime("%d-%m-%Y")]
    ]

    details_table = Table(details, colWidths=[2.2 * inch, 3.8 * inch])
    details_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, "black"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6)
    ]))
    story.append(details_table)

    total_score = sum(scores)
    average = total_score / len(scores) if scores else 0
    best = max(scores) if scores else 0
    lowest = min(scores) if scores else 0

    performance = (
        "Excellent" if average >= 8
        else "Good" if average >= 6
        else "Needs More Practice"
    )

    story.append(Paragraph("3. Performance Summary", heading_style))

    summary = [
        ["Total Score", f"{total_score:.1f}/{len(scores) * 10 if scores else 0:.0f}"],
        ["Average Score", f"{average:.1f}/10"],
        ["Highest Score", f"{best:.1f}/10"],
        ["Lowest Score", f"{lowest:.1f}/10"],
        ["Overall Performance", performance]
    ]

    summary_table = Table(summary, colWidths=[2.2 * inch, 3.8 * inch])
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, "black"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6)
    ]))
    story.append(summary_table)

    story.append(Paragraph("4. Question-wise Performance", heading_style))

    score_data = [["Question", "Score"]]
    for i, score in enumerate(scores, 1):
        score_data.append([f"Question {i}", f"{score:.1f}/10"])

    score_table = Table(score_data, colWidths=[3 * inch, 3 * inch])
    score_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, "black"),
        ("BACKGROUND", (0, 0), (-1, 0), "#DDDDDD"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6)
    ]))
    story.append(score_table)

    story.append(Paragraph("5. Detailed Interview Evaluation", heading_style))

    for i, item in enumerate(history, 1):
        story.append(Paragraph(f"Question {i}", styles["Heading3"]))
        story.append(
            Paragraph(
                f"<b>Question:</b> {pdf_text(item.get('question'))}",
                normal_style
            )
        )
        story.append(
            Paragraph(
                f"<b>Candidate Answer:</b> {pdf_text(item.get('answer'))}",
                normal_style
            )
        )
        story.append(
            Paragraph(
                f"<b>Score:</b> {item.get('score', 0)}/10",
                normal_style
            )
        )
        story.append(
            Paragraph(
                f"<b>AI Evaluation:</b><br/>{pdf_text(item.get('feedback'))}",
                normal_style
            )
        )
        story.append(Spacer(1, 8))

    if voice_analysis:
        story.append(Paragraph("6. Voice Analysis", heading_style))

        total_words = sum(item.get("word_count", 0) for item in voice_analysis)
        total_fillers = sum(item.get("filler_count", 0) for item in voice_analysis)

        voice_data = [
            ["Metric", "Result"],
            ["Total Words Spoken", str(total_words)],
            ["Total Filler Words", str(total_fillers)]
        ]

        voice_table = Table(voice_data, colWidths=[3 * inch, 3 * inch])
        voice_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, "black"),
            ("BACKGROUND", (0, 0), (-1, 0), "#DDDDDD"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("PADDING", (0, 0), (-1, -1), 6)
        ]))
        story.append(voice_table)

    story.append(Paragraph("7. AI Performance Analysis", heading_style))

    if final_analysis:
        story.append(Paragraph(pdf_text(final_analysis), normal_style))
    else:
        story.append(
            Paragraph(
                "Detailed AI analysis was not generated.",
                normal_style
            )
        )

    if study_plan:
        story.append(Paragraph("8. Personalized 7-Day Study Plan", heading_style))
        story.append(Paragraph(pdf_text(study_plan), normal_style))

    story.append(Paragraph("9. Final Verdict", heading_style))

    if average >= 8:
        verdict = "Ready - The candidate demonstrated strong overall interview performance."
    elif average >= 6:
        verdict = "Almost Ready - The candidate has a good foundation but should continue practicing."
    else:
        verdict = "Needs More Practice - The candidate should focus on improving weak areas."

    story.append(Paragraph(verdict, normal_style))
    story.append(Spacer(1, 20))

    footer_style = ParagraphStyle(
        "Footer",
        parent=normal_style,
        alignment=TA_CENTER,
        fontSize=8
    )
    story.append(
        Paragraph(
            "Generated by AI Interview Preparation System",
            footer_style
        )
    )

    doc.build(story)
    buffer.seek(0)

    return buffer.getvalue()




# ============================================================
# COMPUTER SCIENCE / CSE JOB ROLES
# ============================================================

ROLES = [
    "Software Engineer",
    "Software Developer",
    "Full Stack Developer",
    "Frontend Developer",
    "Backend Developer",
    "Web Developer",
    "Mobile App Developer",
    "Android Developer",
    "iOS Developer",
    "Python Developer",
    "Java Developer",
    "C++ Developer",
    "JavaScript Developer",
    "React Developer",
    "Node.js Developer",
    "Data Scientist",
    "Data Analyst",
    "Business Intelligence Analyst",
    "Machine Learning Engineer",
    "AI Engineer",
    "Deep Learning Engineer",
    "NLP Engineer",
    "Computer Vision Engineer",
    "Data Engineer",
    "Big Data Engineer",
    "Database Administrator",
    "Cloud Engineer",
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Cybersecurity Analyst",
    "Cybersecurity Engineer",
    "Security Engineer",
    "Network Engineer",
    "System Administrator",
    "Cloud Solutions Architect",
    "Solutions Architect",
    "QA Engineer",
    "Test Automation Engineer",
    "Embedded Systems Engineer",
    "IoT Engineer",
    "Blockchain Developer",
    "Game Developer",
    "UI/UX Designer",
    "Technical Support Engineer",
    "Software Consultant",
    "Product Engineer"
]

INTERVIEW_TYPES = [
    "HR Interview",
    "Technical Interview",
    "Behavioral Interview",
    "Coding Interview",
    "Mixed Interview"
]

DIFFICULTIES = ["Easy", "Medium", "Hard"]
LEVELS = ["Fresher", "1-2 Years", "3-5 Years", "5+ Years"]


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "candidate": {}, "profile_created": False, "interview_started": False,
    "question_number": 1, "total_score": 0.0, "question": "", "feedback": "",
    "evaluated": False, "answer_text": "", "voice_transcript": "",
    "question_audio": None, "scores": [], "voice_analysis": [],
    "current_voice_analysis": None, "final_analysis": "", "study_plan": "",
    "history": [], "pdf_report": None, "tts_requested": False,
    "current_interview_saved": False, "active_page": "Dashboard",
    "role": "Software Engineer", "interview_type": "Technical Interview",
    "difficulty": "Medium", "level": "Fresher", "theme": "Dark"
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_interview(keep_profile=True):
    candidate = st.session_state.candidate.copy() if keep_profile else {}
    theme = st.session_state.get("theme", "Dark")
    for key in DEFAULTS:
        if key in st.session_state:
            del st.session_state[key]
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state.theme = theme
    if keep_profile:
        st.session_state.candidate = candidate
        st.session_state.profile_created = True


def candidate_history():
    if not st.session_state.profile_created:
        return []
    email = st.session_state.candidate.get("email", "").strip().lower()
    return [x for x in load_history()
            if x.get("candidate", {}).get("email", "").strip().lower() == email]


def performance_label(score):
    return "Excellent" if score >= 8 else ("Good" if score >= 6 else "Needs Practice")


def start_interview(role, interview_type, difficulty, level):
    theme = st.session_state.theme
    reset_interview(True)
    st.session_state.theme = theme
    st.session_state.role = role
    st.session_state.interview_type = interview_type
    st.session_state.difficulty = difficulty
    st.session_state.level = level
    st.session_state.interview_started = True
    st.session_state.active_page = "Dashboard"


# ============================================================
# THEME + VISUAL SYSTEM
# ============================================================

theme = st.session_state.theme
if theme == "Light":
    vars_css = """
    :root { --bg:#f5f7fb; --panel:#ffffff; --panel2:#f0f3f9; --text:#172033; --muted:#667085; --border:#dfe4ec; --soft:#eef2ff; --purple:#6d28d9; --blue:#2563eb; --shadow:0 14px 35px rgba(15,23,42,.08); }
    """
elif theme == "System":
    vars_css = """
    :root { --bg:#f5f7fb; --panel:#ffffff; --panel2:#f0f3f9; --text:#172033; --muted:#667085; --border:#dfe4ec; --soft:#eef2ff; --purple:#6d28d9; --blue:#2563eb; --shadow:0 14px 35px rgba(15,23,42,.08); }
    @media (prefers-color-scheme: dark) { :root { --bg:#080d18; --panel:#0f1829; --panel2:#121e33; --text:#f8fafc; --muted:#94a3b8; --border:rgba(148,163,184,.14); --soft:#1d1b45; --purple:#a855f7; --blue:#3b82f6; --shadow:0 18px 42px rgba(0,0,0,.25); } }
    """
else:
    vars_css = """
    :root { --bg:#080d18; --panel:#0f1829; --panel2:#121e33; --text:#f8fafc; --muted:#94a3b8; --border:rgba(148,163,184,.14); --soft:#1d1b45; --purple:#a855f7; --blue:#3b82f6; --shadow:0 18px 42px rgba(0,0,0,.25); }
    """

if theme == "Light":
    color_scheme_css = ":root { color-scheme: light; }"
elif theme == "System":
    color_scheme_css = ":root { color-scheme: light; } @media (prefers-color-scheme: dark) { :root { color-scheme: dark; } }"
else:
    color_scheme_css = ":root { color-scheme: dark; }"

st.markdown(f"""
<style>
{vars_css}

/* ================= THEME-SAFE BASE ================= */
.stApp {{ background:var(--bg); color:var(--text); }}
.block-container {{ max-width:1450px; padding:4.8rem 1.5rem 3rem !important; }}
#MainMenu, footer {{ visibility:hidden; }}

/* Force Streamlit text to follow the selected theme. */
.stApp, .stApp p, .stApp span, .stApp label, .stApp div,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] strong,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
[data-testid="stTextInputRootElement"] input, textarea {{
    color:var(--text);
}}

/* ================= SIDEBAR ================= */
section[data-testid="stSidebar"] {{
    background:var(--panel);
    border-right:1px solid var(--border);
}}
section[data-testid="stSidebar"] .block-container {{ padding:.9rem .8rem; }}

/* Keep Streamlit's top toolbar clear of the application content. */
header[data-testid="stHeader"] {{ height: 3.25rem; }}
[data-testid="stAppViewContainer"] > .main {{ padding-top: 0 !important; }}

section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ color:var(--text) !important; }}
section[data-testid="stSidebar"] .brand {{ padding:.65rem .55rem 1rem; border-bottom:1px solid var(--border); margin-bottom:.85rem; }}
.brand-mark {{ width:42px;height:42px;border-radius:13px;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--purple),var(--blue));box-shadow:0 9px 25px rgba(109,40,217,.24); }}
.brand-mark svg {{ width:25px;height:25px; }}
.brand-text {{ display:inline-block;vertical-align:top;margin:.15rem 0 0 .55rem;font-weight:850;font-size:1rem;color:var(--text); }}
.brand-sub {{ margin:-.22rem 0 0 3.1rem;color:var(--purple) !important;font-size:.62rem;font-weight:800;letter-spacing:.8px; }}
.profile-mini {{ padding:.8rem;border-radius:15px;background:var(--panel2);border:1px solid var(--border);margin-bottom:.8rem; }}
.profile-dot {{ width:42px;height:42px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#a78bfa,#60a5fa);color:white !important;font-weight:900; }}
.profile-name {{ display:inline-block;vertical-align:top;margin:.1rem 0 0 .5rem;font-weight:800;color:var(--text) !important; }}
.profile-role {{ margin:-.48rem 0 0 3rem;color:var(--muted) !important;font-size:.68rem; }}
.sidebar-label {{ color:var(--muted) !important;font-size:.68rem;text-transform:uppercase;letter-spacing:1px;font-weight:800;margin:.7rem .4rem .35rem; }}

/* Navigation radio */
div[data-testid="stRadio"] label {{ border-radius:10px;padding:.43rem .55rem !important;margin:.08rem 0;color:var(--text) !important; }}
div[data-testid="stRadio"] label p, div[data-testid="stRadio"] label span {{ color:var(--text) !important; }}
div[data-testid="stRadio"] label:hover {{ background:var(--panel2); }}

/* ================= HERO ================= */
.hero {{ border-radius:24px;padding:1.35rem 1.45rem;min-height:230px;background:linear-gradient(115deg,#172554,#4c1d95 52%,#1d4ed8);border:1px solid rgba(167,139,250,.28);box-shadow:0 22px 55px rgba(30,41,59,.22);overflow:hidden; }}
.hero-copy {{ padding:.25rem .25rem; }}
.hero-kicker {{ color:#c4b5fd !important;text-transform:uppercase;letter-spacing:1.5px;font-size:.67rem;font-weight:850; }}
.hero-title {{ color:white !important;font-size:2.15rem;line-height:1.12;font-weight:900;margin:.45rem 0 .5rem; }}
.hero-sub {{ color:rgba(255,255,255,.78) !important;font-size:.9rem;line-height:1.5;max-width:620px; }}
.hero-image {{ width:100%;max-height:225px;object-fit:contain; }}
.pill {{ display:inline-block;padding:.3rem .62rem;border-radius:999px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);color:white !important;font-size:.66rem;margin:.8rem .25rem 0 0; }}

/* ================= SECTIONS / CARDS ================= */
.section-title {{ font-size:1.2rem;font-weight:850;color:var(--text) !important;margin-top:1.15rem; }}
.section-sub {{ color:var(--muted) !important;font-size:.78rem;margin:.15rem 0 .7rem; }}
.card {{ padding:1rem 1.05rem;border-radius:17px;background:var(--panel);border:1px solid var(--border);box-shadow:var(--shadow); }}
.metric-card {{ padding:1rem;border-radius:16px;background:var(--panel);border:1px solid var(--border);box-shadow:var(--shadow); }}
.metric-top {{ color:var(--muted) !important;font-size:.7rem;font-weight:750; }}
.metric-value {{ color:var(--text) !important;font-size:1.65rem;font-weight:900;margin:.2rem 0; }}
.metric-note {{ color:#16a34a !important;font-size:.68rem;font-weight:700; }}
.feature {{ min-height:125px;padding:1rem;border-radius:16px;background:var(--panel);border:1px solid var(--border);box-shadow:var(--shadow); }}
.feature-icon {{ width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--purple),var(--blue));color:white !important;font-size:.75rem;font-weight:900;margin-bottom:.55rem; }}
.feature-title {{ color:var(--text) !important;font-weight:800;font-size:.88rem; }}
.feature-text {{ color:var(--muted) !important;font-size:.73rem;line-height:1.45;margin-top:.25rem; }}
.live {{ padding:.65rem .8rem;border-radius:13px;background:linear-gradient(90deg,rgba(124,58,237,.17),rgba(37,99,235,.1));border:1px solid rgba(139,92,246,.2);display:flex;justify-content:space-between;font-size:.72rem;font-weight:800;color:var(--text) !important; }}
.question-card {{ padding:1.3rem;border-radius:19px;background:var(--panel);border:1px solid rgba(139,92,246,.3);box-shadow:var(--shadow);margin:.7rem 0; }}
.ai-chip {{ color:var(--purple) !important;background:var(--soft);border:1px solid rgba(139,92,246,.2);border-radius:999px;padding:.28rem .55rem;font-size:.64rem;font-weight:850; }}
.question-text {{ color:var(--text) !important;font-size:1.22rem;font-weight:780;line-height:1.5;margin-top:.7rem; }}
.score-card {{ text-align:center;padding:1rem;border-radius:18px;background:var(--panel);border:1px solid var(--border);box-shadow:var(--shadow); }}
.score-ring {{ width:126px;height:126px;border-radius:50%;margin:.55rem auto 1rem;display:flex;align-items:center;justify-content:center;background:conic-gradient(var(--purple) 0 38%,var(--blue) 38% 62%,#22c55e 62% 82%,#f59e0b 82% 100%); }}
.score-inner {{ width:96px;height:96px;border-radius:50%;background:var(--panel);display:flex;align-items:center;justify-content:center;color:var(--text) !important;font-size:1.6rem;font-weight:900; }}
.feedback {{ padding:.9rem 1rem;border-radius:14px;background:var(--soft);border:1px solid rgba(139,92,246,.2);color:var(--text) !important; }}
.footer {{ text-align:center;color:var(--muted) !important;font-size:.7rem;padding-top:1.7rem; }}

/* ================= STREAMLIT CONTROLS ================= */
[data-testid="stWidgetLabel"] p {{ color:var(--text) !important; font-weight:650; }}
[data-baseweb="select"] {{ color:var(--text) !important; }}
div[data-baseweb="select"] > div {{ background:var(--panel2) !important; border:1px solid var(--border) !important; border-radius:10px !important; }}
div[data-baseweb="select"] input, div[data-baseweb="select"] span {{ color:var(--text) !important; }}
div[data-baseweb="select"] svg {{ fill:var(--muted) !important; }}
[data-baseweb="popover"] *, [role="option"] {{ color:var(--text) !important; background:var(--panel) !important; }}
input, textarea {{ background:var(--panel2) !important; color:var(--text) !important; border-color:var(--border) !important; }}
textarea::placeholder, input::placeholder {{ color:var(--muted) !important; opacity:1; }}
.stButton>button,.stDownloadButton>button {{ border-radius:10px;min-height:2.5rem;font-weight:760;color:var(--text) !important;background:var(--panel2);border:1px solid var(--border); }}
.stButton>button:hover,.stDownloadButton>button:hover {{ border-color:var(--purple); }}
div[data-testid="stMetric"] {{ background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:.7rem; }}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"], div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{ color:var(--text) !important; }}

/* Theme-aware native controls. */
{color_scheme_css}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown('''
    <div class="brand">
      <span class="brand-mark">
        <svg viewBox="0 0 32 32" fill="none"><path d="M16 3C10 3 8 7 8 11V21C8 25 11 28 16 28C21 28 24 25 24 21V11C24 7 22 3 16 3Z" stroke="white" stroke-width="2"/><path d="M11 13C13 11 15 11 16 13C17 11 19 11 21 13M12 19C14 21 18 21 20 19" stroke="#DDD6FE" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="16" r="1.5" fill="#60A5FA"/><circle cx="20" cy="16" r="1.5" fill="#C084FC"/></svg>
      </span>
      <span class="brand-text">AI Interview</span>
      <div class="brand-sub">PREPARATION SYSTEM</div>
    </div>
    ''', unsafe_allow_html=True)

    if st.session_state.profile_created:
        name = html.escape(st.session_state.candidate.get("name", "Candidate"))
        education = html.escape(st.session_state.candidate.get("education", "Candidate"))
        st.markdown(f'''<div class="profile-mini"><span class="profile-dot">{name[:1].upper()}</span><span class="profile-name">{name}</span><div class="profile-role">{education}</div></div>''', unsafe_allow_html=True)

        pages = ["Dashboard", "New Interview", "Interview History", "Performance", "Study Plan", "Reports"]
        st.markdown('<div class="sidebar-label">Workspace</div>', unsafe_allow_html=True)
        st.session_state.active_page = st.radio(
            "Workspace", pages,
            index=pages.index(st.session_state.active_page) if st.session_state.active_page in pages else 0,
            label_visibility="collapsed"
        )

        if st.session_state.interview_started:
            st.markdown('<div class="sidebar-label">Live Session</div>', unsafe_allow_html=True)
            st.progress(min(st.session_state.question_number / TOTAL_QUESTIONS, 1.0))
            st.caption(f"Question {min(st.session_state.question_number, TOTAL_QUESTIONS)} of {TOTAL_QUESTIONS}")

        st.markdown('<div class="sidebar-label">Appearance</div>', unsafe_allow_html=True)
        chosen_theme = st.selectbox("Theme", ["Dark", "Light", "System"], index=["Dark","Light","System"].index(st.session_state.theme), label_visibility="collapsed")
        if chosen_theme != st.session_state.theme:
            st.session_state.theme = chosen_theme
            st.rerun()

        if st.button("Change Profile", use_container_width=True):
            reset_interview(False)
            st.rerun()

# ============================================================
# PROFILE

if not st.session_state.profile_created:
    st.markdown('''<div class="hero"><div class="hero-copy"><div class="hero-kicker">AI-powered career preparation</div><div class="hero-title">Build confidence before the real interview.</div><div class="hero-sub">Set up your profile once, choose what you want to practice, and let the AI interviewer guide the rest.</div><span class="pill">AI Interviewer</span><span class="pill">Voice Practice</span><span class="pill">Performance Analytics</span></div></div>''', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Create your candidate profile</div><div class="section-sub">Enter your details and interview preferences in one simple step.</div>', unsafe_allow_html=True)

    # Deliberately stacked: Name → Email → Education → Role → Interview Type → Difficulty → Experience.
    with st.form("candidate_profile_form", clear_on_submit=False):
        name = st.text_input("Full Name", placeholder="e.g. Navreen Kaur")
        email = st.text_input("Email", placeholder="e.g. navreen@example.com")
        education = st.text_input("Education / Qualification", placeholder="e.g. B.Tech CSE")
        role = st.selectbox("Preferred Job Role", ROLES)
        interview_type = st.selectbox("Preferred Interview Type", INTERVIEW_TYPES)
        difficulty = st.select_slider("Preferred Difficulty", options=DIFFICULTIES, value="Medium")
        level = st.selectbox("Experience Level", LEVELS)

        submitted = st.form_submit_button("Create My Profile & Continue", use_container_width=True)

    if submitted:
        if not name.strip() or not email.strip() or not education.strip():
            st.warning("Please complete all profile fields.")
        else:
            st.session_state.candidate = {
                "name": name.strip(),
                "email": email.strip(),
                "education": education.strip()
            }
            st.session_state.role = role
            st.session_state.interview_type = interview_type
            st.session_state.difficulty = difficulty
            st.session_state.level = level
            st.session_state.profile_created = True
            st.session_state.active_page = "Dashboard"
            st.rerun()

    st.stop()


# ============================================================
# DASHBOARD
# ============================================================

def render_dashboard():
    hist=candidate_history()
    latest=float(hist[-1].get("average_score",0)) if hist else 0
    best=max([float(x.get("average_score",0)) for x in hist],default=0)
    avg=sum(float(x.get("average_score",0)) for x in hist)/len(hist) if hist else 0
    delta=latest-float(hist[-2].get("average_score",0)) if len(hist)>=2 else 0
    name=html.escape(st.session_state.candidate.get("name","Candidate"))

    if st.session_state.interview_started:
        render_live_interview()
        return

    h1,h2=st.columns([1.55,.85])
    with h1:
        st.markdown(f'''<div class="hero"><div class="hero-copy"><div class="hero-kicker">AI-powered career preparation</div><div class="hero-title">Welcome back, {name}.</div><div class="hero-sub">Let's ace your next interview. Practice smarter, improve faster and turn every session into measurable progress.</div><span class="pill">Personalized</span><span class="pill">AI Feedback</span><span class="pill">7-Day Plan</span></div></div>''',unsafe_allow_html=True)
    with h2:
        st.markdown(f'<div class="hero" style="padding:.4rem;display:flex;align-items:center;justify-content:center;"><img class="hero-image" src="data:image/svg+xml;base64,{HERO_SVG_B64}"></div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">Your performance snapshot</div><div class="section-sub">A clean overview of your recent interview activity.</div>',unsafe_allow_html=True)
    vals=[("Overall Score",f"{latest:.1f}/10",("↗ %.1f this round"%delta) if delta>0 else "Keep building consistency"),("Interviews Taken",str(len(hist)),"Practice makes progress"),("Average Score",f"{avg:.1f}/10","Across saved interviews"),("Best Score",f"{best:.1f}/10","Personal best")]
    cols=st.columns(4)
    for col,(title,val,note) in zip(cols,vals):
        with col: st.markdown(f'<div class="metric-card"><div class="metric-top">{title}</div><div class="metric-value">{val}</div><div class="metric-note">{note}</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">Start your next practice</div><div class="section-sub">Set your role, interview type and difficulty, then let the AI interviewer guide you.</div>',unsafe_allow_html=True)
    a,b,c=st.columns([1.15,1,1])
    with a:
        st.markdown('<div class="feature"><div class="feature-icon">GO</div><div class="feature-title">Smart Interview</div><div class="feature-text">Five adaptive questions with instant scoring, feedback and a final performance review.</div></div>',unsafe_allow_html=True)
        if st.button("Start New Interview",use_container_width=True): st.session_state.active_page="New Interview"; st.rerun()
    with b:
        st.markdown('<div class="feature"><div class="feature-icon">AN</div><div class="feature-title">Performance</div><div class="feature-text">See your score progression and understand where your interview skills are improving.</div></div>',unsafe_allow_html=True)
        if st.button("View Performance",use_container_width=True): st.session_state.active_page="Performance"; st.rerun()
    with c:
        st.markdown('<div class="feature"><div class="feature-icon">PL</div><div class="feature-title">Study Plan</div><div class="feature-text">Turn your latest interview weaknesses into a focused seven-day learning plan.</div></div>',unsafe_allow_html=True)
        if st.button("Open Study Plan",use_container_width=True): st.session_state.active_page="Study Plan"; st.rerun()

    if hist:
        st.markdown('<div class="section-title">Recent interviews</div>',unsafe_allow_html=True)
        for item in reversed(hist[-3:]):
            score=float(item.get("average_score",0))
            st.markdown(f'<div class="card" style="margin:.45rem 0;"><b>{item.get("role","Interview")}</b> <span style="color:var(--muted)">• {item.get("interview_type","Interview")} • {item.get("date","-")}</span><span style="float:right;font-weight:850;color:var(--purple)">{score:.1f}/10</span></div>',unsafe_allow_html=True)


def render_new_interview():
    if st.session_state.interview_started:
        render_live_interview(); return
    st.markdown('<div class="section-title">New Interview</div><div class="section-sub">Configure a realistic practice session.</div>',unsafe_allow_html=True)
    a,b=st.columns([1.25,.75])
    with a:
        role=st.selectbox("Job Role",ROLES,index=ROLES.index(st.session_state.role))
        itype=st.selectbox("Interview Type",INTERVIEW_TYPES,index=INTERVIEW_TYPES.index(st.session_state.interview_type))
        difficulty=st.select_slider("Difficulty",DIFFICULTIES,value=st.session_state.difficulty)
        level=st.selectbox("Experience Level",LEVELS,index=LEVELS.index(st.session_state.level))
        if st.button("Start Smart Interview",use_container_width=True): start_interview(role,itype,difficulty,level); st.rerun()
    with b:
        st.markdown('<div class="card"><b>What you get</b><br><br>Adaptive questions<br><br>Optional voice answers<br><br>AI scoring & feedback<br><br>Performance analysis<br><br>Personalized 7-day plan<br><br>Professional PDF report</div>',unsafe_allow_html=True)


def render_live_interview():
    qn=st.session_state.question_number; role=st.session_state.role; itype=st.session_state.interview_type
    st.markdown(f'<div class="live"><span>LIVE AI INTERVIEW</span><span>Question {qn} of {TOTAL_QUESTIONS}</span></div>',unsafe_allow_html=True)
    st.progress(min(qn/TOTAL_QUESTIONS,1.0))
    if not st.session_state.question:
        with st.spinner("Preparing your question..."):
            st.session_state.question=generate_question(role,itype,st.session_state.difficulty,st.session_state.level)
    st.markdown(f'<div class="question-card"><span class="ai-chip">AI INTERVIEWER</span><div class="question-text">{html.escape(st.session_state.question)}</div></div>',unsafe_allow_html=True)
    if st.button("Play Question",key=f"play_{qn}"):
        try: st.session_state.question_audio=create_tts_audio(st.session_state.question); st.rerun()
        except Exception as e: st.error(f"Audio error: {e}")
    if st.session_state.question_audio: st.audio(st.session_state.question_audio,format="audio/mp3")

    mode=st.radio("Answer mode",["Type Answer","Voice Answer"],horizontal=True,key=f"mode_{qn}")
    if mode=="Type Answer":
        ans=st.text_area("Your answer",height=160,placeholder="Type your answer here...",key=f"answer_{qn}")
        if ans.strip(): st.session_state.answer_text=ans.strip()
    else:
        audio=st.audio_input("Record your answer",sample_rate=16000,key=f"voice_{qn}")
        if audio:
            st.audio(audio,format="audio/wav")
            if st.button("Convert Voice to Text",key=f"transcribe_{qn}"):
                try:
                    with st.spinner("Converting voice to text..."): transcript=transcribe_audio(audio)
                    st.session_state.voice_transcript=transcript; st.session_state.answer_text=transcript
                    st.session_state.current_voice_analysis={"word_count":len(transcript.split()),"filler_count":count_filler_words(transcript)}
                    st.success("Voice converted successfully.")
                except Exception as e: st.error(f"Voice conversion error: {e}")
        if st.session_state.voice_transcript:
            st.markdown(f'<div class="feedback"><b>Transcript</b><br>{html.escape(st.session_state.voice_transcript)}</div>',unsafe_allow_html=True)
            x,y=st.columns(2)
            x.metric("Words",st.session_state.current_voice_analysis.get("word_count",0)); y.metric("Filler Words",st.session_state.current_voice_analysis.get("filler_count",0))

    if st.session_state.answer_text.strip() and not st.session_state.evaluated:
        if st.button("Evaluate My Answer",use_container_width=True):
            try:
                with st.spinner("AI is evaluating your answer..."):
                    feedback=evaluate_answer(role,itype,st.session_state.difficulty,st.session_state.level,st.session_state.question,st.session_state.answer_text)
                match=re.search(r"Score:\s*(\d+(?:\.\d+)?)",feedback,re.I)
                if not match: st.error("AI response did not contain a valid score.")
                else:
                    score=max(0,min(float(match.group(1)),10)); st.session_state.feedback=feedback; st.session_state.total_score+=score; st.session_state.scores.append(score)
                    if st.session_state.voice_transcript and st.session_state.current_voice_analysis: st.session_state.voice_analysis.append(st.session_state.current_voice_analysis.copy())
                    st.session_state.history.append({"question":st.session_state.question,"answer":st.session_state.answer_text,"score":score,"feedback":feedback})
                    st.session_state.evaluated=True; st.rerun()
            except Exception as e: st.error(f"Evaluation error: {e}")
    if st.session_state.feedback:
        st.markdown('<div class="section-title">AI Evaluation</div>',unsafe_allow_html=True)
        st.markdown(f'<div class="feedback">{html.escape(st.session_state.feedback).replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)
    if st.session_state.evaluated:
        if qn<TOTAL_QUESTIONS:
            if st.button("Next Smart Question",use_container_width=True):
                prevq=st.session_state.question; preva=st.session_state.answer_text; prevs=st.session_state.scores[-1]
                with st.spinner("Adapting your next question..."): nxt=generate_adaptive_question(role,itype,st.session_state.difficulty,st.session_state.level,prevq,preva,prevs)
                st.session_state.question_number+=1; st.session_state.question=nxt; st.session_state.feedback=""; st.session_state.evaluated=False; st.session_state.answer_text=""; st.session_state.voice_transcript=""; st.session_state.question_audio=None; st.session_state.current_voice_analysis=None; st.rerun()
        else: render_final_dashboard()


def render_final_dashboard():
    average=st.session_state.total_score/TOTAL_QUESTIONS
    st.success("Interview completed successfully.")
    a,b=st.columns([1,1.25])
    with a:
        st.markdown(f'<div class="score-card"><div class="metric-top">OVERALL SCORE</div><div class="score-ring"><div class="score-inner">{average:.1f}/10</div></div><b>{performance_label(average)}</b></div>',unsafe_allow_html=True)
    with b:
        st.empty()

    if st.session_state.voice_analysis:
        st.markdown('<div class="section-title">Voice performance</div><div class="section-sub">Useful speaking metrics from your recorded answers.</div>',unsafe_allow_html=True)
        words=sum(x.get("word_count",0) for x in st.session_state.voice_analysis); fillers=sum(x.get("filler_count",0) for x in st.session_state.voice_analysis)
        x,y=st.columns(2); x.metric("Words Spoken",words); y.metric("Filler Words",fillers)

    st.markdown('<div class="section-title">AI Performance Analysis</div>',unsafe_allow_html=True)
    if not st.session_state.final_analysis:
        if st.button("Generate Detailed AI Analysis",use_container_width=True):
            with st.spinner("Analyzing your complete interview..."):
                st.session_state.final_analysis=generate_final_analysis(st.session_state.candidate,st.session_state.role,st.session_state.interview_type,average,st.session_state.history)
                st.rerun()
    if st.session_state.final_analysis: st.markdown(f'<div class="feedback">{html.escape(st.session_state.final_analysis).replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">Personalized 7-Day Study Plan</div>',unsafe_allow_html=True)
    if not st.session_state.study_plan:
        if st.button("Generate My Study Plan",use_container_width=True):
            with st.spinner("Building your plan..."):
                st.session_state.study_plan=generate_study_plan(st.session_state.candidate,st.session_state.role,st.session_state.interview_type,st.session_state.level,average,st.session_state.history,st.session_state.final_analysis)
                st.rerun()
    if st.session_state.study_plan: st.markdown(f'<div class="card">{html.escape(st.session_state.study_plan).replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)

    x,y=st.columns(2)
    with x:
        if st.button("Save Interview to History",use_container_width=True):
            if not st.session_state.current_interview_saved:
                h=load_history(); h.append({"candidate":st.session_state.candidate,"date":datetime.now().strftime("%d-%m-%Y %H:%M"),"role":st.session_state.role,"interview_type":st.session_state.interview_type,"difficulty":st.session_state.difficulty,"level":st.session_state.level,"total_score":round(st.session_state.total_score,1),"average_score":round(average,1),"scores":st.session_state.scores,"performance":performance_label(average),"final_analysis":st.session_state.final_analysis,"study_plan":st.session_state.study_plan,"voice_analysis":st.session_state.voice_analysis}); save_history(h); st.session_state.current_interview_saved=True; st.success("Interview saved.")
            else: st.info("This interview is already saved.")
    with y:
        if st.button("Generate Professional Report",use_container_width=True):
            st.session_state.pdf_report=create_pdf_report(st.session_state.candidate,st.session_state.role,st.session_state.interview_type,st.session_state.difficulty,st.session_state.level,st.session_state.scores,st.session_state.history,st.session_state.final_analysis,st.session_state.voice_analysis,st.session_state.study_plan); st.success("Report generated.")
    if st.session_state.pdf_report: st.download_button("Download Interview Report PDF",data=st.session_state.pdf_report,file_name="AI_Interview_Performance_Report.pdf",mime="application/pdf",use_container_width=True)
    if st.button("Start Another Interview",use_container_width=True): reset_interview(True); st.session_state.active_page="New Interview"; st.rerun()


def render_history_page():
    hist=candidate_history(); st.markdown('<div class="section-title">Interview History</div><div class="section-sub">Review your saved sessions and scores.</div>',unsafe_allow_html=True)
    if not hist: st.info("No saved interviews yet."); return
    for i,item in enumerate(reversed(hist),1):
        score=float(item.get("average_score",0))
        with st.expander(f"Interview {i}  •  {item.get('date','-')}  •  {item.get('role','-')}  •  {score:.1f}/10"):
            a,b,c,d=st.columns(4); a.metric("Score",f"{score:.1f}/10"); b.metric("Type",item.get("interview_type","-")); c.metric("Difficulty",item.get("difficulty","-")); d.metric("Result",item.get("performance","-"))
            if item.get("final_analysis"): st.markdown(f'<div class="feedback">{html.escape(item["final_analysis"]).replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)
            if item.get("study_plan"): st.write(item["study_plan"])


def render_performance_page():
    hist=candidate_history(); st.markdown('<div class="section-title">Performance Analytics</div><div class="section-sub">See your improvement across saved interviews.</div>',unsafe_allow_html=True)
    if not hist: st.info("Complete and save an interview to unlock analytics."); return
    scores=[float(x.get("average_score",0)) for x in hist]; latest=scores[-1]; best=max(scores); avg=sum(scores)/len(scores)
    a,b,c,d=st.columns(4); a.metric("Interviews",len(scores)); b.metric("Latest",f"{latest:.1f}/10"); c.metric("Best",f"{best:.1f}/10"); d.metric("Average",f"{avg:.1f}/10")
    st.markdown("### Score progression"); st.line_chart({"Average Score":scores},height=300)
    if len(scores)>=2:
        change=scores[-1]-scores[-2]
        (st.success if change>0 else st.warning if change<0 else st.info)(f"{'You improved' if change>0 else 'Your score decreased' if change<0 else 'Your score stayed the same'} by {abs(change):.1f} points in your latest interview.")
    voice=[]
    for item in hist: voice.extend(item.get("voice_analysis",[]))
    if voice:
        st.markdown("### Voice performance"); x,y=st.columns(2); x.metric("Words Spoken",sum(v.get("word_count",0) for v in voice)); y.metric("Filler Words",sum(v.get("filler_count",0) for v in voice))


def render_study_page():
    st.markdown('<div class="section-title">Personalized Study Plan</div><div class="section-sub">Your latest plan focuses on the areas that need the most attention.</div>',unsafe_allow_html=True)
    if st.session_state.study_plan: st.markdown(f'<div class="card">{html.escape(st.session_state.study_plan).replace(chr(10),"<br>")}</div>',unsafe_allow_html=True); return
    for item in reversed(candidate_history()):
        if item.get("study_plan"): st.markdown(f'<div class="card">{html.escape(item["study_plan"]).replace(chr(10),"<br>")}</div>',unsafe_allow_html=True); return
    st.info("Complete an interview and generate a study plan to see it here.")


def render_reports_page():
    hist=candidate_history(); st.markdown('<div class="section-title">Reports</div><div class="section-sub">Professional PDF reports for completed interviews.</div>',unsafe_allow_html=True)
    if not hist: st.info("No saved interviews yet."); return
    for i,item in enumerate(reversed(hist),1):
        score=float(item.get("average_score",0))
        with st.expander(f"Report {i}  •  {item.get('date','-')}  •  {item.get('role','-')}  •  {score:.1f}/10"):
            st.write(f"Performance: {item.get('performance','-')}")
            st.write("Generate a fresh PDF from the completed interview screen to include all current details.")


# ============================================================
# ROUTER
# ============================================================

if st.session_state.active_page=="Dashboard": render_dashboard()
elif st.session_state.active_page=="New Interview": render_new_interview()
elif st.session_state.active_page=="Interview History": render_history_page()
elif st.session_state.active_page=="Performance": render_performance_page()
elif st.session_state.active_page=="Study Plan": render_study_page()
elif st.session_state.active_page=="Reports": render_reports_page()

st.markdown('<div class="footer">AI Interview Preparation System • Practice • Analyze • Improve</div>',unsafe_allow_html=True)
