from typing import Dict, Any, List
import os
import requests
import uuid
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import BaseAgente
from core.leitor_universal import LeitorUniversal
from core.vector_store import VectorStoreManager

class CacadorAnexosAgente(BaseAgente):
    """
    Agente que procura ativamente por links para PDFs (.pdf), editais e termos de referência,
    faz o download em background e injeta o conteúdo no LeitorUniversal e VectorStore.
    """
    def __init__(self, navegador):
        super().__init__(
            nome="CacadorAnexos",
            descricao="Busca e baixa anexos (PDFs de Editais) das licitações para realizar OCR e análise profunda de cláusulas."
        )
        self.navegador = navegador
        self.leitor = LeitorUniversal()
        self.vector_store = VectorStoreManager()
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dados_temp", "anexos")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Palavras suspeitas para alertar imediatamente na OCR
        self.palavras_restritivas = ["exclusividade", "marca de referência", "direcionamento", "somente a marca", "atestado de capacidade técnica restrito"]

    def processar(self, tarefa: str) -> str:
        """
        Tarefa contém URL atual.
        """
        html = ""
        url_atual = ""
        if hasattr(self.navegador, 'obter_html'):
            html = self.navegador.obter_html()
            url_atual = getattr(self.navegador, 'url_atual', 'http://localhost')
            
        if not html:
            return "Nenhum HTML encontrado para buscar anexos."
            
        soup = BeautifulSoup(html, "html.parser")
        links_pdf = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Heurística: link termina em pdf, download, baixar, anexo
            if href.lower().endswith('.pdf') or 'download' in href.lower() or 'anexo' in href.lower() or 'edital' in href.lower():
                full_url = urljoin(url_atual, href)
                texto_link = a.get_text(strip=True) or "Anexo sem nome"
                links_pdf.append((texto_link, full_url))
                
        if not links_pdf:
            return "Não encontrei nenhum link provável de edital ou anexo em PDF na página atual."
            
        print(f"[CacadorAnexos] Encontrados {len(links_pdf)} links para anexos. Baixando os 2 primeiros (para otimização)...")
        
        resultados = []
        for nome_anexo, link in links_pdf[:2]:
            try:
                print(f"  [Baixando] {nome_anexo} -> {link}")
                resp = requests.get(link, timeout=15, verify=False, stream=True)
                if resp.status_code == 200:
                    ext = ".pdf" if "pdf" in resp.headers.get("Content-Type", "").lower() else ".doc"
                    caminho_arquivo = os.path.join(self.temp_dir, f"anexo_{uuid.uuid4().hex[:8]}{ext}")
                    
                    with open(caminho_arquivo, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                            
                    # Faz OCR/Leitura
                    texto_extraido = self.leitor.extrair_texto(caminho_arquivo)
                    
                    # Salva no VectorStore
                    self.vector_store.adicionar_documento(
                        texto=texto_extraido,
                        metadados={"origem": link, "nome": nome_anexo}
                    )
                    
                    # Verifica restrições
                    alertas_ocr = []
                    for palavra in self.palavras_restritivas:
                        if palavra in texto_extraido.lower():
                            alertas_ocr.append(palavra)
                            
                    res_anexo = f"- **{nome_anexo}** lido com sucesso ({len(texto_extraido)} caracteres)."
                    if alertas_ocr:
                        res_anexo += f" 🚨 **ALERTA:** Foram encontradas cláusulas potencialmente restritivas: {', '.join(alertas_ocr)}."
                    resultados.append(res_anexo)
                else:
                    resultados.append(f"- Falha ao baixar **{nome_anexo}** (Status {resp.status_code})")
            except Exception as e:
                resultados.append(f"- Erro no anexo **{nome_anexo}**: {str(e)}")
                
        res = "Resumo do Caçador de Anexos:\n" + "\n".join(resultados)
        return res
