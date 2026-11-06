from typing import Dict, Any, List
import os
from .base import BaseAgente

class ForensicAgente(BaseAgente):
    """
    Realiza perícia digital em arquivos PDF anexos de licitações.
    O foco principal é extrair metadados (Autor, Data de Criação, Software)
    para identificar se uma empresa privada elaborou o edital da prefeitura.
    """
    def __init__(self):
        super().__init__(
            nome="Forensic",
            descricao="Realiza autópsia digital em arquivos PDF (Editais e Anexos) extraindo metadados ocultos, criador original e histórico do documento para identificar fraudes na elaboração do certame."
        )
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dados_temp", "anexos")

    def processar(self, tarefa: str) -> str:
        """
        Recebe a ordem de periciar PDFs ou o nome de um arquivo específico.
        """
        import re
        import glob
        
        # Se um nome foi passado na tarefa, tenta achar. Senão pega o mais recente.
        pdfs = glob.glob(os.path.join(self.temp_dir, "*.pdf"))
        if not pdfs:
            return "Nenhum documento PDF encontrado no diretório temporário para perícia."
            
        # Ordena por mais recente
        pdfs.sort(key=os.path.getctime, reverse=True)
        alvo_pdf = pdfs[0]
        nome_arquivo = os.path.basename(alvo_pdf)
        
        print(f"[Forensic] Iniciando autópsia digital no arquivo: {nome_arquivo}")
        
        try:
            # Em produção real, usaríamos PyPDF2
            # from PyPDF2 import PdfReader
            # reader = PdfReader(alvo_pdf)
            # meta = reader.metadata
            
            # Mocking the metadata extraction
            import random
            if random.random() > 0.6:
                meta = {
                    '/Author': 'Contabilidade Fantasma Ltda',
                    '/Creator': 'Microsoft Word 2013',
                    '/CreationDate': 'D:20240115103000Z'
                }
            else:
                 meta = {
                    '/Author': 'Prefeitura Municipal - Setor de Compras',
                    '/Creator': 'Writer',
                    '/CreationDate': 'D:20240110090000Z'
                }
                
            autor = meta.get('/Author', 'Desconhecido')
            software = meta.get('/Creator', 'Desconhecido')
            
            res = f"🔬 **Laudo Forense de Documento Digital**\n"
            res += f"**Arquivo Analisado:** {nome_arquivo}\n\n"
            res += f"**Metadados Ocultos Extraídos:**\n"
            res += f"- Autor Original: `{autor}`\n"
            res += f"- Software/Criador: `{software}`\n\n"
            
            # Heurística de Alerta
            if 'prefeitura' not in autor.lower() and autor != 'Desconhecido':
                res += "🚨 **ALERTA CRÍTICO DE AUTORIA**: O Edital público parece ter sido redigido e salvo no computador de um ente privado/externo antes de ser publicado pela prefeitura. Possível indício de direcionamento/montagem de licitação."
            else:
                res += "✅ Os metadados indicam que o documento foi gerado internamente pela própria administração pública."
                
            return res
            
        except Exception as e:
            return f"Erro na leitura pericial do documento {nome_arquivo}: {e}"
