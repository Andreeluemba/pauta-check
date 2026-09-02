"""
app.py

API que liga o frontend aos três scripts: extrai_sistema, extrai_fisica e
compara_pautas. Recebe os dois arquivos via upload, processa e devolve só
as divergências.
"""

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from extrai_sistema import processar_pdf_sistema
from extrai_fisica import processar_arquivo_fisico
from compara_pautas import comparar_pautas

app = FastAPI()

# Sem isso, o navegador bloqueia o frontend (localhost:5173) de chamar
# essa API (localhost:8000) — são "origens" diferentes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def salvar_upload_temporario(arquivo: UploadFile) -> str:
    """Salva um arquivo enviado num arquivo temporário em disco (as funções
    de extração esperam um caminho de arquivo, não os bytes crus)."""
    sufixo = Path(arquivo.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
        shutil.copyfileobj(arquivo.file, tmp)
        return tmp.name


@app.get("/")
def status():
    return {"status": "ok"}


@app.post("/comparar")
async def comparar(pdf_sistema: UploadFile = File(...), pauta_fisica: UploadFile = File(...)):
    caminho_sistema = salvar_upload_temporario(pdf_sistema)
    caminho_fisica = salvar_upload_temporario(pauta_fisica)

    try:
        dados_sistema = processar_pdf_sistema(caminho_sistema)
        dados_fisica = processar_arquivo_fisico(caminho_fisica)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar arquivos: {e}")

    resultado = comparar_pautas(dados_sistema, dados_fisica)

    divergencias_reais = [d for d in resultado["divergencias"] if d["tipo"] == "divergencia_real"]
    falhas_leitura = [d for d in resultado["divergencias"] if d["tipo"] != "divergencia_real"]

    return {
        "divergencias_reais": divergencias_reais,
        "falhas_leitura": falhas_leitura,
        "total_alunos_ok": len(resultado["alunos_sem_divergencia"]),
    }