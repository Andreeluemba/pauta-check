import cv2
import pytesseract

CAMINHO_IMAGEM = '/home/andre-luemba/Imagens/pauta.png'  

# --- 1. Carregar e pré-processar ---
imagem = cv2.imread(CAMINHO_IMAGEM)
imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

# Pautas como essa costumam ter resolução baixa pra quantidade de colunas.
# Aumentar o tamanho (upscale) ajuda MUITO o Tesseract a acertar números pequenos.
imagem_grande = cv2.resize(imagem_cinza, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

_, imagem_binarizada = cv2.threshold(
    imagem_grande, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
)

cv2.imwrite('pauta_processada.png', imagem_binarizada)

# --- 2. Extrair texto com posição ---
dados = pytesseract.image_to_data(
    imagem_binarizada, lang='por', output_type=pytesseract.Output.DICT
)

n = len(dados['text'])

# --- 3. Montar uma lista só com o que tem texto de verdade ---
palavras = []
for i in range(n):
    texto = dados['text'][i].strip()
    if texto == '':
        continue
    palavras.append({
        'texto': texto,
        'left': dados['left'][i],
        'top': dados['top'][i],
        'conf': dados['conf'][i],
    })

print(f'Total de palavras detectadas: {len(palavras)}')

# --- 4. Agrupar por LINHA usando a posição vertical (top) ---
# Numa tabela como essa, confiar no line_num do Tesseract pode falhar por causa
# do cabeçalho mesclado. Agrupar por proximidade de "top" é mais confiável aqui.
TOLERANCIA_LINHA = 12  # pixels de diferença que ainda conta como "mesma linha"

palavras.sort(key=lambda p: p['top'])

linhas = []
linha_atual = []
top_referencia = None

for p in palavras:
    if top_referencia is None or abs(p['top'] - top_referencia) <= TOLERANCIA_LINHA:
        linha_atual.append(p)
        top_referencia = p['top'] if top_referencia is None else top_referencia
    else:
        linhas.append(linha_atual)
        linha_atual = [p]
        top_referencia = p['top']
if linha_atual:
    linhas.append(linha_atual)

# --- 5. Dentro de cada linha, ordenar da esquerda pra direita (coluna) ---
for linha in linhas:
    linha.sort(key=lambda p: p['left'])

# --- 6. Imprimir de forma legível ---
print(f'\nTotal de linhas identificadas: {len(linhas)}\n')
for idx, linha in enumerate(linhas):
    textos = [p['texto'] for p in linha]
    print(f'Linha {idx}: {textos}')