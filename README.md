# Miraa Alternative
An open-source alternative to **Miraa**, a Japanese transcription and translation app.
Multilingual audio analysis and alignment system for transcription, translation, and visualization.

## 🚀 What it does
- Processes music into aligned, translated text and explained using a LLM
- Supports en-jp transcription and translation
- Visualizes timing, confidence, and alignment results
- Searches through Japanese dictionaries to find definitons of words
- Separates audio using demucs and masks for better separation
- Auto downloading from YouTube for better input

## 🧠 How it works
- Splits audio into stems (vocal & instrumental)
- Audio preprocessing & segmentation (VAD-based)
- Speech recognition & translation using pretrained models
- Using Genius API to get lyrics
- Saves data to a .json file for easy viewing (debugging)
- HTML-based interactive visualization (soon)

## 🛠 Tech Stack
- Python
- PyTorch / torchaudio
- Speech & translation models
- Transformers
- HTML / JS for dashboards
- External APIs & web scraping

## 📊 Results
- Improved alignment accuracy through iterative refinement (fine-tuning)
- Explanation of Japanese songs and their meaning (for studying the language)
- Robust handling of noisy real-world audio (actual songs)
- Scalable pipeline design (soon)

## 🧪 Status
Actively iterating and experimenting

---

## Flowchart
This diagram shows how the program functions:

### Backend
[![docs/flowchart backend.png](https://github.com/marb17/miraa-alternative/blob/d284f08067cdab9cb6e36af7ba55a2100769a292/docs/flowchart%20backend.png)](https://github.com/marb17/miraa-alternative/blob/7663ed75dd34546ef8b782e0813336fcebe6a8a4/docs/flowchart%20backend.drawio.png)

---


