# 🗣️ Speech-to-Text Argument Analyzer

Welcome to the **Speech-to-Text Argument Analyzer**!  
This project lets you upload or transcribe audio, analyze the resulting text for logical fallacies, argument structure, and more—all in a beautiful, interactive web interface.

---

## 🚀 Features

- 🎤 **Audio Upload & Transcription**: Upload audio files or provide a YouTube link for transcription using Whisper WebUI.
- 🧠 **Argument Analysis**: Detects logical fallacies, evaluates argument structure, coherence, strength, and more.
- 📊 **Visual Results**: Clean, sectioned display of analysis results with color-coded quality indicators.
- 📄 **Export**: Download your analysis as JSON or a nicely formatted PDF.
- 🔒 **Authentication**: Secure connection to the Whisper WebUI API with credentials.

---

## 🛠️ Getting Started

### 1. **Clone the Repository**

```sh
git clone https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
```

### 2. **Setup your environment**
ℹ️ Please refer to the other documentation in the repository to set up your environment.


### 3. **Run the argumentation analysis python Web Api**
```sh
python -m uvicorn api.main:app --port 8000
```

### 4. **Install Frontend Dependencies**

```sh
cd speech-to-text/frontend
npm install
```


### 5. **Configure API Credentials**

Copy the `.env.example` file variables into you `.env` file. Set the following variables:
- `WHISPER_API_URL` (default: `https://whisper-webui.myia.io/`)
- Your API username, password, and API key.

### 6. **Run the Frontend**

```sh
npm run serve
```
or
```sh
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🎬 Usage

1. **Upload an audio file** (e.g., `.mp3`, `.wav`) (In progress...) or paste a YouTube link.
2. Click **Transcribe** to convert speech to text.
3. Click **Analyze** to run the argument analysis.
4. View results: logical fallacies, argument structure, coherence, strength, and more.
5. **Export** your results as JSON or PDF.

---

## 📦 Project Structure

```
frontend/
  ├── src/
  │   ├── components/
  │   │   └── MainComponent.vue   # Main UI and logic
  │   ├── api/
  │   │   └── whisperApiClient.js # API client for Whisper WebUI
  │   └── ...
  └── ... # Main VueJS code
```

---

## 📝 Customization

- **API Endpoint**: Change the Whisper WebUI endpoint in `whisperApiClient.js`.
- **Analysis Options**: Adjust analysis parameters in the UI or code.
- **PDF Export**: Tweak formatting in `exportResults` method in `MainComponent.vue`.

---

## 🧩 Dependencies

- [Vue.js](https://vuejs.org/) (Frontend framework)
- [Vuetify](https://vuetifyjs.com/) (UI components)
- [jsPDF](https://github.com/parallax/jsPDF) (PDF export)
- [@gradio/client](https://www.npmjs.com/package/@gradio/client) (API client)

---

## 🐞 Troubleshooting

- **CORS Errors**: If fetching remote files, use your own backend proxy or ensure the remote server sends proper CORS headers.
- **File Type Errors**: Only upload supported audio formats (see error message for allowed extensions).
- **API Errors**: Check your credentials and API endpoint.

---

## 🤝 Contributing

Pull requests and suggestions are welcome!  
Please open an issue or discussion for feedback or feature requests.

---

## 📄 License

MIT License (c.f. project root license)

---

## 🙏 Acknowledgements

- [OpenAI Whisper](https://github.com/openai/whisper)
- [Gradio](https://gradio.app/)
- [jsPDF](https://github.com/parallax/jsPDF)

---

Enjoy analyzing arguments! 🎉