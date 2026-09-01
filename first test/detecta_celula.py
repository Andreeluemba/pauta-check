import cv2

CAMINHO_IMAGEM = '/home/andre-luemba/Imagens/pauta.png'

# --- 1. Recriar a grade isolada (mesma lógica do detecta_grade.py) ---
imagem = cv2.imread(CAMINHO_IMAGEM)
imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
_, imagem_binarizada = cv2.threshold(
    imagem_cinza, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
)

kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

linhas_horizontais = cv2.morphologyEx(imagem_binarizada, cv2.MORPH_OPEN, kernel_horizontal)
linhas_verticais = cv2.morphologyEx(imagem_binarizada, cv2.MORPH_OPEN, kernel_vertical)

grade = cv2.bitwise_or(linhas_horizontais, linhas_verticais)

# Engrossar um pouco a grade (dilatar) fecha pequenas falhas nos cruzamentos,
# o que evita que duas células "vazem" e sejam lidas como uma só.
grade = cv2.dilate(grade, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)

# --- 2. Encontrar os contornos ---
# IMPORTANTE: até aqui, 'grade' tem as LINHAS em branco sobre fundo preto.
# Se procurarmos contornos nela diretamente, o OpenCV vai contornar os
# TRAÇOS (as linhas), não os espaços vazios entre eles.
# O que queremos são as CÉLULAS (os buracos pretos cercados por linhas brancas).
# Solução: inverter a imagem, transformando cada célula vazia numa "ilha branca".
grade_invertida = cv2.bitwise_not(grade)

contornos, _ = cv2.findContours(grade_invertida, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

# --- 3. Filtrar e converter cada contorno numa caixa (x, y, largura, altura) ---
# Descoberta importante: como a pauta é pequena e densa, cada célula real tem
# só ~18x12 pixels (área ~216). Um filtro de "área mínima 500" jogava fora
# quase todas as células de verdade. Ajustado com base na distribuição real
# medida nos contornos (a maioria das células fica entre área 100 e 3000).
altura_pagina, largura_pagina = imagem.shape[:2]

celulas = []
for c in contornos:
    x, y, w, h = cv2.boundingRect(c)
    area = w * h
    if (
        100 < area < 5000          # descarta ruído minúsculo e blocos grandes demais
        and w < largura_pagina * 0.2   # descarta a página inteira / faixas muito largas
        and h < altura_pagina * 0.2    # descarta a página inteira / faixas muito altas
        and w > 4 and h > 4            # descarta traços residuais finos demais
    ):
        celulas.append((x, y, w, h))

print(f'Total de células candidatas encontradas: {len(celulas)}')

# --- 4. Desenhar as caixas encontradas sobre a imagem original, pra conferir visualmente ---
imagem_debug = imagem.copy()
for (x, y, w, h) in celulas:
    cv2.rectangle(imagem_debug, (x, y), (x + w, y + h), (0, 0, 255), 1)

cv2.imwrite('celulas_detectadas.png', imagem_debug)
print('Salvo: celulas_detectadas.png (confere se as caixas vermelhas batem com as células reais)')