import os
import re
import uuid
import shutil
import subprocess
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.document_service import extract_text, split_text, create_slide
from services.tts_service import generate_audio
from services.video_service import create_video
from services.llm_service import generate_slide_content
from services.image_service import fetch_image

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VIDEO_FOLDER = BASE_DIR / "data" / "videos"

progress_tracker={}
# FastAPI app initialization
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow Angular app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder configuration
# UPLOAD_FOLDER = "uploads"
# TRANSCRIPT_FOLDER = "transcripts"
DATA_FOLDER = "data"

UPLOAD_FOLDER = os.path.join(DATA_FOLDER, "uploads")
TRANSCRIPT_FOLDER = os.path.join(DATA_FOLDER, "transcripts")
# VIDEO_FOLDER = os.path.join(DATA_FOLDER, "videos")
TEMP_FOLDER = os.path.join(DATA_FOLDER, "temp")

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPT_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

print(" Upload folder:", UPLOAD_FOLDER)
print("Transcript folder:", TRANSCRIPT_FOLDER)

# Load Faster-Whisper model (only once when server starts)
print(" Loading Faster-Whisper model...")

model = WhisperModel(
    "base",              # good balance of speed + accuracy
    compute_type="int8",  # optimized for CPU inference
    cpu_threads=4        # allow model to use multiple CPU cores
)

# print(" Model loaded successfully!")


# Function: Extract audio from video using FFmpeg
def extract_audio(video_path, audio_path):
    """
    Extract audio from video using FFmpeg.
    Extracting audio first avoids heavy video decoding
    and improves transcription speed.
    """

    print(" Extracting audio from video...")

    command = [
        "ffmpeg",
        "-y", 
        "-i", video_path,          # input video
        "-vn",                     # disable video stream
        "-acodec", "libmp3lame",
        "-b:a", "32k",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]

    # Run ffmpeg silently
    subprocess.run(
    command,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=True,
    timeout=600
)

    print("Audio extracted:", audio_path)

def split_audio(audio_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    command = [
        "ffmpeg",
        "-i", audio_path,
        "-f", "segment",
        "-segment_time", "300",  # 5 minutes
        "-c", "copy",
        os.path.join(output_folder, "chunk_%03d.mp3")
    ]

    subprocess.run(
    command,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=True,
    timeout=600
)
    
def get_audio_duration(audio_path):
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return float(result.stdout.strip())

def transcribe_chunk(chunk_path, video_id, total_duration, processed_offset):

    segments, info = model.transcribe(
        chunk_path,
        beam_size=1,
        temperature=0,
        vad_filter=True,
        condition_on_previous_text=False
    )

    lines = []

    for segment in segments:

        lines.append(segment.text.strip())

        current_time = processed_offset + segment.end

        progress = int((current_time / total_duration) * 100)

        if progress >= 100:
            progress = 99

        if progress > progress_tracker.get(video_id, 0):
            progress_tracker[video_id] = progress

    return lines

# def transcribe_chunk(chunk_path):
#     print(f"Processing: {os.path.basename(chunk_path)}")
#     segments, info = model.transcribe(
#         chunk_path,
#         beam_size=1,
#         temperature=0,
#         vad_filter=True,
#         condition_on_previous_text=False
#     )

#     lines = []
#     for segment in segments:
#         # print with timestamp in terminal
#         print(f"[{segment.start:.2f}s] {segment.text.strip()}")

#         # store only clean text for UI
#         lines.append(segment.text.strip())

#     return lines
def process_video(video_id, video_path):

    audio_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.mp3")
    chunk_folder = os.path.join(UPLOAD_FOLDER, f"{video_id}_chunks")

    try:

        for i in range(1, 10):
            progress_tracker[video_id] = i

        extract_audio(video_path, audio_path)

        for i in range(10, 20):
            progress_tracker[video_id] = i
            
        split_audio(audio_path, chunk_folder)
        progress_tracker[video_id] = 30
        transcript_lines = []

        chunk_files = sorted(os.listdir(chunk_folder))

        chunk_paths = [
            os.path.join(chunk_folder, f)
            for f in chunk_files
        ]

        total_chunks = len(chunk_paths)
        completed_chunks = 0
        total_duration = get_audio_duration(audio_path)
        with ThreadPoolExecutor(max_workers=2) as executor:

            processed_offset = 0

            for chunk_path in chunk_paths:

                chunk_lines = transcribe_chunk(
                    chunk_path,
                    video_id,
                    total_duration,
                    processed_offset
                )

                transcript_lines.extend(chunk_lines)

                chunk_duration = get_audio_duration(chunk_path)
                processed_offset += chunk_duration

        transcript_text = "\n".join(transcript_lines)

        transcript_path = os.path.join(
            TRANSCRIPT_FOLDER,
            f"{video_id}.txt"
        )

        # Embed video_id as a hidden header so we can recover the original
        # video when this transcript file is re-uploaded later.
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(f"# VIDEO_ID: {video_id}\n")
            f.write(transcript_text.strip())

        progress_tracker[video_id] = 100

    finally:

        if os.path.exists(audio_path):
            os.remove(audio_path)

        if os.path.exists(chunk_folder):
            shutil.rmtree(chunk_folder)

# API: Upload video and generate transcript
@app.post("/upload-video")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):

    print("\n==============================")
    print("New video upload received:", file.filename)

    MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024

    video_id = str(uuid.uuid4())
    progress_tracker[video_id] = 1

    video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.mp4")

    total_size = 0

    with open(video_path, "wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break

            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:
                os.remove(video_path)
                raise HTTPException(status_code=413, detail="File too large")

            buffer.write(chunk)

    print("Video saved:", video_path)

    # Start background transcription
    background_tasks.add_task(process_video, video_id, video_path)

    return {
        "message": "Processing started",
        "video_id": video_id
    }
    

# API: Download transcript file
@app.get("/download/{video_id}")
def download_transcript(video_id: str):

    transcript_path = os.path.join(
        TRANSCRIPT_FOLDER,
        f"{video_id}.txt"
    )

    print(" Download request for:", transcript_path)

    if not os.path.exists(transcript_path):
        print(" Transcript not found")
        raise HTTPException(status_code=404, detail="Transcript not found")

    print(" Sending transcript file")

    return FileResponse(
    transcript_path,
    media_type="text/plain",
    filename="transcript.txt"

)

@app.get("/transcript/{video_id}")
def get_transcript(video_id: str):

    transcript_path = os.path.join(
        TRANSCRIPT_FOLDER,
        f"{video_id}.txt"
    )

    if not os.path.exists(transcript_path):
        raise HTTPException(status_code=404, detail="Transcript not found")

    with open(transcript_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Strip the embedded VIDEO_ID header before returning clean text
    text_lines = [l for l in lines if not l.startswith("# VIDEO_ID:")]
    text = "".join(text_lines).strip()

    return {"transcript": text}

@app.get("/progress/{video_id}")
def get_progress(video_id: str):

    if video_id not in progress_tracker:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "progress": progress_tracker[video_id]
    }


# API: Upload a transcript .txt file and recover the original video
@app.post("/upload-transcript")
async def upload_transcript(file: UploadFile = File(...)):
    """
    Accept a previously generated transcript .txt file.
    Parse the embedded VIDEO_ID header and return the video_id so the
    client can call /download-video/{video_id} to download the original video.
    """

    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Only .txt transcript files are accepted"
        )

    content = await file.read()

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")

    # Look for the embedded header line:  # VIDEO_ID: <uuid>
    video_id = None
    for line in text.splitlines():
        match = re.match(r"^#\s*VIDEO_ID:\s*([a-f0-9\-]+)\s*$", line.strip())
        if match:
            video_id = match.group(1)
            break

    if not video_id:
        raise HTTPException(
            status_code=422,
            detail=(
                "No VIDEO_ID found in this transcript. "
                "Only transcripts generated by this service can be used to recover the original video."
            )
        )

    # Confirm the original video still exists on disk
    video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=404,
            detail="Original video not found. It may have been deleted from the server."
        )

    return {
        "message": "Transcript recognised. Use the video_id to download the original video.",
        "video_id": video_id
    }


# API: Download the original video by video_id

@app.post("/generate-video-from-document")
async def generate_video_from_document(file: UploadFile = File(...)):

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{file.filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # extract text
    text = extract_text(file_path)

    job_id = str(uuid.uuid4())

    job_folder = os.path.join(TEMP_FOLDER, job_id)

    image_folder = os.path.join(job_folder, "images")
    audio_folder = os.path.join(job_folder, "audio")

    os.makedirs(image_folder, exist_ok=True)
    os.makedirs(audio_folder, exist_ok=True)

    chunks = split_text(text, words_per_slide=120)

    slide_images = []
    audio_files = []

    # 🔹 function to process one slide
    def process_slide(chunk, index):

        slide = generate_slide_content(chunk)

        title = slide["title"]
        bullets = slide["bullets"]
        image_query = slide["image_query"]

        image_path = fetch_image(image_query, image_folder)

        slide_image = create_slide(title, bullets, image_path, image_folder)

        audio_path = generate_audio(chunk, audio_folder)

        return {
            "index": index,
            "image": slide_image,
            "audio": audio_path
        }

    # 🔹 PARALLEL PROCESSING
    results = []

    with ThreadPoolExecutor(max_workers=4) as executor:

        futures = [
            executor.submit(process_slide, chunk, i)
            for i, chunk in enumerate(chunks)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    # 🔹 sort slides back to correct order
    results.sort(key=lambda x: x["index"])

    for r in results:
        slide_images.append(r["image"])
        audio_files.append(r["audio"])

    # 🔹 CREATE VIDEO
    video_path = create_video(audio_files, image_folder)
    shutil.rmtree(job_folder, ignore_errors=True)

    # video_id = os.path.basename(video_path)
    video_id = os.path.basename(video_path).replace(".mp4", "")

    return {
        "message": "Video generated successfully",
        "video_id": video_id,
        "download_url": f"/download-video/{video_id}"
    }

@app.get("/download-video/{video_id}")
def download_video(video_id: str):

    video_id = video_id.replace(".mp4", "")

    generated_video = VIDEO_FOLDER / f"{video_id}.mp4"
    uploaded_video = Path(UPLOAD_FOLDER) / f"{video_id}.mp4"

    if generated_video.exists():
        video_path = generated_video

    elif uploaded_video.exists():
        video_path = uploaded_video

    else:
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        str(video_path),
        media_type="video/mp4",
        filename=f"{video_id}.mp4"
    )