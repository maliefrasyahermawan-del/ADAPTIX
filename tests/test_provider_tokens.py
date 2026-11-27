import json
import os

import pytest

from src.adaptix import provider_keys
from src.adaptix.web import app as webapp

GEMINI = 'AIzaSyA1234567890abcdefghijklmnopqrstu'
GROQ = 'gsk_abcdefghijklmnopqrstuvwxyz012345'


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(provider_keys, 'STORE_DIR', tmp_path)
    monkeypatch.setattr(provider_keys, 'STORE_PATH', tmp_path / 'provider_tokens.json')
    for name in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'DEEPSEEK_API_KEY', 'XAI_API_KEY',
                 'OPENROUTER_API_KEY', 'ADAPTIX_API_KEY', 'ADAPTIX_API_BASE'):
        monkeypatch.delenv(name, raising=False)
    yield tmp_path
    for name in ('GEMINI_API_KEY', 'GROQ_API_KEY'):
        os.environ.pop(name, None)


def test_saved_token_is_masked_and_exported(store):
    result = provider_keys.set_token('gemini', GEMINI)
    assert result['key_set'] is True
    assert GEMINI not in json.dumps(result)
    assert os.environ['GEMINI_API_KEY'] == GEMINI
    row = next(r for r in provider_keys.status_rows() if r['id'] == 'gemini')
    assert row['source'] == 'saved'
    assert row['masked'].startswith(GEMINI[:4])
    assert GEMINI not in json.dumps(provider_keys.status_rows())


def test_saved_token_beats_env(store, monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'gsk_env_only_1234567890')
    provider_keys.set_token('groq', GROQ)
    assert provider_keys.get_token('groq') == GROQ


def test_invalid_token_and_provider_rejected(store):
    with pytest.raises(ValueError):
        provider_keys.set_token('gemini', 'short')
    with pytest.raises(ValueError):
        provider_keys.set_token('nope', GROQ)
    with pytest.raises(ValueError):
        provider_keys.set_token('gemini', 'has space in it 123')


def test_delete_removes_saved_token(store):
    provider_keys.set_token('gemini', GEMINI)
    provider_keys.delete_token('gemini')
    assert provider_keys.get_token('gemini') == ''
    assert 'GEMINI_API_KEY' not in os.environ


def test_credentials_prefer_model_provider(store, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'gemini-env-key-1234567890')
    monkeypatch.setenv('ADAPTIX_API_KEY', 'deepseek-key-0987654321')
    monkeypatch.setenv('ADAPTIX_API_BASE', 'https://api.deepseek.com')
    key, base = provider_keys.credentials_for('gemini/gemini-2.5-flash')
    assert key == 'gemini-env-key-1234567890'
    assert base is None
    key, base = provider_keys.credentials_for('ollama_chat/qwen3:14b')
    assert key == 'deepseek-key-0987654321'
    assert base == 'https://api.deepseek.com'


def test_env_for_model_drops_foreign_api_base(store, monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'groq-env-key-1234567890')
    env = provider_keys.env_for_model(
        'groq/llama-3.3-70b-versatile',
        {'ADAPTIX_API_BASE': 'https://api.deepseek.com', 'ADAPTIX_API_KEY': 'deepseek'})
    assert env['ADAPTIX_API_KEY'] == 'groq-env-key-1234567890'
    assert 'ADAPTIX_API_BASE' not in env


def test_web_token_endpoints_never_return_value(store):
    monkeypatch_client = webapp.create_app().test_client()
    response = monkeypatch_client.post('/api/settings/tokens',
                                       json={'provider': 'gemini', 'token': GEMINI})
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert GEMINI not in text
    assert '"key_set":true' in text
    settings = monkeypatch_client.get('/api/settings').get_json()
    assert next(t for t in settings['tokens'] if t['id'] == 'gemini')['source'] == 'saved'
    deleted = monkeypatch_client.delete('/api/settings/tokens/gemini')
    assert deleted.status_code == 200
    assert all(t['id'] != 'gemini' or t['key_set'] is False
               for t in deleted.get_json()['tokens'])


# OpenRouter keys are sk-or-v1- + base64-ish; the regex must accept them.
OR_KEY = 'sk-or-v1-abcdefghijklmnopqrstuvwxyz0123456789abcdef'


def test_openrouter_key_saved_and_belongs_to_audit(store, monkeypatch):
    result = provider_keys.set_token(
        'openrouter', OR_KEY, 'openrouter/anthropic/claude-3.5-sonnet')
    assert result['key_set'] is True
    assert OR_KEY not in json.dumps(result)
    assert os.environ['OPENROUTER_API_KEY'] == OR_KEY
    row = next(r for r in provider_keys.status_rows() if r['id'] == 'openrouter')
    assert row['source'] == 'saved'
    assert row['model'] == 'openrouter/anthropic/claude-3.5-sonnet'


def test_litellm_mapping_for_openrouter(store):
    assert (provider_keys.litellm_model_for('openrouter/deepseek/deepseek-chat')
            == 'openai/deepseek/deepseek-chat')
    assert (provider_keys.litellm_model_for('openrouter/google/gemini-2.5-flash')
            == 'openai/google/gemini-2.5-flash')
    assert provider_keys.litellm_model_for('gemini/gemini-2.5-flash') == 'gemini/gemini-2.5-flash'
    assert provider_keys.litellm_model_for('ollama_chat/qwen3:14b') == 'ollama_chat/qwen3:14b'
    # after mapping the litellm id carries the openai family; the UI id keeps openrouter/
    assert provider_keys.litellm_prefix_for('openrouter/openai/gpt-4o-mini') == 'openai'


def test_openrouter_credentials_use_or_base_and_key(store, monkeypatch):
    provider_keys.set_token('openrouter', OR_KEY, 'openrouter/deepseek/deepseek-chat')
    key, base = provider_keys.credentials_for('openrouter/deepseek/deepseek-chat')
    assert key == OR_KEY
    assert base == 'https://openrouter.ai/api/v1'


def test_audit_models_include_openrouter_without_key_saved(store):
    # The catalog must be selectable before any key exists; the endpoint
    # previously only listed providers whose key was already saved.
    client = webapp.create_app().test_client()
    data = client.get('/api/audit/models').get_json()
    assert 'openrouter/deepseek/deepseek-chat' in data['models']
    assert 'openrouter/anthropic/claude-3.5-sonnet' in data['models']
    assert 'openrouter/google/gemini-2.5-flash' in data['models']


def test_openrouter_models_endpoint_uses_public_catalog(store, monkeypatch):
    """live_models(openrouter) must return provider ids even with no key (public listing)."""
    import httpx as _httpx

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {'data': [
                {'id': 'deepseek/deepseek-chat'},
                {'id': 'anthropic/claude-3.5-sonnet'},
                {'bad-key': 'x'},
            ]}

    def _fake_get(url, headers=None, timeout=15.0):
        assert url == 'https://openrouter.ai/api/v1/models'
        return _Resp()

    monkeypatch.setattr(_httpx, 'get', _fake_get)
    data = provider_keys.live_models('openrouter')
    assert data['source'] == 'live'
    assert 'openrouter/deepseek/deepseek-chat' in data['models']
    assert 'openrouter/anthropic/claude-3.5-sonnet' in data['models']


def test_code_audit_engine_maps_openrouter_id(store, monkeypatch):
    from src.adaptix.code_audit import engine as audit_engine

    seen = {}

    def fake_call(model=None, messages=None, max_tokens=None, temperature=None, timeout=None):
        seen['model'] = model
        return {'choices': [{'message': {'content': '["list_source"]'}}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}

    provider_keys.set_token('openrouter', OR_KEY, 'openrouter/deepseek/deepseek-chat')
    audit_engine._provider_call(
        [{'role': 'user', 'content': 'hi'}],
        model='openrouter/deepseek/deepseek-chat', api_base=None, api_key=None,
        max_tokens=64, timeout=5, call=fake_call)
    assert seen['model'] == 'openai/deepseek/deepseek-chat'
    # credentials resolve to the OpenRouter key without the caller passing them
    key, base = provider_keys.credentials_for('openrouter/deepseek/deepseek-chat')
    assert key == OR_KEY


def test_model_choice_saved_and_preferred(store):
    provider_keys.set_token('deepseek', 'sk-deepseek-key-1234567890', 'deepseek/deepseek-v4-pro')
    row = next(r for r in provider_keys.status_rows() if r['id'] == 'deepseek')
    assert row['model'] == 'deepseek/deepseek-v4-pro'
    assert row['model_saved'] is True
    assert 'deepseek/deepseek-flash' in row['models']
    assert provider_keys.preferred_model('deepseek') == 'deepseek/deepseek-v4-pro'
    # Changing only the model keeps the stored key.
    provider_keys.set_token('deepseek', '', 'deepseek-flash')
    row = next(r for r in provider_keys.status_rows() if r['id'] == 'deepseek')
    assert row['model'] == 'deepseek/deepseek-flash'
    assert provider_keys.get_token('deepseek') == 'sk-deepseek-key-1234567890'


def test_custom_model_gets_provider_prefix(store):
    provider_keys.set_token('xai', 'xai-key-1234567890abcdef', 'grok-3-mini')
    assert provider_keys.preferred_model('xai') == 'xai/grok-3-mini'


def test_invalid_model_rejected(store):
    with pytest.raises(ValueError):
        provider_keys.set_token('deepseek', 'sk-deepseek-key-1234567890', 'bad model!')
    with pytest.raises(ValueError):
        provider_keys.set_token('groq', '', 'groq/llama-3.3-70b-versatile')


def test_delete_keeps_chosen_model(store):
    provider_keys.set_token('deepseek', 'sk-deepseek-key-1234567890', 'deepseek/deepseek-reasoner')
    provider_keys.delete_token('deepseek')
    assert provider_keys.preferred_model('deepseek') == 'deepseek/deepseek-reasoner'
    assert provider_keys.get_token('deepseek') == ''


def test_model_list_endpoint_falls_back_without_key(store):
    client = webapp.create_app().test_client()
    response = client.get('/api/settings/tokens/deepseek/models')
    assert response.status_code == 200
    data = response.get_json()
    assert data['source'] == 'catalog'
    assert 'deepseek/deepseek-flash' in data['models']


def test_web_saves_model_choice(store):
    client = webapp.create_app().test_client()
    response = client.post('/api/settings/tokens', json={
        'provider': 'deepseek', 'token': 'sk-deepseek-key-1234567890',
        'model': 'deepseek/deepseek-v4-pro'})
    assert response.status_code == 200
    row = next(t for t in response.get_json()['tokens'] if t['id'] == 'deepseek')
    assert row['model'] == 'deepseek/deepseek-v4-pro'
    data = client.get('/api/audit/models').get_json()
    assert 'deepseek/deepseek-v4-pro' in data['models']
    assert 'deepseek/deepseek-flash' in data['models']
    assert data['default'] == 'deepseek/deepseek-v4-pro'


def test_web_rejects_unknown_provider(store):
    client = webapp.create_app().test_client()
    response = client.post('/api/settings/tokens',
                           json={'provider': 'not-a-provider', 'token': GEMINI})
    assert response.status_code == 400
