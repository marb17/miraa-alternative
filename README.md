# Miraa Alternative
An open-source alternative to **Miraa**, a Japanese transcription and translation app.
Multilingual audio analysis and alignment system for transcription, translation, and visualization.
Main TUI uses [Textual](https://github.com/Textualize/textual)

## 🚀 How it works
- Automatically queries songs using Spotify API, uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to download songs
- Can auto-detect what song is currently playing in Spotify
- Lyrics and metadata are pulled using Genius API and Spotify API
- The song is separated into stems of varying models using [python-audio-separator](https://github.com/streichgeorg/python-audio-separator)
- Song lyrics are automatically translated using a LLM [Shisa v2.1 8B Qwen](https://huggingface.co/shisa-ai/shisa-v2.1-qwen3-8b)
- WIP

## 🛠 Tech Stack
- Python
- PyTorch / torchaudio
- [LMDeploy](https://github.com/internlm/lmdeploy)
- Textual for dashboards
- External APIs & web scraping

## 🧪 Status
Actively iterating and experimenting, actively working on new features

---

## Flowchart
This diagram shows how the program functions:

### Backend
[![docs/flowchart backend.png](https://github.com/marb17/miraa-alternative/blob/d284f08067cdab9cb6e36af7ba55a2100769a292/docs/flowchart%20backend.png)](https://github.com/marb17/miraa-alternative/blob/7663ed75dd34546ef8b782e0813336fcebe6a8a4/docs/flowchart%20backend.drawio.png)

---


