"""Lecture documentaire bornée, classement explicable, extraction à confirmer.

Aucun service distant ni modèle génératif. Les résultats sont des suggestions.
"""
from __future__ import annotations
import io
import re
from pathlib import Path

MAX_TEXT = 16000
MAX_PAGES = 3
MAX_IMAGE_PIXELS = 12_000_000
MAX_INPUT_BYTES = 20 * 1024 * 1024

KINDS = (
    ("Facture", "vert", ("facture", "invoice", "montant ht", "montant ttc", "total ttc")),
    ("Bon de livraison", "rose", ("bon de livraison", "bl n°", "delivery note", "bon livraison")),
    ("Bon de réception", "rose", ("bon de réception", "bon de reception", "réception matière", "reception matiere")),
    ("Déclaration douanière", "bleu", ("douane", "dedouanement", "dédouanement", "déclaration import", "declaration import")),
    ("Fiche de prix", "jaune", ("fiche de prix", "calcul de prix", "prix de revient", "cost sheet")),
    ("Fiche d’emploi", "jaune", ("fiche d'emploi", "fiche d’emploi", "consommation tissu", "fabric consumption")),
    ("Lancement définitif", "jaune", ("lancement definitif", "lancement définitif")),
    ("Lancement provisoire", "jaune", ("lancement provisoire",)),
    ("Dossier technique", "jaune", ("dossier technique", "technical pack", "tech pack")),
)

PATTERNS = {
    "numero_lancement": r"\b(?:n[°o.]?\s*(?:de\s*)?lancement|lancement\s*n[°o.]?|orli)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,35})",
    "reference_matiere": r"\b(?:r[eé]f[eé]rence\s*(?:mati[eè]re|tissu)|r[eé]f\.\s*tissu)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{2,40})",
    "quantite": r"\b(?:quantit[eé]|qt[eé])\s*[:=]?\s*(\d[\d\s.,]{0,18})\s*(pi[eè]ces?|pcs?|m[eè]tres?|m\b|kg\b)?",
    "date_document": r"\b(?:date|livr[eé]\s*le|r[eé]ception\s*le)\s*[:=]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
    "montant": r"\b(?:montant|total\s*ttc|total\s*ht)\s*[:=]?\s*(\d[\d\s.,]{0,18})\s*(MAD|DH|EUR|€)?",
}


def _read_pdf(path: Path) -> tuple[str, str, list[str]]:
    from pypdf import PdfReader
    warnings = []
    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            return "", "protected", ["PDF protégé : extraction impossible"]
        pages = reader.pages
        chunks = [(p.extract_text() or "") for p in pages[:MAX_PAGES]]
        text = "\n".join(chunks).strip()
        if text:
            warnings.append("Texte natif uniquement : les images et annotations peuvent contenir des données non analysées")
            if len(pages) > MAX_PAGES: warnings.append(f"Analyse limitée aux {MAX_PAGES} premières pages")
            return text[:MAX_TEXT], "pdf_text", warnings
    except Exception:
        return "", "invalid_pdf", ["Extraction PDF impossible"]
    try:
        import fitz
        import pytesseract
        from PIL import Image
        doc = fitz.open(str(path))
        chunks = []
        for page in doc.pages(0,min(len(doc),MAX_PAGES)):
            # Rendu limité (~1,3 Mpx pour un A4) pour contenir la consommation mémoire.
            area=max(1,page.rect.width*page.rect.height)
            scale=min(1.5,(2_000_000/area)**0.5)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            chunks.append(pytesseract.image_to_string(im, lang="fra+eng", config="--psm 3", timeout=12))
        doc.close()
        if len(pages) > MAX_PAGES: warnings.append(f"OCR limité aux {MAX_PAGES} premières pages")
        return "\n".join(chunks)[:MAX_TEXT], "pdf_ocr", warnings
    except Exception:
        return "", "ocr_unavailable", ["OCR PDF indisponible : installer Tesseract et ses langues fra/eng, ainsi que PyMuPDF"]


def _read_document(path: Path, filename: str) -> dict:
    suffix = Path(filename).suffix.lower()
    warnings = []
    text, method = "", "unsupported"
    if suffix == ".pdf":
        text, method, warnings = _read_pdf(path)
    elif suffix in {".png", ".jpg", ".jpeg"}:
        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
            import pytesseract
            with Image.open(path) as raw:
                if raw.width * raw.height > MAX_IMAGE_PIXELS:
                    return {"text":"", "method":"image_limit", "warnings":["Image trop grande pour une analyse OCR sûre"]}
                im = ImageOps.exif_transpose(raw).convert("RGB")
                text = pytesseract.image_to_string(im, lang="fra+eng", timeout=12)[:MAX_TEXT]
                method = "image_ocr"
        except Exception:
            method = "ocr_unavailable"
            warnings.append("OCR image indisponible ou image illisible ; vérifiez Tesseract et fra/eng")
    elif suffix == ".docx":
        try:
            from docx import Document as Word
            document = Word(path)
            text = "\n".join([p.text for p in document.paragraphs] + [" ".join(c.text for c in row.cells) for table in document.tables for row in table.rows])[:MAX_TEXT]
            method = "docx_text"
        except Exception:
            warnings.append("Lecture DOCX impossible")
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT]
        method = "plain_text"
    elif suffix == ".eml":
        from email import policy
        from email.parser import BytesParser
        try:
            email = BytesParser(policy=policy.default).parsebytes(path.read_bytes()[:2_000_000])
            text = "\n".join(str(part.get_content()) for part in email.walk() if part.get_content_type()=="text/plain")[:MAX_TEXT]
            method="email_text"
        except Exception:
            warnings.append("Lecture du courrier impossible")
    elif suffix == ".xlsx":
        try:
            from openpyxl import load_workbook
            stream=path.open('rb')
            wb=load_workbook(stream,read_only=True,data_only=True)
            lines=[]
            for sheet in wb.worksheets[:3]:
                for row in sheet.iter_rows(max_row=min(sheet.max_row,120),max_col=min(sheet.max_column,16),values_only=True):
                    lines.append(" ".join(str(x) for x in row if x is not None))
            wb.close()
            stream.close()
            text="\n".join(lines)[:MAX_TEXT]
            method="xlsx_values"
            warnings.append('Lecture limitée aux 3 premières feuilles, 120 lignes et 16 colonnes ; valeurs mises en cache, formules non calculées')
        except Exception:
            warnings.append("Lecture XLSX impossible")
    if len(text)>=MAX_TEXT:warnings.append(f'Lecture partielle : texte limité à {MAX_TEXT} caractères')
    return {"text":text, "method":method, "warnings":warnings}


from threading import BoundedSemaphore
_READERS=BoundedSemaphore(2)

def read_document(path: Path, filename: str) -> dict:
    """Isolate untrusted parsers with memory, CPU, input and wall-clock limits."""
    import json,os,signal,subprocess,sys
    def limited(message):return {'text':'','method':'limited','warnings':[message]}
    if not path.is_file() or path.stat().st_size>MAX_INPUT_BYTES:return limited('Fichier absent ou limite de 20 Mo dépassée')
    if not _READERS.acquire(blocking=False):return limited('Lectures simultanées en cours ; réessayez plus tard')
    try:
        proc=subprocess.Popen([sys.executable,'-m','app.intake_worker'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            text=True,start_new_session=True,cwd=Path(__file__).resolve().parents[1],env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
        try:output,_=proc.communicate(json.dumps({'path':str(path.resolve()),'filename':filename}),timeout=35)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.communicate();return limited('Temps maximal de lecture atteint ; vérification manuelle nécessaire')
        if proc.returncode!=0:return limited('Lecture interrompue par une limite de ressources ou un format illisible')
        result=json.loads(output)
        if not isinstance(result,dict) or len(result.get('text',''))>MAX_TEXT:return limited('Résultat de lecture invalide')
        return result
    except (OSError,ValueError):return limited('Service local de lecture indisponible')
    finally:_READERS.release()


def classify_document(filename: str, content: str) -> dict:
    filename = filename.casefold().replace("_", " ").replace("-", " ")
    body = content[:5000].casefold()
    matches=[]
    for name,folder,keywords in KINDS:
        hits=[k for k in keywords if k in filename or k in body]
        if not hits: continue
        score = sum(3 if k in filename else 1 for k in hits)
        matches.append({"doc_type":name,"folder":folder,"score":score,"evidence":hits[:3]})
    matches.sort(key=lambda x:x["score"],reverse=True)
    result=[]
    for m in matches[:3]:
        result.append({"doc_type":m["doc_type"],"folder":m["folder"],"reason":"Mots-clés repérés : "+", ".join(m["evidence"]),"confidence_label":"indice fort" if m["score"]>=3 else "indice faible"})
    return {"suggestions":result,"needs_confirmation":True,"ambiguous":len(matches)>1 and matches[0]["score"]==matches[1]["score"]}


def extract_fields(text: str) -> list[dict]:
    result=[]
    for key,pattern in PATTERNS.items():
        match=re.search(pattern,text,re.IGNORECASE)
        if not match: continue
        value=match.group(1).strip()
        # Une chaîne tronquée ou un séparateur seul n'est pas une donnée exploitable.
        if not value or (key in {"quantite","montant"} and not re.search(r"\d",value)): continue
        result.append({"key":key,"value":value,"unit":(match.group(2) or "") if match.lastindex and match.lastindex>=2 else "", "source_excerpt":text[max(0,match.start()-35):min(len(text),match.end()+35)].replace("\n"," ").strip()[:180],"status":"proposed"})
    return result


def preview(path: Path,filename: str) -> dict:
    read=read_document(path,filename)
    return {"filename":filename,"method":read["method"],"warnings":read["warnings"],
            "text_excerpt":read["text"][:650],"classification":classify_document(filename,read["text"]),
            "fields":extract_fields(read["text"]),"provenance":read.get("provenance",{}),"human_validation_required":True}
