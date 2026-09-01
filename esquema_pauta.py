"""
esquema_pauta.py

Define a ORDEM das colunas de nota da pauta (Nº e Aluno ficam de fora daqui,
e OBS também fica de fora — é tratado à parte no final de cada linha).

Isso é o "mapa" que tanto o extrator do sistema (PDF) quanto o extrator da
física (OCR) usam pra saber "a 5ª coluna de nota é a disciplina X, campo Y".

Baseado no cabeçalho real observado na pauta do IMEL (TAP11AM):
Nº | Aluno | ECON-10º | DLC-10º | PORT(CF-10º,MT3,CA,CFD) | INGLÊS(...) |
F.A.L(...) | ED.FÍS(MTI,MT2,MT3,CA) | GEOG(...) | DIREITO(...) | SOCIOL(...) |
INFORMAT(CF-10º,MT3,CA,CFD) | C.GERAL(...) | MAT(MTI,MT2,MT3,CA) | GEP(...) | OBS

IMPORTANTE: se a pauta do sistema ou outra turma tiver disciplinas diferentes
(cursos técnicos variam), ajuste esta lista. É o único lugar que precisa mudar.
"""

# Disciplinas cujo "sub-cabeçalho" é CF-10º, MT3, CA, CFD
GRUPO_TIPO_A = ['CF-10º', 'MT3', 'CA', 'CFD']

# Disciplinas cujo "sub-cabeçalho" é MTI, MT2, MT3, CA
GRUPO_TIPO_B = ['MTI', 'MT2', 'MT3', 'CA']

# Ordem das disciplinas exatamente como aparecem na pauta, da esquerda pra direita,
# com o tipo de sub-cabeçalho de cada uma.
DISCIPLINAS_EM_ORDEM = [
    ('ECON-10º', None),       # coluna única, sem sub-campos
    ('DLC-10º', None),        # coluna única, sem sub-campos
    ('PORT', GRUPO_TIPO_A),
    ('INGLÊS', GRUPO_TIPO_A),
    ('F.A.L', GRUPO_TIPO_A),
    ('ED.FÍS', GRUPO_TIPO_B),
    ('GEOG', GRUPO_TIPO_B),
    ('DIREITO', GRUPO_TIPO_B),
    ('SOCIOL', GRUPO_TIPO_B),
    ('INFORMAT', GRUPO_TIPO_A),
    ('C.GERAL', GRUPO_TIPO_A),
    ('MAT', GRUPO_TIPO_B),
    ('GEP', GRUPO_TIPO_B),
]


def construir_esquema_colunas():
    """
    Achata DISCIPLINAS_EM_ORDEM numa lista simples de (disciplina, campo),
    uma entrada por COLUNA DE NOTA (sem contar Nº, Aluno e OBS).

    Pra colunas sem sub-campo (ECON-10º, DLC-10º), usa campo='NOTA'.
    """
    esquema = []
    for disciplina, campos in DISCIPLINAS_EM_ORDEM:
        if campos is None:
            esquema.append((disciplina, 'NOTA'))
        else:
            for campo in campos:
                esquema.append((disciplina, campo))
    return esquema


ESQUEMA_COLUNAS = construir_esquema_colunas()


def linha_larga_para_longa(numero, aluno, valores_notas, obs=''):
    """
    Converte uma linha "larga" (um aluno, uma lista de valores de nota na
    ordem das colunas) em várias entradas "longas" (uma por nota), no formato
    que compara_pautas.py espera.

    Se 'valores_notas' tiver um tamanho diferente do ESQUEMA_COLUNAS, ainda
    assim faz o mapeamento até onde der (zip para no menor dos dois) e avisa,
    porque isso normalmente indica célula perdida/sobrando na extração.
    """
    linhas_longas = []

    if len(valores_notas) != len(ESQUEMA_COLUNAS):
        print(
            f"[AVISO] Aluno '{aluno}': esperava {len(ESQUEMA_COLUNAS)} colunas de nota, "
            f"recebeu {len(valores_notas)}. Conferir se alguma célula foi perdida "
            f"ou duplicada na extração dessa linha."
        )

    for (disciplina, campo), nota in zip(ESQUEMA_COLUNAS, valores_notas):
        linhas_longas.append({
            'numero': numero,
            'aluno': aluno,
            'disciplina': disciplina,
            'campo': campo,
            'nota': nota,
        })

    linhas_longas.append({
        'numero': numero,
        'aluno': aluno,
        'disciplina': 'OBS',
        'campo': 'STATUS',
        'nota': obs,
    })

    return linhas_longas


if __name__ == '__main__':
    # Auto-teste: confere quantas colunas de nota o esquema define
    print(f'Total de colunas de nota no esquema: {len(ESQUEMA_COLUNAS)}')
    for i, (disciplina, campo) in enumerate(ESQUEMA_COLUNAS):
        print(f'  {i:2d}: {disciplina} - {campo}')