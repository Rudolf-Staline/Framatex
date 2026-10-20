"""Catalogue provisoire de la fiche commande, partagé par les deux formulaires.

Les clés sont stables : renommer un libellé ne modifie aucune donnée enregistrée.
Les informations métier restent facultatives jusqu'à validation par Framatex.
"""
from datetime import date
import json
from pydantic import BaseModel, ConfigDict, Field

ORDER_FIELDS = [
    {"key": "name", "label": "Nom du dossier", "type": "text", "max_length": 180, "required": True, "storage": "base", "placeholder": "Ex. Vestes coton · automne"},
    {"key": "order_ref", "label": "Numéro de commande", "type": "text", "max_length": 100, "storage": "base"},
    {"key": "client_name", "label": "Client", "type": "text", "max_length": 150, "storage": "base"},
    {"key": "workshop", "label": "Atelier", "type": "text", "max_length": 150},
    {"key": "program", "label": "Programme / collection", "type": "text", "max_length": 150},
    {"key": "article_ref", "label": "Référence article / modèle", "type": "text", "max_length": 150},
    {"key": "quantity", "label": "Quantité commandée", "type": "number", "min": 1, "max": 2147483647, "step": 1},
    {"key": "delivery_date", "label": "Date de livraison prévue", "type": "date"},
    {"key": "orli_ref", "label": "Référence ORLI", "type": "text", "max_length": 100, "storage": "base"},
    {"key": "notes", "label": "Observations", "type": "textarea", "max_length": 2000},
]

class OrderIdentification(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    workshop: str | None = Field(default=None, max_length=150)
    program: str | None = Field(default=None, max_length=150)
    article_ref: str | None = Field(default=None, max_length=150)
    quantity: int | None = Field(default=None, strict=True, ge=1, le=2147483647)
    delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


def identification_values(launch):
    return json.loads(launch.identification_json or "{}")


def merge_identification(launch, payload):
    # PATCH is partial; omitted keys (including old retired fields) are retained.
    values = identification_values(launch)
    values.update(payload.model_dump(mode="json", exclude_unset=True))
    launch.identification_json = json.dumps(values, ensure_ascii=False)
