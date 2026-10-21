"""
=============================================================================
                  WRAD - AUTOMOTIVE TINTING STUDIO
    Application Web Streamlit de Métrage, Plan de Coupe & Rentabilité
=============================================================================
Architecture : Python 3.9+ | Streamlit (Web & Cloud) | Supabase Cloud | Gemini AI
Conformité Cloud : 100% headless, zéro dépendance Tkinter (compatible Streamlit Cloud)
Charte Graphique : Identité Officielle Wrad (Noir Carbone & Rouge Course #E10600)
Contact : 07 67 60 10 98 | wradauto@gmail.com | Instagram: @wradauto
=============================================================================
"""

import os
import json
import io
import math
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Any, Optional

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# CODES COULEURS & CHARTE VISUELLE WRAD
# =============================================================================
COLOR_BG_DARK = "#09090b"        # Fond principal (Noir Onyx profond)
COLOR_PANEL = "#121215"          # Panneaux de contenu
COLOR_CARD = "#18181c"           # Cartes et conteneurs
COLOR_BORDER = "#27272a"         # Bordures subtiles
COLOR_RED_WRAD = "#E10600"       # Rouge Wrad officiel (Logo & Flyers)
COLOR_RED_HOVER = "#B91C1C"      # Survol boutons rouges
COLOR_RED_DARK = "#450a0a"       # Fond badges rouges
COLOR_TEXT_WHITE = "#FFFFFF"     # Blanc
COLOR_TEXT_MUTED = "#a1a1aa"     # Gris métallisé
COLOR_PRICE_GOLD = "#fde047"     # Accent doré
COLOR_SUCCESS = "#22c55e"        # Vert bénéfice
COLOR_WARNING = "#ef4444"        # Rouge alerte dépassement laize

# Fichiers locaux de secours (cache hors-ligne)
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")
CLIENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clients.json")
ROLLS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rolls.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# Identifiants Supabase (avec fallback transparent sur le cache local)
SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "https://grnpluqowqgprmqwxify.supabase.co"
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("VITE_SUPABASE_ANON_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdybnBsdXFvd3FncHJtcXd4aWZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI1Nzk5ODksImV4cCI6MjEwODE1NTk4OX0.RyiCSnVA1HDf0RSpVamkFXwaJZbff9RT_GazgdVUwUki"

# Rouleaux par défaut Wrad
DEFAULT_ROLLS = [
    {"id": "roll-76-30", "nom": "Rouleau Standard Wrad 76cm (Teinte 15% Black)", "laize_cm": 76.0, "longueur_m": 30.0, "prix_achat_ttc": 188.0, "isDefault": True},
    {"id": "roll-100-30", "nom": "Rouleau Large 100cm (Carbone 5% Limousine)", "laize_cm": 100.0, "longueur_m": 30.0, "prix_achat_ttc": 248.0},
    {"id": "roll-152-30", "nom": "Rouleau Extra-Large 152cm (Nano-Céramique 20%)", "laize_cm": 152.0, "longueur_m": 30.0, "prix_achat_ttc": 365.0},
    {"id": "roll-50-30", "nom": "Rouleau Étroit 50cm (Homologué Avant 70%)", "laize_cm": 50.0, "longueur_m": 30.0, "prix_achat_ttc": 125.0},
]

# =============================================================================
# PERSISTANCE HYBRIDE SUPABASE (REST EN DIRECT) & CACHE LOCAL
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
            try:
                with open(DATABASE_FILE, "w", encoding="utf-8") as f:
                    json.dump(db_map, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return db_map

        if os.path.exists(DATABASE_FILE):
            try:
                with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def save_vehicle(key: str, data: Dict[str, Any]) -> bool:
        ok_local = False
        db = PersistenceManager.load_database()
        db[key] = data
        try:
            with open(DATABASE_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            ok_local = True
        except Exception:
            pass

        try:
            payload = {
                "id": key,
                "key": key,
                "marque": data.get("marque", ""),
                "modele": data.get("modele", ""),
                "annee": data.get("annee", ""),
                "generation": data.get("generation", ""),
                "vitres": data.get("vitres", [])
            }
            PersistenceManager._supabase_request("vehicles", method="POST", data=[payload])
        except Exception:
            pass

        return ok_local

    @staticmethod
    def delete_vehicle(key: str) -> bool:
        db = PersistenceManager.load_database()
        if key in db:
            del db[key]
            try:
                with open(DATABASE_FILE, "w", encoding="utf-8") as f:
                    json.dump(db, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        try:
            PersistenceManager._supabase_request(f"vehicles?id=eq.{key}", method="DELETE")
            PersistenceManager._supabase_request(f"vehicles?key=eq.{key}", method="DELETE")
        except Exception:
            pass
        return True

    @staticmethod
    def load_clients() -> List[Dict[str, Any]]:
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
                    "notes": c.get("notes") or ""
                })
            try:
                with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(formatted, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return formatted

        if os.path.exists(CLIENTS_FILE):
            try:
                with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    @staticmethod
    def save_client_record(record: Dict[str, Any]) -> bool:
        clients = PersistenceManager.load_clients()
        clients.insert(0, record)
        try:
            with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(clients, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        try:
            payload = {
                "id": str(record.get("id")),
                "clientNom": record.get("clientNom"),
                "client_nom": record.get("clientNom"),
                "vehicule": record.get("vehicule"),
                "datePose": record.get("datePose"),
                "date_pose": record.get("datePose"),
                "pack": record.get("pack"),
                "metrageUtiliseM": record.get("metrageUtiliseM"),
                "metrage_utilise_m": record.get("metrageUtiliseM"),
                "prixFactureTTC": record.get("prixFactureTTC"),
                "prix_facture_ttc": record.get("prixFactureTTC"),
                "coutRevientTTC": record.get("coutRevientTTC"),
                "cout_revient_ttc": record.get("coutRevientTTC"),
                "beneficeNetTTC": record.get("beneficeNetTTC"),
                "benefice_net_ttc": record.get("beneficeNetTTC"),
                "tauxMargePercent": record.get("tauxMargePercent"),
                "taux_marge_percent": record.get("tauxMargePercent"),
                "notes": record.get("notes", "")
            }
            PersistenceManager._supabase_request("clients", method="POST", data=[payload])
        except Exception:
            pass
        return True

    @staticmethod
    def delete_client_record(cid: str) -> bool:
        clients = [c for c in PersistenceManager.load_clients() if str(c.get("id")) != str(cid)]
        try:
            with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(clients, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        try:
            PersistenceManager._supabase_request(f"clients?id=eq.{cid}", method="DELETE")
        except Exception:
            pass
        return True

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
            except Exception:
                pass
        return list(DEFAULT_ROLLS)

    @staticmethod
    def save_rolls(data: List[Dict[str, Any]]) -> bool:
        try:
            with open(ROLLS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        try:
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
        return True


# =============================================================================
# MOTEUR TECHNIQUE : SENS DU FILM STRICTEMENT HORIZONTAL
# =============================================================================
class StrictHorizontalNestingEngine:
    """
    Règle physique impérative : Le film teinté s'utilise uniquement de façon horizontale.
    - Hauteur vitre (+ marge) alignée sur la Laize du rouleau.
    - Largeur vitre (+ marge) alignée sur la Longueur du déroulé du rouleau.
    - Zéro rotation à 90° autorisée.
    """

    @staticmethod
    def compute(vitres: List[Dict[str, Any]], laize_cm: float = 76.0, marge_cm: float = 5.0) -> Dict[str, Any]:
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
                "has_seam_warning": False,
                "svg_html": ""
            }

        candidates = []
        for v in active_items:
            raw_h = float(v.get("hauteur_cm", 45))
            raw_w = float(v.get("largeur_cm", 60))
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

        # Tri par hauteur décroissante sur laize
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
                    "raw_h": v.get("hauteur_cm", 45),
                    "raw_w": v.get("largeur_cm", 60),
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
                    "raw_h": v.get("hauteur_cm", 45),
                    "raw_w": v.get("largeur_cm", 60),
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
                    "raw_h": v.get("hauteur_cm", 45),
                    "raw_w": v.get("largeur_cm", 60),
                    "fits": True,
                    "exceeds_by": 0.0
                })

        total_linear_cm = sum(s["length"] for s in stripes)
        total_linear_m = round(total_linear_cm / 100.0, 2)
        total_used_cm2 = total_linear_cm * laize_cm
        cut_area_cm2 = sum(p["height_on_laize"] * p["width_on_roll"] for p in placed)
        eff_pct = round((cut_area_cm2 / total_used_cm2 * 100.0), 1) if total_used_cm2 > 0 else 0.0

        # Construction du plan de coupe en SVG interactif
        svg_code = StrictHorizontalNestingEngine._generate_svg(placed, laize_cm, total_linear_cm, total_linear_m, has_seam_warning)

        return {
            "placed": placed,
            "unfitted": unfitted,
            "total_linear_cm": total_linear_cm,
            "total_linear_m": total_linear_m,
            "surface_used_m2": round(total_used_cm2 / 10000.0, 3),
            "surface_cut_m2": round(cut_area_cm2 / 10000.0, 3),
            "efficiency_pct": eff_pct,
            "has_seam_warning": has_seam_warning,
            "svg_html": svg_code
        }

    @staticmethod
    def _generate_svg(placed: List[Dict[str, Any]], laize_cm: float, total_cm: float, total_m: float, has_seam: bool) -> str:
        view_len = max(100.0, total_cm + 20)
        scale = 3.5
        roll_w = laize_cm * scale
        roll_h = view_len * scale
        pad_x = 40
        pad_y = 35

        svg_w = roll_w + (pad_x * 2) + 70
        svg_h = max(280, roll_h + (pad_y * 2))

        rects = []
        for p in placed:
            x = pad_x + (p["x"] * scale)
            y = pad_y + (p["y"] * scale)
            w = p["height_on_laize"] * scale
            h = p["width_on_roll"] * scale
            exceeds = not p.get("fits", True)

            fill_color = "rgba(127, 29, 29, 0.7)" if exceeds else ("rgba(225, 6, 0, 0.4)" if p["zone"] == "arriere" else "rgba(63, 63, 70, 0.6)")
            stroke_color = "#ef4444" if exceeds else ("#E10600" if p["zone"] == "arriere" else "#a1a1aa")

            txt_info = f"{p['nom'][:14]} ({p['height_on_laize']:.0f}×{p['width_on_roll']:.0f}cm)"
            if exceeds:
                txt_info += f" ⚠️ +{p['exceeds_by']:.0f}cm"

            rects.append(f"""
                <g>
                    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3"
                          fill="{fill_color}" stroke="{stroke_color}" stroke-width="1.5" />
                    <text x="{x + (w/2)}" y="{y + (h/2)}" font-size="10" font-family="sans-serif"
                          font-weight="bold" fill="#ffffff" text-anchor="middle" dominant-baseline="middle">
                        {txt_info}
                    </text>
                </g>
            """)

        seam_badge = """
            <text x="20" y="22" font-size="11" font-weight="bold" fill="#ef4444" font-family="sans-serif">
                ⚠️ ALERTE RACCORD : Une hauteur dépasse la laize du rouleau (rouleau plus large requis)
            </text>
        """ if has_seam else ""

        svg = f"""
        <div style="background:#09090b; border:1px solid #27272a; border-radius:8px; padding:10px; overflow-x:auto;">
            <svg width="100%" height="{min(420, int(svg_h))}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg">
                {seam_badge}
                <!-- Rouleau de film -->
                <rect x="{pad_x}" y="{pad_y}" width="{roll_w}" height="{roll_h}"
                      fill="#121215" stroke="#3f3f46" stroke-width="2" rx="4" />
                
                <!-- Règle de laize supérieure -->
                <text x="{pad_x + (roll_w / 2)}" y="{pad_y - 10}" font-size="11" font-family="sans-serif"
                      font-weight="bold" fill="#a1a1aa" text-anchor="middle">
                    ← Laize du rouleau : {laize_cm:.0f} cm →
                </text>

                <!-- Découpes positionnées -->
                {''.join(rects)}

                <!-- Règle latérale de métrage linéaire -->
                <line x1="{pad_x + roll_w + 12}" y1="{pad_y}" x2="{pad_x + roll_w + 12}" y2="{pad_y + (total_cm * scale)}"
                      stroke="#E10600" stroke-width="2" />
                <text x="{pad_x + roll_w + 20}" y="{pad_y + ((total_cm * scale) / 2)}"
                      font-size="12" font-weight="bold" fill="#E10600" font-family="monospace">
                    {total_m:.2f} m
                </text>
            </svg>
        </div>
        """
        return svg


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
# GÉNÉRATEUR DE DEVIS PDF ÉPURÉ (WRAD)
# =============================================================================
class WradPDFGenerator:
    """
    Générateur de devis PDF vectoriel épuré pour l'atelier Wrad.
    Suppression stricte des éléments superflus :
    - Aucun slogan 'automotive tinting'
    - Aucune description 'pose de films solaire haut de gamme & sécurité automobile'
    - Aucun bloc argumentaire (Esthétique, Confort, Intimité, Protection 99% UV)
    - Aucun bloc 'Engagements & Réglementations'
    - Aucune mention 'Validité de l'offre'
    """

    @staticmethod
    def generate_pdf_bytes(
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
    ) -> Optional[bytes]:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm

            buf = io.BytesIO()
            doc = SimpleDocTemplate(
                buf,
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

            title_style = ParagraphStyle('WradTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=colors.black)
            contact_style = ParagraphStyle('WradContact', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=text_muted)
            meta_right_style = ParagraphStyle('WradMetaRight', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=15, alignment=2, textColor=red_wrad)
            meta_date_style = ParagraphStyle('WradMetaDate', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, alignment=2, textColor=text_muted)
            section_title = ParagraphStyle('WradSection', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=text_dark, spaceAfter=4)
            table_header = ParagraphStyle('WradTH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white)
            table_cell = ParagraphStyle('WradTD', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=text_dark)
            table_cell_bold = ParagraphStyle('WradTDBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=text_dark)
            table_cell_price = ParagraphStyle('WradTDPrice', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, alignment=2, textColor=red_wrad)

            story = []

            # 1. En-tête épuré et coordonnées Wrad
            header_data = [
                [Paragraph("<b>WRAD</b>", title_style), Paragraph(f"DEVIS N° {devis_num}", meta_right_style)],
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

            # 2. Coordonnées client & véhicule
            marque = vehicule.get('marque', '')
            modele = vehicule.get('modele', '')
            annee = vehicule.get('annee', '')
            gen = vehicule.get('generation', '')
            veh_str = f"<b>{marque} {modele}</b>" + (f" ({annee})" if annee else "")
            if gen and gen != "Estimé par IA":
                veh_str += f"<br/><font color='#71717A' size='8'>{gen}</font>"

            client_str = f"<b>{client_nom}</b>" if client_nom else "Client Particulier / Professionnel"

            info_data = [
                [Paragraph("<b>COORDONNÉES CLIENT</b>", section_title), Paragraph("<b>VÉHICULE CONCERNÉ</b>", section_title)],
                [Paragraph(f"{client_str}<br/><font color='#71717A'>Pose de films solaires</font>", table_cell), Paragraph(veh_str, table_cell)]
            ]
            if roll_nom:
                info_data.append([
                    Paragraph("", table_cell),
                    Paragraph(f"<font color='#71717A' size='8'>Film sélectionné : {roll_nom} (Laize {laize_cm:.0f} cm)</font>", table_cell)
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

            # 3. Tableau des prestations & chiffrage
            story.append(Paragraph("<b>PRESTATION &amp; TARIFICATION</b>", section_title))
            table_content = [
                [Paragraph("Prestation", table_header), Paragraph("Détails des vitres incluses", table_header), Paragraph("Métrage", table_header), Paragraph("Tarif TTC", table_header)],
                [Paragraph(prestation_title, table_cell_bold), Paragraph(prestation_desc, table_cell), Paragraph(f"{metrage_m:.2f} m", table_cell), Paragraph(f"<b>{prix_ttc:.2f} €</b>", table_cell_price)],
                [Paragraph("<b>TOTAL CONSEILLÉ TTC</b>", table_cell_bold), Paragraph("", table_cell), Paragraph(f"<b>{metrage_m:.2f} m</b>", table_cell_bold), Paragraph(f"<b>{prix_ttc:.2f} € TTC</b>", table_cell_price)]
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

            # 4. Bas de page épuré
            story.append(HRFlowable(width="100%", thickness=0.5, color=border_gray, spaceAfter=8))
            footer_text = Paragraph(
                "<font color='#71717A' size='8'>Atelier WRAD • Poitiers &amp; alentours • 07 67 60 10 98 • wradauto@gmail.com • Devis professionnel épuré</font>",
                ParagraphStyle('Footer', alignment=1, fontName='Helvetica', fontSize=8)
            )
            story.append(footer_text)

            doc.build(story)
            buf.seek(0)
            return buf.getvalue()
        except Exception as e:
            st.error(f"Erreur de création du PDF : {e}")
            return None


# =============================================================================
# APPLICATION PRINCIPALE STREAMLIT
# =============================================================================

# Configuration de la page Streamlit
st.set_page_config(
    page_title="WRAD - Tint Studio | Métrage & Rentabilité",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injection de style CSS Wrad (Sombre & Rouge Course)
st.markdown(f"""
<style>
    /* Thème global Wrad */
    .stApp {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_TEXT_WHITE};
    }}
    /* En-tête et boutons */
    .stButton>button {{
        background-color: {COLOR_RED_WRAD};
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        transition: 0.2s;
    }}
    .stButton>button:hover {{
        background-color: {COLOR_RED_HOVER};
        color: white;
    }}
    /* Métriques financières */
    [data-testid="stMetricValue"] {{
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        color: {COLOR_PRICE_GOLD} !important;
    }}
    /* Onglets */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {COLOR_PANEL};
        border-radius: 8px 8px 0px 0px;
        padding: 8px 16px;
        color: {COLOR_TEXT_MUTED};
        font-weight: bold;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COLOR_CARD} !important;
        color: {COLOR_RED_WRAD} !important;
        border-bottom: 2px solid {COLOR_RED_WRAD} !important;
    }}
</style>
""", unsafe_allow_html=True)

# Initialisation du Session State
if "rolls" not in st.session_state:
    st.session_state["rolls"] = PersistenceManager.load_rolls()

if "active_roll_idx" not in st.session_state:
    st.session_state["active_roll_idx"] = 0

if "coeff_prix" not in st.session_state:
    st.session_state["coeff_prix"] = 2.0

if "marge_coupe" not in st.session_state:
    st.session_state["marge_coupe"] = 5.0

if "vitres_data" not in st.session_state:
    st.session_state["vitres_data"] = [
        {"nom": "Lunette arrière", "hauteur_cm": 52, "largeur_cm": 98, "zone": "arriere", "included": True},
        {"nom": "Vitre latérale arrière gauche", "hauteur_cm": 44, "largeur_cm": 56, "zone": "arriere", "included": True},
        {"nom": "Vitre latérale arrière droite", "hauteur_cm": 44, "largeur_cm": 56, "zone": "arriere", "included": True},
        {"nom": "Custode arrière gauche", "hauteur_cm": 28, "largeur_cm": 22, "zone": "arriere", "included": True},
        {"nom": "Custode arrière droite", "hauteur_cm": 28, "largeur_cm": 22, "zone": "arriere", "included": True},
        {"nom": "Vitre latérale avant gauche", "hauteur_cm": 48, "largeur_cm": 72, "zone": "avant", "included": True},
        {"nom": "Vitre latérale avant droite", "hauteur_cm": 48, "largeur_cm": 72, "zone": "avant", "included": True},
    ]

if "current_vehicle_info" not in st.session_state:
    st.session_state["current_vehicle_info"] = {
        "marque": "Peugeot",
        "modele": "208",
        "annee": "2020",
        "generation": "Génération II (2019-2024)"
    }

# =============================================================================
# BARRE LATÉRALE (PARAMÈTRES ROULEAUX & SUPABASE)
# =============================================================================
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px;">
            <div style="font-size:26px; font-weight:900; color:#FFFFFF; letter-spacing:-1px;">WRAD</div>
            <div style="font-size:10px; font-weight:bold; background:#450a0a; color:#E10600; padding:2px 6px; border-radius:4px; border:1px solid #E10600;">TINT STUDIO</div>
        </div>
        <div style="font-size:11px; color:#a1a1aa; margin-top:-10px; margin-bottom:15px;">
            Poitiers &amp; alentours • Tél: 07 67 60 10 98 • @wradauto
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ Rouleau & Tarifs")

    # Sélection du rouleau actif
    rolls = st.session_state["rolls"]
    roll_names = [r["nom"] for r in rolls]
    selected_name = st.selectbox("Rouleau de film actif", roll_names, index=min(st.session_state["active_roll_idx"], len(rolls) - 1))
    st.session_state["active_roll_idx"] = roll_names.index(selected_name)
    active_roll = rolls[st.session_state["active_roll_idx"]]

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        prix_rouleau = st.number_input("Prix d'achat TTC (€)", value=float(active_roll["prix_achat_ttc"]), min_value=10.0, step=5.0)
        active_roll["prix_achat_ttc"] = prix_rouleau
    with col_r2:
        st.session_state["coeff_prix"] = st.number_input("Coefficient (x)", value=float(st.session_state["coeff_prix"]), min_value=1.0, max_value=10.0, step=0.1)

    cost_per_m = active_roll["prix_achat_ttc"] / active_roll["longueur_m"] if active_roll["longueur_m"] > 0 else 0
    st.caption(f"Laize: **{active_roll['laize_cm']} cm** • Longueur: **{active_roll['longueur_m']} m** • Coût: **{cost_per_m:.3f} €/m**")

    # Gestion des rouleaux (Ajout & Renommage)
    with st.expander("🛠️ Gérer / Ajouter des Rouleaux"):
        st.markdown("**Ajouter un nouveau format :**")
        new_r_nom = st.text_input("Nom / Réf du rouleau", placeholder="Ex: Teinte 5% Carbone")
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            new_r_lz = st.number_input("Laize (cm)", value=76, step=5)
        with c_a2:
            new_r_lg = st.number_input("Longueur (m)", value=30, step=5)
        new_r_px = st.number_input("Prix d'achat TTC (€)", value=188, step=10)

        if st.button("➕ Enregistrer ce rouleau"):
            if new_r_nom.strip():
                new_roll = {
                    "id": f"roll-{len(rolls) + 1}",
                    "nom": new_r_nom.strip(),
                    "laize_cm": float(new_r_lz),
                    "longueur_m": float(new_r_lg),
                    "prix_achat_ttc": float(new_r_px)
                }
                rolls.append(new_roll)
                st.session_state["rolls"] = rolls
                PersistenceManager.save_rolls(rolls)
                st.success("Nouveau rouleau ajouté avec succès !")
                st.rerun()

    # Statut Supabase
    st.markdown("---")
    st.markdown("""
        <div style="font-size:12px; color:#22c55e; display:flex; align-items:center; gap:6px;">
            <span style="height:8px; width:8px; background:#22c55e; border-radius:50%; display:inline-block;"></span>
            <strong>Supabase Cloud Connecté</strong>
        </div>
        <div style="font-size:10px; color:#a1a1aa; margin-top:2px;">
            Synchronisation temps réel PC &amp; Mobile active
        </div>
    """, unsafe_allow_html=True)


# =============================================================================
# ONGLETS PRINCIPAUX DE L'APPLICATION
# =============================================================================
tab_estimator, tab_database, tab_clients = st.tabs([
    "⚡ 1. Estimateur & Plan de Coupe",
    "📁 2. Base de Données Véhicules",
    "💼 3. Suivi Clients & Rentabilité"
])

# -----------------------------------------------------------------------------
# ONGLET 1 : ESTIMATEUR & PLAN DE COUPE
# -----------------------------------------------------------------------------
with tab_estimator:
    st.subheader("Estimation & Découpe Horizontale")

    # Barre de recherche véhicule
    col_v1, col_v2, col_v3, col_v4 = st.columns([2, 2, 1.5, 2])
    with col_v1:
        s_marque = st.text_input("Marque", value=st.session_state["current_vehicle_info"].get("marque", "Peugeot"))
    with col_v2:
        s_modele = st.text_input("Modèle", value=st.session_state["current_vehicle_info"].get("modele", "208"))
    with col_v3:
        s_annee = st.text_input("Année", value=st.session_state["current_vehicle_info"].get("annee", "2020"))
    with col_v4:
        st.write("")
        st.write("")
        btn_search = st.button("⚡ Estimer / Rechercher", use_container_width=True)

    # Exécution de la recherche / estimation
    if btn_search:
        key = f"{s_marque.lower().strip()}_{s_modele.lower().strip()}_{s_annee.lower().strip()}"
        db = PersistenceManager.load_database()

        found = None
        if key in db:
            found = db[key]
        else:
            for k, v in db.items():
                if v.get("marque", "").lower() == s_marque.lower() and v.get("modele", "").lower() == s_modele.lower():
                    found = v
                    break

        if found:
            st.session_state["vitres_data"] = found.get("vitres", [])
            st.session_state["current_vehicle_info"] = found
            st.success(f"Véhicule chargé depuis la base Supabase / database.json ({len(found.get('vitres', []))} vitres)")
        else:
            # Appel IA Gemini
            try:
                res = GeminiEstimator.estimate(s_marque, s_modele, s_annee)
                st.session_state["vitres_data"] = res.get("vitres", [])
                st.session_state["current_vehicle_info"] = {
                    "marque": s_marque,
                    "modele": s_modele,
                    "annee": s_annee,
                    "generation": res.get("generation", "Estimé par IA"),
                    "vitres": res.get("vitres", [])
                }
                # Enregistrement dans Supabase
                PersistenceManager.save_vehicle(key, st.session_state["current_vehicle_info"])
                st.success(f"Dimensions estimées par IA et enregistrées dans Supabase !")
            except Exception as e:
                st.warning(f"Mode local actif : {e}")

    # Calculs de métrage & Nesting
    laize_active = float(active_roll["laize_cm"])
    marge_active = float(st.session_state["marge_coupe"])
    coeff = float(st.session_state["coeff_prix"])

    # Vitres arrière vs avant
    vitres_arr = [v for v in st.session_state["vitres_data"] if v.get("zone") == "arriere"]
    vitres_av = [v for v in st.session_state["vitres_data"] if v.get("zone") == "avant"]

    nest_arr = StrictHorizontalNestingEngine.compute(vitres_arr, laize_active, marge_active)
    nest_av = StrictHorizontalNestingEngine.compute(vitres_av, laize_active, marge_active)
    nest_tot = StrictHorizontalNestingEngine.compute(st.session_state["vitres_data"], laize_active, marge_active)

    # Chiffrages
    cout_arr = nest_arr["total_linear_m"] * cost_per_m
    prix_arr = cout_arr * coeff

    cout_av = nest_av["total_linear_m"] * cost_per_m
    prix_av = cout_av * coeff

    cout_tot = nest_tot["total_linear_m"] * cost_per_m
    prix_tot = cout_tot * coeff

    # Numéro et date du devis
    num_devis = f"WRAD-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M')}"
    date_str = datetime.now().strftime("%d/%m/%Y")

    # Affichage des 3 cartes financières avec boutons Devis dédiés
    st.markdown("#### 💰 Chiffrages & Devis par Prestation")
    card_col1, card_col2, card_col3 = st.columns(3)

    with card_col1:
        st.markdown(f"""
            <div style="background:{COLOR_PANEL}; border:1px solid {COLOR_BORDER}; padding:14px; border-radius:10px;">
                <div style="font-weight:bold; color:{COLOR_RED_WRAD}; font-size:14px;">PACK 3/4 ARRIÈRE</div>
                <div style="font-size:11px; color:#a1a1aa; margin-top:2px;">Lunette + latérales arrière + custodes</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:10px;">
                    <div>
                        <div style="font-size:10px; color:#a1a1aa;">Métrage requis</div>
                        <div style="font-size:18px; font-weight:bold; color:#ffffff;">{nest_arr['total_linear_m']:.2f} m</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:10px; color:#a1a1aa;">Tarif conseillé TTC</div>
                        <div style="font-size:22px; font-weight:900; color:{COLOR_PRICE_GOLD};">{prix_arr:.2f} €</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        pdf_arr_bytes = WradPDFGenerator.generate_pdf_bytes(
            devis_num=num_devis,
            date_str=date_str,
            vehicule=st.session_state["current_vehicle_info"],
            prestation_title="PACK 3/4 ARRIÈRE",
            prestation_desc="Lunette arrière + vitres latérales arrière + custodes arrière",
            metrage_m=nest_arr["total_linear_m"],
            prix_ttc=prix_arr,
            roll_nom=active_roll["nom"],
            laize_cm=laize_active
        )
        if pdf_arr_bytes:
            st.download_button(
                label="📄 Télécharger Devis 3/4 Arrière (PDF)",
                data=pdf_arr_bytes,
                file_name=f"Devis_WRAD_{s_marque}_{s_modele}_Arriere.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_pdf_arr"
            )

    with card_col2:
        st.markdown(f"""
            <div style="background:{COLOR_PANEL}; border:1px solid {COLOR_BORDER}; padding:14px; border-radius:10px;">
                <div style="font-weight:bold; color:#FFFFFF; font-size:14px;">PACK VITRES AVANT</div>
                <div style="font-size:11px; color:#a1a1aa; margin-top:2px;">Vitres latérales avant + custodes avant</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:10px;">
                    <div>
                        <div style="font-size:10px; color:#a1a1aa;">Métrage requis</div>
                        <div style="font-size:18px; font-weight:bold; color:#ffffff;">{nest_av['total_linear_m']:.2f} m</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:10px; color:#a1a1aa;">Tarif conseillé TTC</div>
                        <div style="font-size:22px; font-weight:900; color:{COLOR_PRICE_GOLD};">{prix_av:.2f} €</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        pdf_av_bytes = WradPDFGenerator.generate_pdf_bytes(
            devis_num=num_devis,
            date_str=date_str,
            vehicule=st.session_state["current_vehicle_info"],
            prestation_title="PACK VITRES AVANT",
            prestation_desc="Vitres latérales avant + custodes avant (Conforme TLV ≥ 70%)",
            metrage_m=nest_av["total_linear_m"],
            prix_ttc=prix_av,
            roll_nom=active_roll["nom"],
            laize_cm=laize_active
        )
        if pdf_av_bytes:
            st.download_button(
                label="📄 Télécharger Devis Vitres Avant (PDF)",
                data=pdf_av_bytes,
                file_name=f"Devis_WRAD_{s_marque}_{s_modele}_Avant.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_pdf_av"
            )

    with card_col3:
        st.markdown(f"""
            <div style="background:#1c1414; border:1px solid {COLOR_RED_WRAD}; padding:14px; border-radius:10px;">
                <div style="font-weight:bold; color:{COLOR_RED_WRAD}; font-size:14px;">TOTAL VÉHICULE COMPLET</div>
                <div style="font-size:11px; color:#a1a1aa; margin-top:2px;">Ensemble des vitres avant et arrière</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:10px;">
                    <div>
                        <div style="font-size:10px; color:#a1a1aa;">Métrage global</div>
                        <div style="font-size:18px; font-weight:bold; color:#ffffff;">{nest_tot['total_linear_m']:.2f} m</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:10px; color:#a1a1aa;">Total recommandé</div>
                        <div style="font-size:22px; font-weight:900; color:{COLOR_PRICE_GOLD};">{prix_tot:.2f} €</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        pdf_tot_bytes = WradPDFGenerator.generate_pdf_bytes(
            devis_num=num_devis,
            date_str=date_str,
            vehicule=st.session_state["current_vehicle_info"],
            prestation_title="VÉHICULE COMPLET (TOUS PACKS)",
            prestation_desc="Lunette arrière + latérales arrière + custodes arrière + vitres avant",
            metrage_m=nest_tot["total_linear_m"],
            prix_ttc=prix_tot,
            roll_nom=active_roll["nom"],
            laize_cm=laize_active
        )
        if pdf_tot_bytes:
            st.download_button(
                label="📄 Télécharger Devis Complet (PDF)",
                data=pdf_tot_bytes,
                file_name=f"Devis_WRAD_{s_marque}_{s_modele}_Complet.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_pdf_tot"
            )

    st.markdown("---")

    # Split interactif : Tableau des dimensions à gauche & Plan de coupe à droite
    col_table, col_plan = st.columns([1.1, 1])

    with col_table:
        st.markdown("##### 📋 Cotes des Vitres (Modifiables en direct)")
        st.caption("Sens horizontal strict : Hauteur ➜ Laize | Largeur ➜ Longueur déroulé")

        # Tableau éditable natif Streamlit
        edited_vitres = st.data_editor(
            st.session_state["vitres_data"],
            column_config={
                "included": st.column_config.CheckboxColumn("Inclus", default=True),
                "nom": st.column_config.TextColumn("Nom de la vitre", required=True),
                "hauteur_cm": st.column_config.NumberColumn("Hauteur (cm)", min_value=5, max_value=200, step=1, required=True),
                "largeur_cm": st.column_config.NumberColumn("Largeur (cm)", min_value=5, max_value=300, step=1, required=True),
                "zone": st.column_config.SelectboxColumn("Zone", options=["arriere", "avant"], required=True),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="vitres_editor"
        )
        st.session_state["vitres_data"] = edited_vitres

        if st.button("💾 Sauvegarder cette fiche véhicule dans Supabase"):
            key = f"{s_marque.lower().strip()}_{s_modele.lower().strip()}_{s_annee.lower().strip()}"
            veh_to_save = {
                "marque": s_marque,
                "modele": s_modele,
                "annee": s_annee,
                "generation": st.session_state["current_vehicle_info"].get("generation", "Manuel"),
                "vitres": edited_vitres
            }
            PersistenceManager.save_vehicle(key, veh_to_save)
            st.success(f"Fiche {s_marque} {s_modele} enregistrée en direct sur Supabase !")

    with col_plan:
        st.markdown(f"##### 📐 Plan de Coupe 2D (Laize {laize_active:.0f} cm)")
        st.caption(f"Efficacité matière : **{nest_tot['efficiency_pct']}%** • Déroulé : **{nest_tot['total_linear_m']:.2f} m** ({nest_tot['total_linear_cm']:.0f} cm)")

        if nest_tot.get("svg_html"):
            st.markdown(nest_tot["svg_html"], unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# ONGLET 2 : BASE DE DONNÉES VÉHICULES (SUPABASE)
# -----------------------------------------------------------------------------
with tab_database:
    st.subheader("Base de Données Véhicules & Cotes (Supabase Cloud)")
    st.caption("Consultez, modifiez et enrichissez votre catalogue de vitrages sauvegardé en ligne.")

    db_vehicles = PersistenceManager.load_database()

    search_db = st.text_input("🔍 Filtrer les véhicules par marque ou modèle...", "")
    filtered_keys = [
        k for k, v in db_vehicles.items()
        if search_db.lower() in v.get("marque", "").lower()
        or search_db.lower() in v.get("modele", "").lower()
        or search_db.lower() in v.get("generation", "").lower()
    ]

    st.markdown(f"**{len(filtered_keys)}** véhicules trouvés dans Supabase :")

    for k in filtered_keys:
        v = db_vehicles[k]
        with st.container():
            c1, c2, c3 = st.columns([3, 1.5, 1])
            with c1:
                st.markdown(f"**{v.get('marque')} {v.get('modele')}** ({v.get('annee', 'N/A')})")
                st.caption(f"{v.get('generation', '')} • {len(v.get('vitres', []))} vitres enregistrées")
            with c2:
                if st.button("⚡ Charger dans l'estimateur", key=f"load_{k}", use_container_width=True):
                    st.session_state["vitres_data"] = v.get("vitres", [])
                    st.session_state["current_vehicle_info"] = v
                    st.success(f"Véhicule {v.get('marque')} {v.get('modele')} chargé !")
                    st.rerun()
            with c3:
                if st.button("🗑️", key=f"del_{k}", help="Supprimer de Supabase"):
                    PersistenceManager.delete_vehicle(k)
                    st.warning("Véhicule supprimé de Supabase.")
                    st.rerun()
            st.markdown("<hr style='margin:4px 0 12px 0; border-color:#27272a;'>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# ONGLET 3 : SUIVI CLIENTS & RENTABILITÉ (SUPABASE)
# -----------------------------------------------------------------------------
with tab_clients:
    st.subheader("Suivi Commercial & Rentabilité Réelle Wrad")
    st.caption("Données synchronisées en direct avec Supabase entre votre ordinateur et votre smartphone.")

    clients_list = PersistenceManager.load_clients()

    # Calcul des totaux KPI
    tot_ca = sum(float(c.get("prixFactureTTC", 0)) for c in clients_list)
    tot_cout = sum(float(c.get("coutRevientTTC", 0)) for c in clients_list)
    tot_benef = tot_ca - tot_cout
    tot_metres = sum(float(c.get("metrageUtiliseM", 0)) for c in clients_list)
    avg_marge = (tot_benef / tot_ca * 100.0) if tot_ca > 0 else 0.0

    # Affichage des métriques financières
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Chiffre d'Affaires Total", f"{tot_ca:.2f} €", f"{len(clients_list)} prestations")
    kpi2.metric("Coût Matière Total", f"{tot_cout:.2f} €")
    kpi3.metric("Bénéfice Net Réel", f"+{tot_benef:.2f} €", f"Marge : {avg_marge:.1f}%")
    kpi4.metric("Métrage Total Posé", f"{tot_metres:.2f} m")

    st.markdown("---")

    # Formulaire de saisie d'une nouvelle pose client
    with st.expander("➕ Enregistrer une Prestation & Calculer la Rentabilité", expanded=True):
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            in_cli_nom = st.text_input("Nom du Client / Garage *", placeholder="Ex: M. Dupont ou Garage XYZ")
            in_cli_veh = st.text_input("Véhicule Traité *", value=f"{st.session_state['current_vehicle_info'].get('marque', '')} {st.session_state['current_vehicle_info'].get('modele', '')}".strip())
            in_cli_pack = st.selectbox("Prestation Réalisée", ["Pack 3/4 Arrière", "Pack Vitres Avant", "Véhicule Complet", "Sur Mesure"])

        with f_c2:
            in_cli_metres = st.number_input("Métrage linéaire réel utilisé (m)", value=float(nest_tot["total_linear_m"]) or 2.0, step=0.1)
            in_cli_prix = st.number_input("Prix réellement facturé TTC (€)", value=float(prix_tot) or 150.0, step=10.0)
            in_cli_notes = st.text_input("Notes (optionnel)", placeholder="Ex: Teinte 15% - pose à domicile")

        # Calculs instantanés du formulaire
        cout_revient = round(in_cli_metres * cost_per_m, 2)
        benef_net = round(in_cli_prix - cout_revient, 2)
        marge_pct = round((benef_net / in_cli_prix * 100.0), 1) if in_cli_prix > 0 else 0.0

        st.info(f"💡 Coût matière estimé : **{cout_revient:.2f} €** ➜ **Bénéfice net réalisé : +{benef_net:.2f} €** ({marge_pct}% de marge)")

        if st.button("Enregistrer la Prestation sur Supabase", use_container_width=True):
            if in_cli_nom.strip() and in_cli_veh.strip():
                new_record = {
                    "id": f"cli-{int(datetime.now().timestamp())}",
                    "clientNom": in_cli_nom.strip(),
                    "vehicule": in_cli_veh.strip(),
                    "datePose": datetime.now().strftime("%Y-%m-%d"),
                    "pack": in_cli_pack,
                    "metrageUtiliseM": in_cli_metres,
                    "prixFactureTTC": in_cli_prix,
                    "coutRevientTTC": cout_revient,
                    "beneficeNetTTC": benef_net,
                    "tauxMargePercent": marge_pct,
                    "notes": in_cli_notes.strip()
                }
                PersistenceManager.save_client_record(new_record)
                st.success(f"Prestation enregistrée avec succès dans Supabase ! Bénéfice : +{benef_net:.2f} €")
                st.rerun()
            else:
                st.error("Le nom du client et le véhicule sont obligatoires.")

    # Tableau des prestations enregistrées
    st.markdown("##### Historique des Poses Clients (Temps Réel)")
    if clients_list:
        table_data = []
        for c in clients_list:
            table_data.append({
                "Date": c.get("datePose"),
                "Client": c.get("clientNom"),
                "Véhicule": c.get("vehicule"),
                "Pack": c.get("pack"),
                "Métrage (m)": f"{float(c.get('metrageUtiliseM', 0)):.2f} m",
                "Facturé TTC": f"{float(c.get('prixFactureTTC', 0)):.2f} €",
                "Coût Matière": f"{float(c.get('coutRevientTTC', 0)):.2f} €",
                "Bénéfice Net": f"+{float(c.get('beneficeNetTTC', 0)):.2f} €",
                "Marge": f"{float(c.get('tauxMargePercent', 0)):.1f}%",
                "ID": c.get("id")
            })

        st.dataframe(table_data, use_container_width=True)

        # Export CSV
        csv_buffer = io.StringIO()
        csv_buffer.write("ID,Date,Client,Vehicule,Pack,Metrage_m,Prix_Facture_TTC,Cout_Revient_TTC,Benefice_Net_TTC,Taux_Marge_Pct\n")
        for c in clients_list:
            csv_buffer.write(f'"{c.get("id")}","{c.get("datePose")}","{c.get("clientNom")}","{c.get("vehicule")}","{c.get("pack")}",{c.get("metrageUtiliseM")},{c.get("prixFactureTTC")},{c.get("coutRevientTTC")},{c.get("beneficeNetTTC")},{c.get("tauxMargePercent")}\n')

        st.download_button(
            label="📥 Exporter la comptabilité clients en CSV",
            data=csv_buffer.getvalue(),
            file_name=f"Wrad_Suivi_Clients_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Aucune prestation client enregistrée pour l'instant dans Supabase.")
