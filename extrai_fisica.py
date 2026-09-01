import re
import json
import cv2
import pytesseract

from esquema_pauta import ESQUEMA_COLUNAS, linha_larga_para_longa

CAMINHO_IMAGEM = 'pauta.png'
CAMINHO_SAIDA_JSON = 'dados_fisica.json'
FATOR_UPSCALE = 4  # as células originais são minúsculas (~18x12px); sem isso o OCR não lê nada


def extrair_celulas_da_imagem(caminho_imagem, fator_upscale=FATOR_UPSCALE):
    """Detecta a grade da tabela e retorna as células agrupadas em linhas,
    cada célula como (x, y, largura, altura), já ordenadas (linha, depois coluna)."""
    k = fator_upscale
    imagem = cv2.imread(caminho_imagem)
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


def ocr_celulas(imagem_cinza, linhas, dimensoes_pagina):
    """Recorta e roda OCR em cada célula, retornando uma lista de linhas de texto."""
    altura_pagina, largura_pagina = dimensoes_pagina
    CONFIG_NUMERICA = '--psm 7 -c tessedit_char_whitelist=0123456789'
    CONFIG_TEXTO = '--psm 7'
    MARGEM = 1

    tabela = []
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

            celula_img = cv2.copyMakeBorder(
                celula_img, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255
            )

            eh_texto = indice_coluna in (0, 1) or indice_coluna == len(linha) - 1
            config = CONFIG_TEXTO if eh_texto else CONFIG_NUMERICA

            texto = pytesseract.image_to_string(celula_img, lang='por', config=config).strip()
            linha_textos.append(texto)
        tabela.append(linha_textos)
    return tabela


def eh_linha_de_aluno(linha_textos):
    """
    Filtro heurístico: decide se uma linha da tabela é um ALUNO de verdade,
    ou se é lixo de cabeçalho (nomes de disciplina, sub-cabeçalhos MTI/MT2...).

    Regra usada: a coluna 'Aluno' (índice 1) precisa ter pelo menos duas
    palavras (nome e sobrenome) — cabeçalhos não têm esse formato.
    """
    if len(linha_textos) < 3:
        return False
    aluno = linha_textos[1]
    palavras = aluno.split()
    return len(palavras) >= 2


def extrair_numero_e_nome(texto_aluno):
    """
    A célula de aluno vem tipo '1 - Aliria Daniela Filipe da Silva' ou
    '12 - Délcio Manuel António Pequeno'. Separa o número do nome.
    Se não achar o padrão 'NÚMERO - NOME', retorna (None, texto_aluno completo).
    """
    m = re.match(r'^\s*(\d+)\s*[-.]?\s*(.+)$', texto_aluno)
    if m:
        return m.group(1), m.group(2).strip()
    return None, texto_aluno.strip()


def montar_dados_longos(tabela):
    """Filtra linhas de cabeçalho, separa número/nome/OBS, e usa o esquema
    de colunas pra converter cada linha num conjunto de registros no formato longo."""
    dados_longos = []
    linhas_alunos = [l for l in tabela if eh_linha_de_aluno(l)]

    print(f'Linhas de cabeçalho descartadas: {len(tabela) - len(linhas_alunos)}')
    print(f'Linhas de aluno identificadas: {len(linhas_alunos)}')

    for linha in linhas_alunos:
        numero, nome = extrair_numero_e_nome(linha[1])
        obs = linha[-1]
        valores_notas = linha[2:-1]  # tudo entre Aluno e OBS
        dados_longos.extend(linha_larga_para_longa(numero, nome, valores_notas, obs))

    return dados_longos


if __name__ == '__main__':
    imagem_cinza, linhas, dimensoes = extrair_celulas_da_imagem(CAMINHO_IMAGEM)
    print(f'Total de linhas de célula identificadas: {len(linhas)}')

    tabela = ocr_celulas(imagem_cinza, linhas, dimensoes)
    dados_longos = montar_dados_longos(tabela)

    with open(CAMINHO_SAIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(dados_longos, f, ensure_ascii=False, indent=2)

    print(f'\nSalvo em {CAMINHO_SAIDA_JSON}: {len(dados_longos)} registros de nota.')
    print('\nExemplo (primeiros 5 registros):')
    for registro in dados_longos[:5]:
        print(' ', registro)