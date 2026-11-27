"""Provider API tokens entered through the local web UI.

The keys are stored in ``work/web_data/provider_tokens.json`` (mode 0600) and
never returned to the browser: the API only reports whether a key is set, plus
a masked hint. Each provider maps to the environment variable LiteLLM reads
(``GEMINI_API_KEY``, ``GROQ_API_KEY``, ``DEEPSEEK_API_KEY``, ``XAI_API_KEY``,
``OPENROUTER_API_KEY``) so a saved token makes the matching ``<prefix>/`` model
work without editing ``.env`` or restarting the server.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from src.adaptix.config import ROOT

STORE_DIR = Path(ROOT) / 'work' / 'web_data'
STORE_PATH = STORE_DIR / 'provider_tokens.json'

# env: variable LiteLLM reads. base: optional API base for the provider.
PROVIDERS = {
    'gemini': {
        'label': 'Google Gemini',
        'env': 'GEMINI_API_KEY',
        'prefix': 'gemini/',
        'model': 'gemini/gemini-2.5-flash',
        'models': [
            'gemini/gemini-2.5-flash',
            'gemini/gemini-2.5-pro',
            'gemini/gemini-2.0-flash',
            'gemini/gemini-3.8-flash',
            'gemini/gemini-3.1-pro-preview',
            'gemini/gemini-3-flash-preview',
        ],
        'docs': 'https://aistudio.google.com/apikey',
        'test': 'https://generativelanguage.googleapis.com/v1beta/models',
    },
    'groq': {
        'label': 'Groq',
        'env': 'GROQ_API_KEY',
        'prefix': 'groq/',
        'model': 'groq/llama-3.3-70b-versatile',
        'models': [
            'groq/llama-3.3-70b-versatile',
            'groq/llama-3.1-8b-instant',
            'groq/meta-llama/llama-4-maverick-17b-128e-instruct',
            'groq/meta-llama/llama-4-scout-17b-16e-instruct',
            'groq/moonshotai/kimi-k2-instruct-0905',
            'groq/openai/gpt-oss-120b',
            'groq/openai/gpt-oss-20b',
            'groq/qwen/qwen3-32b',
        ],
        'docs': 'https://console.groq.com/keys',
        'test': 'https://api.groq.com/openai/v1/models',
    },
    'deepseek': {
        'label': 'DeepSeek',
        'env': 'DEEPSEEK_API_KEY',
        'prefix': 'deepseek/',
        'model': 'deepseek/deepseek-chat',
        'models': [
            'deepseek/deepseek-chat',
            'deepseek/deepseek-reasoner',
            'deepseek/deepseek-flash',
            'deepseek/deepseek-v4-pro',
            'deepseek/deepseek-coder',
        ],
        'docs': 'https://platform.deepseek.com/api_keys',
        'test': 'https://api.deepseek.com/models',
    },
    'xai': {
        'label': 'Grok (xAI)',
        'env': 'XAI_API_KEY',
        'prefix': 'xai/',
        'model': 'xai/grok-4.5',
        'models': [
            'xai/grok-4.5',
            'xai/grok-4',
            'xai/grok-3',
            'xai/grok-3-mini',
        ],
        'docs': 'https://console.x.ai/',
        'test': 'https://api.x.ai/v1/models',
    },
    'openrouter': {
        'label': 'OpenRouter',
        'env': 'OPENROUTER_API_KEY',
        'prefix': 'openrouter/',
        'model': 'openrouter/google/gemini-2.5-flash',
        'models': [
            'openrouter/google/gemini-2.5-flash',
            'openrouter/google/gemini-2.5-pro',
            'openrouter/anthropic/claude-3.5-sonnet',
            'openrouter/openai/gpt-4o-mini',
            'openrouter/deepseek/deepseek-chat',
            'openrouter/meta-llama/llama-3.3-70b-instruct',
        ],
        'docs': 'https://openrouter.ai/keys',
        'test': 'https://openrouter.ai/api/v1/key',
    },
}

_TOKEN = re.compile(r'^[A-Za-z0-9._\-]{8,400}$')
_MODEL = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{1,160}$')
# OpenRouter's model listing is public, so it can be fetched before a key exists.
_PUBLIC_MODELS = {'openrouter': 'https://openrouter.ai/api/v1/models'}


def valid_provider(name) -> bool:
    return str(name or '').strip().lower() in PROVIDERS


def _provider(name):
    key = str(name or '').strip().lower()
    if key not in PROVIDERS:
        raise ValueError('provider tidak dikenal')
    return key


def _load() -> dict:
    try:
        data = json.loads(STORE_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    tokens = data.get('providers') if isinstance(data, dict) else None
    return tokens if isinstance(tokens, dict) else {}


def _save(tokens: dict) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {'providers': tokens, 'updated': time.time()}
    tmp = STORE_PATH.with_suffix('.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    os.replace(tmp, STORE_PATH)


def mask(token: str) -> str:
    token = str(token or '')
    if len(token) <= 8:
        return '••••'
    return token[:4] + '…' + token[-4:]


def get_token(provider: str) -> str:
    """Saved token, else the provider env var, else '' (never the ADAPTIX key)."""
    key = _provider(provider)
    saved = (_load().get(key) or {}).get('token')
    if isinstance(saved, str) and saved:
        return saved
    return str(os.getenv(PROVIDERS[key]['env']) or '')


def _clean_model(provider: str, model) -> str:
    """Normalise a LiteLLM model id, adding the provider prefix when omitted."""
    key = _provider(provider)
    spec = PROVIDERS[key]
    value = str(model or '').strip()
    if not _MODEL.match(value):
        raise ValueError('model tidak valid (2-160 karakter, contoh deepseek/deepseek-flash)')
    if not value.startswith(spec['prefix']):
        value = spec['prefix'] + value
    return value


def preferred_model(provider: str) -> str:
    key = _provider(provider)
    saved = _load()
    stored = saved.get(key) if isinstance(saved.get(key), dict) else {}
    return str((stored or {}).get('model') or PROVIDERS[key]['model'])


def status_rows() -> list[dict]:
    saved = _load()
    rows = []
    for key, spec in PROVIDERS.items():
        stored = saved.get(key) if isinstance(saved.get(key), dict) else None
        stored = stored or {}
        saved_token = str(stored.get('token') or '')
        env_token = str(os.getenv(spec['env']) or '')
        token = saved_token or env_token
        source = 'saved' if saved_token else ('env' if env_token else 'unset')
        model = str(stored.get('model') or spec['model'])
        models = list(spec['models'])
        if model not in models:
            models.insert(0, model)
        rows.append({
            'id': key,
            'label': spec['label'],
            'env': spec['env'],
            'prefix': spec['prefix'],
            'model': model,
            'default_model': spec['model'],
            'models': models,
            'catalog': list(spec['models']),
            'model_saved': bool(stored.get('model')),
            'docs': spec['docs'],
            'key_set': bool(token),
            'masked': mask(token) if token else '',
            'source': source,
            'saved_at': stored.get('saved_at'),
        })
    return rows


def set_token(provider: str, token=None, model=None) -> dict:
    """Save/replace a key and/or the provider's preferred model.

    An empty ``token`` keeps the existing key, which is how the UI changes only
    the model after a key was saved once.
    """
    key = _provider(provider)
    value = str(token or '').strip()
    tokens = _load()
    current = tokens.get(key) if isinstance(tokens.get(key), dict) else {}
    chosen = _clean_model(key, model) if str(model or '').strip() else None
    if value:
        if not _TOKEN.match(value):
            raise ValueError('token tidak valid (8-400 karakter, tanpa spasi)')
    elif not current.get('token'):
        raise ValueError('token belum diset')
    if not value and not chosen:
        raise ValueError('tidak ada perubahan untuk disimpan')
    target = dict(current)
    if value:
        target['token'] = value
        target['saved_at'] = time.time()
    if chosen:
        target['model'] = chosen
    tokens[key] = target
    _save(tokens)
    if value:
        os.environ[PROVIDERS[key]['env']] = value
    token_row = next(row for row in status_rows() if row['id'] == key)
    return {'provider': key, 'masked': token_row['masked'], 'key_set': token_row['key_set'],
            'source': token_row['source'], 'model': token_row['model'],
            'models': token_row['models']}


def delete_token(provider: str) -> dict:
    """Forget the saved key but keep the chosen model for later reuse."""
    key = _provider(provider)
    tokens = _load()
    entry = tokens.get(key) if isinstance(tokens.get(key), dict) else {}
    saved = entry.pop('token', None)
    entry.pop('saved_at', None)
    if entry:
        tokens[key] = entry
    else:
        tokens.pop(key, None)
    if saved is not None:
        _save(tokens)
    env_name = PROVIDERS[key]['env']
    if saved and os.environ.get(env_name) == saved:
        os.environ.pop(env_name, None)
    return {'provider': key, 'key_set': bool(os.getenv(env_name)),
            'source': 'env' if os.getenv(env_name) else 'unset',
            'model': preferred_model(key)}


def apply_saved_to_env() -> list[str]:
    """Export saved tokens into os.environ for this process and its children."""
    applied = []
    for key, row in _load().items():
        if key not in PROVIDERS or not isinstance(row, dict):
            continue
        token = str(row.get('token') or '')
        if token:
            os.environ[PROVIDERS[key]['env']] = token
            applied.append(key)
    return applied


def credentials_for(model, api_base=None, api_key=None):
    """Resolve (api_key, api_base) for a LiteLLM model string.

    An explicit argument wins. For a known ``<prefix>/`` model the provider key
    (saved token, then its env var) is used instead of ``ADAPTIX_API_KEY`` so a
    Gemini run never carries the DeepSeek key from ``.env``.
    """
    name = str(model or '')
    prefix = name.split('/', 1)[0] if '/' in name else ''
    spec = PROVIDERS.get(prefix)
    if not spec:
        return (api_key or os.getenv('ADAPTIX_API_KEY') or None,
                api_base or os.getenv('ADAPTIX_API_BASE') or None)
    key = api_key or get_token(prefix) or os.getenv('ADAPTIX_API_KEY') or None
    base = api_base
    if not base and prefix == 'openrouter':
        base = os.getenv('OPENROUTER_API_BASE') or None
    return key, base or None


def env_for_model(model, env=None):
    """Copy ``env`` (default os.environ) with credentials matching ``model``."""
    resolved = dict(os.environ if env is None else env)
    name = str(model or '')
    prefix = name.split('/', 1)[0] if '/' in name else ''
    if prefix not in PROVIDERS:
        return resolved
    key, base = credentials_for(name)
    if key:
        resolved['ADAPTIX_API_KEY'] = key
    if base:
        resolved['ADAPTIX_API_BASE'] = base
    else:
        # A stale ADAPTIX_API_BASE (e.g. a DeepSeek gateway) would break Gemini.
        resolved.pop('ADAPTIX_API_BASE', None)
    return resolved


def live_models(provider: str) -> dict:
    """Ask the provider for its current model list, falling back to the catalog.

    Gemini, Groq, DeepSeek and xAI need a key; OpenRouter's listing is public.
    The returned ids already carry the LiteLLM prefix (``gemini/``, ``xai/``,
    ``openrouter/``) so the caller can store one directly.
    """
    import httpx

    key = _provider(provider)
    spec = PROVIDERS[key]
    token = get_token(key)
    if not token and key not in _PUBLIC_MODELS:
        return {'models': list(spec['models']), 'source': 'catalog',
                'detail': 'simpan token dulu untuk memuat daftar model'}
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    if key == 'gemini' and token:
        headers = {'x-goog-api-key': token}
    url = _PUBLIC_MODELS.get(key, spec['test'])
    try:
        response = httpx.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return {'models': list(spec['models']), 'source': 'catalog',
                'detail': f'gagal memuat model ({type(exc).__name__}); memakai daftar bawaan'}
    ids = []
    if key == 'gemini':
        for item in payload.get('models') or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name') or '')
            if name.startswith('models/'):
                name = name[len('models/'):]
            methods = item.get('supportedGenerationMethods') or []
            if not name or (methods and 'generateContent' not in methods):
                continue
            ids.append('gemini/' + name)
    else:
        rows = payload.get('data') if isinstance(payload, dict) else payload
        for item in rows or []:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get('id') or '').strip()
            if model_id:
                ids.append(spec['prefix'] + model_id)
    models = sorted(set(ids))
    if not models:
        return {'models': list(spec['models']), 'source': 'catalog',
                'detail': 'provider tidak mengembalikan model; memakai daftar bawaan'}
    return {'models': models, 'source': 'live', 'detail': f'{len(models)} model dari provider'}


def test_token(provider: str) -> dict:
    """Check a saved/env token against the provider's own model listing."""
    import httpx

    key = _provider(provider)
    spec = PROVIDERS[key]
    token = get_token(key)
    if not token:
        return {'ok': False, 'detail': 'token belum diset'}
    headers = {'Authorization': f'Bearer {token}'}
    if key == 'gemini':
        headers = {'x-goog-api-key': token}
    try:
        response = httpx.get(spec['test'], headers=headers, timeout=10.0)
    except Exception as exc:
        return {'ok': False, 'detail': f'{type(exc).__name__}: token tidak dapat diverifikasi'[:200]}
    ok = response.status_code == 200
    detail = f'HTTP {response.status_code}'
    if not ok:
        try:
            body = response.json()
            message = (body.get('error') or {}).get('message') if isinstance(body, dict) else ''
            if message:
                detail += ': ' + str(message)[:160]
        except ValueError:
            pass
    return {'ok': ok, 'detail': detail}
