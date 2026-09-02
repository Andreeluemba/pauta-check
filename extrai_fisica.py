import os
import re
import json
import cv2
import numpy as np
import pytesseract
from concurrent.futures import ThreadPoolExecutor
from pdf2image import convert_from_path

from esquema_pauta import ESQUEMA_COLUNAS, linha_larga_para_longa

CAMINHO_ARQUIVO = 'pauta.png'
CAMINHO_SAIDA_JSON = 'dados_fisica.json'
FATOR_UPSCALE = 2  # reduzido de 4 pra 2 — texto impresso não precisa de tanto, e isso corta o tempo bastante


def extrair_celulas_da_imagem(imagem, fator_upscale=FATOR_UPSCALE):
    """Recebe uma imagem JÁ CARREGADA (array do OpenCV, não um caminho) e
    detecta a grade da tabela, retornando as células agrupadas em linhas."""
    k = fator_upscale
    imagem = cv2.resize(imagem, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

    _, imagem_binarizada = cv2.threshold(
        imagem_cinza, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (40 * k, 1))
    kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40 * k))
    linhas_horizontais = cv2.morphologyEx(imagem_binarizada, cv2.MORPH_OPEN, kernel_horizontal)
    linhas_verticais = cv2.morphologyEx(imagem_binarizada, cv2.MORPH_OPEN, kernel_vertical)

    grade = cv2.bitwise_or(linhas_horizontais, linhas_verticais)
    grade = cv2.dilate(grade, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

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

    TOLERANCIA_LINHA = 10 * k
    celulas.sort(key=lambda c: c[1])
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
        linha.sort(key=lambda c: c[0])

    return imagem_cinza, linhas, (altura_pagina, largura_pagina)


def ocr_celulas(imagem_cinza, linhas, dimensoes_pagina, max_workers=None):
    """Roda OCR em cada célula EM PARALELO (usando threads), porque cada
    chamada ao Tesseract sobe um processo próprio — sem paralelizar, milhares
    de células rodam uma atrás da outra e fica muito lento."""
    altura_pagina, largura_pagina = dimensoes_pagina
    CONFIG_NUMERICA = '--psm 7 -c tessedit_char_whitelist=0123456789'
    CONFIG_TEXTO = '--psm 7'
    MARGEM = 1
    max_workers = max_workers or min(32, (os.cpu_count() or 4) * 2)

    def processar_celula(args):
        indice_coluna, x, y, w, h, total_colunas_linha = args
        x0 = max(x + MARGEM, 0)
        y0 = max(y + MARGEM, 0)
        x1 = min(x + w - MARGEM, largura_pagina)
        y1 = min(y + h - MARGEM, altura_pagina)
        celula_img = imagem_cinza[y0:y1, x0:x1]
        if celula_img.size == 0:
            return ''

        celula_img = cv2.copyMakeBorder(
            celula_img, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255
        )

        eh_texto = indice_coluna in (0, 1) or indice_coluna == total_colunas_linha - 1
        config = CONFIG_TEXTO if eh_texto else CONFIG_NUMERICA

        return pytesseract.image_to_string(celula_img, lang='por', config=config).strip()

    tabela = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for linha in linhas:
            tarefas = [(i, x, y, w, h, len(linha)) for i, (x, y, w, h) in enumerate(linha)]
            linha_textos = list(executor.map(processar_celula, tarefas))
            tabela.append(linha_textos)

    return tabela


def eh_linha_de_aluno(linha_textos):
    if len(linha_textos) < 3:
        return False
    aluno = linha_textos[1]
    palavras = aluno.split()
    return len(palavras) >= 2


def extrair_numero_e_nome(texto_aluno):
    m = re.match(r'^\s*(\d+)\s*[-.]?\s*(.+)$', texto_aluno)
    if m:
        return m.group(1), m.group(2).strip()
    return None, texto_aluno.strip()


def montar_dados_longos(tabela):
    dados_longos = []
    linhas_alunos = [l for l in tabela if eh_linha_de_aluno(l)]

    print(f'Linhas de cabeçalho descartadas: {len(tabela) - len(linhas_alunos)}')
    print(f'Linhas de aluno identificadas: {len(linhas_alunos)}')

    for linha in linhas_alunos:
        numero, nome = extrair_numero_e_nome(linha[1])
        obs = linha[-1]
        valores_notas = linha[2:-1]
        dados_longos.extend(linha_larga_para_longa(numero, nome, valores_notas, obs))

    return dados_longos


def processar_pagina(imagem_cv2, fator_upscale=FATOR_UPSCALE):
    """Roda a extração completa numa única página/imagem já carregada."""
    imagem_cinza, linhas, dimensoes = extrair_celulas_da_imagem(imagem_cv2, fator_upscale)
    tabela = ocr_celulas(imagem_cinza, linhas, dimensoes)
    return montar_dados_longos(tabela)


def processar_imagem_fisica(caminho_imagem, fator_upscale=FATOR_UPSCALE):
    """Recebe o caminho de UMA imagem (PNG/JPEG) e devolve os dados no formato longo."""
    imagem = cv2.imread(caminho_imagem)
    if imagem is None:
        raise ValueError(f"Não foi possível abrir a imagem: {caminho_imagem}")
    return processar_pagina(imagem, fator_upscale)


def processar_pdf_fisica(caminho_pdf, fator_upscale=FATOR_UPSCALE, dpi=300):
    """Recebe o caminho de um PDF (pode ter várias páginas, ex: frente e
    verso) e devolve os dados de TODAS as páginas concatenados — assume que
    cada página continua a mesma tabela (mesmas colunas, alunos diferentes),
    igual ao que já acontece com o PDF do sistema."""
    paginas_pil = convert_from_path(caminho_pdf, dpi=dpi)

    dados_longos = []
    for i, pagina_pil in enumerate(paginas_pil):
        print(f'Processando página {i + 1}/{len(paginas_pil)} da pauta física...')
        imagem_cv2 = cv2.cvtColor(np.array(pagina_pil), cv2.COLOR_RGB2BGR)
        dados_longos.extend(processar_pagina(imagem_cv2, fator_upscale))

    return dados_longos


def processar_arquivo_fisico(caminho_arquivo, fator_upscale=FATOR_UPSCALE):
    """Ponto de entrada único: detecta se é PDF ou imagem e chama o processamento certo."""
    extensao = os.path.splitext(caminho_arquivo)[1].lower()
    if extensao == '.pdf':
        return processar_pdf_fisica(caminho_arquivo, fator_upscale)
    return processar_imagem_fisica(caminho_arquivo, fator_upscale)


if __name__ == '__main__':
    dados_longos = processar_arquivo_fisico(CAMINHO_ARQUIVO)

    with open(CAMINHO_SAIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(dados_longos, f, ensure_ascii=False, indent=2)

    print(f'\nSalvo em {CAMINHO_SAIDA_JSON}: {len(dados_longos)} registros de nota.')
    print('\nExemplo (primeiros 5 registros):')
    for registro in dados_longos[:5]:
        print(' ', registro)