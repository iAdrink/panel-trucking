#!/usr/bin/env python3
"""Genera data.json para el panel a partir de la respuesta de Brevo.

Uso: python3 build_data.py brevo_campaigns.json
  brevo_campaigns.json = respuesta tal cual de
  email_campaign_management_get_email_campaigns (statistics=globalStats).
Lee además los ficheros fijos de static/ y escribe data.json.
Solo publica totales y cifras de campañas: ningún dato personal de leads.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
MIAMI = ZoneInfo("America/New_York")
ESTADOS = {"queued": "Programada", "sent": "Enviada", "draft": "Borrador",
           "inProcess": "Enviando", "suspended": "Pausada", "cancelled": "Cancelada"}


def load(p):
    return json.loads((HERE / p).read_text(encoding="utf-8"))


def brevo_rows(answer):
    rows = []
    for c in answer.get("campaigns", []):
        if c.get("status") == "archive":
            continue
        st = (c.get("statistics") or {})
        g = st.get("globalStats") or {}
        name = c.get("name", "")
        m = re.search(r"O(\d)", name)
        idioma = "EN" if " EN " in name + " " else "ES" if " ES " in name + " " else ""
        version = "B · Plantilla" if "B-plantilla" in name else "A · Corto" if "A-corto" in name else "Corto"
        when = c.get("sentDate") or c.get("scheduledAt")
        fecha = hora = ""
        if when:
            d = datetime.fromisoformat(when.replace("Z", "+00:00")).astimezone(MIAMI)
            fecha, hora = d.strftime("%Y-%m-%d"), d.strftime("%-H:%M")
        sent = int(g.get("sent") or 0)
        enviado = c.get("status") == "sent" or sent > 0
        rows.append({
            "campana": name, "plataforma": "Brevo", "ola": int(m.group(1)) if m else None,
            "idioma": idioma, "version": version, "fecha": fecha, "hora_miami": hora,
            "contactos": sent + int(st.get("remaining") or 0),
            "estado": ESTADOS.get(c.get("status"), c.get("status")),
            "enviados": sent if enviado else None,
            "aperturas": int(g.get("uniqueViews") or 0) if enviado else None,
            "clics": int(g.get("uniqueClicks") or 0) if enviado else None,
            "rebotes": int(g.get("hardBounces") or 0) + int(g.get("softBounces") or 0) if enviado else None,
            "bajas": int(g.get("unsubscriptions") or 0) if enviado else None,
            "respuestas": None,
        })
    return rows


def main(src):
    answer = json.loads(Path(src).read_text(encoding="utf-8"))
    leads = load("static/leads_verificados.json")
    momentum = load("static/momentum_envio1.json")
    rebotes_oct = sum(r["rebotes"] for r in load("static/rebotes_envio1.json"))
    resp = load("static/respuestas.json") if (HERE / "static/respuestas.json").exists() else {}

    campanas = momentum + brevo_rows(answer)
    for r in campanas:
        if r["campana"] in resp:
            r["respuestas"] = resp[r["campana"]]

    s = lambda rows, k: sum((r.get(k) or 0) for r in rows)
    enviados = s(campanas, "enviados")
    aperturas = s(campanas, "aperturas")
    rebotes = s(campanas, "rebotes") + rebotes_oct
    g = lambda k: sum(r["contactos"] for r in leads if r["grupo"] == k)
    kpis = {
        "enviables": g("Enviar"), "dudosos": g("Dudoso"), "descartados": g("Descartado"),
        "programados": s([r for r in campanas if r["estado"] == "Programada"], "contactos"),
        "enviados": enviados, "aperturas": aperturas,
        "tasa_apertura": aperturas / enviados if enviados else None,
        "rebotes": rebotes, "tasa_rebote": rebotes / enviados if enviados else None,
        "respuestas": s(campanas, "respuestas"),
    }

    prog = sorted([r for r in campanas if r["estado"] == "Programada" and r["fecha"]], key=lambda r: r["fecha"])
    proximo = None
    if prog:
        f = prog[0]["fecha"]
        dia = [r for r in prog if r["fecha"] == f]
        proximo = {"fecha": f, "campanas": len(dia), "contactos": sum(r["contactos"] for r in dia)}

    por_dia = {}
    for r in campanas:
        if r["plataforma"] == "Brevo" and r["fecha"]:
            por_dia[r["fecha"]] = por_dia.get(r["fecha"], 0) + r["contactos"]

    olas = {}
    meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril"}
    for r in leads:
        k = r["ola"]
        o = olas.setdefault(k, {"ola": f"{k} · {meses.get(k, '')}", "Enviar": 0, "Dudoso": 0, "Descartado": 0})
        o[r["grupo"]] += r["contactos"]

    ab = {}
    for r in campanas:
        if r["ola"] != 2:
            continue
        o = ab.setdefault(r["version"], {"version": r["version"], "fecha": r["fecha"], "contactos": 0,
                                         "enviados": None, "aperturas": None, "respuestas": None})
        o["contactos"] += r["contactos"]
        for k in ("enviados", "aperturas", "respuestas"):
            if r[k] is not None:
                o[k] = (o[k] or 0) + r[k]
    for o in ab.values():
        o["resp_por_100"] = (o["respuestas"] or 0) / o["enviados"] * 100 if o["enviados"] else None

    out = {
        "actualizado": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "kpis": kpis, "proximo": proximo,
        "por_dia": [{"fecha": k, "contactos": v} for k, v in sorted(por_dia.items())],
        "leads_por_ola": [olas[k] for k in sorted(olas)],
        "ab": sorted(ab.values(), key=lambda o: o["version"]),
        "campanas": sorted(campanas, key=lambda r: (r["fecha"] or "9", r["campana"])),
    }
    (HERE / "data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data.json: {len(campanas)} campañas, {enviados} enviados")


if __name__ == "__main__":
    main(sys.argv[1])
