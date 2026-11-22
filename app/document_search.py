"""Index plein texte local du contenu documentaire déjà analysé."""
from __future__ import annotations

import re

from sqlalchemy import text


def index_document_version(db, version, analysis: dict | None):
    if not analysis:
        return
    content = (analysis.get('comparison_text') or analysis.get('text_excerpt') or '').strip()
    references = ' '.join(str(field.get('value', '')) for field in analysis.get('fields', [])
                          if field.get('key', '').startswith('reference_') or field.get('key') == 'numero_lancement')
    db.execute(text('DELETE FROM document_content_fts WHERE version_id = :version_id'),
               {'version_id': version.id})
    db.execute(text('INSERT INTO document_content_fts(version_id, content, title, "references") '
                    'VALUES (:version_id, :content, :title, :references)'),
               {'version_id': version.id, 'content': content,
                'title': f'{version.document.title} {version.original_name}', 'references': references})


def search_content(db, query: str, limit: int = 500) -> dict[str, str]:
    tokens = re.findall(r'[\wÀ-ÿ]{2,}', query, flags=re.UNICODE)[:12]
    if not tokens:
        return {}
    expression = ' AND '.join('"' + token.replace('"', '""') + '"' for token in tokens)
    rows = db.execute(text('''SELECT version_id,
        snippet(document_content_fts, 1, '[', ']', ' … ', 18) AS excerpt
        FROM document_content_fts WHERE document_content_fts MATCH :query LIMIT :limit'''),
        {'query': expression, 'limit': limit}).all()
    return {version_id: excerpt for version_id, excerpt in rows}
