# VerdictAI - AI-Powered Legal Assistant

VerdictAI is a comprehensive legal assistance platform that combines a modern web interface with an AI-powered backend for answering legal questions.

## Architecture

### Frontend (Next.js + TypeScript)
- **Location**: `frontend/`
- **Framework**: Next.js 15 with TypeScript
- **Styling**: Tailwind CSS with custom legal theme
- **Icons**: Lucide React
- **Features**: 
  - Modern, responsive design
  - Dark theme with gold accents
  - AI chat interface
  - Contact forms
  - Professional legal services presentation

### Backend (FastAPI + Python)
- **Location**: `backend/`
- **Framework**: FastAPI
- **AI**: Google Gemini 2.5 Flash
- **RAG System**: FAISS + Sentence Transformers
- **Features**:
  - Legal document retrieval
  - AI-powered question answering
  - CORS support for frontend integration

## Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd VerdictAI
   ```

2. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **Install Backend Dependencies**
   ```bash
   cd ../backend
   pip install -r requirements.txt
   ```

4. **Set up Google Gemini API Key**
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Update the API key in `backend/rag_utils.py`

### Running the Application

#### Option 1: Use the batch script (Windows)
```bash
start_dev.bat
```

#### Option 2: Manual startup

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn app:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

## Features

### Frontend Components
- **Header**: Navigation with contact info
- **Hero**: Main landing section with AI assistant intro
- **Services**: Legal service offerings
- **About**: Company information and expertise
- **Team**: Attorney profiles
- **LegalAI**: AI chat interface (connects to backend)
- **Contact**: ment booking form
- **CTA**: Call-to-action sections
- **Footer**: Complete site footer

### Backend API
- **POST /ask**: Submit legal questions to AI
- **GET /**: API health check
- **CORS**: Configured for frontend integration

## Configuration

### Frontend Customization
- **Colors**: Edit `frontend/tailwind.config.ts` for theme colors
- **Styling**: Modify `frontend/src/app/globals.css` for global styles
- **Components**: Update individual components in `frontend/src/components/`

### Backend Configuration
- **API Key**: Update Google Gemini API key in `backend/rag_utils.py`
- **CORS**: Modify allowed origins in `backend/app.py`
- **RAG System**: Customize legal documents and embeddings

## Project Structure

```
VerdictAI/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   └── components/
│   │       ├── Header.tsx
│   │       ├── Hero.tsx
│   │       ├── Services.tsx
│   │       ├── About.tsx
│   │       ├── Team.tsx
│   │       ├── LegalAI.tsx
│   │       ├── Contact.tsx
│   │       ├── CTA.tsx
│   │       └── Footer.tsx
│   ├── tailwind.config.ts
│   └── package.json
├── backend/
│   ├── app.py
│   ├── rag_utils.py
│   ├── requirements.txt
│   └── embeddings/
│       ├── faiss.index
│       └── chunk_metadata.pkl
└── README.md
```

## 🎯 Key Features

### AI Legal Assistant
- **Instant Responses**: Get legal answers immediately
- **24/7 Availability**: No waiting for office hours
- **Comprehensive Knowledge**: Trained on legal documents
- **Confidential**: Secure and private

### Professional Design
- **Dark Theme**: Professional legal aesthetic
- **Gold Accents**: Premium feel
- **Responsive**: Works on all devices
- **Modern UI**: Clean, professional interface

### Legal Services
- **Multiple Practice Areas**: Contract, Family, Criminal, Business Law
- **Expert Team**: Professional attorney profiles
- **Contact Forms**: Easy appointment booking
- **Service Descriptions**: Detailed legal service information

## 🔒 Security & Privacy

- **CORS Protection**: Configured for secure frontend-backend communication
- **API Key Security**: Store API keys securely
- **Data Privacy**: No personal data stored
- **Disclaimer**: Clear legal disclaimers included

## 🛠️ Development

### Adding New Components
1. Create component in `frontend/src/components/`
2. Import and add to `frontend/src/app/page.tsx`
3. Style using Tailwind CSS classes

### Modifying AI Responses
1. Update prompt in `backend/rag_utils.py`
2. Modify legal document embeddings
3. Test with different question types

### Customizing Theme
1. Edit `frontend/tailwind.config.ts` for colors
2. Update `frontend/src/app/globals.css` for global styles
3. Modify component-specific styling

## 📞 Support

For questions or issues:
- Check the console for error messages
- Verify API keys are correctly set
- Ensure all dependencies are installed
- Test backend connectivity

## 📄 License

This project is for educational and demonstration purposes. Please ensure compliance with local laws and regulations when using AI for legal advice. 

## Backend setup

- Create a `.env` file in `backend/` with:

```
GEMINI_API_KEY=your_key_here
```

- Install deps and run:

```
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload
```

Ensure `backend/embeddings/` contains `faiss.index` and `chunk_metadata.pkl`. Build with:

```
python backend/build_index.py
```

## Frontend setup

- In `frontend/`:

```
npm install
npm run dev
```

Optionally set `NEXT_PUBLIC_API_URL` to your backend URL. # verdictA
