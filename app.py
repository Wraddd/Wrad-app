"""
=============================================================================
                  WRAD - AUTOMOTIVE TINTING STUDIO
       Application de Métrage & Tarification de Film Solaire Automobile
=============================================================================
Auteur : Architecte Logiciel Senior
Technologie : Python 3.9+ | CustomTkinter | Gemini API | Cache JSON Local
Charte Graphique : Identité Officielle Wrad (Noir Carbone & Rouge Course #E10600)
Contact : 07 67 60 10 98 | wradauto@gmail.com | Instagram: @wradauto
=============================================================================
"""

import os
import json
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import urllib.request
import urllib.error
import webbrowser
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import customtkinter as ctk
except ImportError:
    print("ERREUR: customtkinter n'est pas installé. Exécutez: pip install -r requirements.txt")
    raise

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# CODES COULEURS & CHARTE VISUELLE WRAD (PERSONNALISABLES)
# =============================================================================
# Vous pouvez ajuster ici directement les codes HEX pour affiner votre design :
COLOR_BG_DARK = "#09090b"        # Fond principal (Noir Onyx profond)
COLOR_PANEL = "#121215"          # Panneaux de contenu
COLOR_CARD = "#18181c"           # Cartes et conteneurs
COLOR_CARD_HOVER = "#202026"     # Survol des conteneurs
COLOR_BORDER = "#27272a"         # Bordures subtiles
COLOR_RED_WRAD = "#E10600"       # Rouge Wrad officiel (Logo & Flyers)
COLOR_RED_HOVER = "#B91C1C"      # Survol boutons rouges
COLOR_RED_DARK = "#450a0a"       # Fond badges rouges
COLOR_TEXT_WHITE = "#FFFFFF"     # Texte blanc haute lisibilité
COLOR_TEXT_MUTED = "#a1a1aa"     # Texte secondaire gris clair
COLOR_PRICE_GOLD = "#fde047"     # Accent doré pour les prix de vente
COLOR_SUCCESS = "#22c55e"        # Vert bénéfice et validation
COLOR_WARNING = "#ef4444"        # Rouge alerte raccord de laize

# Fichiers locaux
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")
CLIENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clients.json")
ROLLS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rolls.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# Supabase Credentials (synchronisation en temps réel)
SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "https://grnpluqowqgprmqwxify.supabase.co"
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("VITE_SUPABASE_ANON_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdybnBsdXFvd3FncHJtcXd4aWZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI1Nzk5ODksImV4cCI6MjEwODE1NTk4OX0.RyiCSnVA1HDf0RSpVamkFXwaJZbff9RT_GazgdVUwUki"

# Rouleaux par défaut
DEFAULT_ROLLS = [
    {"id": "roll-76-30", "nom": "Rouleau Standard Wrad 76cm (Teinte 15% Black)", "laize_cm": 76.0, "longueur_m": 30.0, "prix_achat_ttc": 188.0, "isDefault": True},
    {"id": "roll-100-30", "nom": "Rouleau Large 100cm (Carbone 5% Limousine)", "laize_cm": 100.0, "longueur_m": 30.0, "prix_achat_ttc": 248.0},
    {"id": "roll-152-30", "nom": "Rouleau Extra-Large 152cm (Nano-Céramique 20%)", "laize_cm": 152.0, "longueur_m": 30.0, "prix_achat_ttc": 365.0},
    {"id": "roll-50-30", "nom": "Rouleau Étroit 50cm (Homologué Avant 70%)", "laize_cm": 50.0, "longueur_m": 30.0, "prix_achat_ttc": 125.0},
]


# =============================================================================
# MOTEUR TECHNIQUE : SENS DU FILM STRICTEMENT HORIZONTAL
# =============================================================================
class StrictHorizontalNestingEngine:
    """
    Règle impérative de pose automobile : Le film s'utilise uniquement à l'horizontale.
    - Hauteur vitre alignée sur la Laize.
    - Largeur vitre alignée sur la Longueur du rouleau.
    - Zéro rotation à 90° autorisée.
    """

    @staticmethod
    def compute(vitres: List[Dict[str, Any]], laize_cm: float = 76.0, marge_cm: float = 5.0):
        active_items = [v for v in vitres if v.get("included", True)]
        if not active_items:
            return {
                "placed": [],
                "unfitted": [],
                "total_linear_cm": 0,
                "total_linear_m": 0.0,
                "surface_used_m2": 0.0,
                "surface_cut_m2": 0.0,
                "efficiency_pct": 0.0,
                "has_seam_warning": False
            }

        candidates = []
        for v in active_items:
            raw_h = float(v["hauteur_cm"])
            raw_w = float(v["largeur_cm"])
            h_laize = max(1.0, raw_h + marge_cm)
            w_roll = max(1.0, raw_w + marge_cm)
            fits = h_laize <= laize_cm
            candidates.append({
                "raw": v,
                "h_laize": h_laize,
                "w_roll": w_roll,
                "fits": fits,
                "exceeds_by": max(0.0, h_laize - laize_cm)
            })

        candidates.sort(key=lambda x: (x["h_laize"], x["w_roll"]), reverse=True)

        stripes = []
        placed = []
        unfitted = []
        has_seam_warning = False

        for c in candidates:
            h_laize = c["h_laize"]
            w_roll = c["w_roll"]
            v = c["raw"]

            if not c["fits"]:
                has_seam_warning = True
                unfitted.append({
                    "nom": v.get("nom", "Vitre"),
                    "zone": v.get("zone", "arriere"),
                    "h_laize": h_laize,
                    "w_roll": w_roll,
                    "exceeds_by": c["exceeds_by"]
                })

                start_y = sum(s["length"] for s in stripes)
                stripes.append({
                    "y": start_y,
                    "length": w_roll,
                    "used_laize": laize_cm
                })

                placed.append({
                    "nom": v.get("nom", "Vitre"),
                    "zone": v.get("zone", "arriere"),
                    "x": 0.0,
                    "y": start_y,
                    "height_on_laize": h_laize,
                    "width_on_roll": w_roll,
                    "raw_h": v["hauteur_cm"],
                    "raw_w": v["largeur_cm"],
                    "fits": False,
                    "exceeds_by": c["exceeds_by"]
                })
                continue

            best_stripe_idx = -1
            min_leftover = float("inf")

            for s_idx, stripe in enumerate(stripes):
                remaining_laize = laize_cm - stripe["used_laize"]
                if remaining_laize >= h_laize:
                    leftover = remaining_laize - h_laize
                    if leftover < min_leftover:
                        min_leftover = leftover
                        best_stripe_idx = s_idx

            if best_stripe_idx != -1:
                stripe = stripes[best_stripe_idx]
                placed.append({
                    "nom": v.get("nom", "Vitre"),
                    "zone": v.get("zone", "arriere"),
                    "x": stripe["used_laize"],
                    "y": stripe["y"],
                    "height_on_laize": h_laize,
                    "width_on_roll": w_roll,
                    "raw_h": v["hauteur_cm"],
                    "raw_w": v["largeur_cm"],
                    "fits": True,
                    "exceeds_by": 0.0
                })
                stripe["used_laize"] += h_laize
                stripe["length"] = max(stripe["length"], w_roll)
            else:
                start_y = sum(s["length"] for s in stripes)
                stripes.append({
                    "y": start_y,
                    "length": w_roll,
                    "used_laize": h_laize
                })
                placed.append({
                    "nom": v.get("nom", "Vitre"),
                    "zone": v.get("zone", "arriere"),
                    "x": 0.0,
                    "y": start_y,
                    "height_on_laize": h_laize,
                    "width_on_roll": w_roll,
                    "raw_h": v["hauteur_cm"],
                    "raw_w": v["largeur_cm"],
                    "fits": True,
                    "exceeds_by": 0.0
                })

        total_linear_cm = sum(s["length"] for s in stripes)
        total_linear_m = round(total_linear_cm / 100.0, 2)
        total_used_cm2 = total_linear_cm * laize_cm
        cut_area_cm2 = sum(p["height_on_laize"] * p["width_on_roll"] for p in placed)
        eff_pct = round((cut_area_cm2 / total_used_cm2 * 100.0), 1) if total_used_cm2 > 0 else 0.0

        return {
            "placed": placed,
            "unfitted": unfitted,
            "total_linear_cm": total_linear_cm,
            "total_linear_m": total_linear_m,
            "surface_used_m2": round(total_used_cm2 / 10000.0, 3),
            "surface_cut_m2": round(cut_area_cm2 / 10000.0, 3),
            "efficiency_pct": eff_pct,
            "has_seam_warning": has_seam_warning
        }


# =============================================================================
# PERSISTANCE HYBRIDE SUPABASE (TEMPS RÉEL) & CACHE LOCAL
# =============================================================================
class PersistenceManager:
    @staticmethod
    def _supabase_request(endpoint: str, method: str = "GET", data: Any = None) -> Optional[Any]:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            return None
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{endpoint}"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates"
        }
        try:
            req_data = json.dumps(data).encode("utf-8") if data is not None else None
            req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=4) as res:
                body = res.read().decode("utf-8")
                return json.loads(body) if body else []
        except Exception:
            return None

    @staticmethod
    def load_database() -> Dict[str, Any]:
        # 1. Tentative Supabase
        supa_res = PersistenceManager._supabase_request("vehicles?select=*")
        if isinstance(supa_res, list) and len(supa_res) > 0:
            db_map = {}
            for v in supa_res:
                k = v.get("key") or v.get("id")
                vitres = v.get("vitres", [])
                if isinstance(vitres, str):
                    try:
                        vitres = json.loads(vitres)
                    except Exception:
                        vitres = []
                db_map[k] = {
                    "marque": v.get("marque", ""),
                    "modele": v.get("modele", ""),
                    "annee": v.get("annee", ""),
                    "generation": v.get("generation", ""),
                    "vitres": vitres
                }
            # Mettre à jour le cache local
            try:
                with open(DATABASE_FILE, "w", encoding="utf-8") as f:
                    json.dump(db_map, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return db_map

        # 2. Fallback cache local database.json
        if os.path.exists(DATABASE_FILE):
            try:
                with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Erreur] Lecture database.json: {e}")
        return {}

    @staticmethod
    def save_database(data: Dict[str, Any]) -> bool:
        # Enregistrement local
        ok_local = False
        try:
            with open(DATABASE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            ok_local = True
        except Exception as e:
            print(f"[Erreur] Écriture database.json: {e}")

        # Synchronisation Supabase en arrière-plan
        try:
            payloads = []
            for k, v in data.items():
                payloads.append({
                    "id": k,
                    "key": k,
                    "marque": v.get("marque", ""),
                    "modele": v.get("modele", ""),
                    "annee": v.get("annee", ""),
                    "generation": v.get("generation", ""),
                    "vitres": v.get("vitres", [])
                })
            if payloads:
                PersistenceManager._supabase_request("vehicles", method="POST", data=payloads)
        except Exception:
            pass

        return ok_local

    @staticmethod
    def load_clients() -> List[Dict[str, Any]]:
        # 1. Tentative Supabase
        supa_res = PersistenceManager._supabase_request("clients?select=*&order=created_at.desc")
        if isinstance(supa_res, list) and len(supa_res) > 0:
            formatted = []
            for c in supa_res:
                formatted.append({
                    "id": str(c.get("id")),
                    "clientNom": c.get("clientNom") or c.get("client_nom") or "Client",
                    "vehicule": c.get("vehicule", ""),
                    "datePose": c.get("datePose") or c.get("date_pose") or "",
                    "pack": c.get("pack", ""),
                    "metrageUtiliseM": float(c.get("metrageUtiliseM") or c.get("metrage_utilise_m") or 0),
                    "prixFactureTTC": float(c.get("prixFactureTTC") or c.get("prix_facture_ttc") or 0),
                    "coutRevientTTC": float(c.get("coutRevientTTC") or c.get("cout_revient_ttc") or 0),
                    "beneficeNetTTC": float(c.get("beneficeNetTTC") or c.get("benefice_net_ttc") or 0),
                    "tauxMargePercent": float(c.get("tauxMargePercent") or c.get("taux_marge_percent") or 0),
                })
            try:
                with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(formatted, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return formatted

        # 2. Fallback clients.json
        if os.path.exists(CLIENTS_FILE):
            try:
                with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Erreur] Lecture clients.json: {e}")
        return []

    @staticmethod
    def save_clients(data: List[Dict[str, Any]]) -> bool:
        ok_local = False
        try:
            with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            ok_local = True
        except Exception as e:
            print(f"[Erreur] Écriture clients.json: {e}")

        # Synchronisation Supabase
        try:
            if data:
                payloads = []
                for c in data:
                    payloads.append({
                        "id": str(c.get("id")),
                        "clientNom": c.get("clientNom"),
                        "client_nom": c.get("clientNom"),
                        "vehicule": c.get("vehicule"),
                        "datePose": c.get("datePose"),
                        "date_pose": c.get("datePose"),
                        "pack": c.get("pack"),
                        "metrageUtiliseM": c.get("metrageUtiliseM"),
                        "metrage_utilise_m": c.get("metrageUtiliseM"),
                        "prixFactureTTC": c.get("prixFactureTTC"),
                        "prix_facture_ttc": c.get("prixFactureTTC"),
                        "coutRevientTTC": c.get("coutRevientTTC"),
                        "cout_revient_ttc": c.get("coutRevientTTC"),
                        "beneficeNetTTC": c.get("beneficeNetTTC"),
                        "benefice_net_ttc": c.get("beneficeNetTTC"),
                        "tauxMargePercent": c.get("tauxMargePercent"),
                        "taux_marge_percent": c.get("tauxMargePercent")
                    })
                PersistenceManager._supabase_request("clients", method="POST", data=payloads)
        except Exception:
            pass

        return ok_local

    @staticmethod
    def load_rolls() -> List[Dict[str, Any]]:
        supa_res = PersistenceManager._supabase_request("rolls?select=*")
        if isinstance(supa_res, list) and len(supa_res) > 0:
            formatted = []
            for r in supa_res:
                formatted.append({
                    "id": str(r.get("id")),
                    "nom": str(r.get("nom")),
                    "laize_cm": float(r.get("laize_cm")),
                    "longueur_m": float(r.get("longueur_m")),
                    "prix_achat_ttc": float(r.get("prix_achat_ttc")),
                    "isDefault": bool(r.get("isDefault", False) or r.get("is_default", False))
                })
            try:
                with open(ROLLS_FILE, "w", encoding="utf-8") as f:
                    json.dump(formatted, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return formatted

        if os.path.exists(ROLLS_FILE):
            try:
                with open(ROLLS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                print(f"[Erreur] Lecture rolls.json: {e}")
        return list(DEFAULT_ROLLS)

    @staticmethod
    def save_rolls(data: List[Dict[str, Any]]) -> bool:
        ok_local = False
        try:
            with open(ROLLS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            ok_local = True
        except Exception as e:
            print(f"[Erreur] Écriture rolls.json: {e}")

        try:
            if data:
                payloads = []
                for r in data:
                    payloads.append({
                        "id": str(r.get("id")),
                        "nom": str(r.get("nom")),
                        "laize_cm": float(r.get("laize_cm")),
                        "longueur_m": float(r.get("longueur_m")),
                        "prix_achat_ttc": float(r.get("prix_achat_ttc")),
                        "isDefault": bool(r.get("isDefault", False)),
                        "is_default": bool(r.get("isDefault", False))
                    })
                PersistenceManager._supabase_request("rolls", method="POST", data=payloads)
        except Exception:
            pass

        return ok_local


# =============================================================================
# ESTIMATION IA GEMINI
# =============================================================================
class GeminiEstimator:
    @staticmethod
    def estimate(marque: str, modele: str, annee: str = "") -> Dict[str, Any]:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Clé API absente. Mode local actif.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        system_instruction = (
            "Tu es un métreur automobile expert en pose de films solaires pour 'Wrad'.\n"
            "RÈGLES STRICTES :\n"
            "1. AUCUN PARE-BRISE ne doit être inclus.\n"
            "2. Liste toutes les vitres (Lunette arrière, vitres latérales arrière, custodes arrière, vitres avant, custodes avant).\n"
            "3. Règle technique : la hauteur s'aligne sur la laize et la largeur sur la longueur.\n"
            "4. Format JSON pur obligatoire :\n"
            '{"generation": "string", "vitres": [{"nom": "string", "hauteur_cm": int, "largeur_cm": int, "zone": "avant" | "arriere"}]}'
        )

        prompt = f"Véhicule : {marque} {modele} {annee or 'récent'}. Dimensions réelles nettes en cm."
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            raw_text = res_json.get("candidates", [])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = json.loads(raw_text)
            vitres = parsed.get("vitres", [])
            clean_vitres = []
            for v in vitres:
                zone = "avant" if "av" in str(v.get("zone", "")).lower() else "arriere"
                clean_vitres.append({
                    "nom": str(v.get("nom", "Vitre")),
                    "hauteur_cm": int(v.get("hauteur_cm", 45)),
                    "largeur_cm": int(v.get("largeur_cm", 60)),
                    "zone": zone,
                    "included": True
                })
            return {"generation": parsed.get("generation", "Estimé par IA"), "vitres": clean_vitres}



# =============================================================================
# GÉNÉRATEUR DE DEVIS PDF ÉPURÉ & PROFESSIONNEL (WRAD)
# =============================================================================
class WradPDFGenerator:
    """
    Générateur de devis PDF épuré pour l'atelier Wrad.
    Suppression stricte des éléments superflus :
    - Aucun slogan 'automotive tinting'
    - Aucune description 'pose de films solaire haut de gamme & sécurité automobile'
    - Aucun bloc argumentaire (Esthétique, Confort thermique, Intimité, Protection 99% UV)
    - Aucun bloc 'Engagements & Réglementations'
    - Aucune mention 'Validité de l'offre'
    Concentré uniquement sur l'essentiel : en-tête Wrad, coordonnées, véhicule,
    tableau des prestations avec métrages et totaux financiers.
    """

    @staticmethod
    def generate_pdf(
        filepath: str,
        devis_num: str,
        date_str: str,
        vehicule: Dict[str, Any],
        prestation_title: str,
        prestation_desc: str,
        metrage_m: float,
        prix_ttc: float,
        roll_nom: str = "",
        laize_cm: float = 76.0,
        client_nom: str = ""
    ) -> bool:
        """
        Génère un fichier PDF natif vectoriel via ReportLab si disponible.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm

            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm
            )

            styles = getSampleStyleSheet()
            red_wrad = colors.HexColor("#E10600")
            dark_bg = colors.HexColor("#121215")
            light_gray = colors.HexColor("#F4F4F5")
            border_gray = colors.HexColor("#E4E4E7")
            text_dark = colors.HexColor("#18181B")
            text_muted = colors.HexColor("#71717A")

            # Styles personnalisés épurés
            title_style = ParagraphStyle(
                'WradTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=26,
                leading=30,
                textColor=colors.black
            )
            contact_style = ParagraphStyle(
                'WradContact',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=13,
                textColor=text_muted
            )
            meta_right_style = ParagraphStyle(
                'WradMetaRight',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=11,
                leading=15,
                alignment=2,
                textColor=red_wrad
            )
            meta_date_style = ParagraphStyle(
                'WradMetaDate',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=13,
                alignment=2,
                textColor=text_muted
            )
            section_title = ParagraphStyle(
                'WradSection',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=10,
                leading=14,
                textColor=text_dark,
                spaceAfter=4
            )
            table_header = ParagraphStyle(
                'WradTH',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=9,
                leading=12,
                textColor=colors.white
            )
            table_cell = ParagraphStyle(
                'WradTD',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=12,
                textColor=text_dark
            )
            table_cell_bold = ParagraphStyle(
                'WradTDBold',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=9,
                leading=12,
                textColor=text_dark
            )
            table_cell_price = ParagraphStyle(
                'WradTDPrice',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=10,
                leading=13,
                alignment=2,
                textColor=red_wrad
            )

            story = []

            # 1. EN-TÊTE ÉPURÉ DE L'ENTREPRISE & COORDONNÉES
            # (Strictement sans slogan 'automotive tinting', sans description commerciale, sans validité de l'offre)
            header_data = [
                [
                    Paragraph("<b>WRAD</b>", title_style),
                    Paragraph(f"DEVIS N° {devis_num}", meta_right_style)
                ],
                [
                    Paragraph(
                        "Atelier Wrad • Poitiers &amp; alentours (Atelier ou Domicile)<br/>"
                        "Tél : 07 67 60 10 98 • Email : wradauto@gmail.com • Instagram : @wradauto",
                        contact_style
                    ),
                    Paragraph(f"Date : {date_str}", meta_date_style)
                ]
            ]
            t_header = Table(header_data, colWidths=[10 * cm, 7 * cm])
            t_header.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(t_header)
            story.append(Spacer(1, 15))
            story.append(HRFlowable(width="100%", thickness=1, color=border_gray, spaceAfter=15))

            # 2. VÉHICULE CONCERNÉ & CLIENT
            marque = vehicule.get('marque', '')
            modele = vehicule.get('modele', '')
            annee = vehicule.get('annee', '')
            gen = vehicule.get('generation', '')
            veh_str = f"<b>{marque} {modele}</b>" + (f" ({annee})" if annee else "")
            if gen and gen != "Estimé par IA":
                veh_str += f"<br/><font color='#71717A' size='8'>{gen}</font>"

            client_str = f"<b>{client_nom}</b>" if client_nom else "Client Particulier / Professionnel"

            info_data = [
                [
                    Paragraph("<b>COORDONNÉES CLIENT</b>", section_title),
                    Paragraph("<b>VÉHICULE CONCERNÉ</b>", section_title)
                ],
                [
                    Paragraph(f"{client_str}<br/><font color='#71717A'>Pose de films solaires</font>", table_cell),
                    Paragraph(veh_str, table_cell)
                ]
            ]
            if roll_nom:
                info_data.append([
                    Paragraph("", table_cell),
                    Paragraph(f"<font color='#71717A' size='8'>Film : {roll_nom} (Laize {laize_cm:.0f} cm)</font>", table_cell)
                ])

            t_info = Table(info_data, colWidths=[8.5 * cm, 8.5 * cm])
            t_info.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), light_gray),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, border_gray),
            ]))
            story.append(t_info)
            story.append(Spacer(1, 20))

            # 3. TABLEAU DES PRESTATIONS ET MÉTRAGES (CONCENTRÉ SUR L'ESSENTIEL)
            story.append(Paragraph("<b>PRESTATION &amp; TARIFICATION</b>", section_title))

            table_content = [
                [
                    Paragraph("Prestation", table_header),
                    Paragraph("Détails des vitres incluses", table_header),
                    Paragraph("Métrage", table_header),
                    Paragraph("Tarif TTC", table_header)
                ],
                [
                    Paragraph(prestation_title, table_cell_bold),
                    Paragraph(prestation_desc, table_cell),
                    Paragraph(f"{metrage_m:.2f} m", table_cell),
                    Paragraph(f"<b>{prix_ttc:.2f} €</b>", table_cell_price)
                ],
                [
                    Paragraph("<b>TOTAL CONSEILLÉ TTC</b>", table_cell_bold),
                    Paragraph("", table_cell),
                    Paragraph(f"<b>{metrage_m:.2f} m</b>", table_cell_bold),
                    Paragraph(f"<b>{prix_ttc:.2f} € TTC</b>", table_cell_price)
                ]
            ]

            t_presta = Table(table_content, colWidths=[4.5 * cm, 7.5 * cm, 2.5 * cm, 2.5 * cm])
            t_presta.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), dark_bg),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, 1), 0.5, border_gray),
                ('BACKGROUND', (0, 2), (-1, 2), light_gray),
                ('LINEABOVE', (0, 2), (-1, 2), 1.5, dark_bg),
                ('GRID', (0, 2), (-1, 2), 0.5, border_gray),
            ]))
            story.append(t_presta)
            story.append(Spacer(1, 30))

            # 4. BAS DE PAGE ÉPURÉ
            story.append(HRFlowable(width="100%", thickness=0.5, color=border_gray, spaceAfter=8))
            footer_text = Paragraph(
                "<font color='#71717A' size='8'>Atelier WRAD • Poitiers &amp; alentours • 07 67 60 10 98 • wradauto@gmail.com • Devis professionnel épuré</font>",
                ParagraphStyle('Footer', alignment=1, fontName='Helvetica', fontSize=8)
            )
            story.append(footer_text)

            doc.build(story)
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"[Erreur ReportLab PDF] {e}")
            return False

    @staticmethod
    def generate_html_print_version(
        filepath: str,
        devis_num: str,
        date_str: str,
        vehicule: Dict[str, Any],
        prestation_title: str,
        prestation_desc: str,
        metrage_m: float,
        prix_ttc: float,
        roll_nom: str = "",
        laize_cm: float = 76.0,
        client_nom: str = ""
    ) -> bool:
        """
        Génère une page HTML épurée avec CSS @media print optimisé
        permettant d'imprimer ou d'enregistrer en PDF directement depuis le navigateur.
        """
        marque = vehicule.get('marque', '')
        modele = vehicule.get('modele', '')
        annee = vehicule.get('annee', '')
        gen = vehicule.get('generation', '')
        veh_full = f"{marque} {modele}" + (f" ({annee})" if annee else "")

        html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Devis {devis_num} - WRAD</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    body {{
      background: #f4f4f5;
      padding: 30px;
      color: #18181b;
    }}
    .sheet {{
      background: #ffffff;
      max-width: 800px;
      margin: 0 auto;
      padding: 40px;
      border-radius: 8px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.06);
    }}
    @media print {{
      body {{
        background: transparent;
        padding: 0;
      }}
      .sheet {{
        box-shadow: none;
        padding: 0;
        border-radius: 0;
      }}
      .no-print {{
        display: none !important;
      }}
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid #e4e4e7;
      padding-bottom: 20px;
      margin-bottom: 25px;
    }}
    .brand-title {{
      font-size: 28px;
      font-weight: 900;
      letter-spacing: -0.5px;
      color: #09090b;
    }}
    .contact-info {{
      font-size: 12px;
      color: #71717a;
      margin-top: 6px;
      line-height: 1.5;
    }}
    .devis-meta {{
      text-align: right;
    }}
    .devis-number {{
      font-size: 14px;
      font-weight: 800;
      color: #E10600;
      font-family: monospace;
    }}
    .devis-date {{
      font-size: 12px;
      color: #71717a;
      margin-top: 4px;
    }}
    .card-info {{
      background: #fafafa;
      border: 1px solid #e4e4e7;
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 25px;
      display: flex;
      justify-content: space-between;
    }}
    .info-col-title {{
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 700;
      color: #71717a;
      margin-bottom: 4px;
    }}
    .info-col-val {{
      font-size: 15px;
      font-weight: 700;
      color: #18181b;
    }}
    .info-col-sub {{
      font-size: 12px;
      color: #71717a;
      margin-top: 2px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 25px;
      font-size: 13px;
    }}
    th {{
      background: #18181b;
      color: #ffffff;
      text-align: left;
      padding: 10px 14px;
      font-weight: 700;
    }}
    td {{
      padding: 12px 14px;
      border-bottom: 1px solid #e4e4e7;
      color: #27272a;
    }}
    .td-price {{
      text-align: right;
      font-weight: 800;
      color: #E10600;
      font-family: monospace;
      font-size: 14px;
    }}
    .td-center {{
      text-align: center;
      font-family: monospace;
    }}
    tfoot td {{
      background: #f4f4f5;
      border-top: 2px solid #18181b;
      font-weight: 800;
      font-size: 14px;
      color: #09090b;
    }}
    .footer {{
      border-top: 1px solid #e4e4e7;
      padding-top: 15px;
      text-align: center;
      font-size: 11px;
      color: #a1a1aa;
    }}
    .btn-print {{
      background: #E10600;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-weight: bold;
      cursor: pointer;
      font-size: 14px;
      margin-bottom: 20px;
    }}
  </style>
</head>
<body>
  <div class="no-print" style="max-width: 800px; margin: 0 auto 10px; display: flex; justify-content: flex-end;">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimer ou Enregistrer en PDF</button>
  </div>
  <div class="sheet">
    <div class="header">
      <div>
        <div class="brand-title">WRAD</div>
        <div class="contact-info">
          Atelier Wrad • Poitiers &amp; alentours (Atelier ou Domicile)<br>
          Tél : 07 67 60 10 98 • Email : wradauto@gmail.com • Instagram : @wradauto
        </div>
      </div>
      <div class="devis-meta">
        <div class="devis-number">DEVIS N° {devis_num}</div>
        <div class="devis-date">Date : {date_str}</div>
      </div>
    </div>

    <div class="card-info">
      <div>
        <div class="info-col-title">Véhicule concerné</div>
        <div class="info-col-val">{veh_full}</div>
        {f'<div class="info-col-sub">{gen}</div>' if gen else ''}
        {f'<div class="info-col-sub" style="margin-top: 4px;">Film : {roll_nom} (Laize {laize_cm:.0f} cm)</div>' if roll_nom else ''}
      </div>
      <div style="text-align: right;">
        <div class="info-col-title">Client</div>
        <div class="info-col-val">{client_nom or 'Client Particulier / Professionnel'}</div>
        <div class="info-col-sub">Pose de films solaires</div>
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th>Prestation</th>
          <th>Détails inclus</th>
          <th style="text-align: center;">Métrage estimé</th>
          <th style="text-align: right;">Tarif TTC</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="font-weight: 700; color: #E10600;">{prestation_title}</td>
          <td style="color: #52525b;">{prestation_desc}</td>
          <td class="td-center">{metrage_m:.2f} m</td>
          <td class="td-price">{prix_ttc:.2f} €</td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colspan="2">TOTAL CONSEILLÉ TTC</td>
          <td class="td-center" style="color: #E10600;">{metrage_m:.2f} m</td>
          <td class="td-price" style="font-size: 16px;">{prix_ttc:.2f} € TTC</td>
        </tr>
      </tfoot>
    </table>

    <div class="footer">
      Atelier WRAD • Poitiers &amp; alentours • 07 67 60 10 98 • Devis épuré professionnel
    </div>
  </div>
</body>
</html>
"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            return True
        except Exception as e:
            print(f"[Erreur Écriture HTML Devis] {e}")
            return False


# =============================================================================
# APPLICATION PRINCIPALE CUSTOMTKINTER - STYLE WRAD NOIR & ROUGE
# =============================================================================
class WradTintStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WRAD - Tint Studio | Métrage & Rentabilité")
        self.geometry("1360x900")
        self.minsize(1100, 750)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Configuration des couleurs de l'application
        self.configure(fg_color=COLOR_BG_DARK)

        # Données des rouleaux
        self.rolls = PersistenceManager.load_rolls()
        self.active_roll_idx = 0
        self.coeff_prix = 2.0
        self.marge_coupe = 5.0

        # Données calcul en cours
        self.vitres_data: List[Dict[str, Any]] = []
        self.current_vehicle_info = {"marque": "", "modele": "", "annee": "", "generation": ""}

        # Initialisation UI
        self.setup_ui()
        self.load_initial_vehicle()

    def get_active_roll(self) -> Dict[str, Any]:
        if 0 <= self.active_roll_idx < len(self.rolls):
            return self.rolls[self.active_roll_idx]
        return self.rolls[0]

    # -------------------------------------------------------------------------
    # 1. INTERFACE PRINCIPALE
    # -------------------------------------------------------------------------
    def setup_ui(self):
        # Header avec Logo Wrad et Contrôles Rouleaux
        self.create_header()

        # Onglets Métier Wrad
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLOR_PANEL,
            segmented_button_selected_color=COLOR_RED_WRAD,
            segmented_button_selected_hover_color=COLOR_RED_HOVER,
            segmented_button_unselected_color=COLOR_CARD,
            segmented_button_unselected_hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_WHITE
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(4, 15))

        self.tab_estimator = self.tabview.add("⚡ 1. Estimateur & Découpe Horizontale")
        self.tab_database = self.tabview.add("📁 2. Base de Données Véhicules")
        self.tab_clients = self.tabview.add("💼 3. Suivi Clients & Rentabilité")

        self.setup_estimator_tab(self.tab_estimator)
        self.setup_database_tab(self.tab_database)
        self.setup_clients_tab(self.tab_clients)

    # -------------------------------------------------------------------------
    # 2. EN-TÊTE GRAPHIQUE WRAD
    # -------------------------------------------------------------------------
    def create_header(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        header.pack(fill="x", padx=20, pady=(12, 6))

        # Logo et Identité Wrad
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=15, pady=8)

        badge_wrad = ctk.CTkLabel(left, text="WRAD", font=ctk.CTkFont(family="Arial", size=24, weight="bold"), text_color=COLOR_TEXT_WHITE)
        badge_wrad.pack(side="left", padx=(0, 8))

        sub_tint = ctk.CTkLabel(
            left,
            text="TINT STUDIO",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_RED_WRAD,
            fg_color=COLOR_RED_DARK,
            corner_radius=4,
            padx=6,
            pady=2
        )
        sub_tint.pack(side="left", padx=(0, 12))

        contact_tag = ctk.CTkLabel(
            left,
            text="Poitiers & alentours • Tél: 07 67 60 10 98 • @wradauto",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_MUTED
        )
        contact_tag.pack(side="left")

        # Contrôles Rouleaux & Coefficients
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=15, pady=6)

        ctk.CTkLabel(right, text="Rouleau actif :", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=4)

        self.combo_rolls = ctk.CTkOptionMenu(
            right,
            values=[r["nom"] for r in self.rolls],
            command=self.on_roll_selected,
            width=240,
            fg_color=COLOR_CARD,
            button_color=COLOR_RED_WRAD,
            button_hover_color=COLOR_RED_HOVER,
            dropdown_fg_color=COLOR_PANEL,
            text_color=COLOR_TEXT_WHITE
        )
        self.combo_rolls.pack(side="left", padx=4)

        # Bouton Gérer les Rouleaux (Renommer & Ajouter)
        btn_manage_rolls = ctk.CTkButton(
            right,
            text="⚙️ Gérer Rouleaux",
            width=110,
            height=28,
            fg_color=COLOR_CARD,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_RED_WRAD,
            text_color=COLOR_TEXT_WHITE,
            command=self.open_manage_rolls_dialog
        )
        btn_manage_rolls.pack(side="left", padx=4)

        # Prix rouleau
        ctk.CTkLabel(right, text="Prix (€) :", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(8, 2))
        self.entry_roll_price = ctk.CTkEntry(right, width=65, height=26, justify="center", fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER)
        self.entry_roll_price.insert(0, str(self.get_active_roll()["prix_achat_ttc"]))
        self.entry_roll_price.pack(side="left", padx=2)
        self.entry_roll_price.bind("<KeyRelease>", lambda e: self.on_price_or_coeff_changed())

        # Coefficient
        ctk.CTkLabel(right, text="Coeff (x) :", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(8, 2))
        self.entry_coeff = ctk.CTkEntry(right, width=50, height=26, justify="center", fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER)
        self.entry_coeff.insert(0, str(self.coeff_prix))
        self.entry_coeff.pack(side="left", padx=2)
        self.entry_coeff.bind("<KeyRelease>", lambda e: self.on_price_or_coeff_changed())

    def on_roll_selected(self, choice):
        for idx, r in enumerate(self.rolls):
            if r["nom"] == choice:
                self.active_roll_idx = idx
                self.entry_roll_price.delete(0, tk.END)
                self.entry_roll_price.insert(0, str(r["prix_achat_ttc"]))
                break
        self.recalculate_all()

    def on_price_or_coeff_changed(self):
        try:
            p = float(self.entry_roll_price.get())
            c = float(self.entry_coeff.get())
            self.rolls[self.active_roll_idx]["prix_achat_ttc"] = p
            self.coeff_prix = c
            PersistenceManager.save_rolls(self.rolls)
            self.recalculate_all()
        except ValueError:
            pass

    # -------------------------------------------------------------------------
    # GESTIONNAIRE COMPLET DES ROULEAUX (RENOMMER & AJOUTER MANUELLEMENT)
    # -------------------------------------------------------------------------
    def open_manage_rolls_dialog(self):
        d = ctk.CTkToplevel(self)
        d.title("Gestion & Renommage des Rouleaux Wrad")
        d.geometry("680x520")
        d.configure(fg_color=COLOR_BG_DARK)
        d.transient(self)

        ctk.CTkLabel(d, text="Personnalisation des Rouleaux de Film", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(pady=(12, 4))
        ctk.CTkLabel(d, text="Modifiez le nom de chaque rouleau ou ajoutez de nouveaux formats (Laize, Longueur, Prix)", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(pady=(0, 10))

        # Liste des rouleaux existants
        sc = ctk.CTkScrollableFrame(d, fg_color=COLOR_PANEL, height=220, border_width=1, border_color=COLOR_BORDER)
        sc.pack(fill="x", padx=20, pady=5)

        roll_entries = []
        for idx, r in enumerate(self.rolls):
            row = ctk.CTkFrame(sc, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_BORDER)
            row.pack(fill="x", pady=2, padx=4)

            # Nom modifiable
            en_nom = ctk.CTkEntry(row, width=220, fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER, font=ctk.CTkFont(size=11, weight="bold"))
            en_nom.insert(0, r["nom"])
            en_nom.pack(side="left", padx=4, pady=4)

            # Laize
            ctk.CTkLabel(row, text="Lz:", font=ctk.CTkFont(size=10)).pack(side="left")
            en_lz = ctk.CTkEntry(row, width=45, justify="center", fg_color=COLOR_BG_DARK)
            en_lz.insert(0, str(int(r["laize_cm"])))
            en_lz.pack(side="left", padx=2)

            # Longueur
            ctk.CTkLabel(row, text="Lg:", font=ctk.CTkFont(size=10)).pack(side="left")
            en_lg = ctk.CTkEntry(row, width=40, justify="center", fg_color=COLOR_BG_DARK)
            en_lg.insert(0, str(int(r["longueur_m"])))
            en_lg.pack(side="left", padx=2)

            # Prix
            ctk.CTkLabel(row, text="€:", font=ctk.CTkFont(size=10)).pack(side="left")
            en_px = ctk.CTkEntry(row, width=55, justify="center", fg_color=COLOR_BG_DARK, text_color=COLOR_PRICE_GOLD)
            en_px.insert(0, str(r["prix_achat_ttc"]))
            en_px.pack(side="left", padx=2)

            roll_entries.append({"id": r.get("id", f"r-{idx}"), "en_nom": en_nom, "en_lz": en_lz, "en_lg": en_lg, "en_px": en_px, "isDefault": r.get("isDefault", False)})

        # Formulaire d'ajout d'un nouveau rouleau
        f_add = ctk.CTkFrame(d, fg_color=COLOR_PANEL, border_width=1, border_color=COLOR_BORDER)
        f_add.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(f_add, text="+ Ajouter un Nouveau Rouleau", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_RED_WRAD).pack(anchor="w", padx=10, pady=(6, 4))
        grid_add = ctk.CTkFrame(f_add, fg_color="transparent")
        grid_add.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(grid_add, text="Nom / Réf :", font=ctk.CTkFont(size=10)).grid(row=0, column=0, sticky="w")
        new_nom = ctk.CTkEntry(grid_add, width=180, placeholder_text="Ex: Teinte 5% Carbone")
        new_nom.grid(row=0, column=1, padx=4, pady=2)

        ctk.CTkLabel(grid_add, text="Laize (cm) :", font=ctk.CTkFont(size=10)).grid(row=0, column=2, sticky="w")
        new_lz = ctk.CTkEntry(grid_add, width=60, justify="center")
        new_lz.insert(0, "76")
        new_lz.grid(row=0, column=3, padx=4, pady=2)

        ctk.CTkLabel(grid_add, text="Longueur (m) :", font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky="w")
        new_lg = ctk.CTkEntry(grid_add, width=180, justify="center")
        new_lg.insert(0, "30")
        new_lg.grid(row=1, column=1, padx=4, pady=2)

        ctk.CTkLabel(grid_add, text="Prix TTC (€) :", font=ctk.CTkFont(size=10)).grid(row=1, column=2, sticky="w")
        new_px = ctk.CTkEntry(grid_add, width=60, justify="center")
        new_px.insert(0, "188")
        new_px.grid(row=1, column=3, padx=4, pady=2)

        def save_all_changes():
            updated = []
            for item in roll_entries:
                try:
                    updated.append({
                        "id": item["id"],
                        "nom": item["en_nom"].get().strip() or "Rouleau",
                        "laize_cm": float(item["en_lz"].get()),
                        "longueur_m": float(item["en_lg"].get()),
                        "prix_achat_ttc": float(item["en_px"].get()),
                        "isDefault": item["isDefault"]
                    })
                except ValueError:
                    pass

            # Ajout si nouveau rouleau rempli
            if new_nom.get().strip():
                try:
                    updated.append({
                        "id": f"roll-{len(updated)+1}",
                        "nom": new_nom.get().strip(),
                        "laize_cm": float(new_lz.get()),
                        "longueur_m": float(new_lg.get()),
                        "prix_achat_ttc": float(new_px.get()),
                    })
                except ValueError:
                    pass

            if updated:
                self.rolls = updated
                PersistenceManager.save_rolls(self.rolls)
                names = [r["nom"] for r in self.rolls]
                self.combo_rolls.configure(values=names)
                if self.active_roll_idx >= len(self.rolls):
                    self.active_roll_idx = 0
                self.combo_rolls.set(self.rolls[self.active_roll_idx]["nom"])
                self.entry_roll_price.delete(0, tk.END)
                self.entry_roll_price.insert(0, str(self.rolls[self.active_roll_idx]["prix_achat_ttc"]))
                self.recalculate_all()
                d.destroy()
                messagebox.showinfo("Succès", "Liste des rouleaux mise à jour avec succès !")

        btn_save = ctk.CTkButton(
            d,
            text="Enregistrer les modifications",
            fg_color=COLOR_RED_WRAD,
            hover_color=COLOR_RED_HOVER,
            command=save_all_changes
        )
        btn_save.pack(pady=10)

    # -------------------------------------------------------------------------
    # 3. ONGLET 1 : ESTIMATEUR & PLAN DE COUPE
    # -------------------------------------------------------------------------
    def setup_estimator_tab(self, parent):
        s_bar = ctk.CTkFrame(parent, fg_color=COLOR_PANEL, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        s_bar.pack(fill="x", padx=10, pady=(10, 8))

        ctk.CTkLabel(s_bar, text="Marque :", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4))
        self.entry_est_marque = ctk.CTkEntry(s_bar, width=120, fg_color=COLOR_BG_DARK)
        self.entry_est_marque.pack(side="left", padx=3)

        ctk.CTkLabel(s_bar, text="Modèle :", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(8, 4))
        self.entry_est_modele = ctk.CTkEntry(s_bar, width=130, fg_color=COLOR_BG_DARK)
        self.entry_est_modele.pack(side="left", padx=3)

        ctk.CTkLabel(s_bar, text="Année :", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(8, 4))
        self.entry_est_annee = ctk.CTkEntry(s_bar, width=75, fg_color=COLOR_BG_DARK)
        self.entry_est_annee.pack(side="left", padx=3)

        btn_run = ctk.CTkButton(
            s_bar,
            text="⚡ Estimer",
            fg_color=COLOR_RED_WRAD,
            hover_color=COLOR_RED_HOVER,
            text_color=COLOR_TEXT_WHITE,
            width=90,
            command=self.on_estimate_clicked
        )
        btn_run.pack(side="left", padx=8)

        self.combo_est_presets = ctk.CTkOptionMenu(
            s_bar,
            values=["Peugeot 208 (2020)", "Volkswagen Golf 8 (2021)", "Tesla Model 3 (2022)", "Renault Clio (2021)", "BMW Série 3 (2021)"],
            command=self.on_est_preset_selected,
            width=180,
            fg_color=COLOR_CARD,
            button_color=COLOR_RED_WRAD,
            button_hover_color=COLOR_RED_HOVER
        )
        self.combo_est_presets.pack(side="left", padx=5)

        self.lbl_est_status = ctk.CTkLabel(s_bar, text="Prêt", text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_est_status.pack(side="right", padx=12)

        # Split conteneur
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        # Colonne Gauche : Dimensions
        left_col = ctk.CTkFrame(split, fg_color=COLOR_PANEL, width=520, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6))

        top_vitres = ctk.CTkFrame(left_col, fg_color="transparent")
        top_vitres.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(top_vitres, text="📋 Vitres du Véhicule (Cotes Nettes en cm)", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        ctk.CTkButton(
            top_vitres,
            text="+ Ajouter une vitre",
            width=120,
            height=26,
            fg_color=COLOR_CARD,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_RED_WRAD,
            command=self.add_manual_vitre_row
        ).pack(side="right")

        # Entêtes
        hdr = ctk.CTkFrame(left_col, fg_color=COLOR_CARD, height=24)
        hdr.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(hdr, text="Inc.", width=30, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(hdr, text="Nom vitre", width=180, anchor="w", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=4)
        ctk.CTkLabel(hdr, text="H (cm)", width=65, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="L (cm)", width=65, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Zone", width=80, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=2)

        self.scroll_vitres = ctk.CTkScrollableFrame(left_col, fg_color="transparent")
        self.scroll_vitres.pack(fill="both", expand=True, padx=6, pady=4)

        # Colonne Droite : Cartes financières avec bouton "Devis" INDÉPENDANT par pack
        right_col = ctk.CTkFrame(split, fg_color="transparent", width=580)
        right_col.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # 3 Cartes de prestations avec boutons devis individuels
        self.card_arriere = self.create_pack_card_with_quote(right_col, "PACK 3/4 ARRIÈRE", "arriere")
        self.card_avant = self.create_pack_card_with_quote(right_col, "PACK VITRES AVANT", "avant")
        self.card_total = self.create_pack_card_with_quote(right_col, "TOTAL VÉHICULE COMPLET", "total", is_total=True)

        # Plan de coupe Canvas
        cv_frame = ctk.CTkFrame(right_col, fg_color="#09090b", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        cv_frame.pack(fill="both", expand=True, pady=(6, 0))

        cv_hdr = ctk.CTkFrame(cv_frame, fg_color="transparent")
        cv_hdr.pack(fill="x", padx=10, pady=(6, 2))
        self.lbl_canvas_info = ctk.CTkLabel(cv_hdr, text="Plan de coupe (Sens horizontal strict - Sans rotation 90°)", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_RED_WRAD)
        self.lbl_canvas_info.pack(side="left")

        self.canvas_est = tk.Canvas(cv_frame, bg="#09090b", highlightthickness=0)
        self.canvas_est.pack(fill="both", expand=True, padx=8, pady=6)

    def create_pack_card_with_quote(self, parent, title, pack_key, is_total=False):
        f = ctk.CTkFrame(
            parent,
            fg_color=COLOR_PANEL if not is_total else "#1c1414",
            corner_radius=8,
            border_width=1,
            border_color=COLOR_RED_WRAD if is_total else COLOR_BORDER
        )
        f.pack(fill="x", pady=2.5)

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=5)

        t_lbl = ctk.CTkLabel(row, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_RED_WRAD if is_total else COLOR_TEXT_WHITE, width=160, anchor="w")
        t_lbl.pack(side="left")

        val_m = ctk.CTkLabel(row, text="0.00 m", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_WHITE, width=65)
        val_m.pack(side="left", padx=2)

        val_c = ctk.CTkLabel(row, text="Coût: 0.00 €", font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED, width=85)
        val_c.pack(side="left", padx=2)

        val_p = ctk.CTkLabel(row, text="0.00 €", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_PRICE_GOLD, width=75)
        val_p.pack(side="left", padx=4)

        # BOUTON "GÉNÉRER DEVIS" DÉDIÉ PAR PACK
        btn_devis = ctk.CTkButton(
            row,
            text="📄 Devis",
            width=70,
            height=24,
            fg_color=COLOR_RED_WRAD,
            hover_color=COLOR_RED_HOVER,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=lambda pk=pack_key: self.generate_devis_for_pack(pk)
        )
        btn_devis.pack(side="right", padx=2)

        return {"m": val_m, "c": val_c, "p": val_p, "card": f}

    def generate_devis_for_pack(self, pack_key: str):
        marque = self.entry_est_marque.get().strip() or "Véhicule"
        modele = self.entry_est_modele.get().strip()
        annee = self.entry_est_annee.get().strip()

        active_r = self.get_active_roll()
        laize = active_r["laize_cm"]

        if pack_key == "arriere":
            pack_title = "PACK 3/4 ARRIÈRE"
            desc = "Lunette arrière + vitres latérales arrière + custodes arrière"
            m_txt = self.card_arriere["m"].cget("text")
            p_txt = self.card_arriere["p"].cget("text")
        elif pack_key == "avant":
            pack_title = "PACK VITRES AVANT"
            desc = "Vitres latérales avant + custodes avant (Conforme TLV ≥ 70%)"
            m_txt = self.card_avant["m"].cget("text")
            p_txt = self.card_avant["p"].cget("text")
        else:
            pack_title = "VÉHICULE COMPLET (TOUS PACKS)"
            desc = "Lunette arrière + latérales arrière + custodes + vitres avant"
            m_txt = self.card_total["m"].cget("text")
            p_txt = self.card_total["p"].cget("text")

        try:
            metrage_float = float(m_txt.replace("m", "").strip())
        except ValueError:
            metrage_float = 0.0

        try:
            prix_float = float(p_txt.replace("€", "").strip())
        except ValueError:
            prix_float = 0.0

        num_devis = f"WRAD-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M')}"
        date_str = datetime.now().strftime("%d/%m/%Y")

        # Devis épuré : strictement sans slogan, sans description superflue, sans les 4 badges,
        # sans engagements/réglementations et sans mention de validité de l'offre
        devis_text = f"""==================================================
           DEVIS POSE DE FILMS TEINTÉS - WRAD
==================================================
DEVIS N° : {num_devis} | Date : {date_str}
Atelier WRAD - Poitiers & alentours (Atelier ou Domicile)
Contact : 07 67 60 10 98 | wradauto@gmail.com | @wradauto
--------------------------------------------------
VÉHICULE : {marque} {modele} {annee}
Film utilisé : {active_r['nom']} (Laize {laize:.0f} cm)
--------------------------------------------------
PRESTATION RETENUE : {pack_title}
Détail : {desc}
Métrage linéaire requis : {m_txt}
Teintes disponibles au choix : 5% / 15% / 20% / 35% / 50%

PRIX TOTAL CONSEILLÉ : {p_txt} TTC
=================================================="""

        self.clipboard_clear()
        self.clipboard_append(devis_text)

        # Fenêtre de prévisualisation et génération PDF
        d = ctk.CTkToplevel(self)
        d.title(f"Devis Wrad Épuré - {pack_title}")
        d.geometry("580x520")
        d.configure(fg_color=COLOR_BG_DARK)
        d.transient(self)

        top_f = ctk.CTkFrame(d, fg_color="transparent")
        top_f.pack(fill="x", padx=20, pady=(12, 4))
        ctk.CTkLabel(top_f, text=f"Devis Client Épuré : {pack_title}", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_RED_WRAD).pack(side="left")
        ctk.CTkLabel(top_f, text="N° " + num_devis, font=ctk.CTkFont(size=11, family="Courier"), text_color=COLOR_TEXT_MUTED).pack(side="right")

        # Barre d'actions d'export PDF & Impression
        btn_bar = ctk.CTkFrame(d, fg_color=COLOR_PANEL, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        btn_bar.pack(fill="x", padx=20, pady=6)

        veh_dict = {"marque": marque, "modele": modele, "annee": annee, "generation": self.current_vehicle_info.get("generation", "")}

        def on_export_pdf():
            default_name = f"Devis_WRAD_{num_devis}.pdf"
            save_path = filedialog.asksaveasfilename(
                parent=d,
                defaultextension=".pdf",
                filetypes=[("Fichier PDF", "*.pdf"), ("Tous fichiers", "*.*")],
                initialfile=default_name,
                title="Enregistrer le Devis PDF Épuré"
            )
            if not save_path:
                return

            ok = WradPDFGenerator.generate_pdf(
                filepath=save_path,
                devis_num=num_devis,
                date_str=date_str,
                vehicule=veh_dict,
                prestation_title=pack_title,
                prestation_desc=desc,
                metrage_m=metrage_float,
                prix_ttc=prix_float,
                roll_nom=active_r["nom"],
                laize_cm=laize
            )
            if ok:
                messagebox.showinfo("Succès", f"Devis PDF épuré créé avec succès :\n{save_path}", parent=d)
                try:
                    if os.name == 'nt':
                        os.startfile(save_path)
                    else:
                        webbrowser.open(f"file://{os.path.abspath(save_path)}")
                except Exception:
                    pass
            else:
                # Si reportlab n'est pas encore installé, proposition du HTML print immédiat
                html_path = save_path.replace(".pdf", ".html")
                WradPDFGenerator.generate_html_print_version(
                    filepath=html_path,
                    devis_num=num_devis,
                    date_str=date_str,
                    vehicule=veh_dict,
                    prestation_title=pack_title,
                    prestation_desc=desc,
                    metrage_m=metrage_float,
                    prix_ttc=prix_float,
                    roll_nom=active_r["nom"],
                    laize_cm=laize
                )
                webbrowser.open(f"file://{os.path.abspath(html_path)}")
                messagebox.showinfo(
                    "Format Imprimable Prêt",
                    "Le devis épuré a été ouvert dans votre navigateur (sélectionnez 'Enregistrer en PDF' pour imprimer).\n\n"
                    "Note : Pour la création directe de fichiers .pdf sans passer par le navigateur, exécutez :\npip install reportlab",
                    parent=d
                )

        def on_open_print():
            temp_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"devis_print_{num_devis}.html")
            WradPDFGenerator.generate_html_print_version(
                filepath=temp_html,
                devis_num=num_devis,
                date_str=date_str,
                vehicule=veh_dict,
                prestation_title=pack_title,
                prestation_desc=desc,
                metrage_m=metrage_float,
                prix_ttc=prix_float,
                roll_nom=active_r["nom"],
                laize_cm=laize
            )
            webbrowser.open(f"file://{os.path.abspath(temp_html)}")

        def on_copy_text():
            self.clipboard_clear()
            self.clipboard_append(devis_text)
            messagebox.showinfo("Copié", "Texte du devis épuré copié dans le presse-papier !", parent=d)

        btn_pdf = ctk.CTkButton(
            btn_bar,
            text="📄 Exporter en PDF",
            fg_color=COLOR_RED_WRAD,
            hover_color=COLOR_RED_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=on_export_pdf
        )
        btn_pdf.pack(side="left", padx=8, pady=8)

        btn_print = ctk.CTkButton(
            btn_bar,
            text="🖨️ Version Imprimable",
            fg_color=COLOR_CARD,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(size=11),
            command=on_open_print
        )
        btn_print.pack(side="left", padx=4, pady=8)

        btn_copy = ctk.CTkButton(
            btn_bar,
            text="📋 Copier Texte",
            fg_color=COLOR_CARD,
            hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(size=11),
            command=on_copy_text
        )
        btn_copy.pack(side="left", padx=4, pady=8)

        # Aperçu textuel
        tb = ctk.CTkTextbox(d, fg_color=COLOR_PANEL, text_color=COLOR_TEXT_WHITE, font=ctk.CTkFont(family="Courier", size=10))
        tb.pack(fill="both", expand=True, padx=20, pady=(4, 8))
        tb.insert("1.0", devis_text)

        ctk.CTkButton(d, text="Fermer", fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER, command=d.destroy).pack(pady=(0, 10))

    # -------------------------------------------------------------------------
    # 4. ONGLET 2 : BASE DE DONNÉES VÉHICULES
    # -------------------------------------------------------------------------
    def setup_database_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(10, 6))

        ctk.CTkLabel(top, text="Catalogue des Véhicules & Cotes (database.json)", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(side="left")

        ctk.CTkButton(
            top,
            text="+ Ajouter un véhicule manuellement",
            fg_color=COLOR_RED_WRAD,
            hover_color=COLOR_RED_HOVER,
            command=self.open_manual_vehicle_dialog
        ).pack(side="right")

        self.scroll_db_list = ctk.CTkScrollableFrame(parent, fg_color=COLOR_PANEL, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        self.scroll_db_list.pack(fill="both", expand=True, padx=15, pady=8)

        self.refresh_database_view()

    def refresh_database_view(self):
        for w in self.scroll_db_list.winfo_children():
            w.destroy()

        db = PersistenceManager.load_database()
        if not db:
            ctk.CTkLabel(self.scroll_db_list, text="Aucun véhicule enregistré dans database.json.", text_color=COLOR_TEXT_MUTED).pack(pady=30)
            return

        for key, v in db.items():
            card = ctk.CTkFrame(self.scroll_db_list, fg_color=COLOR_CARD, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
            card.pack(fill="x", pady=3, padx=4)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=10, pady=6)

            title_txt = f"{v.get('marque', '')} {v.get('modele', '')} ({v.get('annee', 'N/A')})"
            ctk.CTkLabel(left, text=title_txt, font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(anchor="w")

            gen_txt = f"{v.get('generation', 'Standard')} • {len(v.get('vitres', []))} vitres enregistrées"
            ctk.CTkLabel(left, text=gen_txt, font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED).pack(anchor="w")

            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="right", padx=8)

            ctk.CTkButton(
                right,
                text="Charger dans l'estimateur",
                width=140,
                height=26,
                fg_color=COLOR_RED_WRAD,
                hover_color=COLOR_RED_HOVER,
                command=lambda veh=v: self.load_vehicle_from_db(veh)
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                right,
                text="✕",
                width=28,
                height=26,
                fg_color=COLOR_CARD_HOVER,
                hover_color="#ef4444",
                command=lambda k=key: self.delete_vehicle_from_db(k)
            ).pack(side="left", padx=2)

    def load_vehicle_from_db(self, v: Dict[str, Any]):
        self.entry_est_marque.delete(0, tk.END)
        self.entry_est_marque.insert(0, v.get("marque", ""))
        self.entry_est_modele.delete(0, tk.END)
        self.entry_est_modele.insert(0, v.get("modele", ""))
        self.entry_est_annee.delete(0, tk.END)
        self.entry_est_annee.insert(0, v.get("annee", ""))
        self.load_vitres_into_estimator(v.get("vitres", []), v)
        self.tabview.set("⚡ 1. Estimateur & Découpe Horizontale")
        self.lbl_est_status.configure(text="Chargé depuis database.json", text_color=COLOR_SUCCESS)

    def delete_vehicle_from_db(self, key: str):
        if not messagebox.askyesno("Confirmation", "Supprimer ce véhicule de database.json ?"):
            return
        db = PersistenceManager.load_database()
        if key in db:
            del db[key]
            PersistenceManager.save_database(db)
            self.refresh_database_view()

    def open_manual_vehicle_dialog(self):
        d = ctk.CTkToplevel(self)
        d.title("Ajout Manuel de Véhicule - Wrad")
        d.geometry("650x550")
        d.configure(fg_color=COLOR_BG_DARK)
        d.transient(self)

        ctk.CTkLabel(d, text="Fiche Véhicule & Cotes des Vitres", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_RED_WRAD).pack(pady=10)

        meta = ctk.CTkFrame(d, fg_color=COLOR_PANEL, border_width=1, border_color=COLOR_BORDER)
        meta.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(meta, text="Marque :").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        e_m = ctk.CTkEntry(meta, width=130, fg_color=COLOR_BG_DARK)
        e_m.grid(row=0, column=1, padx=4, pady=4)

        ctk.CTkLabel(meta, text="Modèle :").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        e_mod = ctk.CTkEntry(meta, width=130, fg_color=COLOR_BG_DARK)
        e_mod.grid(row=0, column=3, padx=4, pady=4)

        ctk.CTkLabel(meta, text="Année :").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        e_yr = ctk.CTkEntry(meta, width=130, fg_color=COLOR_BG_DARK)
        e_yr.grid(row=1, column=1, padx=4, pady=4)

        ctk.CTkLabel(meta, text="Génération :").grid(row=1, column=2, sticky="w", padx=6, pady=4)
        e_gen = ctk.CTkEntry(meta, width=130, fg_color=COLOR_BG_DARK)
        e_gen.grid(row=1, column=3, padx=4, pady=4)

        ctk.CTkLabel(d, text="Liste des Vitres (H = Laize, L = Longueur déroulé) :", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(pady=(8, 2))
        sc_v = ctk.CTkScrollableFrame(d, height=200, fg_color=COLOR_PANEL)
        sc_v.pack(fill="both", expand=True, padx=20)

        vitres_rows = []

        def add_v_row(nom="Vitre", h=45, w=60, z="arriere"):
            r = ctk.CTkFrame(sc_v, fg_color=COLOR_CARD)
            r.pack(fill="x", pady=2)
            en = ctk.CTkEntry(r, width=160, fg_color=COLOR_BG_DARK)
            en.insert(0, nom)
            en.pack(side="left", padx=2)

            eh = ctk.CTkEntry(r, width=60, justify="center", fg_color=COLOR_BG_DARK)
            eh.insert(0, str(h))
            eh.pack(side="left", padx=2)

            ew = ctk.CTkEntry(r, width=60, justify="center", fg_color=COLOR_BG_DARK)
            ew.insert(0, str(w))
            ew.pack(side="left", padx=2)

            ez = ctk.CTkOptionMenu(r, values=["arriere", "avant"], width=80, fg_color=COLOR_BG_DARK)
            ez.set(z)
            ez.pack(side="left", padx=2)

            btn_del = ctk.CTkButton(r, text="✕", width=25, fg_color=COLOR_CARD_HOVER, command=lambda row=r: row.destroy())
            btn_del.pack(side="right", padx=2)

            vitres_rows.append({"r": r, "en": en, "eh": eh, "ew": ew, "ez": ez})

        add_v_row("Lunette arrière", 55, 100, "arriere")
        add_v_row("Vitre latérale arrière gauche", 45, 60, "arriere")
        add_v_row("Vitre latérale arrière droite", 45, 60, "arriere")
        add_v_row("Vitre latérale avant gauche", 50, 75, "avant")
        add_v_row("Vitre latérale avant droite", 50, 75, "avant")

        ctk.CTkButton(d, text="+ Ajouter une ligne de vitre", fg_color=COLOR_CARD, hover_color=COLOR_CARD_HOVER, command=lambda: add_v_row("Nouvelle vitre", 40, 50, "arriere")).pack(pady=4)

        def save_manual():
            marque = e_m.get().strip()
            modele = e_mod.get().strip()
            annee = e_yr.get().strip()
            gen = e_gen.get().strip() or "Ajout Manuel Wrad"

            if not marque or not modele:
                messagebox.showerror("Erreur", "Marque et modèle obligatoires.")
                return

            vitres = []
            for item in vitres_rows:
                if item["r"].winfo_exists():
                    try:
                        vitres.append({
                            "nom": item["en"].get().strip(),
                            "hauteur_cm": int(item["eh"].get()),
                            "largeur_cm": int(item["ew"].get()),
                            "zone": item["ez"].get(),
                            "included": True
                        })
                    except ValueError:
                        pass

            if not vitres:
                messagebox.showerror("Erreur", "Renseignez au moins une vitre.")
                return

            key = f"{marque.lower().strip()}_{modele.lower().strip()}_{annee.lower().strip()}"
            db = PersistenceManager.load_database()
            db[key] = {"marque": marque, "modele": modele, "annee": annee, "generation": gen, "vitres": vitres}
            PersistenceManager.save_database(db)
            self.refresh_database_view()
            d.destroy()
            messagebox.showinfo("Succès", f"Fiche {marque} {modele} mémorisée dans database.json !")

        ctk.CTkButton(d, text="Sauvegarder définitivement", fg_color=COLOR_RED_WRAD, hover_color=COLOR_RED_HOVER, command=save_manual).pack(pady=8)

    # -------------------------------------------------------------------------
    # 5. ONGLET 3 : SUIVI CLIENTS & RENTABILITÉ
    # -------------------------------------------------------------------------
    def setup_clients_tab(self, parent):
        kpi_frame = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=15, pady=(10, 6))

        self.lbl_kpi_ca = self.create_kpi_box(kpi_frame, "CHIFFRE D'AFFAIRES", "0.00 €", COLOR_PRICE_GOLD)
        self.lbl_kpi_cout = self.create_kpi_box(kpi_frame, "COÛT MATIÈRE", "0.00 €", COLOR_TEXT_MUTED)
        self.lbl_kpi_benef = self.create_kpi_box(kpi_frame, "BÉNÉFICE NET RÉEL", "+0.00 €", COLOR_SUCCESS)
        self.lbl_kpi_metres = self.create_kpi_box(kpi_frame, "MÉTRAGE POSÉ", "0.00 m", COLOR_RED_WRAD)

        form_frame = ctk.CTkFrame(parent, fg_color=COLOR_PANEL, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        form_frame.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(form_frame, text="Enregistrer une Pose & Calculer la Rentabilité Nette Wrad", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_RED_WRAD).pack(anchor="w", padx=12, pady=(8, 4))

        f_inputs = ctk.CTkFrame(form_frame, fg_color="transparent")
        f_inputs.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(f_inputs, text="Client :").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_cli_nom = ctk.CTkEntry(f_inputs, width=140, fg_color=COLOR_BG_DARK)
        self.entry_cli_nom.grid(row=0, column=1, padx=4, pady=2)

        ctk.CTkLabel(f_inputs, text="Véhicule :").grid(row=0, column=2, sticky="w", pady=2)
        self.entry_cli_veh = ctk.CTkEntry(f_inputs, width=140, fg_color=COLOR_BG_DARK)
        self.entry_cli_veh.grid(row=0, column=3, padx=4, pady=2)

        ctk.CTkLabel(f_inputs, text="Métrage (m) :").grid(row=0, column=4, sticky="w", pady=2)
        self.entry_cli_metres = ctk.CTkEntry(f_inputs, width=70, justify="center", fg_color=COLOR_BG_DARK)
        self.entry_cli_metres.insert(0, "2.0")
        self.entry_cli_metres.grid(row=0, column=5, padx=4, pady=2)

        ctk.CTkLabel(f_inputs, text="Facturé (€) :").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_cli_prix = ctk.CTkEntry(f_inputs, width=140, justify="center", fg_color=COLOR_BG_DARK, text_color=COLOR_PRICE_GOLD)
        self.entry_cli_prix.insert(0, "150.0")
        self.entry_cli_prix.grid(row=1, column=1, padx=4, pady=2)

        ctk.CTkLabel(f_inputs, text="Prestation :").grid(row=1, column=2, sticky="w", pady=2)
        self.combo_cli_pack = ctk.CTkOptionMenu(f_inputs, values=["Pack 3/4 Arrière", "Pack Vitres Avant", "Véhicule Complet"], width=140, fg_color=COLOR_CARD)
        self.combo_cli_pack.grid(row=1, column=3, padx=4, pady=2)

        btn_add_cli = ctk.CTkButton(
            f_inputs,
            text="+ Enregistrer la prestation",
            fg_color=COLOR_RED_WRAD,
            hover_color=COLOR_RED_HOVER,
            command=self.save_client_record
        )
        btn_add_cli.grid(row=1, column=4, columnspan=2, padx=4, pady=2)

        self.scroll_clients = ctk.CTkScrollableFrame(parent, fg_color=COLOR_PANEL, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        self.scroll_clients.pack(fill="both", expand=True, padx=15, pady=6)

        self.refresh_clients_table()

    def create_kpi_box(self, parent, title, value, color):
        b = ctk.CTkFrame(parent, fg_color=COLOR_PANEL, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        b.pack(side="left", fill="both", expand=True, padx=4)
        ctk.CTkLabel(b, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(pady=(6, 0))
        val_lbl = ctk.CTkLabel(b, text=value, font=ctk.CTkFont(size=16, weight="bold"), text_color=color)
        val_lbl.pack(pady=(0, 6))
        return val_lbl

    def save_client_record(self):
        nom = self.entry_cli_nom.get().strip()
        veh = self.entry_cli_veh.get().strip()
        try:
            m = float(self.entry_cli_metres.get())
            prix = float(self.entry_cli_prix.get())
        except ValueError:
            messagebox.showerror("Erreur", "Métrage et prix doivent être numériques.")
            return

        if not nom or not veh:
            messagebox.showerror("Erreur", "Nom et véhicule obligatoires.")
            return

        active_r = self.get_active_roll()
        cost_per_m = active_r["prix_achat_ttc"] / active_r["longueur_m"]
        cout = round(m * cost_per_m, 2)
        benef = round(prix - cout, 2)
        marge_pct = round((benef / prix * 100), 1) if prix > 0 else 0.0

        record = {
            "id": f"cli-{int(datetime.now().timestamp())}",
            "clientNom": nom,
            "vehicule": veh,
            "datePose": datetime.now().strftime("%Y-%m-%d"),
            "pack": self.combo_cli_pack.get(),
            "metrageUtiliseM": m,
            "prixFactureTTC": prix,
            "coutRevientTTC": cout,
            "beneficeNetTTC": benef,
            "tauxMargePercent": marge_pct
        }

        clients = PersistenceManager.load_clients()
        clients.insert(0, record)
        PersistenceManager.save_clients(clients)

        self.entry_cli_nom.delete(0, tk.END)
        self.refresh_clients_table()
        messagebox.showinfo("Enregistré", f"Bénéfice net réalisé : +{benef} € ({marge_pct}%)")

    def refresh_clients_table(self):
        for w in self.scroll_clients.winfo_children():
            w.destroy()

        clients = PersistenceManager.load_clients()

        tot_ca = sum(c.get("prixFactureTTC", 0) for c in clients)
        tot_cout = sum(c.get("coutRevientTTC", 0) for c in clients)
        tot_benef = tot_ca - tot_cout
        tot_m = sum(c.get("metrageUtiliseM", 0) for c in clients)

        self.lbl_kpi_ca.configure(text=f"{tot_ca:.2f} €")
        self.lbl_kpi_cout.configure(text=f"{tot_cout:.2f} €")
        self.lbl_kpi_benef.configure(text=f"+{tot_benef:.2f} €")
        self.lbl_kpi_metres.configure(text=f"{tot_m:.2f} m")

        hdr = ctk.CTkFrame(self.scroll_clients, fg_color=COLOR_CARD)
        hdr.pack(fill="x", pady=2)
        ctk.CTkLabel(hdr, text="Date", width=80, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(hdr, text="Client", width=140, anchor="w", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=4)
        ctk.CTkLabel(hdr, text="Véhicule", width=140, anchor="w", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=4)
        ctk.CTkLabel(hdr, text="Métrage", width=70, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(hdr, text="Facturé", width=80, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(hdr, text="Bénéfice Net", width=90, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_SUCCESS).pack(side="left")

        for c in clients:
            r = ctk.CTkFrame(self.scroll_clients, fg_color=COLOR_CARD)
            r.pack(fill="x", pady=1)

            ctk.CTkLabel(r, text=c.get("datePose", ""), width=80, font=ctk.CTkFont(size=10)).pack(side="left")
            ctk.CTkLabel(r, text=c.get("clientNom", ""), width=140, anchor="w", font=ctk.CTkFont(size=10, weight="bold")).pack(side="left", padx=4)
            ctk.CTkLabel(r, text=c.get("vehicule", ""), width=140, anchor="w", font=ctk.CTkFont(size=10)).pack(side="left", padx=4)
            ctk.CTkLabel(r, text=f"{c.get('metrageUtiliseM', 0):.2f}m", width=70, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(side="left")
            ctk.CTkLabel(r, text=f"{c.get('prixFactureTTC', 0):.2f}€", width=80, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_PRICE_GOLD).pack(side="left")
            ctk.CTkLabel(r, text=f"+{c.get('beneficeNetTTC', 0):.2f}€", width=90, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_SUCCESS).pack(side="left")

            btn_del = ctk.CTkButton(
                r,
                text="✕",
                width=24,
                height=22,
                fg_color=COLOR_CARD_HOVER,
                hover_color="#ef4444",
                command=lambda cid=c.get("id"): self.delete_client_record(cid)
            )
            btn_del.pack(side="right", padx=6)

    def delete_client_record(self, cid: str):
        clients = [c for c in PersistenceManager.load_clients() if c.get("id") != cid]
        PersistenceManager.save_clients(clients)
        self.refresh_clients_table()

    # -------------------------------------------------------------------------
    # CALCULS & CANVAS 2D
    # -------------------------------------------------------------------------
    def load_initial_vehicle(self):
        self.entry_est_marque.insert(0, "Peugeot")
        self.entry_est_modele.insert(0, "208")
        self.entry_est_annee.insert(0, "2020")
        self.on_estimate_clicked()

    def on_est_preset_selected(self, choice):
        p_map = {
            "Peugeot 208 (2020)": ("Peugeot", "208", "2020"),
            "Volkswagen Golf 8 (2021)": ("Volkswagen", "Golf", "2021"),
            "Tesla Model 3 (2022)": ("Tesla", "Model 3", "2022"),
            "Renault Clio (2021)": ("Renault", "Clio", "2021"),
            "BMW Série 3 (2021)": ("BMW", "Série 3", "2021")
        }
        if choice in p_map:
            m, mod, y = p_map[choice]
            self.entry_est_marque.delete(0, tk.END)
            self.entry_est_marque.insert(0, m)
            self.entry_est_modele.delete(0, tk.END)
            self.entry_est_modele.insert(0, mod)
            self.entry_est_annee.delete(0, tk.END)
            self.entry_est_annee.insert(0, y)
            self.on_estimate_clicked()

    def on_estimate_clicked(self):
        marque = self.entry_est_marque.get().strip()
        modele = self.entry_est_modele.get().strip()
        annee = self.entry_est_annee.get().strip()

        if not marque or not modele:
            messagebox.showwarning("Champs requis", "Renseignez au minimum la marque et le modèle.")
            return

        self.lbl_est_status.configure(text="Recherche...", text_color=COLOR_PRICE_GOLD)
        self.update_idletasks()

        db = PersistenceManager.load_database()
        key = f"{marque.lower().strip()}_{modele.lower().strip()}_{annee.lower().strip()}"
        if key in db:
            self.lbl_est_status.configure(text="⚡ Base database.json", text_color=COLOR_SUCCESS)
            self.load_vitres_into_estimator(db[key].get("vitres", []), db[key])
            return

        for k, v in db.items():
            if v.get("marque", "").lower() == marque.lower() and v.get("modele", "").lower() == modele.lower():
                self.lbl_est_status.configure(text="⚡ Base database.json", text_color=COLOR_SUCCESS)
                self.load_vitres_into_estimator(v.get("vitres", []), v)
                return

        self.lbl_est_status.configure(text="🤖 Appel Gemini...", text_color=COLOR_RED_WRAD)
        self.update_idletasks()

        try:
            res = GeminiEstimator.estimate(marque, modele, annee)
            vitres = res.get("vitres", [])
            gen = res.get("generation", "Estimé par IA")
            db[key] = {"marque": marque, "modele": modele, "annee": annee, "generation": gen, "vitres": vitres}
            PersistenceManager.save_database(db)
            self.lbl_est_status.configure(text="✨ IA mémorisée", text_color=COLOR_SUCCESS)
            self.load_vitres_into_estimator(vitres, db[key])
            self.refresh_database_view()
        except Exception as e:
            self.lbl_est_status.configure(text="⚠️ Mode local actif", text_color=COLOR_WARNING)
            default_v = [
                {"nom": "Lunette arrière", "hauteur_cm": 55, "largeur_cm": 100, "zone": "arriere", "included": True},
                {"nom": "Vitre latérale arrière gauche", "hauteur_cm": 45, "largeur_cm": 60, "zone": "arriere", "included": True},
                {"nom": "Vitre latérale arrière droite", "hauteur_cm": 45, "largeur_cm": 60, "zone": "arriere", "included": True},
                {"nom": "Vitre latérale avant gauche", "hauteur_cm": 50, "largeur_cm": 75, "zone": "avant", "included": True},
                {"nom": "Vitre latérale avant droite", "hauteur_cm": 50, "largeur_cm": 75, "zone": "avant", "included": True},
            ]
            self.load_vitres_into_estimator(default_v, {"marque": marque, "modele": modele, "annee": annee, "generation": "Modèle local"})

    def load_vitres_into_estimator(self, vitres: List[Dict[str, Any]], meta: Dict[str, Any]):
        self.vitres_data = [dict(v, included=v.get("included", True)) for v in vitres]
        self.current_vehicle_info = meta
        self.render_vitres_rows()
        self.recalculate_all()

    def render_vitres_rows(self):
        for w in self.scroll_vitres.winfo_children():
            w.destroy()

        for idx, item in enumerate(self.vitres_data):
            r = ctk.CTkFrame(self.scroll_vitres, fg_color=COLOR_CARD, height=28)
            r.pack(fill="x", pady=1)

            inc_var = tk.BooleanVar(value=item.get("included", True))
            def on_toggle(v=inc_var, i=idx):
                self.vitres_data[i]["included"] = v.get()
                self.recalculate_all()
            chk = ctk.CTkCheckBox(r, text="", variable=inc_var, width=20, command=on_toggle, fg_color=COLOR_RED_WRAD)
            chk.pack(side="left", padx=4)

            en = ctk.CTkEntry(r, width=170, height=24, font=ctk.CTkFont(size=10), fg_color=COLOR_BG_DARK)
            en.insert(0, item.get("nom", ""))
            en.pack(side="left", padx=2)
            en.bind("<KeyRelease>", lambda e, i=idx, entry=en: self.on_vitre_field_change(i, "nom", entry.get()))

            eh = ctk.CTkEntry(r, width=60, height=24, justify="center", font=ctk.CTkFont(size=10), fg_color=COLOR_BG_DARK)
            eh.insert(0, str(item.get("hauteur_cm", 45)))
            eh.pack(side="left", padx=2)
            eh.bind("<KeyRelease>", lambda e, i=idx, entry=eh: self.on_vitre_field_change(i, "hauteur_cm", entry.get()))

            ew = ctk.CTkEntry(r, width=60, height=24, justify="center", font=ctk.CTkFont(size=10), fg_color=COLOR_BG_DARK)
            ew.insert(0, str(item.get("largeur_cm", 60)))
            ew.pack(side="left", padx=2)
            ew.bind("<KeyRelease>", lambda e, i=idx, entry=ew: self.on_vitre_field_change(i, "largeur_cm", entry.get()))

            ez = ctk.CTkOptionMenu(r, values=["arriere", "avant"], width=75, height=24, font=ctk.CTkFont(size=10), fg_color=COLOR_BG_DARK)
            ez.set(item.get("zone", "arriere"))
            ez.pack(side="left", padx=2)
            ez.configure(command=lambda choice, i=idx: self.on_vitre_zone_change(i, choice))

            btn_del = ctk.CTkButton(r, text="✕", width=22, height=22, fg_color=COLOR_CARD_HOVER, command=lambda i=idx: self.delete_vitre_row(i))
            btn_del.pack(side="right", padx=4)

    def on_vitre_field_change(self, idx: int, field: str, val: str):
        try:
            if field in ["hauteur_cm", "largeur_cm"]:
                self.vitres_data[idx][field] = float(val or 0)
            else:
                self.vitres_data[idx][field] = val
            self.recalculate_all()
        except ValueError:
            pass

    def on_vitre_zone_change(self, idx: int, choice: str):
        self.vitres_data[idx]["zone"] = choice
        self.recalculate_all()

    def add_manual_vitre_row(self):
        self.vitres_data.append({
            "nom": f"Vitre #{len(self.vitres_data) + 1}",
            "hauteur_cm": 45,
            "largeur_cm": 60,
            "zone": "arriere",
            "included": True
        })
        self.render_vitres_rows()
        self.recalculate_all()

    def delete_vitre_row(self, idx: int):
        if 0 <= idx < len(self.vitres_data):
            self.vitres_data.pop(idx)
            self.render_vitres_rows()
            self.recalculate_all()

    def recalculate_all(self):
        roll = self.get_active_roll()
        laize = roll["laize_cm"]
        longueur = roll["longueur_m"]
        prix_rouleau = roll["prix_achat_ttc"]
        cost_per_m = (prix_rouleau / longueur) if longueur > 0 else 0.0

        # Pack Arrière
        v_arr = [v for v in self.vitres_data if v.get("zone") == "arriere"]
        nest_arr = StrictHorizontalNestingEngine.compute(v_arr, laize, self.marge_coupe)
        m_arr = nest_arr["total_linear_m"]
        c_arr = m_arr * cost_per_m
        p_arr = c_arr * self.coeff_prix
        self.card_arriere["m"].configure(text=f"{m_arr:.2f} m")
        self.card_arriere["c"].configure(text=f"Coût: {c_arr:.2f} €")
        self.card_arriere["p"].configure(text=f"{p_arr:.2f} €")

        # Pack Avant
        v_av = [v for v in self.vitres_data if v.get("zone") == "avant"]
        nest_av = StrictHorizontalNestingEngine.compute(v_av, laize, self.marge_coupe)
        m_av = nest_av["total_linear_m"]
        c_av = m_av * cost_per_m
        p_av = c_av * self.coeff_prix
        self.card_avant["m"].configure(text=f"{m_av:.2f} m")
        self.card_avant["c"].configure(text=f"Coût: {c_av:.2f} €")
        self.card_avant["p"].configure(text=f"{p_av:.2f} €")

        # Véhicule Complet
        nest_tot = StrictHorizontalNestingEngine.compute(self.vitres_data, laize, self.marge_coupe)
        m_tot = nest_tot["total_linear_m"]
        c_tot = m_tot * cost_per_m
        p_tot = c_tot * self.coeff_prix
        self.card_total["m"].configure(text=f"{m_tot:.2f} m")
        self.card_total["c"].configure(text=f"Coût: {c_tot:.2f} €")
        self.card_total["p"].configure(text=f"{p_tot:.2f} €")

        self.draw_cutting_plan(nest_tot, laize)

    def draw_cutting_plan(self, nesting_res: Dict[str, Any], laize_cm: float):
        self.canvas_est.delete("all")
        cw = self.canvas_est.winfo_width()
        ch = self.canvas_est.winfo_height()

        if cw <= 1 or ch <= 1:
            self.canvas_est.after(100, lambda: self.draw_cutting_plan(nesting_res, laize_cm))
            return

        tot_linear_cm = max(100.0, nesting_res.get("total_linear_cm", 0.0) + 15)
        pad_x, pad_y = 35, 35
        avail_w = cw - (pad_x * 2)
        avail_h = ch - (pad_y * 2)

        scale_x = avail_w / laize_cm
        scale_y = avail_h / tot_linear_cm
        scale = min(scale_x, scale_y, 3.5)
        scale = max(scale, 0.4)

        roll_w = laize_cm * scale
        roll_h = tot_linear_cm * scale

        # Fond rouleau avec bordure sobre Wrad
        self.canvas_est.create_rectangle(pad_x, pad_y, pad_x + roll_w, pad_y + roll_h, fill="#121215", outline=COLOR_BORDER, width=2)
        self.canvas_est.create_text(pad_x + (roll_w / 2), pad_y - 12, text=f"Laize du rouleau: {laize_cm:.0f} cm", fill=COLOR_TEXT_MUTED, font=("Helvetica", 9, "bold"))

        placed = nesting_res.get("placed", [])
        for p in placed:
            x1 = pad_x + (p["x"] * scale)
            y1 = pad_y + (p["y"] * scale)
            x2 = x1 + (p["height_on_laize"] * scale)
            y2 = y1 + (p["width_on_roll"] * scale)

            exceeds = not p.get("fits", True)
            fill_col = "#7f1d1d" if exceeds else ("#7f1d1d" if p["zone"] == "arriere" else "#27272a")
            border_col = COLOR_WARNING if exceeds else (COLOR_RED_WRAD if p["zone"] == "arriere" else "#71717a")

            self.canvas_est.create_rectangle(x1, y1, x2, y2, fill=fill_col, outline=border_col, width=1.5)

            pw, ph = x2 - x1, y2 - y1
            if pw > 35 and ph > 20:
                txt = f"{p['nom'][:14]}\nH:{p['height_on_laize']:.0f}×L:{p['width_on_roll']:.0f}cm"
                if exceeds:
                    txt += f"\n⚠️ +{p['exceeds_by']:.0f}cm"
                self.canvas_est.create_text(x1 + (pw / 2), y1 + (ph / 2), text=txt, fill="#ffffff", font=("Helvetica", 8, "bold"), justify="center")

        # Règle de métrage
        actual_len_cm = nesting_res.get("total_linear_cm", 0.0)
        y_end = pad_y + (actual_len_cm * scale)
        self.canvas_est.create_line(pad_x + roll_w + 10, pad_y, pad_x + roll_w + 10, y_end, fill=COLOR_RED_WRAD, width=2, arrow=tk.BOTH)
        self.canvas_est.create_text(pad_x + roll_w + 50, pad_y + ((y_end - pad_y) / 2), text=f"{nesting_res.get('total_linear_m', 0):.2f} m\n({actual_len_cm:.0f} cm)", fill=COLOR_RED_WRAD, font=("Helvetica", 8, "bold"))

        warn_str = " | ⚠️ ALERTE RACCORD NÉCESSAIRE" if nesting_res.get("has_seam_warning") else ""
        self.lbl_canvas_info.configure(text=f"Découpe Horizontale • Rouleau actif: {laize_cm:.0f} cm • Métrage: {nesting_res.get('total_linear_m', 0):.2f} m{warn_str}")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================
if __name__ == "__main__":
    app = WradTintStudioApp()
    app.mainloop()
