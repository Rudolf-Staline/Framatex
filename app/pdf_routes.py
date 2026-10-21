"""PDF previews and actual PDF annotations saved as immutable document versions."""
from io import BytesIO
from pathlib import Path
from typing import Literal
import math

import fitz
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import Document, DocumentVersion, User
from .document_comment_routes import authorize
from .main import STORAGE, audit, cloud_file, new_version, permitted

router = APIRouter()


class Point(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class Annotation(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    kind: Literal['highlight', 'ink', 'text']
    page: int = Field(ge=1, le=10000, strict=True)
    points: list[Point] = Field(min_length=2, max_length=2000)
    text: str = Field(default='', max_length=500)
    color: Literal['#edb900', '#265bc5', '#c43c39'] = '#265bc5'

    @model_validator(mode='after')
    def shape(self):
        if self.kind != 'ink' and len(self.points) != 2:
            raise ValueError('Deux coins sont requis pour le rectangle')
        if self.kind != 'ink' and (abs(self.points[0].x-self.points[1].x) < .003 or abs(self.points[0].y-self.points[1].y) < .003):
            raise ValueError('Le rectangle est trop petit')
        if self.kind == 'text' and not self.text.strip():
            raise ValueError('Le texte ne peut pas être vide')
        return self


class AnnotationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    base_version_id: str = Field(min_length=1, max_length=36)
    annotations: list[Annotation] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def budget(self):
        if sum(len(a.points) for a in self.annotations) > 20000:
            raise ValueError('Trop de points dans les annotations')
        return self


def version_for(doc, version_id=None):
    version = next((v for v in doc.versions if v.id == version_id), None) if version_id else max(doc.versions, key=lambda v: v.number, default=None)
    if not version:
        raise HTTPException(404, 'Version introuvable')
    if Path(version.original_name).suffix.lower() != '.pdf':
        raise HTTPException(422, 'Ce lecteur est réservé aux PDF')
    return version


def open_pdf(version):
    path = cloud_file(version.disk_name, STORAGE)
    if not path.is_file():
        raise HTTPException(503, 'Fichier indisponible dans le stockage')
    try:
        pdf = fitz.open(path)
        if pdf.needs_pass or not 0 < len(pdf) <= 10000:
            pdf.close()
            raise ValueError('PDF protégé ou vide')
        return pdf
    except Exception as exc:
        raise HTTPException(422, 'Impossible de lire ce PDF. Vérifiez qu’il n’est pas protégé par un mot de passe.') from exc


@router.get('/api/documents/{doc_id}/pdf')
def metadata(doc_id: str, version_id: str | None = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = authorize(db, user, doc_id)
    version = version_for(doc, version_id)
    latest = max(doc.versions, key=lambda v: v.number)
    with open_pdf(version) as pdf:
        return {'document_id': doc.id, 'title': doc.title, 'version_id': version.id,
                'version': version.number, 'latest_version': latest.number,
                'can_write': version.id == latest.id and permitted(user, 'document.write', doc.folder.slug),
                'pages': [{'number': i+1, 'width': p.rect.width, 'height': p.rect.height} for i, p in enumerate(pdf)]}


@router.get('/api/document-versions/{version_id}/pdf-pages/{page_number}')
def page_image(version_id: str, page_number: int, scale: float = Query(default=1.5, ge=.5, le=2),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version:
        raise HTTPException(404, 'Version introuvable')
    doc = authorize(db, user, version.document_id)
    version_for(doc, version_id)
    with open_pdf(version) as pdf:
        if not 1 <= page_number <= len(pdf):
            raise HTTPException(404, 'Page introuvable')
        page = pdf[page_number-1]
        bounded = min(scale, math.sqrt(12_000_000 / max(1, page.rect.width*page.rect.height)), 8192 / max(1, page.rect.width, page.rect.height))
        pix = page.get_pixmap(matrix=fitz.Matrix(bounded, bounded), alpha=False)
        return Response(pix.tobytes('png'), media_type='image/png', headers={'Cache-Control': 'private, no-store'})


def apply_annotations(pdf, annotations, author):
    for a in annotations:
        if a.page > len(pdf):
            raise HTTPException(422, f'Ce PDF contient {len(pdf)} page(s)')
        page = pdf[a.page-1]
        # Browser points refer to the displayed (rotated) page; PDF annotation coordinates do not.
        points = [fitz.Point(p.x*page.rect.width, p.y*page.rect.height)*page.derotation_matrix for p in a.points]
        color = tuple(int(a.color[i:i+2], 16)/255 for i in (1, 3, 5))
        if a.kind == 'ink':
            annotation = page.add_ink_annot([[tuple(p) for p in points]])
            annotation.set_colors(stroke=color)
            annotation.set_border(width=1.5)
        else:
            rect = fitz.Rect(points[0], points[1]).normalize()
            if a.kind == 'highlight':
                visual = fitz.Rect(a.points[0].x*page.rect.width, a.points[0].y*page.rect.height, a.points[1].x*page.rect.width, a.points[1].y*page.rect.height).normalize()
                quad = fitz.Quad([p*page.derotation_matrix for p in (visual.tl, visual.tr, visual.bl, visual.br)])
                annotation = page.add_highlight_annot(quad)
                annotation.set_colors(stroke=(1, .82, .1))
                annotation.set_opacity(.4)
            else:
                # Shrink text until it fits; never silently clip a saved comment.
                text = a.text.strip()
                fontsize = 12
                while fontsize >= 4:
                    layout_rect = fitz.Rect(0, 0, abs(a.points[1].x-a.points[0].x)*page.rect.width, abs(a.points[1].y-a.points[0].y)*page.rect.height)
                    layout = fitz.TextWriter(layout_rect)
                    rest = layout.fill_textbox(layout_rect, text, font=fitz.Font('helv'), fontsize=fontsize, warn=False)
                    if not rest:
                        break
                    fontsize -= .5
                if rest:
                    raise HTTPException(422, 'Ce texte est trop long pour la zone choisie. Agrandissez la zone ou raccourcissez le texte.')
                annotation = page.add_freetext_annot(rect, text, fontsize=fontsize, fontname='helv', text_color=color,
                                                   fill_color=(1, 1, .94), rotate=(360-page.rotation) % 360)
        annotation.set_info(title=author, subject='Annotation Framatex')
        annotation.update()


@router.post('/api/documents/{doc_id}/pdf-annotations', status_code=201)
async def save_annotations(doc_id: str, payload: AnnotationInput,
                           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Same lock as ordinary uploads prevents silent overwrites of another user's version.
    db.scalar(select(Document).where(Document.id == doc_id).with_for_update())
    doc = authorize(db, user, doc_id, write=True)
    db.expire(doc, ['versions'])
    version = version_for(doc, payload.base_version_id)
    if version.id != max(doc.versions, key=lambda v: v.number).id:
        raise HTTPException(409, 'Une nouvelle version existe déjà. Vos annotations restent à l’écran mais ne peuvent pas remplacer la version courante. Conservez vos notes avant de fermer puis rouvrir ce PDF.')
    with open_pdf(version) as pdf:
        apply_annotations(pdf, payload.annotations, user.name)
        output = pdf.tobytes(garbage=4, deflate=True)
    audit(db, user, 'document.pdf.annotate', 'document', doc.id,
          {'base_version_id': version.id, 'count': len(payload.annotations)})
    filename = Path(version.original_name).stem.removesuffix('-annote')+'-annote.pdf'
    upload = UploadFile(file=BytesIO(output), filename=filename)
    return await new_version(doc_id=doc_id, file=upload, user=user, db=db)
