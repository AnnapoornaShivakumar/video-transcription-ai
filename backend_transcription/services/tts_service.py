from gtts import gTTS
import uuid
import os

# AUDIO_FOLDER = "static/audio"

# os.makedirs(AUDIO_FOLDER, exist_ok=True)

def generate_audio(script: str, audio_folder= str):

    os.makedirs(audio_folder, exist_ok=True)

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(audio_folder, filename)

    tts = gTTS(script, lang="en")
    tts.save(filepath)

    return filepath