import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from core.leitor_universal import LeitorUniversal
from core.base_conhecimento import BaseConhecimento
from core.entidades import Documento, TipoDocumento

router = APIRouter()

TEMP_DIR = os.path.join("data", "temp_uploads")


class DocumentoResponse(BaseModel):
    id: str
    fonte: str
    tipo: str
    data_processamento: str
    entidades_encontradas: int = 0
    resumo: Optional[str] = None
    confianca_ocr: float = 0.0
    orgao_origem: Optional[str] = None


@router.get("/", response_model=List[DocumentoResponse])
async def listar_documentos(
    limite: int = Query(50, description="Número máximo de documentos"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (pdf, imagem, html, etc)"),
):
    """Lista todos os documentos processados."""
    try:
        base = BaseConhecimento()
        documentos = base.carregar_documentos()
    except Exception:
        documentos = []

    # Filtra por tipo se especificado
    if tipo:
        documentos = [d for d in documentos if d.tipo.value == tipo]

    # Ordena por data de processamento (mais recente primeiro)
    documentos.sort(key=lambda d: d.data_processamento, reverse=True)

    return [
        DocumentoResponse(
            id=doc.id,
            fonte=os.path.basename(doc.fonte) if doc.fonte else doc.fonte,
            tipo=doc.tipo.value,
            data_processamento=doc.data_processamento.isoformat(),
            entidades_encontradas=len(doc.entidades),
            resumo=(doc.resumo or "")[:200],
            confianca_ocr=doc.confianca_ocr,
            orgao_origem=doc.orgao_origem,
        )
        for doc in documentos[:limite]
    ]


@router.get("/{documento_id}", response_model=DocumentoResponse)
async def get_documento(documento_id: str):
    """Obtém detalhes de um documento específico."""
    try:
        base = BaseConhecimento()
        documentos = base.carregar_documentos()
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao carregar documentos")

    for doc in documentos:
        if doc.id == documento_id:
            return DocumentoResponse(
                id=doc.id,
                fonte=doc.fonte,
                tipo=doc.tipo.value,
                data_processamento=doc.data_processamento.isoformat(),
                entidades_encontradas=len(doc.entidades),
                resumo=(doc.resumo or "")[:200],
                confianca_ocr=doc.confianca_ocr,
                orgao_origem=doc.orgao_origem,
            )

    raise HTTPException(status_code=404, detail="Documento não encontrado")


@router.post("/upload")
async def upload_documento(file: UploadFile = File(...)):
    """
    Recebe um documento para ser processado pela IA.
    Suporta: PDF, PNG, JPG, HTML, TXT, CSV, XLSX, JSON, XML
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo não fornecido")

    # Validar extensão
    ext = os.path.splitext(file.filename)[1].lower()
    extensoes_validas = {".pdf", ".png", ".jpg", ".jpeg", ".html", ".htm", ".txt", ".csv", ".xlsx", ".xls", ".json", ".xml"}
    if ext not in extensoes_validas:
        raise HTTPException(
            status_code=400,
            detail=f"Formato '{ext}' não suportado. Formatos aceitos: {', '.join(extensoes_validas)}"
        )

    try:
        # Salva o arquivo temporariamente
        os.makedirs(TEMP_DIR, exist_ok=True)
        file_path = os.path.join(TEMP_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Processa o documento
        leitor = LeitorUniversal()
        doc = leitor.processar_documento(file_path)

        if not doc:
            raise HTTPException(status_code=400, detail="Erro ao processar documento")

        # Persiste na base de conhecimento
        base = BaseConhecimento()
        base.salvar_documentos([doc])

        return {
            "id": doc.id,
            "filename": file.filename,
            "tipo": doc.tipo.value,
            "entidades_encontradas": len(doc.entidades),
            "resumo": (doc.resumo or "")[:200],
            "status": "sucesso",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {str(e)}")


@router.delete("/{documento_id}")
async def deletar_documento(documento_id: str):
    """
    Remove um documento da base de conhecimento.
    Nota: A implementação atual remove do arquivo JSON de documentos.
    """
    try:
        base = BaseConhecimento()
        documentos = base.carregar_documentos()
        documentos_filtrados = [d for d in documentos if d.id != documento_id]

        if len(documentos_filtrados) == len(documentos):
            raise HTTPException(status_code=404, detail="Documento não encontrado")

        # Salva a lista atualizada (sem o documento removido)
        base.salvar_documentos(documentos_filtrados)

        return {"status": "sucesso", "mensagem": f"Documento {documento_id} removido"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover documento: {str(e)}")


@router.delete("/")
async def limpar_documentos():
    """Remove todos os documentos da base de conhecimento."""
    try:
        # Sobrescreve com lista vazia
        base = BaseConhecimento()
        base.salvar_documentos([])

        # Limpa diretório de uploads temporários
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)

        return {"status": "sucesso", "mensagem": "Todos os documentos foram removidos"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar documentos: {str(e)}")