# Pauta Check

Sistema para **conferir automaticamente** as notas de uma pauta escolar do sistema (PDF, exportado digitalmente) contra a pauta física (impressa/assinada, digitalizada), apontando **quais notas divergem**, por aluno, disciplina e tipo de avaliação.

Nasceu de um problema real: pautas físicas às vezes têm notas diferentes das que estão registadas no sistema, e conferir isso manualmente, linha por linha, é lento e sujeito a erro humano.

---

## Índice

- [Como funciona](#como-funciona)
- [Arquitetura](#arquitetura)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
  - [Backend](#backend-python--fastapi)
  - [Frontend](#frontend-react--vite--tailwind--shadcnui)
- [Como rodar](#como-rodar)
- [Endpoints da API](#endpoints-da-api)
- [Limitações conhecidas](#limitações-conhecidas)
- [Roadmap](#roadmap)

---

## Como funciona

O sistema recebe **dois arquivos**:

1. **Pauta do sistema** — PDF exportado diretamente do sistema acadêmico (texto digital, não escaneado)
2. **Pauta física** — a pauta impressa, assinada e digitalizada (PDF de várias páginas ou imagem PNG/JPEG)

E faz o seguinte, nessa ordem:

1. **Extrai** a pauta do sistema lendo o texto do PDF diretamente (`extrai_sistema.py`, usando `pdfplumber`)
2. **Extrai** a pauta física usando OCR — detecta a grade da tabela, recorta cada célula e lê o conteúdo com Tesseract (`extrai_fisica.py`, usando OpenCV + `pytesseract`). Funciona tanto para imagem única quanto PDF de várias páginas (ex: frente e verso)
3. **Casa os alunos** das duas pautas por similaridade de nome (tolera pequenas diferenças de grafia/OCR) e **compara nota a nota** (`compara_pautas.py`)
4. Separa o resultado em dois grupos:
   - **Divergências reais** — os dois lados têm um valor, e são diferentes (o que realmente interessa investigar)
   - **Falhas de leitura** — o OCR não conseguiu ler aquela célula específica (não é um erro do professor, é uma limitação da digitalização)
5. Mostra o resultado agrupado por aluno no frontend, e permite gerar um **relatório em PDF** com tudo detalhado

## Arquitetura

```
┌─────────────────┐        multipart/form-data        ┌──────────────────────┐
│   Frontend       │ ─────────────────────────────────▶│   Backend (FastAPI)  │
│   React + Vite   │                                    │                       │
│   + Tailwind     │◀───────────────────────────────── │  extrai_sistema.py    │
│   + shadcn/ui     │      JSON / PDF (relatório)        │  extrai_fisica.py     │
└─────────────────┘                                    │  compara_pautas.py    │
                                                          └──────────────────────┘
```

O backend é **stateless**: cada requisição recebe os dois arquivos, processa tudo em memória/arquivos temporários e devolve o resultado — nada fica salvo em banco de dados nesta versão.

## Estrutura do projeto

```
pauta-check/
├── venv/                      # ambiente virtual Python (não versionado)
├── esquema_pauta.py           # define a ordem das colunas de disciplina/campo da pauta
├── extrai_sistema.py          # lê o PDF do sistema e devolve os dados em formato "longo"
├── extrai_fisica.py           # OCR da pauta física (imagem ou PDF multi-página)
├── compara_pautas.py          # casa alunos e compara notas, classificando divergências
├── app.py                     # API FastAPI que liga os três scripts acima
├── requirements.txt           # dependências Python
└── frontend/
    ├── src/
    │   ├── App.tsx             # tela principal: upload, tabela de resultados, botão de PDF
    │   ├── components/ui/      # componentes shadcn/ui
    │   └── lib/utils.ts
    ├── package.json
    ├── vite.config.ts
    └── tsconfig.json
```

**Formato "longo"** (usado internamente entre os scripts): cada nota é um registro separado, não uma linha por aluno —

```json
{ "numero": "7", "aluno": "Ana Gonga Vungi", "disciplina": "PORT", "campo": "MT1", "nota": "14" }
```

Isso permite comparar granularmente **qual nota específica** divergiu, em vez de só saber que "algo" está diferente na linha do aluno.

## Pré-requisitos

| Ferramenta | Uso | Instalação (Ubuntu/Debian) |
|---|---|---|
| Python 3.10+ | backend | já vem no sistema, ou `sudo apt install python3` |
| `python3-venv` | ambiente isolado | `sudo apt install python3-venv` |
| Tesseract OCR + idioma português | leitura da pauta física | `sudo apt install tesseract-ocr tesseract-ocr-por` |
| Poppler | converter PDF → imagem (pauta física em PDF) | `sudo apt install poppler-utils` |
| Node.js + npm | frontend | [nodejs.org](https://nodejs.org) ou `nvm` |

## Instalação

### Backend (Python + FastAPI)

```bash
# na raiz do projeto
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` (se não existir ainda, cria com este conteúdo):

```
fastapi
uvicorn
python-multipart
pdfplumber
opencv-python
pytesseract
numpy
pdf2image
unidecode
rapidfuzz
reportlab
```

### Frontend (React + Vite + Tailwind + shadcn/ui)

```bash
cd frontend
npm install
```

O Tailwind e o shadcn/ui já vêm configurados no projeto (alias `@/` em `tsconfig.json` e `vite.config.ts`, tema em `components.json`). Se estiver clonando do zero e algo não existir, veja as seções de configuração no histórico do projeto ou a [documentação oficial do shadcn/ui](https://ui.shadcn.com/docs/installation/vite).

## Como rodar

Precisa de **dois terminais abertos ao mesmo tempo**:

**Terminal 1 — backend**
```bash
cd pauta-check
source venv/bin/activate
uvicorn app:app --reload
```
Sobe em `http://127.0.0.1:8000`. A documentação interativa (útil pra testar sem o frontend) fica em `http://127.0.0.1:8000/docs`.

**Terminal 2 — frontend**
```bash
cd pauta-check/frontend
npm run dev
```
Sobe em `http://localhost:5173`.

Abre `http://localhost:5173` no navegador, escolhe os dois arquivos (PDF do sistema + pauta física em PDF/PNG/JPEG) e clica em **Verificar**.

## Endpoints da API

### `GET /`
Health check simples.
```json
{ "status": "ok" }
```

### `POST /comparar`
Recebe os dois arquivos (`multipart/form-data`) e devolve as divergências em JSON.

**Campos do form:**
- `pdf_sistema` — arquivo PDF
- `pauta_fisica` — arquivo PDF, PNG ou JPEG

**Resposta:**
```json
{
  "divergencias_reais": [
    {
      "numero_sistema": "7",
      "aluno_sistema": "Ana Gonga Vungi",
      "disciplina": "port",
      "campo": "MT1",
      "nota_sistema": "14",
      "nota_fisica": "4"
    }
  ],
  "falhas_leitura": [ ... ],
  "total_alunos_ok": 32
}
```

### `POST /relatorio`
Mesmos campos de entrada que `/comparar`, mas devolve um **arquivo PDF** (`application/pdf`) com o relatório completo, agrupado por aluno, incluindo o resumo geral e as células que o OCR não conseguiu ler.

## Limitações conhecidas

- **Qualidade do OCR depende da resolução da digitalização.** Em testes com imagens de baixa resolução (~1349×949px), a taxa de leitura correta célula-a-célula ficou em torno de 39%. Recomenda-se digitalizar a pauta física a pelo menos **200–300 DPI**.
- **A pauta física em PDF assume que todas as páginas seguem a mesma estrutura de colunas** (ex: frente e verso com alunos diferentes, mesmas disciplinas) — não foi testado com layouts onde as colunas mudam entre páginas.
- **Sem persistência**: nada é salvo em banco de dados; cada verificação é isolada por requisição.
- **Sem autenticação**: pensado como protótipo/demonstração, não para uso em produção sem adicionar controle de acesso.
- O `esquema_pauta.py` está calibrado para o layout específico de uma pauta (curso técnico observado). Pautas de outros cursos/turmas com disciplinas diferentes exigem ajustar `DISCIPLINAS_EM_ORDEM` nesse arquivo.

## Roadmap

- [ ] Persistência em banco de dados (histórico de verificações)
- [ ] Autenticação e controle de acesso
- [ ] Suporte a múltiplos templates de pauta (detecção automática de curso/turma)
- [ ] Melhorar a taxa de acerto do OCR (pré-processamento adicional, ou OCR baseado em modelo de tabela dedicado)
- [ ] Módulo integrado ao sistema acadêmico existente (CodeIgniter), reaproveitando o banco de dados direto em vez de exportação por PDF