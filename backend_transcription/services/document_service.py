from PyPDF2 import PdfReader
from docx import Document
from PIL import Image, ImageDraw, ImageFont
import uuid
import os


def extract_text(file_path):

    if file_path.endswith(".pdf"):

        reader = PdfReader(file_path)
        text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        return text


    elif file_path.endswith(".docx"):

        doc = Document(file_path)

        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


    elif file_path.endswith(".txt"):

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


    else:
        raise ValueError("Unsupported file format")

def split_text(text, words_per_slide=100):

    words = text.split()

    slides = []

    for i in range(0, len(words), words_per_slide):
        slides.append(" ".join(words[i:i + words_per_slide]))

    return slides



def create_slide(title, bullets, image_path, output_folder):

    os.makedirs(output_folder, exist_ok=True)

    width, height = 1280, 720

    # load background image
    img = Image.open(image_path).resize((width, height)).convert("RGBA")

    # add dark overlay for readability
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 100))
    img = Image.alpha_composite(img, overlay)

    # draw = ImageDraw.Draw(img)

    # try:
    #     font = ImageFont.truetype("arial.ttf", 60)
    # except:
    #     font = ImageFont.load_default()

    # # draw title only (no bullets to keep video clean)
    # draw.text((80, 600), title, fill="white", font=font)

    filename = f"{uuid.uuid4()}.png"

    path = os.path.join(output_folder, filename)

    img.convert("RGB").save(path)

    return path