# Miraa Alternative
An open-source alternative to **Miraa**, a Japanese transcription and translation app.

---

## Flowchart
This diagram shows how the program functions:

### Backend
![docs/flowchart backend.png](https://github.com/marb17/miraa-alternative/blob/d284f08067cdab9cb6e36af7ba55a2100769a292/docs/flowchart%20backend.png)

---

## System Requirements **OUTDATED**
This project uses multiple heavy ML models, so a decent GPU is recommended.

**Minimum Requirements:**
- GPU: Any GPU with enough VRAM for the model (in the pre-setup case around 12GB)
- CPU: Any CPU that can handle some light multi-threading and enough to handle the GPU load
- RAM: 4GB + Any off-load amount if the model doesn't fit in the GPU
- Storage: Enough for all the models, around 40GB in my case
- Internet: WiFi/Ethernet (50Mbps, only for downloading models)

**Recommended Specs (My Setup):**
- CPU: Intel i7-13700F
- RAM: 32GB DDR5
- Storage: SSD + HDD
- GPU: RTX 4060 (8GB VRAM)

---

## Prerequisites **OUTDATED**
Install the required Python packages:

```bash
pip install yt-dlp
pip install base58
pip install requests
pip install python-dotenv
pip install lyricsgenius
pip install demucs
pip install torch  # CUDA version recommended
pip install faster-whisper
pip install hf-xet
pip install MeCab
pip install unidic-lite
````

> ⚠️ **Note:** For torch, download the CUDA version compatible with your GPU for faster processing.

---

## Usage
```bash
```

---

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

---
