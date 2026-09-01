import pytesseract
from PIL import Image
import cv2

image = cv2.imread('/home/andre-luemba/Imagens/test.png')

text = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
valor_usado, imagem_binarizada = cv2.threshold(text, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
text = pytesseract.image_to_string(imagem_binarizada, lang='por')

print(text)