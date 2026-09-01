import pytesseract 
from PIL import Image

image = Image.open('/home/andre-luemba/Imagens/test.png')

text = pytesseract.image_to_string(image, lang='por')

print(text)