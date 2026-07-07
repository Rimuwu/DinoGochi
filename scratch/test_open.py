import os
from PIL import Image

path = "images/backgrounds/1.png"
print("CWD:", os.getcwd())
print("File exists:", os.path.exists(path))
try:
    img = Image.open(path)
    print("Image loaded successfully:", img.size)
except Exception as e:
    print("Error opening image:", e)
