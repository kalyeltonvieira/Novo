"""
Testes Unitários de Validação da Infraestrutura Kubernetes e Helm
===================================================================
"""

import os
import yaml
import pytest


def test_validar_chart_yaml():
    filepath = os.path.join("k8s", "helm", "Chart.yaml")
    assert os.path.exists(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["name"] == "transparencia-ia"
        assert data["apiVersion"] == "v2"


def test_validar_values_yaml():
    filepath = os.path.join("k8s", "helm", "values.yaml")
    assert os.path.exists(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert data["service"]["port"] == 8000
        assert data["ingress"]["enabled"] is True
        assert data["autoscaling"]["maxReplicas"] == 10
