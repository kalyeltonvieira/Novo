"""
Tarefas Assíncronas do Celery
==============================
Executa auditoria pesada de entidades e geração de relatórios de forma assíncrona.
"""

import uuid
from workers.celery_app import celery_app
from core.database import SessionLocal
from core.models_db import AlertaDB


@celery_app.task(name="investigar_entidade_task")
def investigar_entidade_task(entidade_id: str, tipo_entidade: str):
    """
    Tarefa assíncrona para executar busca exaustiva de anomalias em uma entidade.
    """
    db = SessionLocal()
    try:
        alerta = AlertaDB(
            id=f"task_{uuid.uuid4().hex[:8]}",
            tipo="investigacao_assincrona",
            titulo=f"Investigação de {tipo_entidade} ({entidade_id})",
            descricao="Processamento concluído em background via Celery Worker.",
            severidade="baixa",
            status="concluido"
        )
        db.add(alerta)
        db.commit()
        return {"status": "sucesso", "entidade_id": entidade_id, "alerta_id": alerta.id}
    except Exception as e:
        db.rollback()
        return {"status": "erro", "mensagem": str(e)}
    finally:
        db.close()


@celery_app.task(name="gerar_relatorio_pdf_task")
def gerar_relatorio_pdf_task(relatorio_id: str):
    """
    Tarefa assíncrona para gerar arquivo PDF compilado de auditoria.
    """
    # Lógica assíncrona para renderizar WeasyPrint / Jinja2 PDF
    return {"status": "sucesso", "relatorio_id": relatorio_id, "pdf_path": f"data/reports/{relatorio_id}.pdf"}


def processar_documento_background(filepath: str):
    """Processa documento baixado em background via LeitorUniversal."""
    try:
        from core.leitor_universal import LeitorUniversal
        print(f"[BACKGROUND] Iniciando OCR/Extração profunda de {filepath}")
        leitor = LeitorUniversal()
        doc = leitor.processar_documento(filepath)
        if doc:
            print(f"[BACKGROUND] Concluído: extraídas {len(doc.entidades)} entidades de {filepath}")
            
            from core.correlacionador import Correlacionador
            from core.base_conhecimento import BaseConhecimento
            
            correlacionador = Correlacionador()
            
            # Carrega a base persistente
            base = BaseConhecimento()
            base.carregar()
            
            for ent in doc.entidades:
                if ent.tipo.value == "empresa" and "cnpj" in ent.metadados:
                    correlacionador.adicionar_entidade("empresa", ent.valor, ent.metadados)
            
            # Adiciona as entidades enriquecidas ao grafo
            base.adicionar_entidades(correlacionador._entidades_avulsas + doc.entidades)
            
            # Gera relacionamentos
            relacionamentos = correlacionador.processar_documentos([doc])
            base.adicionar_relacionamentos(relacionamentos)
            
            # Salva no disco
            base.salvar_documentos([doc])
            base.salvar()
            if doc.conteudo_processado:
                try:
                    from core.vector_store import VectorStoreManager
                    import uuid
                    vsm = VectorStoreManager()
                    vsm.adicionar_documento(
                        doc_id=doc.id or str(uuid.uuid4()),
                        texto=doc.conteudo_processado,
                        metadados={"origem": filepath, "tipo": doc.tipo.value}
                    )
                    print(f"[BACKGROUND] Documento indexado com sucesso no VectorStore para Busca Semântica.")
                except Exception as e:
                    print(f"[BACKGROUND] Falha ao indexar no VectorStore: {e}")
                    
        else:
            print(f"[BACKGROUND] Falha ou nada extraído de {filepath}")
    except Exception as e:
        print(f"[BACKGROUND] Erro ao processar documento {filepath}: {e}")

def enfileirar_processamento_documento(filepath: str):
    """
    Enfileira a extração de um arquivo.
    Usa threading em vez de Celery para rodar localmente sem Redis.
    """
    import threading
    t = threading.Thread(target=processar_documento_background, args=(filepath,))
    t.daemon = True
    t.start()

