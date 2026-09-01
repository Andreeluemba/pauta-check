"""
extrai_sistema.py

Lê a pauta do SISTEMA em PDF (esperado: texto digital, não escaneado — então
sem necessidade de OCR) e converte pro mesmo formato longo que extrai_fisica.py
gera, pra poder alimentar compara_pautas.py.

IMPORTANTE: este script foi escrito e testado com um PDF FICTÍCIO
(pauta_sistema_teste.pdf, gerado por gerar_pdf_teste.py), porque ainda não
temos acesso ao PDF real do sistema do IMEL. A lógica de "achar a tabela e
mapear colunas" é genérica e deve funcionar, mas provavelmente vai precisar
de pequenos ajustes quando testarmos com o arquivo de verdade — cada sistema
acadêmico formata o PDF de um jeito. Pontos prováveis de ajuste estão
marcados com "AJUSTAR" abaixo.
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
    grade do pdfplumber. Descarta tabelas pequenas demais (ex: o quadro de
    'Área de Formação / Curso Técnico' no topo da página, que pdfplumber às
    vezes também detecta como tabela) — só nos interessa a tabela de notas."""
    todas_as_linhas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages):
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                n_colunas = len(tabela[0]) if tabela else 0
                if n_colunas < COLUNAS_ESPERADAS - 5:  # tolerância pequena
                    print(f'Página {i + 1}: ignorando tabela pequena ({n_colunas} colunas) — não é a pauta')
                    continue
                print(f'Página {i + 1}: tabela de notas encontrada ({len(tabela)} linhas, {n_colunas} colunas)')
                todas_as_linhas.extend(tabela)
    return todas_as_linhas


def eh_linha_de_aluno(linha):
    """Mesma ideia do extrai_fisica.py: uma linha de ALUNO de verdade tem
    nome com pelo menos 2 palavras na coluna 'Aluno' (índice 1).
    AJUSTAR: se o PDF real tiver colunas em ordem diferente (ex: Aluno é a
    coluna 0, não a 1), mude o índice aqui."""
    if not linha or len(linha) < 3:
        return False
    aluno = linha[1] or ''
    return len(aluno.split()) >= 2


def extrair_numero_e_nome(texto_aluno):
    """Mesma lógica do extrai_fisica.py — mantida idêntica de propósito,
    pra tratar os dois extratores da forma mais parecida possível."""
    texto_aluno = (texto_aluno or '').strip()
    m = re.match(r'^\s*(\d+)\s*[-.]?\s*(.+)$', texto_aluno)
    if m:
        return m.group(1), m.group(2).strip()
    return None, texto_aluno


def montar_dados_longos(linhas_tabela):
    """Filtra cabeçalhos e converte cada linha de aluno pro formato longo,
    usando o mesmo esquema de colunas que a pauta física usa.
    AJUSTAR: se o PDF do sistema tiver uma ORDEM DE DISCIPLINAS diferente da
    pauta física, o esquema_pauta.py é o lugar certo pra corrigir isso (não
    aqui) — assim os dois extratores continuam consistentes."""
    dados_longos = []
    linhas_alunos = [l for l in linhas_tabela if eh_linha_de_aluno(l)]

    print(f'Linhas de cabeçalho descartadas: {len(linhas_tabela) - len(linhas_alunos)}')
    print(f'Linhas de aluno identificadas: {len(linhas_alunos)}')

    for linha in linhas_alunos:
        numero, nome = extrair_numero_e_nome(linha[1])
        # Se o nome (índice 1) não tinha o número embutido (formato "N - Nome"),
        # tenta usar a coluna Nº separada (índice 0), que é o formato mais comum
        # em tabelas de PDF digital.
        if numero is None and (linha[0] or '').strip().isdigit():
            numero = linha[0].strip()
        obs = linha[-1] or ''
        valores_notas = linha[2:-1]
        dados_longos.extend(linha_larga_para_longa(numero, nome, valores_notas, obs))

    return dados_longos


if __name__ == '__main__':
    linhas_tabela = extrair_tabelas_do_pdf(CAMINHO_PDF)
    print(f'\nTotal de linhas extraídas (todas as páginas, com cabeçalho): {len(linhas_tabela)}')

    print('\nPrimeiras 5 linhas BRUTAS (antes de qualquer filtro), pra conferência visual:')
    for linha in linhas_tabela[:5]:
        print(' ', linha)

    dados_longos = montar_dados_longos(linhas_tabela)

    with open(CAMINHO_SAIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(dados_longos, f, ensure_ascii=False, indent=2)

    print(f'\nSalvo em {CAMINHO_SAIDA_JSON}: {len(dados_longos)} registros de nota.')
    print('\nExemplo (primeiros 5 registros):')
    for registro in dados_longos[:5]:
        print(' ', registro)