# CodeMind: Full-Stack Semantic Indexing & RAG

CodeMind is now a full-stack application featuring a modern React frontend and a powerful FastAPI backend.

## 📂 Project Structure

- `backend/`: FastAPI system for repository indexing, AST analysis, and LLM reasoning.
- `frontend/`: React + Vite application for a premium user experience.

## 🚀 Getting Started

### 1. Launch the Backend
```bash
cd backend
# Ensure your .env is configured
python3 run.py
```

### 2. Launch the Frontend
In a new terminal:
```bash
cd frontend
npm install  # If not already done
npm run dev
```

## ✨ New Features
- **Modern Dashboard**: A clean, light-themed UI with glassmorphism aesthetics.
- **Async Indexing**: Initiate repos indexing in the UI and track progress in real-time.
- **Execution Lab**: Run RAG queries and view beautifully formatted markdown results with syntax highlighting.
- **Unified LLM**: Leverages configured Local, Ollama, or Apigee drivers automatically.
