"""
compara_pautas.py

Motor de comparação entre a pauta do SISTEMA (PDF, extração direta de texto)
e a pauta FÍSICA escaneada (OCR). Detecta alunos e notas divergentes.

FORMATO DE ENTRADA ESPERADO (lista de dicionários, "formato longo"):
    {'aluno': 'Ana Gonga Vungi', 'disciplina': 'L.Portuguesa', 'campo': 'MT1', 'nota': '14'}

Por que "formato longo" (uma linha por nota) em vez de uma linha por aluno?
Porque cada aluno tem dezenas de notas (uma por disciplina x campo: MT1, MT2, CA...).
Comparar linha a linha inteira esconderia QUAL nota específica divergiu.
Assim, cada comparação é o mais granular possível: 1 aluno + 1 disciplina + 1 campo.

Quando tivermos os extratores de PDF/OCR prontos, a saída deles deve ser
convertida pra essa lista de dicionários antes de chamar este script.
"""

from unidecode import unidecode
from rapidfuzz import fuzz, process


def normalizar_nome(nome):
    """Remove acentos, espaços extras e deixa em minúsculo, pra comparar nomes
    que podem ter vindo com pequenas diferenças de digitação/OCR."""
    return unidecode(nome).lower().strip()


def normalizar_disciplina(nome):
    """Mesma ideia, mas pra nomes de disciplina (ex: 'L.Portuguesa' vs 'Língua Portuguesa')."""
    texto = unidecode(nome).lower().strip()
    texto = texto.replace('.', '').replace('_', ' ')
    return ' '.join(texto.split())  # colapsa espaços múltiplos


def casar_alunos(nomes_sistema, nomes_fisica, limite_similaridade=80):
    """
    Casa os nomes de aluno entre as duas pautas, mesmo com pequenas diferenças
    de grafia (comuns em OCR). Usa similaridade de texto (0-100).

    Retorna:
        pares: lista de (nome_sistema, nome_fisica, pontuacao)
        sem_par_sistema: nomes do sistema sem correspondência confiável na física
        sem_par_fisica: nomes da física sem correspondência confiável no sistema
    """
    nomes_fisica_norm = {normalizar_nome(n): n for n in nomes_fisica}
    disponiveis = dict(nomes_fisica_norm)  # cópia, pra ir "consumindo" à medida que casa

    pares = []
    sem_par_sistema = []

    for nome_sis in nomes_sistema:
        nome_sis_norm = normalizar_nome(nome_sis)
        if not disponiveis:
            sem_par_sistema.append(nome_sis)
            continue

        melhor = process.extractOne(
            nome_sis_norm, disponiveis.keys(), scorer=fuzz.token_sort_ratio
        )
        if melhor and melhor[1] >= limite_similaridade:
            chave_norm = melhor[0]
            nome_fis_original = disponiveis.pop(chave_norm)
            pares.append((nome_sis, nome_fis_original, melhor[1]))
        else:
            sem_par_sistema.append(nome_sis)

    sem_par_fisica = list(disponiveis.values())
    return pares, sem_par_sistema, sem_par_fisica


def comparar_pautas(dados_sistema, dados_fisica, limite_similaridade_nome=80, ignorar_disciplinas=('OBS',)):
    nomes_sistema = sorted({d['aluno'] for d in dados_sistema})
    nomes_fisica = sorted({d['aluno'] for d in dados_fisica})

    pares, sem_par_sistema, sem_par_fisica = casar_alunos(
        nomes_sistema, nomes_fisica, limite_similaridade_nome
    )

    divergencias = []
    alunos_ok = []

    for nome_sis, nome_fis, pontuacao in pares:
        registros_sis = [d for d in dados_sistema if d['aluno'] == nome_sis]
        registros_fis = [d for d in dados_fisica if d['aluno'] == nome_fis]

        numero_sis = registros_sis[0]['numero'] if registros_sis else None
        numero_fis = registros_fis[0]['numero'] if registros_fis else None

        notas_sis = {
            (normalizar_disciplina(d['disciplina']), d['campo']): d['nota']
            for d in registros_sis if d['disciplina'] not in ignorar_disciplinas
        }
        notas_fis = {
            (normalizar_disciplina(d['disciplina']), d['campo']): d['nota']
            for d in registros_fis if d['disciplina'] not in ignorar_disciplinas
        }

        todas_chaves = set(notas_sis.keys()) | set(notas_fis.keys())
        aluno_teve_divergencia_real = False

        for chave in sorted(todas_chaves):
            disciplina, campo = chave
            nota_sis = str(notas_sis.get(chave, '')).strip()
            nota_fis = str(notas_fis.get(chave, '')).strip()

            if nota_sis == nota_fis:
                continue  # bateu certinho, nem entra na lista

            # Classifica O TIPO da diferença, em vez de tratar tudo igual
            if not nota_fis:
                tipo = 'leitura_fisica_falhou'   # OCR não conseguiu ler essa célula
            elif not nota_sis:
                tipo = 'leitura_sistema_falhou'  # raro, mas pode acontecer
            else:
                tipo = 'divergencia_real'        # os dois têm valor, e são diferentes
                aluno_teve_divergencia_real = True

            divergencias.append({
                'tipo': tipo,
                'numero_sistema': numero_sis,
                'numero_fisica': numero_fis,
                'aluno_sistema': nome_sis,
                'aluno_fisica': nome_fis,
                'similaridade_nome': pontuacao,
                'disciplina': disciplina,
                'campo': campo,
                'nota_sistema': nota_sis or '(vazio)',
                'nota_fisica': nota_fis or '(vazio)',
            })

        if not aluno_teve_divergencia_real:
            alunos_ok.append(nome_sis)

    return {
        'divergencias': divergencias,
        'alunos_sem_divergencia': alunos_ok,
        'alunos_so_no_sistema': sem_par_sistema,
        'alunos_so_na_fisica': sem_par_fisica,
    }


def imprimir_relatorio(resultado):
    print('=' * 70)
    print('RELATÓRIO DE COMPARAÇÃO DE PAUTAS')
    print('=' * 70)

    if resultado['alunos_so_no_sistema']:
        print(f"\n⚠ Alunos só encontrados na pauta do SISTEMA (sem par na física):")
        for nome in resultado['alunos_so_no_sistema']:
            print(f"  - {nome}")

    if resultado['alunos_so_na_fisica']:
        print(f"\n⚠ Alunos só encontrados na pauta FÍSICA (sem par no sistema):")
        for nome in resultado['alunos_so_na_fisica']:
            print(f"  - {nome}")

    print(f"\n✓ Alunos conferidos SEM divergência: {len(resultado['alunos_sem_divergencia'])}")

    print(f"\n✗ Divergências encontradas: {len(resultado['divergencias'])}")
    for d in resultado['divergencias']:
        print(
            f"  Aluno: {d['aluno_sistema']}  |  Disciplina: {d['disciplina']} ({d['campo']})  "
            f"|  Sistema = {d['nota_sistema']}   Física = {d['nota_fisica']}"
        )


# ---------------------------------------------------------------------------
# EXEMPLO / TESTE com dados fictícios, só pra validar a lógica antes de termos
# os dados reais extraídos dos dois PDFs.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Pauta do SISTEMA (consideramos "a fonte da verdade" nesse exemplo fictício)
    pauta_sistema = [
        {'aluno': 'Ana Gonga Vungi', 'disciplina': 'L.Portuguesa', 'campo': 'MT1', 'nota': '10'},
        {'aluno': 'Ana Gonga Vungi', 'disciplina': 'L.Portuguesa', 'campo': 'MT2', 'nota': '11'},
        {'aluno': 'Ana Gonga Vungi', 'disciplina': 'Matemática', 'campo': 'MT1', 'nota': '14'},
        {'aluno': 'Álvaro Pedro Kianvankuti', 'disciplina': 'L.Portuguesa', 'campo': 'MT1', 'nota': '13'},
        {'aluno': 'Álvaro Pedro Kianvankuti', 'disciplina': 'Matemática', 'campo': 'MT1', 'nota': '9'},
        {'aluno': 'Bernice Samuel Francisco', 'disciplina': 'L.Portuguesa', 'campo': 'MT1', 'nota': '12'},
    ]

    # Pauta FÍSICA escaneada (via OCR) — nomes levemente diferentes, e algumas notas trocadas de propósito
    pauta_fisica = [
        {'aluno': 'Ana Gonga Vengi', 'disciplina': 'L.Portuguesa', 'campo': 'MT1', 'nota': '5'},   # DIVERGE (era 10)
        {'aluno': 'Ana Gonga Vengi', 'disciplina': 'L.Portuguesa', 'campo': 'MT2', 'nota': '11'},  # igual
        {'aluno': 'Ana Gonga Vengi', 'disciplina': 'Matematica', 'campo': 'MT1', 'nota': '14'},    # igual
        {'aluno': 'Alvaro Pedro Kiamvankuti', 'disciplina': 'L.Portuguesa', 'campo': 'MT1', 'nota': '13'},  # igual
        {'aluno': 'Alvaro Pedro Kiamvankuti', 'disciplina': 'Matematica', 'campo': 'MT1', 'nota': '19'},    # DIVERGE (era 9)
        # 'Bernice Samuel Francisco' nem aparece aqui de propósito, pra testar "só no sistema"
        {'aluno': 'Carlos José Bira Pundo', 'disciplina': 'L.Portuguesa', 'campo': 'MT1', 'nota': '13'},  # só na física
    ]

    resultado = comparar_pautas(pauta_sistema, pauta_fisica)
    imprimir_relatorio(resultado)