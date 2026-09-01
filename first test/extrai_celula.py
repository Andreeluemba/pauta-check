import cv2
import pytesseract

CAMINHO_IMAGEM = '/home/andre-luemba/Imagens/pauta.png'
FATOR_UPSCALE = 4  # as células originais são minúsculas (~18x12px); sem isso o OCR não lê nada

# --- 1. Carregar e ampliar a imagem inteira ANTES de tudo ---
# Fazemos isso porque células de 18x12px são pequenas demais pro Tesseract ler.
# Ampliando a página toda, a grade e as células crescem juntas, na mesma proporção.
imagem = cv2.imread(CAMINHO_IMAGEM)
imagem = cv2.resize(imagem, None, fx=FATOR_UPSCALE, fy=FATOR_UPSCALE, interpolation=cv2.INTER_CUBIC)
imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

_, imagem_binarizada = cv2.threshold(
    imagem_cinza, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
)

# --- 2. Detectar a grade (mesma lógica de antes, kernels escalados 4x junto) ---
k = FATOR_UPSCALE
kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (40 * k, 1))
kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40 * k))

linhas_horizontais = cv2.morphologyEx(imagem_binarizada, cv2.MORPH_OPEN, kernel_horizontal)
linhas_verticais = cv2.morphologyEx(imagem_binarizada, cv2.MORPH_OPEN, kernel_vertical)

grade = cv2.bitwise_or(linhas_horizontais, linhas_verticais)
grade = cv2.dilate(grade, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

# --- 3. Encontrar as células (contornos dos espaços vazios, não das linhas) ---
grade_invertida = cv2.bitwise_not(grade)
contornos, _ = cv2.findContours(grade_invertida, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

altura_pagina, largura_pagina = imagem.shape[:2]
celulas = []
for c in contornos:
    x, y, w, h = cv2.boundingRect(c)
    area = w * h
    if (
        100 * k * k < area < 5000 * k * k
        and w < largura_pagina * 0.2
        and h < altura_pagina * 0.2
        and w > 4 * k and h > 4 * k
    ):
        celulas.append((x, y, w, h))

print(f'Total de células encontradas: {len(celulas)}')

# --- 4. Agrupar em LINHAS por proximidade vertical (y), depois ordenar por x dentro da linha ---
TOLERANCIA_LINHA = 10 * k

celulas.sort(key=lambda c: c[1])  # ordena tudo por y primeiro

linhas = []
linha_atual = []
y_referencia = None
for (x, y, w, h) in celulas:
    if y_referencia is None or abs(y - y_referencia) <= TOLERANCIA_LINHA:
        linha_atual.append((x, y, w, h))
        y_referencia = y if y_referencia is None else y_referencia
    else:
        linhas.append(linha_atual)
        linha_atual = [(x, y, w, h)]
        y_referencia = y
if linha_atual:
    linhas.append(linha_atual)

for linha in linhas:
    linha.sort(key=lambda c: c[0])  # ordena da esquerda pra direita

print(f'Total de linhas identificadas: {len(linhas)}')

# --- 5. Recortar cada célula e rodar OCR nela individualmente ---
# Ideia chave: a maioria das colunas só tem números (0-20). Se avisarmos isso
# pro Tesseract com um whitelist de dígitos, ele para de confundir "1" com "I"
# ou "0" com "o". Só as duas primeiras colunas (Nº, Aluno) e a última (OBS)
# têm texto de verdade, então usamos uma config diferente pra essas.

CONFIG_NUMERICA = '--psm 7 -c tessedit_char_whitelist=0123456789'
CONFIG_TEXTO = '--psm 7'

tabela = []
MARGEM = 1  # equilíbrio entre não cortar dígito e não pegar a linha da grade

for linha in linhas:
    linha_textos = []
    for indice_coluna, (x, y, w, h) in enumerate(linha):
        x0 = max(x + MARGEM, 0)
        y0 = max(y + MARGEM, 0)
        x1 = min(x + w - MARGEM, largura_pagina)
        y1 = min(y + h - MARGEM, altura_pagina)
        celula_img = imagem_cinza[y0:y1, x0:x1]
        if celula_img.size == 0:
            linha_textos.append('')
            continue

        # Dá um respiro branco ao redor da célula: ajuda o Tesseract a não
        # "cortar" a primeira/última letra ou dígito colado na borda.
        celula_img = cv2.copyMakeBorder(
            celula_img, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255
        )

        # As duas primeiras colunas (Nº, Aluno) e a última (OBS) são texto;
        # o resto (colunas 2 em diante, exceto a última) tende a ser nota numérica.
        eh_texto = indice_coluna in (0, 1) or indice_coluna == len(linha) - 1
        config = CONFIG_TEXTO if eh_texto else CONFIG_NUMERICA

        texto = pytesseract.image_to_string(celula_img, lang='por', config=config).strip()
        linha_textos.append(texto)
    tabela.append(linha_textos)

# --- 6. Mostrar o resultado ---
for i, linha_textos in enumerate(tabela):
    print(f'Linha {i}: {linha_textos}')