import cv2

CAMINHO_IMAGEM = '/home/andre-luemba/Imagens/pauta.png'

# --- 1. Carregar e binarizar ---
imagem = cv2.imread(CAMINHO_IMAGEM)
imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
_, imagem_binarizada = cv2.threshold(
    imagem_cinza, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
)
# THRESH_BINARY_INV: linhas e texto ficam BRANCOS sobre fundo PRETO.
# Isso facilita as operações morfológicas a seguir.

# --- 2. Carimbos (kernels) para isolar linhas ---
kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

# --- 3. Isolar linhas horizontais e verticais ---
linhas_horizontais = cv2.morphologyEx(
    imagem_binarizada, cv2.MORPH_OPEN, kernel_horizontal, iterations=1
)
linhas_verticais = cv2.morphologyEx(
    imagem_binarizada, cv2.MORPH_OPEN, kernel_vertical, iterations=1
)

# --- 4. Salvar para inspeção visual ---
cv2.imwrite('linhas_h.png', linhas_horizontais)
cv2.imwrite('linhas_v.png', linhas_verticais)

# Bônus: as duas juntas, pra já ter uma ideia da grade completa
grade_completa = cv2.bitwise_or(linhas_horizontais, linhas_verticais)
cv2.imwrite('grade_completa.png', grade_completa)

print('Salvo: linhas_h.png, linhas_v.png, grade_completa.png')