# 🎯 AI Interview Preparation System

An AI-powered interview practice platform that helps candidates prepare for **technical, HR, behavioral, coding, and mixed interviews** through interactive questions, AI-based feedback, voice practice, performance analytics, and personalized study planning.

---

## 🚀 Live Demo

👉 [**Open the deployed application**](https://29sjuv75xffct3bw87vgwu.streamlit.app/)

---

## 📌 Project Overview

The **AI Interview Preparation System** is a Generative AI project built with **Python and Streamlit**. It simulates an interview experience by generating role-specific questions, evaluating candidate responses, and providing actionable feedback.

The system is designed for **students, freshers, and job seekers** who want to improve their interview confidence and identify areas for improvement.

---

## ✨ Key Features

### 👤 Candidate Profile

* Enter candidate name, email, and educational qualification
* Select preferred job role
* Select experience level
* Choose interview type
* Select interview difficulty level

### 🧠 AI-Powered Interview Practice

* Generates interview questions using an AI model
* Supports multiple interview categories:

  * HR Interview
  * Technical Interview
  * Behavioral Interview
  * Coding Interview
  * Mixed Interview
* Supports different difficulty levels:

  * Easy
  * Medium
  * Hard
* Provides adaptive questions based on the interview context and previous responses

### ✍️ Answer Evaluation

* Accepts typed answers
* Evaluates answers using AI
* Provides a score out of 10
* Generates feedback and suggestions for improvement

### 🎙️ Voice Interview Support

Allows candidates to submit voice answers.

The system converts recorded speech into text and calculates basic speaking metrics, including:

* Word count
* Filler-word count

It also provides **text-to-speech support** for generated content.

### 📊 Performance Analytics

* Displays the overall interview score
* Shows performance summaries
* Tracks interview performance across saved sessions
* Provides basic voice-performance metrics

### 📚 Personalized 7-Day Study Plan

Generates a focused study plan based on interview performance.

The system:

* Identifies areas that require improvement
* Creates a seven-day learning structure
* Provides targeted preparation recommendations

### 📄 Professional Interview Report

Generates a downloadable **PDF interview report** containing:

* Candidate information
* Interview details
* Performance summary
* Question and answer information
* Voice analysis
* AI-generated performance analysis
* Personalized study plan

### 🗂️ Interview History

* Saves completed interview sessions locally
* Allows users to review previous scores and interview details
* Uses a local JSON file for history storage

---

## 🛠️ Technologies Used

| Technology            | Purpose                                 |
| --------------------- | --------------------------------------- |
| **Python**            | Core application development            |
| **Streamlit**         | Web interface and application framework |
| **OpenRouter API**    | Access to Generative AI models          |
| **OpenAI Python SDK** | API communication                       |
| **python-dotenv**     | Environment variable management         |
| **SpeechRecognition** | Speech-to-text processing               |
| **gTTS**              | Text-to-speech generation               |
| **ReportLab**         | PDF report generation                   |
| **JSON**              | Local interview-history storage         |

---

## 🏗️ Application Workflow

```text
Candidate Profile
       ↓
Interview Configuration
       ↓
AI Question Generation
       ↓
Candidate Answer
       ↓
Text or Voice Input
       ↓
AI Evaluation and Scoring
       ↓
Adaptive Interview Questions
       ↓
Final Performance Analysis
       ↓
Personalized 7-Day Study Plan
       ↓
Professional PDF Report
```

---

## 📂 Project Structure

```text
AI-Interview-Preparation-System/
│
├── app.py                  # Main Streamlit application
├── requirements.txt        # Required Python packages
├── interview_history.json  # Generated locally to store history
├── .gitignore              # Files excluded from Git
└── README.md               # Project documentation
```

> **Note:** `interview_history.json` is generated while using the application and may not exist in the repository initially.

---

## ⚙️ Local Installation

### 1. Clone the Repository

```bash
git clone https://github.com/NavreenKaur06/AI-Interview-Preparation-System.git
```

### 2. Open the Project Directory

```bash
cd AI-Interview-Preparation-System
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

### 4. Activate the Virtual Environment

**Windows:**

```bash
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure the API Key

Create a `.env` file in the project directory:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

> ⚠️ **Never upload your `.env` file or API key to GitHub.**

### 7. Run the Application

```bash
streamlit run app.py
```

The application will open in your browser at a local Streamlit URL.

---

## ☁️ Streamlit Cloud Deployment

1. Push `app.py`, `requirements.txt`, and `README.md` to GitHub.
2. Open **Streamlit Community Cloud**.
3. Connect your GitHub repository.
4. Select the main branch.
5. Select `app.py` as the main file.
6. Choose **Python 3.11** if available.
7. Add the following secret in the Streamlit Cloud settings:

```toml
OPENROUTER_API_KEY = "your_openrouter_api_key"
```

8. Deploy the application.

---

## 🔐 Security Notes

* Store API keys in environment variables or Streamlit Secrets.
* Do not commit `.env` files to GitHub.
* Do not expose API keys in screenshots, code, or public documentation.
* The current application uses local JSON storage for interview history.
* The project does not require a login system or database for basic local usage.

---

## ⚠️ Current Limitations

* AI-generated scores and feedback may not always match human evaluator judgments.
* Voice metrics are basic and should be treated as supportive indicators rather than definitive communication assessments.
* Interview history is stored locally in a JSON file.
* The application depends on the availability and rate limits of the selected OpenRouter model.
* The system is intended for practice and preparation, not as a replacement for a professional interviewer.

---

## 🔮 Future Enhancements

* User authentication and cloud-based profile storage
* MongoDB or another database for persistent multi-user history
* Resume-based interview questions
* More detailed technical-answer evaluation
* Improved speech analysis, including pace and pauses
* Interview comparison and progress charts
* Multilingual interview support
* Admin dashboard for monitoring model quality and evaluation consistency

---

## 🎓 Academic Project

This project was developed as a **Generative AI application** to demonstrate:

* Prompt engineering
* API integration with an LLM provider
* Interactive web application development
* AI-based response evaluation
* Voice input processing
* Automated report generation
* Performance-based study planning

---

## 👩‍💻 Author

**Navreen Kaur**

**GitHub:** [NavreenKaur06](https://github.com/NavreenKaur06)

---

⭐ **If you find this project useful, consider giving the repository a star.**
