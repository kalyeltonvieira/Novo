"""
Exportação de Dados
===================
Funcionalidade para exportar dados em CSV e Excel.
"""

import csv
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

from core.entidades import (
    Documento, EntidadeExtraida, Pessoa, Empresa,
    Contrato, Relacionamento, Alerta
)

logger = logging.getLogger("ia_analisadora.data_export")


class DataExporter:
    """Exportador de dados para diferentes formatos."""
    
    def __init__(self, output_dir: str = "data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_entidades_csv(
        self,
        entidades: List[EntidadeExtraida],
        filename: Optional[str] = None
    ) -> str:
        """Exporta entidades para CSV."""
        if not filename:
            filename = f"entidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Tipo', 'Valor', 'Normalizado', 'Contexto',
                'Confiança', 'Posição Início', 'Posição Fim', 'Documento ID'
            ])
            
            for ent in entidades:
                writer.writerow([
                    ent.id,
                    ent.tipo.value,
                    ent.valor,
                    ent.normalizado,
                    ent.contexto[:200] if ent.contexto else '',
                    ent.confianca,
                    ent.posicao_inicio,
                    ent.posicao_fim,
                    ent.documento_id or ''
                ])
        
        logger.info(f"Entidades exportadas para {filepath}")
        return str(filepath)
    
    def export_pessoas_csv(
        self,
        pessoas: Dict[str, Pessoa],
        filename: Optional[str] = None
    ) -> str:
        """Exporta pessoas para CSV."""
        if not filename:
            filename = f"pessoas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Nome', 'Nome Normalizado', 'CPF',
                'Cargos', 'Órgãos Relacionados', 'Empresas Relacionadas',
                'Parentes', 'Contratos', 'Processos'
            ])
            
            for pid, pessoa in pessoas.items():
                writer.writerow([
                    pid,
                    pessoa.nome,
                    pessoa.nome_normalizado,
                    pessoa.cpf or '',
                    '; '.join(pessoa.cargos),
                    '; '.join(pessoa.orgaos_relacionados),
                    '; '.join(pessoa.empresas_relacionadas),
                    '; '.join(pessoa.parentes),
                    '; '.join(pessoa.contratos),
                    '; '.join(pessoa.processos)
                ])
        
        logger.info(f"Pessoas exportadas para {filepath}")
        return str(filepath)
    
    def export_empresas_csv(
        self,
        empresas: Dict[str, Empresa],
        filename: Optional[str] = None
    ) -> str:
        """Exporta empresas para CSV."""
        if not filename:
            filename = f"empresas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Nome', 'Nome Normalizado', 'CNPJ',
                'Data Abertura', 'Endereço', 'Capital Social',
                'Funcionários', 'Contratos', 'Licitações',
                'Órgãos Contratantes', 'Score Suspeita'
            ])
            
            for eid, empresa in empresas.items():
                writer.writerow([
                    eid,
                    empresa.nome,
                    empresa.nome_normalizado,
                    empresa.cnpj or '',
                    empresa.data_abertura.strftime('%Y-%m-%d') if empresa.data_abertura else '',
                    empresa.endereco or '',
                    empresa.capital_social or '',
                    empresa.funcionarios or '',
                    '; '.join(empresa.contratos),
                    '; '.join(empresa.licitacoes_participadas),
                    '; '.join(empresa.orgaos_contratantes),
                    empresa.score_suspeita
                ])
        
        logger.info(f"Empresas exportadas para {filepath}")
        return str(filepath)
    
    def export_alertas_csv(
        self,
        alertas: List[Alerta],
        filename: Optional[str] = None
    ) -> str:
        """Exporta alertas para CSV."""
        if not filename:
            filename = f"alertas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Tipo', 'Título', 'Descrição', 'Severidade',
                'Score Confiança', 'Entidades Envolvidas',
                'Documentos Relacionados', 'Valor Envolvido',
                'Status', 'Data Detecção'
            ])
            
            for alerta in alertas:
                writer.writerow([
                    alerta.id,
                    alerta.tipo.value,
                    alerta.titulo,
                    alerta.descricao[:500],
                    alerta.severidade,
                    alerta.score_confianca,
                    '; '.join(alerta.entidades_envolvidas),
                    '; '.join(alerta.documentos_relacionados),
                    alerta.valor_envolvido or '',
                    alerta.status,
                    alerta.data_deteccao.strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        logger.info(f"Alertas exportados para {filepath}")
        return str(filepath)
    
    def export_relacionamentos_csv(
        self,
        relacionamentos: List[Relacionamento],
        filename: Optional[str] = None
    ) -> str:
        """Exporta relacionamentos para CSV."""
        if not filename:
            filename = f"relacionamentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Tipo', 'Entidade Origem', 'Entidade Destino',
                'Tipo Origem', 'Tipo Destino', 'Força',
                'Valor', 'Data Início', 'Data Fim', 'Detalhes', 'Documento ID'
            ])
            
            for rel in relacionamentos:
                writer.writerow([
                    rel.id,
                    rel.tipo,
                    rel.entidade_origem,
                    rel.entidade_destino,
                    rel.tipo_origem,
                    rel.tipo_destino,
                    rel.forca,
                    rel.valor or '',
                    rel.data_inicio.strftime('%Y-%m-%d') if rel.data_inicio else '',
                    rel.data_fim.strftime('%Y-%m-%d') if rel.data_fim else '',
                    rel.detalhes[:200],
                    rel.documento_id or ''
                ])
        
        logger.info(f"Relacionamentos exportados para {filepath}")
        return str(filepath)
    
    def export_excel_dashboard(
        self,
        documentos: List[Documento],
        alertas: List[Alerta],
        relacionamentos: List[Relacionamento],
        pessoas: Dict[str, Pessoa],
        empresas: Dict[str, Empresa],
        filename: Optional[str] = None
    ) -> str:
        """Exporta dashboard completo para Excel com múltiplas abas."""
        if not filename:
            filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        filepath = self.output_dir / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Aba de Documentos
            if documentos:
                docs_data = []
                for doc in documentos:
                    docs_data.append({
                        'ID': doc.id,
                        'Fonte': doc.fonte,
                        'Tipo': doc.tipo.value,
                        'Data Processamento': doc.data_processamento.strftime('%Y-%m-%d %H:%M:%S'),
                        'Data Documento': doc.data_documento.strftime('%Y-%m-%d') if doc.data_documento else '',
                        'Órgão Origem': doc.orgao_origem or '',
                        'URL Origem': doc.url_origem or '',
                        'Entidades': len(doc.entidades),
                        'Resumo': doc.resumo[:200] if doc.resumo else ''
                    })
                pd.DataFrame(docs_data).to_excel(writer, sheet_name='Documentos', index=False)
            
            # Aba de Alertas
            if alertas:
                alertas_data = []
                for alerta in alertas:
                    alertas_data.append({
                        'ID': alerta.id,
                        'Tipo': alerta.tipo.value,
                        'Título': alerta.titulo,
                        'Descrição': alerta.descricao[:300],
                        'Severidade': alerta.severidade,
                        'Confiança': alerta.score_confianca,
                        'Valor': alerta.valor_envolvido or 0,
                        'Status': alerta.status,
                        'Data': alerta.data_deteccao.strftime('%Y-%m-%d')
                    })
                pd.DataFrame(alertas_data).to_excel(writer, sheet_name='Alertas', index=False)
            
            # Aba de Pessoas
            if pessoas:
                pessoas_data = []
                for pid, pessoa in pessoas.items():
                    pessoas_data.append({
                        'ID': pid,
                        'Nome': pessoa.nome,
                        'CPF': pessoa.cpf or '',
                        'Cargos': '; '.join(pessoa.cargos),
                        'Empresas': len(pessoa.empresas_relacionadas),
                        'Contratos': len(pessoa.contratos)
                    })
                pd.DataFrame(pessoas_data).to_excel(writer, sheet_name='Pessoas', index=False)
            
            # Aba de Empresas
            if empresas:
                empresas_data = []
                for eid, empresa in empresas.items():
                    empresas_data.append({
                        'ID': eid,
                        'Nome': empresa.nome,
                        'CNPJ': empresa.cnpj or '',
                        'Capital Social': empresa.capital_social or 0,
                        'Contratos': len(empresa.contratos),
                        'Score Suspeita': empresa.score_suspeita,
                        'Alertas': len(empresa.alertas)
                    })
                pd.DataFrame(empresas_data).to_excel(writer, sheet_name='Empresas', index=False)
            
            # Aba de Relacionamentos
            if relacionamentos:
                rel_data = []
                for rel in relacionamentos:
                    rel_data.append({
                        'ID': rel.id,
                        'Tipo': rel.tipo,
                        'Origem': rel.entidade_origem,
                        'Destino': rel.entidade_destino,
                        'Força': rel.forca,
                        'Valor': rel.valor or 0
                    })
                pd.DataFrame(rel_data).to_excel(writer, sheet_name='Relacionamentos', index=False)
        
        logger.info(f"Dashboard exportado para {filepath}")
        return str(filepath)
    
    def export_all_to_excel(
        self,
        documentos: List[Documento],
        alertas: List[Alerta],
        relacionamentos: List[Relacionamento],
        pessoas: Dict[str, Pessoa],
        empresas: Dict[str, Empresa],
        filename: Optional[str] = None
    ) -> str:
        """Exporta todos os dados para Excel (alias para export_excel_dashboard)."""
        return self.export_excel_dashboard(
            documentos, alertas, relacionamentos, pessoas, empresas, filename
        )


def export_to_csv(
    data_type: str,
    data: Any,
    output_dir: str = "data/exports",
    filename: Optional[str] = None
) -> str:
    """Função conveniente para exportar dados para CSV."""
    exporter = DataExporter(output_dir)
    
    if data_type == "entidades":
        return exporter.export_entidades_csv(data, filename)
    elif data_type == "pessoas":
        return exporter.export_pessoas_csv(data, filename)
    elif data_type == "empresas":
        return exporter.export_empresas_csv(data, filename)
    elif data_type == "alertas":
        return exporter.export_alertas_csv(data, filename)
    elif data_type == "relacionamentos":
        return exporter.export_relacionamentos_csv(data, filename)
    else:
        raise ValueError(f"Tipo de dados não suportado: {data_type}")


def export_to_excel(
    documentos: List[Documento],
    alertas: List[Alerta],
    relacionamentos: List[Relacionamento],
    pessoas: Dict[str, Pessoa],
    empresas: Dict[str, Empresa],
    output_dir: str = "data/exports",
    filename: Optional[str] = None
) -> str:
    """Função conveniente para exportar dashboard para Excel."""
    exporter = DataExporter(output_dir)
    return exporter.export_excel_dashboard(
        documentos, alertas, relacionamentos, pessoas, empresas, filename
    )
