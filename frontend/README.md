# VerdictAI Frontend

A modern, responsive web interface for the VerdictAI legal assistant. Built with Next.js 15, TypeScript, and Tailwind CSS.

## Features

- 🤖 **AI-Powered Legal Assistant**: Chat interface for legal questions
- 🎨 **Modern UI**: Clean, professional design with dark mode support
- 📱 **Responsive**: Works on desktop, tablet, and mobile devices
- ⚡ **Real-time**: Instant responses with loading indicators
- 🔒 **Type-safe**: Built with TypeScript for better development experience

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React + React Icons
- **State Management**: React Hooks

## Getting Started

### Prerequisites

- Node.js 18+ 
- Backend server running on `http://localhost:8000`

### Installation

1. Install dependencies:
   ```bash
   npm install --legacy-peer-deps
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## API Integration

The frontend connects to the VerdictAI backend API:

- **Endpoint**: `POST /ask`
- **Request**: `{ query: string }`
- **Response**: `{ answer: string }`

## Environment Variables

Create a `.env.local` file to customize the API URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── app/
│   ├── globals.css      # Global styles
│   ├── layout.tsx       # Root layout
│   └── page.tsx         # Main chat interface
└── lib/
    └── api.ts           # API utilities
```

## Features

### Chat Interface
- Real-time messaging with the AI assistant
- Message history with timestamps
- Loading states and error handling
- Responsive design for all screen sizes

### UI Components
- Modern chat bubbles with user/assistant distinction
- Professional header with branding
- Smooth animations and transitions
- Dark mode support

### Error Handling
- Graceful error messages for API failures
- Network connectivity issues
- Input validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the VerdictAI legal assistant system.
