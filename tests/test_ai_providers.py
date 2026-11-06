import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai_providers import AIManager, AIProvider, AIProviderClient

class TestAIProviders:
    @patch.dict(os.environ, {"NVIDIA_API_KEY": "fake_key"})
    def test_aimanager_initialization(self):
        manager = AIManager()
        assert manager.default_provider == AIProvider.NVIDIA
        assert manager.get_client().provider == AIProvider.NVIDIA

    @patch.dict(os.environ, {"NVIDIA_API_KEY": "fake_nvidia_key"})
    @patch("utils.ai_providers.AIProviderClient._initialize_client")
    def test_openai_client_chat(self, mock_init):
        manager = AIManager()
        manager.set_provider(AIProvider.NVIDIA)
        client = manager.get_client()
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Resposta simulada"
        mock_response.choices[0].message.reasoning = None
        mock_client.chat.completions.create.return_value = mock_response
        
        client.client = mock_client
        
        response = client.chat_completion([{"role": "user", "content": "Olá"}])
        assert response is not None
        assert response["content"] == "Resposta simulada"
        mock_client.chat.completions.create.assert_called_once()

    @patch.dict(os.environ, {"HF_TOKEN": "fake_hf_key"})
    @patch("utils.ai_providers.AIProviderClient._initialize_client")
    def test_anthropic_client_chat(self, mock_init):
        # Renomeado internamente para testar HF no lugar de Anthropic
        manager = AIManager()
        manager.set_provider(AIProvider.HUGGINGFACE)
        client = manager.get_client()
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Resposta do HF"
        mock_client.chat.completions.create.return_value = mock_response
        
        client.client = mock_client
        
        response = client.chat_completion([{"role": "user", "content": "Olá HF"}])
        assert response is not None
        assert response["content"] == "Resposta do HF"
        mock_client.chat.completions.create.assert_called_once()
