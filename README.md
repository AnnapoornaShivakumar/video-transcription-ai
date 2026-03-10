# AI Video Transcription & Document-to-Video Generator

This project converts videos to transcripts and documents to narrated videos using AI.

## Features

* Upload video → Generate transcript (.txt)
* Upload document (.txt, .pdf, .docx) → Generate narrated video
* AI slide generation
* Text-to-speech narration
* Image generation for slides
* Parallel slide processing for faster video generation
* Angular frontend + FastAPI backend

## Tech Stack

Backend

* FastAPI
* Faster-Whisper
* gTTS
* MoviePy
* Python

Frontend

* Angular

Infrastructure

* Docker
* REST API

## How It Works

### Video → Transcript

1. Upload video
2. Audio extracted using FFmpeg
3. Faster-Whisper generates transcript
4. Transcript saved as `.txt`

### Document → Video

1. Document text extracted
2. Text split into slides
3. AI generates slide title + image query
4. Images downloaded
5. gTTS generates narration
6. MoviePy merges images + audio into video

## Run Backend

```
cd backend_transcription
uvicorn main:app --reload
```

## Run Frontend

```
cd frontend_transcription
ng serve
```

Frontend runs at:

```
http://localhost:4200
```

Backend runs at:

```
http://localhost:8000
```
