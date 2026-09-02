"""
extrai_sistema.py

Lê a pauta do SISTEMA em PDF (esperado: texto digital, não escaneado — então
sem necessidade de OCR) e converte pro mesmo formato longo que extrai_fisica.py
gera, pra poder alimentar compara_pautas.py.
"""

import re
import json
import pdfplumber

from esquema_pauta import ESQUEMA_COLUNAS, linha_larga_para_longa

CAMINHO_PDF = 'IMEL_PAUTA-ANUAL-TAP11AM-11A-2025_2026.pdf'
CAMINHO_SAIDA_JSON = 'dados_sistema.json'

COLUNAS_ESPERADAS = 2 + len(ESQUEMA_COLUNAS) + 1  # Nº + Aluno + notas + OBS


def extrair_tabelas_do_pdf(caminho_pdf):
    """Abre o PDF e tenta extrair tabelas de cada página usando a detecção de
    grade do pdfplumber. Descarta tabelas pequenas demais."""
    todas_as_linhas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages):
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                n_colunas = len(tabela[0]) if tabela else 0
                if n_colunas < COLUNAS_ESPERADAS - 5:
                    print(f'Página {i + 1}: ignorando tabela pequena ({n_colunas} colunas) — não é a pauta')
                    continue
                print(f'Página {i + 1}: tabela de notas encontrada ({len(tabela)} linhas, {n_colunas} colunas)')
                todas_as_linhas.extend(tabela)
    return todas_as_linhas


def eh_linha_de_aluno(linha):
    if not linha or len(linha) < 3:
        return False
    aluno = linha[1] or ''
    return len(aluno.split()) >= 2


def extrair_numero_e_nome(texto_aluno):
    texto_aluno = (texto_aluno or '').strip()
    m = re.match(r'^\s*(\d+)\s*[-.]?\s*(.+)$', texto_aluno)
    if m:
        return m.group(1), m.group(2).strip()
    return None, texto_aluno


def montar_dados_longos(linhas_tabela):
    dados_longos = []
    linhas_alunos = [l for l in linhas_tabela if eh_linha_de_aluno(l)]

    print(f'Linhas de cabeçalho descartadas: {len(linhas_tabela) - len(linhas_alunos)}')
    print(f'Linhas de aluno identificadas: {len(linhas_alunos)}')

    for linha in linhas_alunos:
        numero, nome = extrair_numero_e_nome(linha[1])
        if numero is None and (linha[0] or '').strip().isdigit():
            numero = linha[0].strip()
        obs = linha[-1] or ''
        valores_notas = linha[2:-1]
        dados_longos.extend(linha_larga_para_longa(numero, nome, valores_notas, obs))

    return dados_longos


def processar_pdf_sistema(caminho_pdf):
    """Recebe o caminho de um PDF do sistema e devolve os dados no formato
    longo (lista de registros aluno/disciplina/campo/nota), prontos pra
    comparar com a pauta física."""
    linhas_tabela = extrair_tabelas_do_pdf(caminho_pdf)
    dados_longos = montar_dados_longos(linhas_tabela)
    return dados_longos


if __name__ == '__main__':
    dados_longos = processar_pdf_sistema(CAMINHO_PDF)

    with open(CAMINHO_SAIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(dados_longos, f, ensure_ascii=False, indent=2)

    print(f'\nSalvo em {CAMINHO_SAIDA_JSON}: {len(dados_longos)} registros de nota.')
    print('\nExemplo (primeiros 5 registros):')
    for registro in dados_longos[:5]:
        print(' ', registro)