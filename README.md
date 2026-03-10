<div align="center">

#  FocusPilot

### AI-Powered Productivity OS — Learn Your Patterns. Block Distractions. Own Your Focus.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-focuspilot.vercel.app-brightgreen?style=for-the-badge&logo=vercel)](https://focuspilot.vercel.app)
[![GitHub](https://img.shields.io/badge/GitHub-FocusPilot-black?style=for-the-badge&logo=github)](https://github.com/olatunjitobiloba/FocusPilot)
[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-35%20Passing-success?style=for-the-badge)](https://github.com/olatunjitobiloba/FocusPilot)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Tests-14%20Passing-success?style=for-the-badge)](https://github.com/olatunjitobiloba/FocusPilot)

</div>

---

##  Demo

[![FocusPilot Demo](https://img.youtube.com/vi/y9jI2dACznU/0.jpg)](https://www.youtube.com/watch?v=y9jI2dACznU)

> 👆 Click to watch the full demo

---

## 🧠 What is FocusPilot?

FocusPilot is an **AI-powered productivity operating system** that doesn't just block distractions — it *learns you.*

Most focus tools treat everyone the same. FocusPilot builds your **personal productivity fingerprint** — detecting procrastination in real-time, blocking distracting sites adaptively, and generating optimized schedules based on your actual behavioral patterns.

> You don't have a focus problem. You have a system problem. FocusPilot is that system.

---

##  Features Built (MVP)

| Feature | Status |
|--------|--------|
| Full Authentication System (JWT) |  Done |
| Session Tracking with Activity Logging |  Done |
| Website Blocking via Chrome Extension |  Done |
| Analytics Dashboard with Charts |  Done |
| ML Distraction Scorer (4-Factor Algorithm) |  Done |
| AI-Powered Site Suggestions |  Done |
| 35 Backend Tests Passing |  Done |
| 14 Frontend Tests Passing |  Done |

---

##  Tech Stack

### Frontend
- **React** + **Vite**
- **Tailwind CSS**
- **Recharts** (data visualization)
- Deployed on **Vercel**

### Backend
- **FastAPI** (Python)
- **Supabase** (PostgreSQL + Auth)
- **JWT Authentication**
- Deployed on **Render**

### Chrome Extension
- Vanilla JS — **Manifest V3**
- Chrome Storage API
- Real-time sync with backend

### Machine Learning
- **Scikit-learn**
- 4-Factor ML Distraction Scoring Algorithm
- Behavioral pattern detection
- AI-powered site suggestions

---

##  Getting Started

### Prerequisites
- Node.js v18+
- Python 3.10+
- Chrome Browser

---

### 1. Clone the Repository

```bash
git clone https://github.com/olatunjitobiloba/FocusPilot.git
cd FocusPilot
```

---

### 2. Frontend Setup

```bash
cd focuspilot-frontend
npm install
cp .env.example .env.local   # Add your Supabase + API keys
npm run dev
```

---

### 3. Backend Setup

```bash
cd focuspilot-backend
pip install -r requirements.txt
cp .env.example .env         # Add your Supabase keys
uvicorn main:app --reload
```

---

### 4. Chrome Extension Setup

1. Open Chrome → go to `chrome://extensions/`
2. Enable **Developer Mode** (top right)
3. Click **Load unpacked**
4. Select the `focuspilot-extension/` folder
5. Pin the extension and start a focus session

---

##  Running Tests

### Backend (35 tests)
```bash
cd focuspilot-backend
pytest
```

### Frontend (14 tests)
```bash
cd focuspilot-frontend
npm run test
```

---

##  Project Structure

```
FocusPilot/
├── focuspilot-frontend/     # React web dashboard
├── focuspilot-backend/      # FastAPI + ML backend
├── focuspilot-extension/    # Chrome Extension (MV3)
├── Dockerfile
└── README.md
```

---

##  Live Links

| Resource | Link |
|----------|------|
|  Live App | [focuspilot.vercel.app](https://focuspilot.vercel.app) |
|  Demo Video | [Watch on YouTube](https://www.youtube.com/watch?v=y9jI2dACznU) |
|  GitHub Repo | [olatunjitobiloba/FocusPilot](https://github.com/olatunjitobiloba/FocusPilot) |

---

##  Roadmap

- [ ] Productivity DNA Profile (K-Means clustering)
- [ ] Smart Timetable Generator
- [ ] AI Coach with weekly insights
- [ ] Gamification (streaks, points, leaderboard)
- [ ] Parent Dashboard (premium)
- [ ] Mobile app (React Native)

---

##  Contributing

Contributions, issues, and feature requests are welcome!
Feel free to open an issue or submit a pull request.

---

##  License

This project is licensed under the **MIT License**.

---

<div align="center">

**Built with focus, shipped with purpose.**

*Hope is not a strategy. Execution is.*

⭐ Star this repo if FocusPilot resonates with you!

</div>