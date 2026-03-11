# from moviepy.editor import *
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import uuid
import os

VIDEO_FOLDER = "data/videos"
# IMAGE_FOLDER = "static/images"

os.makedirs(VIDEO_FOLDER, exist_ok=True)


def create_video(audio_files, image_folder):

    filename = f"{uuid.uuid4()}.mp4"
    video_path = os.path.join(VIDEO_FOLDER, filename)

    images = sorted([
        os.path.join(image_folder, img)
        for img in os.listdir(image_folder)
        if img.endswith(".png")
    ])

    clips = []

    for img, audio_path in zip(images, audio_files):

        audio = AudioFileClip(audio_path)

        clip = ImageClip(img).set_duration(audio.duration)
        # clip = clip.resize(lambda t: 1 + 0.02*t)

        clip = clip.set_audio(audio)

        clips.append(clip)

    final_video = concatenate_videoclips(clips, method="chain")
    # final_video = concatenate_videoclips(clips, method="compose").crossfadein(0.5)

    final_video.write_videofile(
        video_path,
        fps=24,
        codec="libx264",
        preset="ultrafast",
        threads=4,
        audio_codec="aac"
    )

    return video_path