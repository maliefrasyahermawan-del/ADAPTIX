"""Evaluasi keamanan menyeluruh untuk static code audit.

Tidak seperti scanner yang mencari pola bug satu per satu, modul ini
menilai *kondisi keamanan* bundle: struktur file, dependensi, konfigurasi
server, penyimpanan data, autentikasi, dan input handling. Hasilnya selalu
ada walau scanner menemukan 0 kandidat — skor, grade (A–F), dan daftar
rekomendasi upgrade per kategori.

Kategori yang dinilai (berbasis heuristik deterministik, bukan LLM):

  1. **Struktur & cakupan** — berapa file masuk bundle vs dikecualikan,
     apakah file utama >1 MB, apakah ada folder privat bocor.
  2. **Dependensi & CVE** — lockfile/`pyproject.toml`/`package.json` ada?
     OSV scanner tersedia? Dependensi yang rentan terdeteksi?
  3. **Konfigurasi server** — http.server dev, bind 0.0.0.0, TLS absen,
     debug flag.
  4. **Penyimpanan data sensitif** — localStorage/sessionStorage dengan
     token/password/NIK; indexDB.
  5. **Autentikasi & sesi** — token di URL/query, cookie tanpa Secure/HttpOnly,
     JWT tanpa expiry terlihat.
  6. **Input handling / injeksi** — eval, innerHTML dinamis, SQL concat,
     shell=True.
  7. **Kredensial & secret** — API key / token / password hardcoded.

Skor dihitung sebagai 100 - sum(deduction). Tiap kategori memberi
deduction 0–25; grade:
  A (>=85) · B (70–84) · C (55–69) · D (40–54) · F (<40).
"""
from __future__ import annotations

import os
import re

CATEGORIES = [
    'structure',
    'dependencies',
    'server_config',
    'storage_sensitive',
    'auth_session',
    'input_injection',
    'credentials',
]

_GRADE = [(85, 'A'), (70, 'B'), (55, 'C'), (40, 'D'), (0, 'F')]


def _grade_for(score: int) -> str:
    for threshold, letter in _GRADE:
        if score >= threshold:
            return letter
    return 'F'


def _grade_text(score: int) -> str:
    letter = _grade_for(score)
    mapping = {
        'A': 'A — Kecil risiko, tinggal hardening',
        'B': 'B — Cukup aman, beberapa hardening diperlukan',
        'C': 'C — Risiko sedang, perlu upgrade sebelum produksi',
        'D': 'D — Risiko tinggi, jangan produksi',
        'F': 'F — Kritis, perbaiki segera',
    }
    return mapping[letter]


def _evidence(bundle, pattern, path_filter=None, max_hits=3):
    files = bundle.get('files') or {}
    hits = []
    for path, row in sorted(files.items()):
        if path_filter and not any(f in path for f in path_filter):
            continue
        text = row.get('text') or ''
        for lineno, line in enumerate(text.splitlines(), start=1):
            m = pattern.search(line)
            if m:
                hits.append({'path': path, 'line': lineno,
                             'snippet': line.strip()[:200]})
                if len(hits) >= max_hits:
                    break
        if len(hits) >= max_hits:
            break
    return hits


# ------------------------------------------------------------------ checks

def _check_structure(bundle, scanner_findings):
    files = bundle.get('files') or {}
    total_files = len(files)
    excluded = int(bundle.get('excluded') or 0)
    deduction = 0
    notes = []
    if total_files < 3:
        deduction += 15
        notes.append(f'Hanya {total_files} file masuk bundle — cakupan audit sangat terbatas. '
                     'Naikkan batas file atau sertakan file utama.')
    if excluded and excluded / max(1, total_files + excluded) > 0.8:
        deduction += 10
        notes.append(f'{excluded} file dikecualikan (>80% bundle) — gambar/PDF/arsip mendominasi; '
                     'pastikan HTML/JS/Python utama tidak tertinggal.')
    html = [p for p in files if p.lower().endswith(('.html', '.htm'))]
    if not html and total_files > 0:
        deduction += 8
        notes.append('Tidak ada file .html di bundle — audit UI tidak dapat dilakukan.')
    elif html:
        notes.append(f'{len(html)} file HTML masuk audit.')
    return _row('Struktur & cakupan', deduction, notes,
                'Semua file utama (.html/.js/.py) ada di bundle; '
                'file dikecualikan hanya gambar/arsip.')


def _check_dependencies(bundle, scanner_findings):
    files = bundle.get('files') or {}
    deduction = 0
    notes = []
    has_lock = any(re.search(r'(requirements|package\.json|pyproject\.toml|package-lock|yarn\.lock|pnpm-lock|Cargo\.lock|go\.mod|composer\.lock|Gemfile\.lock)', p, re.I)
                   for p in files)
    osv_hits = [f for f in scanner_findings if f.get('scanner') == 'osv-scanner']
    if not has_lock:
        deduction += 12
        notes.append('Tidak ada lockfile/manifest dependensi di bundle — versi library tidak terpin, '
                     'CVE tidak dapat dilacak.')
    if osv_hits:
        deduction += min(20, 5 + len(osv_hits) * 3)
        notes.append(f'{len(osv_hits)} kandidat CVE dependensi (osv-scanner) — upgrade ke versi minimum fixed.')
    else:
        notes.append('Tidak ada kandidat CVE dependensi terdeteksi scanner.'
                     if has_lock else 'Dependensi tidak dapat diverifikasi (manifest tidak ada).')
    return _row('Dependensi & CVE', deduction, notes,
                'Manifest + lockfile tersedia dan osv-scanner: 0 CVE.')


def _check_server_config(bundle, scanner_findings):
    hits = _evidence(bundle, re.compile(r'http\.server|bind\s*=\s*["\']0\.0\.0\.0|debug\s*=\s*True|app\.run\(', re.I))
    deduction = 0
    notes = []
    if hits:
        deduction += 15
        for h in hits:
            notes.append(f"{h['path']}:{h['line']} — server dev / bind terbuka / debug: {h['snippet'][:110]}")
        notes.append('Jangan pakai http.server/python -m untuk produksi; gunakan server produksi + TLS + bind localhost.')
    else:
        notes.append('Tidak ada indikasi server dev / bind terbuka / debug on di bundle.')
    return _row('Konfigurasi server', deduction, notes,
                'Server produksi dengan TLS, bind eksplisit, debug off.')


def _check_storage(bundle, scanner_findings):
    hits = _evidence(bundle, re.compile(
        r'(?:localStorage|sessionStorage)\s*\.\s*setItem\s*\([^,]*?(?:token|password|secret|api[_-]?key|email|nik|ktp|card|rek)|\bindexedDB\b', re.I))
    deduction = 0
    notes = []
    if hits:
        deduction += min(20, 5 + len(hits) * 5)
        for h in hits:
            notes.append(f"{h['path']}:{h['line']} — data sensitif di storage browser: {h['snippet'][:110]}")
        notes.append('Simpan token di httpOnly cookie; jangan simpan data keuangan/KUR di localStorage.')
    else:
        notes.append('Tidak ada indikasi data sensitif di localStorage/sessionStorage/indexedDB.')
    return _row('Penyimpanan data sensitif', deduction, notes,
                'Tidak ada kredensial/data finansial di storage browser.')


def _check_auth(bundle, scanner_findings):
    hits = _evidence(bundle, re.compile(
        r'(?:url|query|param).*(?:token|secret|api[_-]?key)\s*=|Set-Cookie:[^;]*(?:(?!;\\s*Secure)(?!;\\s*HttpOnly))', re.I))
    deduction = 0
    notes = []
    if hits:
        deduction += min(15, 5 + len(hits) * 5)
        for h in hits:
            notes.append(f"{h['path']}:{h['line']} — indikasi sesi tidak aman: {h['snippet'][:110]}")
    else:
        notes.append('Tidak ada indikasi token di URL atau cookie tanpa Secure/HttpOnly.')
    return _row('Autentikasi & sesi', deduction, notes,
                'Token tidak di URL; cookie Secure + HttpOnly + SameSite.')


def _check_input(bundle, scanner_findings):
    # Jangan pakai Function( — itu callback JS normal (function(){}, new Promise(function))
    # Bukan eksploitasi. Hanya: eval( , innerHTML= dari data pengguna, document.write, shell=True, SQL concat.
    hits = _evidence(bundle, re.compile(
        r'(?<!\w)eval\s*\(|innerHTML\s*=\s*(?!["\'][\w\s]+["\']\s*;)|document\.write\s*\(|shell\s*=\s*True|execute\s*\([^)]*(?:\+|%s|f["\'])', re.I))
    # Filter lebih ketat: innerHTML yang di-assign dari variabel (bukan string literal)
    hits = [h for h in hits if not re.search(r'innerHTML\s*=\s*["\'][^"\']{0,40}["\']\s*;?\s*$', h.get('snippet', ''))]
    deduction = 0
    notes = []
    if hits:
        deduction += min(25, 5 + len(hits) * 7)
        for h in hits:
            notes.append(f"{h['path']}:{h['line']} — injeksi/XSS risk: {h['snippet'][:110]}")
        notes.append('Escape output (textContent / DOMPurify), parameter binding untuk SQL, jangan eval.')
    else:
        notes.append('Tidak ada pola injeksi klasik (eval/SQL concat/innerHTML variabel) terdeteksi. '
                     'Catatan: Function(/callback JS bukan injeksi dan tidak dihitung.')
    return _row('Input handling / injeksi', deduction, notes,
                'Input di-escape; query terparameter; tidak ada eval.')


def _check_credentials(bundle, scanner_findings):
    hits = _evidence(bundle, re.compile(
        r'(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{16,}|AIza[A-Za-z0-9_-]{10,}|(?:api[_-]?key|password)\b\s*[:=]\s*["\'][^"\']{8,}["\'])', re.I))
    deduction = 0
    notes = []
    if hits:
        deduction += min(20, 8 + len(hits) * 6)
        for h in hits:
            notes.append(f"{h['path']}:{h['line']} — kredensial hardcoded: {h['snippet'][:110]}")
        notes.append('Rotasi kredensial yang bocor; pindahkan ke env/secret store server-side.')
    else:
        notes.append('Tidak ada kredensial hardcoded terdeteksi di bundle (setelah redaksi).')
    return _row('Kredensial & secret', deduction, notes,
                'Tidak ada secret hardcoded; semua via env.')


def _row(category, deduction, notes, recommendation):
    return {
        'category': category,
        'deduction': int(deduction),
        'notes': notes,
        'recommendation': recommendation,
    }


def evaluate(bundle, scanner_findings, report_findings=None) -> dict:
    """Hitung skor keamanan + grade + rekomendasi upgrade.

    Selalu mengembalikan dict lengkap walau scanner 0 kandidat dan
    laporan LLM belum ada — evaluasi ini deterministik.
    """
    scanner_findings = scanner_findings or []
    report_findings = report_findings or []
    rows = [
        _check_structure(bundle, scanner_findings),
        _check_dependencies(bundle, scanner_findings),
        _check_server_config(bundle, scanner_findings),
        _check_storage(bundle, scanner_findings),
        _check_auth(bundle, scanner_findings),
        _check_input(bundle, scanner_findings),
        _check_credentials(bundle, scanner_findings),
    ]
    # scanner verified findings menambah deduction
    extra = 0
    for f in scanner_findings:
        sev = str(f.get('severity') or 'info').lower()
        extra += {'critical': 15, 'high': 10, 'medium': 5, 'low': 2}.get(sev, 1)
    extra = min(25, extra)
    # report finding LLM menambah sedikit
    llm_extra = min(10, len(report_findings) * 2)
    total_deduction = min(100, sum(r['deduction'] for r in rows) + extra + llm_extra)
    score = max(0, 100 - total_deduction)
    # prioritas upgrade: kategori dengan deduction tertinggi dulu
    priorities = sorted(rows, key=lambda r: -r['deduction'])
    upgrades = []
    for row in priorities:
        if row['deduction'] > 0:
            upgrades.append({
                'prioritas': 'tinggi' if row['deduction'] >= 15 else ('sedang' if row['deduction'] >= 8 else 'rendah'),
                'kategori': row['category'],
                'aksi': row['recommendation'],
                'detail': ' '.join(row['notes'][:2])[:600],
            })
    if not upgrades:
        upgrades.append({
            'prioritas': 'rendah', 'kategori': 'Overall',
            'aksi': 'Pertahankan hygiene: keep lockfile terpin, update scanner rules, tes berkala.',
            'detail': 'Tidak ada indikasi kritis dari heuristik ini; laporkan sebagai hardening.',
        })
    # verdict bahasa Indonesia
    if score >= 85:
        verdict = (f'Bundle ini berisiko KECIL berdasarkan heuristik deterministik '
                   f'(skor {score}/100, grade {_grade_for(score)}). Scanner 0 kandidat '
                   'bukan berarti “aman absolut” — tetap jalankan pentest dinamis sebelum produksi.')
    elif score >= 55:
        verdict = (f'Bundle ini berisiko SEDANG (skor {score}/100, grade {_grade_for(score)}). '
                   'Perbaiki kategori ber-deduction tinggi sebelum produksi.')
    else:
        verdict = (f'Bundle ini berisiko TINGGI (skor {score}/100, grade {_grade_for(score)}). '
                   'Jangan produksi sebelum upgrade di bawah dilakukan.')
    return {
        'score': score,
        'grade': _grade_for(score),
        'grade_text': _grade_text(score),
        'verdict': verdict,
        'categories': rows,
        'scanner_extra_deduction': extra,
        'llm_extra_deduction': llm_extra,
        'upgrades': upgrades[:7],
        'total_deduction': total_deduction,
    }


def summary_text(evaluation: dict) -> str:
    lines = [
        f"Skor keamanan: {evaluation['score']}/100 — {evaluation['grade_text']}",
        evaluation['verdict'],
        '',
        'Rincian per kategori:',
    ]
    for row in evaluation['categories']:
        lines.append(f"  - {row['category']}: -{row['deduction']}pt — {'; '.join(row['notes'][:2])[:300]}")
    lines.append('')
    lines.append('Rekomendasi upgrade (prioritas):')
    for up in evaluation['upgrades']:
        lines.append(f"  [{up['prioritas']}] {up['kategori']}: {up['aksi']}")
    return '\n'.join(lines)
