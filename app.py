#Import Liberaries
import streamlit as st
from resume import Rag, Retrieve, pdf_extract, analyze, extract_skills
from groq import Groq
import os
import time
import re
from dotenv import load_dotenv
# to access camera and audio
from streamlit_webrtc import webrtc_streamer

load_dotenv()
#Page Description
st.set_page_config(page_title="AI Interview Coach",layout="wide")
st.markdown("<h1 style='text-align:center;'>AI Interview Coach</h1>",unsafe_allow_html=True)
#Background
st.markdown("""
<style>
.stApp {
    background: linear-gradient(
        135deg,
        #667eea 0%,
        #764ba2 100%
    );
}
</style>
""", unsafe_allow_html=True)
#side background
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #4C51BF 0%,
        #553C9A 100%
    );
}
</style>
""", unsafe_allow_html=True)
#video css
st.markdown("""
<style>
video {
    width:100% !important;
    height:350px !important;
    object-fit:cover !important;
    border-radius:15px;
}
</style>
""", unsafe_allow_html=True)
# Session States
if "audio_data" not in st.session_state:
    st.session_state.audio_data = None
if "questions" not in st.session_state:
    st.session_state.questions = []
if "qno" not in st.session_state:
    st.session_state.qno = 0
if "answer" not in st.session_state:
    st.session_state.answer = ""
if "scores" not in st.session_state:
    st.session_state.scores = []
if "page" not in st.session_state:
    st.session_state.page = "interview"
# API Client
client = Groq(api_key=os.getenv("Groq_API_KEY"))
# Inputs
col1, col2 = st.columns(2)
with col1:
    data_path = st.file_uploader("Upload Your Resume",type=["pdf"])
with col2:
    query = st.text_area("Enter Your Job Description",height=150)

# Speech to Text function
from streamlit_mic_recorder import mic_recorder
import tempfile

# Generate Questions
if st.button("Record Your AI Interview"):
        st.session_state.page = "interview"
        if data_path is not None and query:
            pdf_text = pdf_extract(data_path)
            index, resume = Rag(pdf_text)
            context = Retrieve(query, index, resume)
            label = analyze(query, context)
            score = label * 100
            if score >= 35:
                skills, projects = extract_skills(context)
                prompt = f"""
Generate exactly 10 interview questions.

Skills:
{skills}

Projects:
{projects}

Difficulty: Fresher

Rules:
- One question per line
- No headings
- No explanations
"""
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    temperature=0.3,
                    max_tokens=1200,
                    messages=[{"role": "user","content": prompt}])
                questions = [
                    q.strip()
                    for q in response.choices[0].message.content.split("\n")
                    if q.strip()
                ]
                st.session_state.questions = questions
                st.session_state.qno = 0
                st.session_state.answer = ""
                st.session_state.scores = []
                st.success("Questions Generated")
            else:
                st.warning("Resume match score is too low?Improve your resume then try again")
        else:
            st.error("Please Upload Resume and Enter Job Description")
# Interview Section
if (st.session_state.page == "interview" and st.session_state.questions and st.session_state.qno < len(st.session_state.questions)):
    current_question = st.session_state.questions[st.session_state.qno]
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown(
        f"""
        <div style="
            background:white;
            height:350px;
            padding:20px;
            border-radius:15px;
            color:black;
            font-size:22px;
            box-shadow:0px 4px 10px rgba(0,0,0,0.2);
            overflow-y:auto;
        ">
            <h3>Question {st.session_state.qno + 1}</h3>
            <p>{current_question}</p>
        </div>
        """,unsafe_allow_html=True)
    with right_col:
        webrtc_streamer(key="camera",media_stream_constraints={"video": True,"audio": False})
        audio = mic_recorder(start_prompt="🎤 Start Recording",stop_prompt="⏹ Stop Recording",key=f"mic_{st.session_state.qno}")
        if audio and "bytes" in audio:
            st.session_state.audio_data = audio["bytes"]
            st.success("Audio captured successfully")
    # Record Answer
    col1, col2 = st.columns(2)
    with col1:
        record_btn = st.button("Record Answer",use_container_width=True)
    with col2:
        next_btn = st.button("Next Question",use_container_width=True)
    if record_btn:
        if not st.session_state.audio_data:
            st.warning("Please record audio first")
            st.stop()
        with tempfile.NamedTemporaryFile(delete=False,suffix=".wav") as tmp:
                tmp.write(st.session_state.audio_data)
                audio_path = tmp.name
        with open(audio_path, "rb") as file:
                transcript = client.audio.transcriptions.create(file=file,model="whisper-large-v3")
        answer = transcript.text
        st.session_state.answer = answer
        st.write("### Your Answer")
        st.write(answer)
        evaluation_prompt = f"""
Question:
{current_question}

Candidate Answer:
{answer}

Evaluate the answer and return:

Technical Score: X/10
Communication Score: X/10
Confidence Score: X/10

Feedback:
Strengths:
Areas for Improvement:
"""

        evaluation = client.chat.completions.create(model="llama-3.1-8b-instant",
                                                    temperature=0.3,
                                                    messages=[{"role": "user",
                                                               "content": evaluation_prompt}])
        st.write("AI Feedback")
        feedback=evaluation.choices[0].message.content
        st.write(evaluation.choices[0].message.content)
        technical = re.search(r"Technical Score:\s*(\d+)",feedback)
        communication = re.search(r"Communication Score:\s*(\d+)",feedback)
        confidence = re.search(r"Confidence Score:\s*(\d+)",feedback)
        if technical and communication and confidence:
                tech = int(technical.group(1))
                comm = int(communication.group(1))
                conf = int(confidence.group(1))
                overall = (tech + comm + conf) / 3
                st.session_state.scores.append(overall)
                st.metric("Current Score",f"{overall:.1f}/10")
        else:
            st.warning("No voice detected")
    # Next Question
    if next_btn:
        st.session_state.audio_data = None
        if (st.session_state.qno< len(st.session_state.questions) - 1):
            st.session_state.qno += 1
            st.rerun()
        else:
            st.success("Interview Completed!")
            if st.session_state.scores:
                final_score = (sum(st.session_state.scores)/ len(st.session_state.scores))
                st.metric("Final Interview Score",f"{final_score:.1f}/10")

# Resume Analysis
if st.sidebar.button("Analyze Resume"):
    st.session_state.page = "analysis"
    st.rerun()
if st.session_state.page == "analysis":
    st.session_state.questions = []
    st.session_state.qno = 0
    st.session_state.answer = ""
    st.session_state.scores = []
    if data_path is not None and query:
        pdf_text = pdf_extract(data_path)
        index, resume = Rag(pdf_text)
        context = Retrieve(query, index, resume)
        label = analyze(query, context)
        score = label * 100
        if score >= 35:
            context = "\n".join(context)
            prompt = f"""
Extract:

1. Technical Skills
2. Projects
3. Experience
4. Education

Resume:
{context}

Return in structured format.
"""
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=1200,
                messages=[{"role": "user","content": prompt}])
            st.write(response.choices[0].message.content)
        else:
            st.warning("Resume match score is too low/Please Upgrade your Resume")
    else:
        st.error("Please Upload Your Resume and Job Description")
# Sidebar Instructions
with st.sidebar:
    st.title("📋 How to Use")

    st.markdown("""
## 🚀 AI Interview Coach Guide

---

### 📌 Step 1: Upload Resume
Upload your **PDF Resume**

---

### 📌 Step 2: Enter Job Description
Paste the **Job Description (JD)** you want to prepare for

---

### 📌 Step 3: Generate Interview
Click **"Record Your AI Interview"**

✔ AI will:
- Extract skills & projects from resume  
- Match resume with JD  
- Generate 10 interview questions  

---

### 📌 Step 4: Start Interview
- Camera will open (for monitoring only)
- Use microphone to record your answer

---

### 📌 Step 5: Save Answer
Click **"Save Recorded Answer"**

✔ AI will:
- Convert speech → text (Whisper AI)  
- Evaluate your response  

---

### 📌 Step 6: Get Feedback
You will receive:
- 🎯 Technical Score  
- 🗣 Communication Score  
- 💡 Confidence Score  
- 🧠 Detailed AI Feedback  

---

### 📌 Step 7: Next Question
Click **"Next Question"** to continue interview

---

### 📌 Step 8: Complete Interview
Repeat until all questions are finished

---

## 🏁 Final Result
At the end you get:
- ⭐ Final Interview Score  
- 📊 Average Performance Rating  

---

## 📄 Resume Analysis Mode
Click **"Analyze Resume"**

You will get:
- Skills Extraction  
- Projects Overview  
- Experience Summary  
- Education Details  
""",unsafe_allow_html=True)
