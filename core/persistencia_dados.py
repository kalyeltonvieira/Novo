"""
Persistência de Dados Crawleados
=================================
Salva e recupera dados extraídos de portais de transparência.
Permite que dados não sejam perdidos ao reiniciar o sistema.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("ia_analisadora.persistencia")


class PersistenciaDados:
    """
    Sistema de persistência para dados crawleados de portais.
    Salva em JSON estruturado por data e portal.
    """

    def __init__(self, base_dir: str = "data/crawled"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def salvar_crawl(
        self,
        url_portal: str,
        dados: Dict[str, Any],
        portal_nome: str = None
    ) -> str:
        """
        Salva os dados de um crawl no disco.

        Args:
            url_portal: URL do portal crawleado
            dados: Dados extraídos (estrutura do CrawlerAgente)
            portal_nome: Nome identificador do portal

        Returns:
            Caminho do arquivo salvo
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Nome do portal a partir da URL
        if not portal_nome:
            from urllib.parse import urlparse
            parsed = urlparse(url_portal)
            portal_nome = parsed.netloc.replace(".", "_")

        # Estrutura do arquivo
        registro = {
            "id": f"crawl_{timestamp}_{portal_nome}",
            "timestamp": datetime.now().isoformat(),
            "url_portal": url_portal,
            "portal_nome": portal_nome,
            "total_registros": dados.get("total_registros", 0),
            "secoes": dados.get("secoes", {}),
            "pdfs_encontrados": dados.get("pdfs_encontrados", []),
            "erros": dados.get("erros", []),
        }

        # Salva em arquivo JSON
        nome_arquivo = f"{timestamp}_{portal_nome}.json"
        caminho = self.base_dir / nome_arquivo

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Dados de crawl salvos: {caminho}")
        return str(caminho)

    def carregar_crawl(self, crawl_id: str) -> Optional[Dict[str, Any]]:
        """Carrega um crawl específico por ID."""
        for arquivo in self.base_dir.glob("*.json"):
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    if dados.get("id") == crawl_id:
                        return dados
            except Exception:
                continue
        return None

    def listar_crawls(self, limite: int = 50) -> List[Dict[str, Any]]:
        """Lista todos os crawls salvos (mais recentes primeiro)."""
        crawls = []
        for arquivo in sorted(self.base_dir.glob("*.json"), reverse=True):
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    crawls.append({
                        "id": dados.get("id"),
                        "timestamp": dados.get("timestamp"),
                        "url_portal": dados.get("url_portal"),
                        "portal_nome": dados.get("portal_nome"),
                        "total_registros": dados.get("total_registros", 0),
                        "total_pdfs": len(dados.get("pdfs_encontrados", [])),
                        "total_secoes": len(dados.get("secoes", {})),
                        "arquivo": str(arquivo),
                    })
                    if len(crawls) >= limite:
                        break
            except Exception as e:
                logger.warning(f"Erro ao ler {arquivo}: {e}")

        return crawls

    def buscar_crawls_por_portal(self, portal_nome: str) -> List[Dict[str, Any]]:
        """Busca crawls de um portal específico."""
        todos = self.listar_crawls(limite=1000)
        return [c for c in todos if portal_nome.lower() in c.get("portal_nome", "").lower()]

    def salvar_empresas_enriquecidas(
        self,
        empresas: Dict[str, Dict[str, Any]],
        portal_nome: str = None
    ) -> str:
        """
        Salva dados de empresas enriquecidas (Receita Federal + CEIS + CNEP).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"empresas_{timestamp}_{portal_nome or 'geral'}.json"
        caminho = self.base_dir / nome_arquivo

        registro = {
            "id": f"empresas_{timestamp}",
            "timestamp": datetime.now().isoformat(),
            "portal_origem": portal_nome,
            "total_empresas": len(empresas),
            "empresas": empresas,
        }

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Dados de empresas salvos: {caminho}")
        return str(caminho)

    def carregar_empresas_enriquecidas(self, arquivo_id: str = None) -> Optional[Dict[str, Any]]:
        """Carrega dados de empresas enriquecidas."""
        if arquivo_id:
            for arquivo in self.base_dir.glob("empresas_*.json"):
                try:
                    with open(arquivo, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                        if dados.get("id") == arquivo_id:
                            return dados
                except Exception:
                    continue
        else:
            # Carrega o mais recente
            arquivos = sorted(self.base_dir.glob("empresas_*.json"), reverse=True)
            if arquivos:
                with open(arquivos[0], "r", encoding="utf-8") as f:
                    return json.load(f)

        return None

    def salvar_investigacao_completa(
        self,
        url_portal: str,
        dados_crawl: Dict[str, Any],
        dados_empresas: Dict[str, Any],
        alertas: List[Dict[str, Any]],
        laudo: str = None
    ) -> str:
        """
        Salva uma investigação completa (crawl + empresas + alertas + laudo).
        Cria um pacote único para auditoria.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from urllib.parse import urlparse
        portal_nome = urlparse(url_portal).netloc.replace(".", "_")

        investigacao = {
            "id": f"investigacao_{timestamp}_{portal_nome}",
            "timestamp": datetime.now().isoformat(),
            "url_portal": url_portal,
            "portal_nome": portal_nome,
            "dados_crawl": dados_crawl,
            "dados_empresas": dados_empresas,
            "alertas": alertas,
            "laudo": laudo,
            "status": "concluida",
        }

        nome_arquivo = f"investigacao_{timestamp}_{portal_nome}.json"
        caminho = self.base_dir / nome_arquivo

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(investigacao, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Investigação completa salva: {caminho}")
        return str(caminho)

    def listar_investigacoes(self, limite: int = 20) -> List[Dict[str, Any]]:
        """Lista investigações completas salvas."""
        investigacoes = []
        for arquivo in sorted(self.base_dir.glob("investigacao_*.json"), reverse=True):
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    investigacoes.append({
                        "id": dados.get("id"),
                        "timestamp": dados.get("timestamp"),
                        "url_portal": dados.get("url_portal"),
                        "portal_nome": dados.get("portal_nome"),
                        "total_alertas": len(dados.get("alertas", [])),
                        "tem_laudo": bool(dados.get("laudo")),
                        "status": dados.get("status"),
                    })
                    if len(investigacoes) >= limite:
                        break
            except Exception:
                continue

        return investigacoes

    def carregar_investigacao(self, investigacao_id: str) -> Optional[Dict[str, Any]]:
        """Carrega uma investigação completa por ID."""
        for arquivo in self.base_dir.glob("investigacao_*.json"):
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    if dados.get("id") == investigacao_id:
                        return dados
            except Exception:
                continue
        return None

    def limpar_dados_antigos(self, dias: int = 30):
        """Remove dados mais antigos que o número de dias especificado."""
        from datetime import timedelta
        limite = datetime.now() - timedelta(days=dias)
        removidos = 0

        for arquivo in self.base_dir.glob("*.json"):
            try:
                stats = arquivo.stat()
                data_mod = datetime.fromtimestamp(stats.st_mtime)
                if data_mod < limite:
                    arquivo.unlink()
                    removidos += 1
            except Exception:
                continue

        if removidos > 0:
            logger.info(f"Removidos {removidos} arquivos antigos (>{dias} dias)")

        return removidos

    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas dos dados persistidos."""
        total_crawls = len(list(self.base_dir.glob("crawl_*.json"))) + len(list(self.base_dir.glob("2*.json")))
        total_empresas = len(list(self.base_dir.glob("empresas_*.json")))
        total_investigacoes = len(list(self.base_dir.glob("investigacao_*.json")))

        tamanho_total = sum(f.stat().st_size for f in self.base_dir.glob("*.json"))

        return {
            "total_crawls": total_crawls,
            "total_dados_empresas": total_empresas,
            "total_investigacoes": total_investigacoes,
            "tamanho_total_mb": tamanho_total / (1024 * 1024),
            "diretorio": str(self.base_dir),
        }