# Argumentation Analysis Frontend

A minimal React frontend for the Argumentation Analysis system.

## Features

- **Text Analysis**: Analyze argumentative text for structure, coherence, and fallacies
- **Fallacy Detection**: Detect logical fallacies in text with configurable sensitivity
- **Logic Analysis**: Convert text to logical belief sets and execute queries

## Prerequisites

- Node.js (v14 or higher)
- npm
- The Flask backend running on `http://localhost:5000`

## Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The application will open in your browser at `http://localhost:3000`.

## Backend Setup

Make sure the Flask API is running on port 5000. From the project root:

```bash
cd services/web_api
python app.py
```

## Usage

### Text Analysis
1. Go to the "Text Analysis" tab
2. Enter argumentative text in the textarea
3. Click "Analyze Text" to get a complete analysis

### Fallacy Detection
1. Go to the "Fallacy Detection" tab
2. Enter text to check for fallacies
3. Adjust the severity threshold if needed
4. Click "Detect Fallacies"

### Logic Analysis
1. Go to the "Logic Analysis" tab
2. Select logic type (propositional, first order, or modal)
3. Enter logical statements
4. Click "Create Belief Set"
5. Once created, enter queries to test against the belief set

## API Endpoints Used

- `GET /api/health` - Check API status
- `POST /api/analyze` - Full text analysis
- `POST /api/fallacies` - Fallacy detection
- `POST /api/logic/belief-set` - Create belief sets
- `POST /api/logic/query` - Execute logical queries

## Development

This is a minimal implementation focusing on functionality over aesthetics. The interface provides:

- Clean, responsive design
- Real-time API status monitoring
- Loading states and error handling
- Structured result display
- Tab-based navigation

For production use, consider adding:
- Better visualization components (D3.js, Cytoscape.js)
- Advanced UI components (Material-UI, Tailwind)
- User authentication
- Result persistence
- Export functionality
