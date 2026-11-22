"""Lecture documentaire bornée, classement explicable, extraction à confirmer.

Aucun service distant ni modèle génératif. Les résultats sont des suggestions.
"""
from __future__ import annotations
import itertools
import re
import unicodedata
import zipfile
from pathlib import Path

MAX_TEXT = 16000
MAX_PAGES = 3
MAX_IMAGE_PIXELS = 12_000_000
MAX_ANALYSIS_BYTES = 12 * 1024 * 1024

KINDS = (
    ("Calcul du besoin", "jaune", ("calcul du besoin", "besoin matiere", "besoin matière", "besoins matière", "material requirement")),
    ("Facture", "vert", ("facture", "invoice", "montant ht", "montant ttc", "total ttc")),
    ("Bon de livraison", "rose", ("bon de livraison", "bl n°", "delivery note", "bon livraison")),
    ("Bon de réception", "rose", ("bon de réception", "bon de reception", "réception matière", "reception matiere")),
    ("Déclaration douanière", "bleu", ("douane", "dedouanement", "dédouanement", "déclaration import", "declaration import")),
    ("Fiche de prix", "jaune", ("fiche de prix", "calcul de prix", "prix de revient", "cost sheet")),
    ("Fiche d’emploi", "jaune", ("fiche d'emploi", "fiche d’emploi", "consommation tissu", "fabric consumption")),
    ("Lancement définitif", "jaune", ("lancement definitif", "lancement définitif")),
    ("Lancement provisoire", "jaune", ("lancement provisoire",)),
    ("Dossier technique", "jaune", ("dossier technique", "technical pack", "tech pack")),
    ("Commande client", "jaune", ("commande client", "bon de commande", "purchase order")),
    ("Excel BE", "jaune", ("étude be", "bureau d'études", "étude technique")),
    ("Tests tissu", "jaune", ("test tissu", "essai textile", "rapport de test tissu")),
    ("Document réception", "rose", ("document de réception matière", "contrôle réception matière")),
    ("Justificatif import/export", "bleu", ("justificatif import", "justificatif export")),
    ("Document transit", "bleu", ("document transit", "déclaration de transit")),
    ("Document transport", "bleu", ("document transport", "lettre de voiture", "bill of lading")),
    ("Justificatif de dédouanement", "bleu", ("justificatif de dédouanement", "quittance douanière")),
    ("Document facturation", "vert", ("pièce de facturation", "document de facturation")),
    ("Avoir / correction de facture", "vert", ("note de crédit", "avoir client", "facture d'avoir")),
)

PATTERNS = {
    "numero_lancement": r"\b(?:n[°o.]?\s*(?:de\s*)?lancement|lancement\s*n[°o.]?|orli)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,35})",
    "reference_matiere": r"\b(?:r[eé]f[eé]rence\s*(?:mati[eè]re|tissu)|r[eé]f\.\s*tissu)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,40})",
    "quantite": r"\b(?:quantit[eé]|qt[eé])[ \t]*[:=]?[ \t]*(\d[\d \u00a0\u202f.,]{0,18})[ \t]*(pi[eè]ces?|pcs?|m[eè]tres?|m\b|kg\b)?",
    "date_document": r"\b(?:date|livr[eé]\s*le|r[eé]ception\s*le)\s*[:=]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
    "montant": r"\b(?:montant|total\s*ttc|total\s*ht)\s*[:=]?\s*(\d[\d\s.,]{0,18})\s*(MAD|DH|EUR|€)?",
    "reference_commande": r"\b(?:r[eé]f[eé]rence\s+(?:de\s+)?commande|commande\s+n[°o.]?)\s*[:#]?\s+([A-Z0-9][A-Z0-9_/-]{2,39})",
    "reference_article": r"\br[eé]f[eé]rence\s+(?:article|mod[eè]le)\s*[:#]?\s+([A-Z0-9][A-Z0-9_/-]{2,39})",
}
for key, label, units in (
    ('consommation_matiere', r'consommation(?:\s+(?:mati[eè]re|tissu))?', r'm\s*/\s*(?:pi[eè]ce|pc)|kg\s*/\s*(?:pi[eè]ce|pc)'),
    ('besoin_matiere', r'besoin\s+(?:mati[eè]re|tissu)', r'kg|m[eè]tres?|m'),
    ('prix_unitaire', r'prix\s+unitaire', r'(?:MAD|DH|EUR|€|USD)\s*/\s*(?:pi[eè]ce|pc)'),
    ('prix_total', r'(?:prix\s+total|total\s+ht)', r'MAD|DH|EUR|€|USD'),
):
    PATTERNS[key] = rf'\b{label}[ \t]*[:=]?[ \t]*(\d[\d \u00a0\u202f.,]{{0,18}})[ \t]*({units})\b'


def _ocr_image(image, pytesseract):
    """Bounded local OCR preprocessing; failures fall back to the original raster."""
    from PIL import ImageOps, ImageEnhance, ImageFilter
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(1.25)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    try:
        osd = pytesseract.image_to_osd(image, timeout=3)
        rotate = int(re.search(r'Rotate:\s*(\d+)', osd).group(1))
        if rotate in (90, 180, 270):
            image = image.rotate(rotate, expand=True)
    except Exception:
        pass
    return pytesseract.image_to_string(image, lang='fra+eng', timeout=7)


def _read_pdf(path: Path, allow_ocr: bool) -> tuple[str, str, list[str], list[dict]]:
    import pymupdf as fitz
    try:
        with fitz.open(path, filetype='pdf') as doc:
            if doc.is_encrypted:
                return '', 'protected', ['PDF protégé : extraction impossible'], []
            pages = [doc[i] for i in range(min(MAX_PAGES, len(doc)))]
            warnings = [f'Analyse limitée aux {MAX_PAGES} premières pages'] if len(doc) > MAX_PAGES else []
            chunks, sources, methods = [], [], set()
            for index, page in enumerate(pages, start=1):
                native = page.get_text()[:MAX_TEXT]
                if native.strip():
                    chunks.append(native); methods.add('pdf_text')
                    sources.append({'page': index, 'method': 'pdf_text', 'text': native[:MAX_TEXT]})
                    continue
                if not allow_ocr:
                    warnings.append(f'Page {index} sans texte natif; OCR requis')
                    continue
                try:
                    import pytesseract
                    from PIL import Image
                    scale = min(2.0, 1800 / max(page.rect.width, page.rect.height, 1))
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
                    image = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                    extracted = _ocr_image(image, pytesseract)[:MAX_TEXT]
                    methods.add('pdf_ocr')
                    if extracted.strip():
                        chunks.append(extracted)
                        sources.append({'page': index, 'method': 'pdf_ocr', 'text': extracted})
                    else:
                        warnings.append(f'Page {index} illisible par OCR')
                except Exception:
                    warnings.append(f'Page {index}: OCR indisponible ou illisible (Tesseract fra/eng requis)')
            if len(doc) > MAX_PAGES:
                warnings.append(f'Analyse limitée aux {MAX_PAGES} premières pages')
            method = 'pdf_hybrid' if len(methods) > 1 else next(iter(methods), 'ocr_unavailable' if allow_ocr else 'ocr_required')
            return '\n'.join(chunks)[:MAX_TEXT], method, warnings, sources
    except Exception:
        return '', 'pdf_unreadable', ['Extraction PDF impossible. Vérifiez le fichier.'], []


def read_document(path: Path, filename: str, allow_ocr=True) -> dict:
    suffix = Path(filename).suffix.lower()
    warnings = []
    page_sources = []
    text, method = "", "unsupported"
    if path.stat().st_size > MAX_ANALYSIS_BYTES:
        return {'text': '', 'method': 'size_limit', 'warnings': ['Analyse automatique limitée à 12 Mo. Vérification manuelle requise.']}
    if suffix in {'.docx', '.xlsx'}:
        try:
            with zipfile.ZipFile(path) as archive:
                if sum(item.file_size for item in archive.infolist()) > 24 * 1024 * 1024:
                    return {'text': '', 'method': 'size_limit', 'warnings': ['Contenu Office trop volumineux pour une lecture automatique.']}
        except (OSError, zipfile.BadZipFile):
            return {'text': '', 'method': 'unreadable', 'warnings': ['Archive Office illisible.']}
    if suffix == ".pdf":
        text, method, warnings, page_sources = _read_pdf(path, allow_ocr)
    elif suffix in {".png", ".jpg", ".jpeg"} and allow_ocr:
        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
            import pytesseract
            with Image.open(path) as raw:
                if raw.width * raw.height > MAX_IMAGE_PIXELS:
                    return {"text":"", "method":"image_limit", "warnings":["Image trop grande pour une analyse OCR sûre"]}
                im = ImageOps.exif_transpose(raw).convert("RGB")
                text = _ocr_image(im, pytesseract)[:MAX_TEXT]
                method = "image_ocr"
        except Exception:
            method = "ocr_unavailable"
            warnings.append("OCR image indisponible ou image illisible ; vérifiez Tesseract et fra/eng")
    elif suffix == ".docx":
        try:
            from docx import Document as Word
            document = Word(path)
            paragraphs = (p.text for p in itertools.islice(document.paragraphs, 300))
            rows = (" ".join(c.text for c in row.cells[:16]) for table in document.tables[:10] for row in table.rows[:100])
            text = "\n".join(line[:MAX_TEXT] for line in itertools.chain(paragraphs, rows))[:MAX_TEXT]
            method = "docx_text"
        except Exception:
            warnings.append("Lecture DOCX impossible")
    elif suffix in {'.txt', '.csv'}:
        with path.open(encoding='utf-8-sig', errors='replace') as source:
            text = source.read(MAX_TEXT)
        method = "plain_text"
    elif suffix == ".eml":
        from email import policy
        from email.parser import BytesParser
        try:
            with path.open('rb') as source:
                email = BytesParser(policy=policy.default).parsebytes(source.read(2_000_000))
            text = str(email.get('Subject', '')) + '\n' + '\n'.join(str(part.get_content()) for part in email.walk() if part.get_content_type()=="text/plain")[:MAX_TEXT]
            method="email_text"
        except Exception:
            warnings.append("Lecture du courrier impossible")
    elif suffix == ".xlsx":
        try:
            from openpyxl import load_workbook
            lines = []
            with path.open('rb') as source:
                wb = load_workbook(source, read_only=True, data_only=False, keep_links=False)
                try:
                    for sheet in wb.worksheets[:3]:
                        lines.append(sheet.title)
                        for row in sheet.iter_rows(max_row=min(sheet.max_row or 120, 120), max_col=min(sheet.max_column or 16, 16)):
                            lines.append(' '.join(str(cell.value)[:160] if cell.data_type != 'f' else '[formule]' for cell in row if cell.value is not None))
                finally:
                    wb.close()
            text="\n".join(lines)[:MAX_TEXT]
            method="xlsx_values"
            warnings.append('Lecture des valeurs saisies. Les formules et leurs valeurs en cache sont exclues.')
        except Exception:
            warnings.append("Lecture XLSX impossible")
        if text:
            page_sources = [{'page': None, 'method': method, 'text': text}]
    return {"text":text, "method":method, "warnings":warnings, 'sources': page_sources}


def normalized(text):
    text = unicodedata.normalize('NFKD', text.casefold().replace('’', "'"))
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return ' '.join(re.sub(r'[_-]', ' ', text).split())


def classify_document(filename: str, content: str) -> dict:
    name = normalized(Path(filename).stem)
    body = normalized(content[:MAX_TEXT])
    headings = [normalized(line) for line in content.splitlines()[:12] if line.strip()]
    matches = []
    for kind, folder, keywords in KINDS:
        terms = set(map(normalized, keywords))
        body_hits = sorted(term for term in terms if re.search(r'\b' + re.escape(term) + r'\b', body))
        name_hits = sorted(term for term in terms if re.search(r'\b' + re.escape(term) + r'\b', name))
        if not body_hits and not name_hits:
            continue
        primary = normalized(keywords[0])
        # A heading beats mentions in prose. Two competing headings require a person.
        title = any(line == primary or (line.startswith(primary + ' ') and len(line) < len(primary) + 32)
                    for line in headings)
        explicit = title or any(term == primary and ' ' in term for term in body_hits)
        strength = 3 if title else 2 if explicit else 1 if body_hits else 0
        evidence = [f'Contenu : {hit}' for hit in body_hits[:3]] + [f'Nom du fichier : {hit}' for hit in name_hits[:2]]
        matches.append((strength, {'doc_type': kind, 'folder': folder, 'reason': ' · '.join(evidence),
                                   'evidence': evidence, 'confidence_label': 'type explicite' if explicit else 'indice à vérifier'}))
    matches.sort(key=lambda item: item[0], reverse=True)
    ambiguous = len(matches) > 1 and matches[0][0] == matches[1][0]
    decisive = bool(matches and matches[0][0] >= 2 and not ambiguous)
    return {'suggestions': [record for _, record in matches[:3]], 'needs_confirmation': True,
            'ambiguous': ambiguous, 'decisive': decisive}


def extract_fields(text: str) -> list[dict]:
    result=[]
    for key,pattern in PATTERNS.items():
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if not matches:
            continue
        match = matches[0]
        value=match.group(1).strip()
        # Une chaîne tronquée ou un séparateur seul n'est pas une donnée exploitable.
        if not value or (key in {"quantite","montant"} and not re.search(r"\d",value)): continue
        alternatives = {(normalized(item.group(1)), normalized(item.group(2) or '') if item.lastindex >= 2 else '') for item in matches}
        result.append({"key":key,"value":value,"unit":(match.group(2) or "") if match.lastindex and match.lastindex>=2 else "", "source_excerpt":text[max(0,match.start()-35):min(len(text),match.end()+35)].replace("\n"," ").strip()[:180],"offset":match.start(),"status":"ambiguous" if len(alternatives) > 1 else "proposed"})
    return result


def preview(path: Path, filename: str, allow_ocr=True) -> dict:
    read=read_document(path,filename,allow_ocr)
    fields = extract_fields(read['text'])
    for field in fields:
        offset = field['offset']
        cursor = 0
        source = None
        for item in read.get('sources', []):
            end = cursor + len(item['text'])
            if cursor <= offset < end:
                source = item
                field['source_excerpt'] = item['text'][max(0, offset-cursor-35):min(len(item['text']), offset-cursor+150)].replace('\n',' ').strip()[:180]
                break
            cursor = end + 1
        field['page'] = source['page'] if source else None
        field['method'] = source['method'] if source else read['method']
        field.pop('offset', None)
    return {"filename":filename,"method":read["method"],"warnings":read["warnings"],
            "text_excerpt":read["text"][:650],"classification":classify_document(filename,read["text"]),
            "comparison_text":normalized(read["text"])[:12000],
            "fields":fields,"human_validation_required":True}
