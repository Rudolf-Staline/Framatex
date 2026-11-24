"""Local, bounded and explainable document reading.

This module extracts and proposes information only.  A human confirmation is
always required before an extracted business value can be used.
"""
from __future__ import annotations

import hashlib
import itertools
import logging
import os
import re
import shutil
import subprocess
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

LOG = logging.getLogger(__name__)


def _positive_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class ReadingLimits:
    max_bytes: int = _positive_env("FRAMATEX_ANALYSIS_MAX_BYTES", 12 * 1024 * 1024)
    max_pages: int = _positive_env("FRAMATEX_ANALYSIS_MAX_PAGES", 80)
    max_text: int = _positive_env("FRAMATEX_ANALYSIS_MAX_TEXT", 180_000)
    max_image_pixels: int = _positive_env("FRAMATEX_OCR_MAX_IMAGE_PIXELS", 12_000_000)
    ocr_page_timeout: int = _positive_env("FRAMATEX_OCR_PAGE_TIMEOUT_SECONDS", 12)
    document_timeout: int = _positive_env("FRAMATEX_ANALYSIS_TIMEOUT_SECONDS", 90)
    render_dpi: int = _positive_env("FRAMATEX_OCR_DPI", 240)
    max_sheets: int = _positive_env("FRAMATEX_ANALYSIS_MAX_SHEETS", 12)
    max_rows: int = _positive_env("FRAMATEX_ANALYSIS_MAX_ROWS", 1_000)
    max_columns: int = _positive_env("FRAMATEX_ANALYSIS_MAX_COLUMNS", 32)
    max_memory_mib: int = _positive_env("FRAMATEX_ANALYSIS_MAX_MEMORY_MIB", 768)


LIMITS = ReadingLimits()
MAX_TEXT, MAX_PAGES = LIMITS.max_text, LIMITS.max_pages
MAX_IMAGE_PIXELS, MAX_ANALYSIS_BYTES = LIMITS.max_image_pixels, LIMITS.max_bytes

# The existing 22 standard types; additions are alternate labels only.
KINDS = (
    ("Calcul du besoin", "jaune", ("calcul du besoin", "besoin matière", "besoins matière", "material requirement", "mrp")),
    ("Facture", "vert", ("facture", "invoice", "montant ht", "montant ttc", "total ttc")),
    ("Bon de livraison", "rose", ("bon de livraison", "delivery note", "bl n", "bon livraison")),
    ("Bon de réception", "rose", ("bon de réception", "réception matière", "reception matiere", "goods receipt")),
    ("Pièce douanière", "bleu", ("déclaration douanière", "douane", "dédouanement", "déclaration import", "customs declaration")),
    ("Fiche de prix", "jaune", ("fiche de prix", "calcul de prix", "prix de revient", "cost sheet")),
    ("Fiche d’emploi", "jaune", ("fiche d'emploi", "consommation tissu", "fabric consumption", "fiche emploi")),
    ("Lancement définitif", "jaune", ("lancement définitif", "lancement definitif")),
    ("Lancement provisoire", "jaune", ("lancement provisoire",)),
    ("Dossier technique client", "jaune", ("dossier technique client", "dossier technique", "technical pack", "tech pack")),
    ("Commande client", "jaune", ("commande client", "bon de commande", "purchase order", "po number")),
    ("Excel BE", "jaune", ("étude be", "bureau d'études", "étude technique", "excel be")),
    ("Tests tissu", "jaune", ("test tissu", "essai textile", "rapport de test tissu", "fabric test")),
    ("Document réception", "rose", ("document de réception matière", "contrôle réception matière", "reception control")),
    ("Justificatif import/export", "bleu", ("justificatif import", "justificatif export", "import export proof")),
    ("Document transit", "bleu", ("document transit", "déclaration de transit", "transit declaration")),
    ("Document transport", "bleu", ("document transport", "lettre de voiture", "bill of lading", "cmr")),
    ("Justificatif de dédouanement", "bleu", ("justificatif de dédouanement", "quittance douanière", "customs clearance")),
    ("Document facturation", "vert", ("pièce de facturation", "document de facturation", "billing document")),
    ("Avoir / correction de facture", "vert", ("note de crédit", "avoir client", "facture d'avoir", "credit note")),
    ("Email", "jaune", ("email technique", "courriel technique", "technical email")),
    ("Email", "rose", ("email réception", "email logistique", "courriel logistique", "logistics email")),
)

PATTERNS = {
    "numero_lancement": r"\b(?:n[°o.]?\s*(?:de\s*)?lancement|lancement\s*n[°o.]?|orli)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,35})",
    "reference_matiere": r"\b(?:r[eé]f[eé]rence\s*(?:mati[eè]re|tissu)|r[eé]f\.\s*tissu)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,40})",
    "reference_client": r"\b(?:r[eé]f[eé]rence\s+client|r[eé]f\.\s*client)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,39})",
    "reference_commande": r"\b(?:r[eé]f[eé]rence\s+(?:de\s+)?commande|commande\s*(?:n[°o.]?|no|#))\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,39})",
    "reference_article": r"\b(?:r[eé]f[eé]rence\s+(?:article|mod[eè]le)|article\s*(?:n[°o.]?|#))\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,39})",
    "client": r"\b(?:client|customer)\s*[:#-]\s*([^\n|;]{2,90})",
    "fournisseur": r"\b(?:fournisseur|supplier|vendor)\s*[:#-]\s*([^\n|;]{2,90})",
    "quantite_commandee": r"\bquantit[eé]\s+command[eé]e\s*[:=]?\s*(\d[\d \u00a0\u202f.,]{0,18})\s*(pi[eè]ces?|pcs?)?",
    "quantite_produite": r"\bquantit[eé]\s+produite\s*[:=]?\s*(\d[\d \u00a0\u202f.,]{0,18})\s*(pi[eè]ces?|pcs?)?",
    "quantite_livree": r"\bquantit[eé]\s+livr[eé]e\s*[:=]?\s*(\d[\d \u00a0\u202f.,]{0,18})\s*(pi[eè]ces?|pcs?)?",
    "quantite": r"\b(?:quantit[eé](?!\s+(?:command[eé]e|produite|livr[eé]e))|qt[eé])\s*[:=]?\s*(\d[\d \u00a0\u202f.,]{0,18})\s*(pi[eè]ces?|pcs?|m[eè]tres?|m\b|kg\b)?",
    "date_document": r"\b(?:date|livr[eé]\s*le|r[eé]ception\s*le)\s*[:=]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    "montant_total": r"\b(?:montant\s+total|total\s*(?:ttc|ht)|grand\s+total)\s*[:=]?\s*(\d[\d\s.,]{0,18})\s*(MAD|DH|EUR|€|USD|\$)?",
    "montant": r"\bmontant(?!\s+total)\s*[:=]?\s*(\d[\d\s.,]{0,18})\s*(MAD|DH|EUR|€|USD|\$)?",
    "devise": r"\b(MAD|DH|EUR|USD|GBP|€|\$)\b",
    "reference_documentaire": r"\b(?:r[eé]f[eé]rence\s+document(?:aire)?|document\s*(?:n[°o.]?|#))\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,39})",
}
for key, label, units in (
    ("consommation_matiere", r"consommation(?:\s+(?:mati[eè]re|tissu))?", r"m\s*/\s*(?:pi[eè]ce|pc)|kg\s*/\s*(?:pi[eè]ce|pc)"),
    ("besoin_matiere", r"besoin\s+(?:mati[eè]re|tissu)", r"kg|m[eè]tres?|m"),
    ("prix_unitaire", r"prix\s+unitaire", r"(?:MAD|DH|EUR|€|USD|\$)\s*/\s*(?:pi[eè]ce|pc)"),
    ("prix_total", r"prix\s+total", r"MAD|DH|EUR|€|USD|\$"),
): PATTERNS[key] = rf"\b{label}\s*[:=]?\s*(\d[\d \u00a0\u202f.,]{{0,18}})\s*({units})\b"


class OCRProblem(RuntimeError):
    def __init__(self, code, message): super().__init__(message); self.code, self.message = code, message


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).casefold().replace("’", "'"))
    return " ".join(re.sub(r"[_-]", " ", "".join(c for c in text if not unicodedata.combining(c))).split())


def _tesseract_candidates():
    candidates = [os.getenv("TESSERACT_CMD", ""), shutil.which("tesseract") or ""]
    for root in (os.getenv("ProgramFiles", ""), os.getenv("ProgramW6432", ""), r"C:\\Program Files"):
        if root: candidates.append(str(Path(root) / "Tesseract-OCR" / "tesseract.exe"))
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def tesseract_diagnostics() -> dict:
    command = next((item for item in _tesseract_candidates() if Path(item).is_file() or shutil.which(item)), None)
    if not command: return {"available": False, "code": "tesseract_missing", "languages": [], "message": "Tesseract est absent ou son chemin n'est pas configuré."}
    try:
        result = subprocess.run([command, "--list-langs"], capture_output=True, text=True, timeout=5, check=True)
        languages = [line.strip() for line in result.stdout.splitlines() if line.strip() and "List of" not in line]
    except (OSError, subprocess.SubprocessError) as exc:
        LOG.warning("Tesseract configuration unavailable: %s", type(exc).__name__)
        return {"available": False, "code": "tesseract_misconfigured", "languages": [], "message": "Tesseract est présent mais sa configuration est invalide."}
    missing = [language for language in ("fra", "eng") if language not in languages]
    return {"available": not missing, "code": "ocr_language_missing" if missing else "ready", "path": command, "languages": languages, "missing_languages": missing, "message": f"Langue OCR manquante : {', '.join(missing)}." if missing else "Tesseract prêt."}


def _ocr_engine():
    diagnostic = tesseract_diagnostics()
    if not diagnostic["available"]: raise OCRProblem(diagnostic["code"], diagnostic["message"])
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = diagnostic["path"]
    return pytesseract


def _ocr_image(image, pytesseract):
    from PIL import ImageEnhance, ImageFilter, ImageOps
    image = ImageOps.exif_transpose(image); image = ImageOps.grayscale(image); image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(1.35).filter(ImageFilter.MedianFilter(size=3))
    try:
        rotate = int(re.search(r"Rotate:\s*(\d+)", pytesseract.image_to_osd(image, timeout=min(4, LIMITS.ocr_page_timeout))).group(1))
        if rotate in (90, 180, 270): image = image.rotate(rotate, expand=True)
    except Exception: pass
    return pytesseract.image_to_string(image, lang="fra+eng", timeout=LIMITS.ocr_page_timeout)


def _limit(code, message, **detail): return {"code": code, "message": message, **detail}
def _usable_native_text(text): return len(re.findall(r"[\wÀ-ÿ]", text)) >= 12
def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def _read_pdf(path: Path, allow_ocr: bool):
    import pymupdf as fitz
    warnings, limitations = [], []
    try:
        with fitz.open(path, filetype="pdf") as document:
            if document.is_encrypted: return "", "pdf_protected", ["PDF protégé : extraction impossible."], [], [_limit("pdf_protected", "PDF protégé")]
            total, count = len(document), min(len(document), LIMITS.max_pages)
            if total > count:
                message = f"Lecture partielle : {count} pages sur {total} ont été analysées."
                warnings.append(message); limitations.append(_limit("page_limit", message, analyzed_pages=count, total_pages=total))
            started, chunks, sources, methods, engine = time.monotonic(), [], [], set(), None
            for index in range(count):
                number = index + 1
                if time.monotonic() - started >= LIMITS.document_timeout:
                    message = f"Lecture partielle : délai atteint après la page {index}."
                    warnings.append(message); limitations.append(_limit("document_timeout", message, analyzed_pages=index, total_pages=total)); break
                page, native = document[index], document[index].get_text("text", sort=True).strip()
                if _usable_native_text(native):
                    value = native[:LIMITS.max_text]; chunks.append(value); sources.append({"page": number, "method": "pdf_text", "text": value}); methods.add("pdf_text"); continue
                if not allow_ocr:
                    message = f"Page {number} sans texte natif exploitable ; OCR requis."
                    warnings.append(message); limitations.append(_limit("ocr_required", message, page=number)); continue
                try:
                    engine = engine or _ocr_engine(); area = max(float(page.rect.width * page.rect.height), 1.0)
                    scale = min(LIMITS.render_dpi / 72, (LIMITS.max_image_pixels / area) ** .5)
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
                    from PIL import Image
                    value = _ocr_image(Image.frombytes("RGB", [pix.width, pix.height], pix.samples), engine).strip()[:LIMITS.max_text]; methods.add("pdf_ocr")
                    if value: chunks.append(value); sources.append({"page": number, "method": "pdf_ocr", "text": value})
                    else:
                        message = f"Page {number} illisible par OCR."; warnings.append(message); limitations.append(_limit("page_unreadable", message, page=number))
                except OCRProblem as exc:
                    LOG.warning("OCR unavailable (%s) for PDF page %s", exc.code, number); warnings.append(exc.message); limitations.append(_limit(exc.code, exc.message, page=number)); break
                except Exception as exc:
                    code = "ocr_timeout" if "timeout" in type(exc).__name__.lower() else "page_unreadable"; message = f"Délai OCR dépassé pour la page {number}." if code == "ocr_timeout" else f"Page {number} illisible par OCR."
                    LOG.warning("OCR failed (%s) for PDF page %s", type(exc).__name__, number); warnings.append(message); limitations.append(_limit(code, message, page=number))
            text = "\n".join(chunks)
            if len(text) > LIMITS.max_text:
                text = text[:LIMITS.max_text]; warnings.append("Lecture partielle : limite de texte atteinte."); limitations.append(_limit("text_limit", "Limite de texte atteinte"))
            return text, "pdf_hybrid" if len(methods) > 1 else next(iter(methods), "ocr_required" if allow_ocr else "pdf_text"), warnings, sources, limitations
    except Exception as exc:
        LOG.warning("PDF read failed (%s)", type(exc).__name__)
        return "", "pdf_unreadable", ["Extraction PDF impossible."], [], [_limit("pdf_unreadable", "Extraction PDF impossible")]


def read_document(path: Path, filename: str, allow_ocr=True) -> dict:
    suffix, warnings, limitations, sources, text, method = Path(filename).suffix.lower(), [], [], [], "", "unsupported"
    try: size, digest = path.stat().st_size, _sha256(path)
    except OSError: return {"text":"", "method":"unreadable", "warnings":["Fichier introuvable ou illisible."], "sources":[], "limitations":[_limit("unreadable", "Fichier introuvable ou illisible")], "sha256":None}
    if size > LIMITS.max_bytes:
        message = f"Document trop volumineux pour la lecture automatique (limite : {LIMITS.max_bytes // (1024 * 1024)} Mo)."
        return {"text":"", "method":"size_limit", "warnings":[message], "sources":[], "limitations":[_limit("size_limit", message, size=size)], "sha256":digest}
    if suffix in {".docx", ".xlsx"}:
        try:
            with zipfile.ZipFile(path) as archive:
                if sum(item.file_size for item in archive.infolist()) > 24 * 1024 * 1024: return {"text":"", "method":"size_limit", "warnings":["Contenu Office trop volumineux pour une lecture automatique."], "sources":[], "limitations":[_limit("office_content_limit", "Contenu Office trop volumineux")], "sha256":digest}
        except (OSError, zipfile.BadZipFile): return {"text":"", "method":"unreadable", "warnings":["Archive Office illisible."], "sources":[], "limitations":[_limit("office_unreadable", "Archive Office illisible")], "sha256":digest}
    if suffix == ".pdf": text, method, warnings, sources, limitations = _read_pdf(path, allow_ocr)
    elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        if not allow_ocr: method = "ocr_required"; warnings.append("OCR requis pour cette image."); limitations.append(_limit("ocr_required", "OCR requis pour cette image"))
        else:
            try:
                from PIL import Image
                with Image.open(path) as image:
                    if image.width * image.height > LIMITS.max_image_pixels: raise OCRProblem("image_limit", "Image trop grande pour une analyse OCR sûre.")
                    text = _ocr_image(image.convert("RGB"), _ocr_engine()).strip()[:LIMITS.max_text]
                method = "image_ocr"; sources = [{"page":1, "method":method, "text":text}]
                if not text: warnings.append("Image illisible par OCR."); limitations.append(_limit("page_unreadable", "Image illisible par OCR", page=1))
            except OCRProblem as exc: method = exc.code; warnings.append(exc.message); limitations.append(_limit(exc.code, exc.message))
            except Exception as exc:
                code = "ocr_timeout" if "timeout" in type(exc).__name__.lower() else "page_unreadable"; message = "Délai OCR dépassé." if code == "ocr_timeout" else "Image illisible par OCR."
                LOG.warning("image OCR failed (%s)", type(exc).__name__); method = code; warnings.append(message); limitations.append(_limit(code, message))
    elif suffix == ".docx":
        try:
            from docx import Document as Word
            document = Word(path)
            for index, paragraph in enumerate(document.paragraphs, 1):
                if paragraph.text.strip(): sources.append({"paragraph":index, "method":"docx_text", "text":paragraph.text[:1000]})
            for table_index, table in enumerate(document.tables, 1):
                for row_index, row in enumerate(table.rows[:LIMITS.max_rows], 1):
                    value = " | ".join(cell.text[:300] for cell in row.cells[:LIMITS.max_columns] if cell.text.strip())
                    if value: sources.append({"table":table_index, "row":row_index, "method":"docx_table", "text":value})
            text, method = "\n".join(item["text"] for item in sources)[:LIMITS.max_text], "docx_text"
        except Exception as exc: LOG.warning("DOCX read failed (%s)", type(exc).__name__); method = "docx_unreadable"; warnings.append("Lecture DOCX impossible."); limitations.append(_limit("docx_unreadable", "Lecture DOCX impossible"))
    elif suffix in {".txt", ".csv"}:
        with path.open(encoding="utf-8-sig", errors="replace") as source: text = source.read(LIMITS.max_text)
        method, sources = "plain_text", [{"method":"plain_text", "text":text}]
    elif suffix == ".eml":
        from email import policy
        from email.parser import BytesParser
        try:
            with path.open("rb") as source: email = BytesParser(policy=policy.default).parsebytes(source.read(2_000_000))
            text = (str(email.get("Subject", "")) + "\n" + "\n".join(str(part.get_content()) for part in email.walk() if part.get_content_type() == "text/plain"))[:LIMITS.max_text]; method, sources = "email_text", [{"method":"email_text", "text":text}]
        except Exception: method = "email_unreadable"; warnings.append("Lecture du courrier impossible."); limitations.append(_limit("email_unreadable", "Lecture du courrier impossible"))
    elif suffix == ".xlsx":
        try:
            from openpyxl import load_workbook
            with path.open("rb") as source:
                book = load_workbook(source, read_only=True, data_only=False, keep_links=False)
                try:
                    for sheet in book.worksheets[:LIMITS.max_sheets]:
                        sources.append({"sheet":sheet.title, "method":"xlsx_values", "text":sheet.title})
                        for row in sheet.iter_rows(max_row=min(sheet.max_row or LIMITS.max_rows, LIMITS.max_rows), max_col=min(sheet.max_column or LIMITS.max_columns, LIMITS.max_columns)):
                            cells = [cell for cell in row if cell.value is not None and cell.data_type != "f"]
                            if cells: sources.append({"sheet":sheet.title, "cell":f"{cells[0].coordinate}:{cells[-1].coordinate}", "method":"xlsx_values", "text":" ".join(str(cell.value)[:160] for cell in cells)})
                finally: book.close()
            text, method = "\n".join(item["text"] for item in sources)[:LIMITS.max_text], "xlsx_values"; warnings.append("Lecture des valeurs saisies ; les formules et leurs valeurs en cache sont exclues.")
        except Exception as exc: LOG.warning("XLSX read failed (%s)", type(exc).__name__); method = "xlsx_unreadable"; warnings.append("Lecture XLSX impossible."); limitations.append(_limit("xlsx_unreadable", "Lecture XLSX impossible"))
    else: warnings.append("Format non pris en charge pour l'extraction automatique."); limitations.append(_limit("unsupported", "Format non pris en charge"))
    return {"text":text, "method":method, "warnings":list(dict.fromkeys(warnings)), "sources":sources, "limitations":limitations, "sha256":digest}


def _fuzzy_match(term, value):
    if term in value: return True
    words, target = value.split(), term.split()
    if len(target) < 2: return False
    for index in range(max(0, len(words) - len(target) + 1)):
        candidate = " ".join(words[index:index + len(target)])
        if sum(a != b for a, b in itertools.zip_longest(candidate, term)) <= 2: return True
    return False


def classify_document(filename: str, content: str) -> dict:
    name, body = normalized(Path(filename).stem), normalized(content[:LIMITS.max_text]); headings = [normalized(line) for line in content.splitlines()[:30] if line.strip()][:12]; matches = []
    for kind, folder, keywords in KINDS:
        terms = list(dict.fromkeys(normalized(item) for item in keywords)); body_hits = [term for term in terms if _fuzzy_match(term, body)]; name_hits = [term for term in terms if _fuzzy_match(term, name)]; heading_hits = [term for term in terms if any(_fuzzy_match(term, heading) for heading in headings)]
        if not (body_hits or name_hits): continue
        score = min(1.0, .22 * len(set(body_hits)) + .16 * len(set(name_hits)) + .34 * len(set(heading_hits)) + (.20 if terms[0] in body_hits else 0))
        evidence = ([{"source":"en-tête", "match":item} for item in heading_hits[:2]] + [{"source":"contenu", "match":item} for item in body_hits[:3]] + [{"source":"nom du fichier", "match":item} for item in name_hits[:2]])
        matches.append({"doc_type":kind, "folder":folder, "evidence":evidence, "reason":" · ".join(f"{item['source']} : {item['match']}" for item in evidence), "confidence":round(score, 2)})
    matches.sort(key=lambda item: item["confidence"], reverse=True); ambiguous = len(matches) > 1 and matches[0]["confidence"] - matches[1]["confidence"] < .12; decisive = bool(matches and matches[0]["confidence"] >= .60 and not ambiguous)
    for item in matches: item["confidence_label"] = "élevée" if item["confidence"] >= .75 else "à vérifier"
    return {"suggestions":matches[:3], "needs_confirmation":True, "status":"identified" if decisive else "multiple" if ambiguous else "probable" if matches else "impossible", "ambiguous":ambiguous, "decisive":decisive}


def _normalized_value(key, value):
    if key == "date_document":
        for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
            try: return datetime.strptime(value, pattern).date().isoformat()
            except ValueError: pass
        return None
    if key in {"quantite", "quantite_commandee", "quantite_produite", "quantite_livree", "consommation_matiere", "besoin_matiere", "prix_unitaire", "prix_total", "montant", "montant_total"}:
        compact = value.replace("\u00a0", " ").replace("\u202f", " ").replace(" ", "")
        if compact.count(",") == 1 and compact.count(".") >= 1: compact = compact.replace(".", "").replace(",", ".") if compact.rfind(",") > compact.rfind(".") else compact.replace(",", "")
        elif compact.count(",") == 1: compact = compact.replace(",", ".")
        elif compact.count(".") > 1: compact = compact.replace(".", "")
        try: return format(Decimal(compact), "f")
        except InvalidOperation: return None
    return None


def extract_fields(text: str) -> list[dict]:
    result = []
    for key, pattern in PATTERNS.items():
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if not matches: continue
        match, value = matches[0], matches[0].group(1).strip()
        if not value or (key.startswith(("quantite", "montant", "prix", "besoin", "consommation")) and not re.search(r"\d", value)): continue
        unit = (match.group(2) or "").strip() if match.lastindex and match.lastindex >= 2 else ""; values = {(normalized(item.group(1)), normalized((item.group(2) or "") if item.lastindex and item.lastindex >= 2 else "")) for item in matches}
        result.append({"key":key, "value":value, "original_value":value, "normalized_value":_normalized_value(key, value), "unit":unit, "source_excerpt":text[max(0, match.start()-35):min(len(text), match.end()+120)].replace("\n", " ").strip()[:180], "offset":match.start(), "method":"pattern", "confidence":.58 if len(values) > 1 else .78, "status":"ambiguous" if len(values) > 1 else "proposed"})
    return result


def preview(path: Path, filename: str, allow_ocr=True) -> dict:
    read = read_document(path, filename, allow_ocr)
    fields = extract_fields(read["text"])
    for field in fields:
        cursor, source = 0, None
        for item in read.get("sources", []):
            end = cursor + len(item["text"])
            if cursor <= field["offset"] < end:
                source, local = item, field["offset"] - cursor; field["source_excerpt"] = item["text"][max(0, local-35):min(len(item["text"]), local+150)].replace("\n", " ").strip()[:180]; break
            cursor = end + 1
        for locator in ("page", "sheet", "cell", "paragraph", "table", "row"): field[locator] = source.get(locator) if source else None
        field["method"] = source["method"] if source else read["method"]; field.pop("offset", None)
    reading_status = "impossible" if not read["text"] and read["limitations"] else "partial" if read["limitations"] else "success"
    return {"schema_version":"document-intelligence/v2", "filename":filename, "sha256":read["sha256"], "method":read["method"], "reading_status":reading_status, "warnings":read["warnings"], "limitations":read["limitations"], "sources":read["sources"], "text_excerpt":read["text"][:650], "extracted_text":read["text"], "classification":classify_document(filename, read["text"]), "comparison_text":normalized(read["text"])[:12000], "comparison_lines":[line.strip()[:500] for line in read["text"].splitlines() if len(line.strip()) >= 4][:80], "fields":fields, "uncertain_fields":[item["key"] for item in fields if item["status"] == "ambiguous" or item["confidence"] < .7], "human_validation_required":True}
