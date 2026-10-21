"""Synthetic personas comment on any question, each from its own life (live model).

    python -m src.simulation.comments "Kira zammı hakkında ne düşünüyorsunuz?"

A weighted sample of the synthetic personas (personas_synthetic.csv: who they
are, household, work, values, main worry) answers in Turkish: a stance first,
then two or three sentences on what the question changes in *their* life. One
call per persona, temperature 1, thinking off. A comment that contradicts its
own persona (personas.rules.check_text), can't be read (e.g. a refusal) or
repeats another word for word is dropped and counted.

These are illustrations, not measurements: a dozen synthetic people are not a
population estimate, and the comments carry the model's own leanings. Shares
come only from probes and scenarios scored against real answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from src.common import paths
from src.personas import rules
from src.simulation.model import AnthropicModel

MODEL = "claude-haiku-4-5-20251001"
N_PERSONAS = 12
MAX_TOKENS = 220
STANCES = ("OLUMLU", "OLUMSUZ", "KARARSIZ")

AGE_TR = {"65+": "65 yaş ve üstü"}
GENDER_TR = {"male": "erkek", "female": "kadın"}
EDU_TR = {"primary": "ilkokul ya da ortaokul mezunu", "secondary": "lise mezunu",
          "vocational": "meslek okulu mezunu", "bachelor": "üniversite mezunu",
          "graduate": "yüksek lisans ya da doktora mezunu"}
REGION_TR = {"Ic Anadolu": "İç Anadolu", "Dogu Anadolu": "Doğu Anadolu", "Guneydogu Anadolu": "Güneydoğu Anadolu"}
SETTLEMENT_TR = {"urban": "şehirde", "rural": "kırsalda"}
MARITAL_TR = {"married": "evli", "single": "bekâr", "divorced": "boşanmış", "widowed": "dul"}
EMPLOYMENT_TR = {"employed": "çalışıyor", "unemployed": "işsiz", "student": "öğrenci", "retired": "emekli",
                 "homemaker": "ev işleriyle ilgileniyor"}
RELIGIOSITY_TR = {"low": "pek önemli değil", "medium": "biraz önemli", "high": "çok önemli",
                  "very_high": "son derece önemli"}
POLITICAL_TR = {"left": "solda", "centre": "ortada", "right": "sağda"}
TENURE_TR = {"owner": "oturduğu ev kendisinin", "tenant": "kirada oturuyor",
             "rent_free": "kira ödemeden (aile evi ya da lojman) oturuyor"}
SECTOR_TR = {"agriculture": "tarım", "industry": "sanayi", "construction": "inşaat", "services": "hizmet",
             "public": "kamu"}
CONCERN_TR = {"cost_of_living": "hayat pahalılığı", "poverty": "yoksulluk", "education": "eğitim"}


def _has(v) -> bool:
    return v is not None and not (isinstance(v, float) and np.isnan(v)) and str(v) not in ("", "nan")


def _age(band: str) -> str:
    return AGE_TR.get(band, f"{band} yaş")


def facts(p: dict) -> list[str]:
    """Short Turkish labels of a persona's fields, for the comment card."""
    out = [GENDER_TR.get(p.get("gender"), "kişi").capitalize(), _age(p["age_band"]),
           f"{REGION_TR.get(p['region'], p['region'])} · {SETTLEMENT_TR.get(p.get('settlement_type'), '')}".strip(" ·"),
           EDU_TR.get(p.get("education_level"), ""), MARITAL_TR.get(p.get("marital_status"), "").capitalize(),
           EMPLOYMENT_TR.get(p.get("employment_status"), "").capitalize()]
    if _has(p.get("sector")):
        out.append(f"{SECTOR_TR[p['sector']].capitalize()} sektörü" + (", sigortasız" if p.get("informal") is True else ""))
    if _has(p.get("income_decile")):
        out.append(f"Gelir {int(p['income_decile'])}/10")
    if _has(p.get("household_size")):
        out.append(f"{int(p['household_size'])} kişilik hane")
    if _has(p.get("tenure")):
        out.append({"owner": "Ev sahibi", "tenant": "Kiracı", "rent_free": "Kira ödemiyor"}[p["tenure"]])
    if _has(p.get("religiosity_band")):
        out.append(f"Din: {RELIGIOSITY_TR[p['religiosity_band']]}")
    if _has(p.get("political_leaning_band")):
        out.append(f"Siyaset: {POLITICAL_TR[p['political_leaning_band']]}")
    if p.get("concern") in CONCERN_TR:
        out.append(f"Kaygı: {CONCERN_TR[p['concern']]}")
    return [f for f in out if f]


def describe(p: dict) -> str:
    """The persona as labelled lines (Turkish), every field it has."""
    lines = [f"Cinsiyet: {GENDER_TR.get(p.get('gender'), 'belirtilmemiş')}", f"Yaş: {_age(p['age_band'])}",
             f"Bölge: {REGION_TR.get(p['region'], p['region'])}, {SETTLEMENT_TR.get(p.get('settlement_type'), '')}",
             f"Eğitim: {EDU_TR.get(p.get('education_level'), 'belirtilmemiş')}",
             f"Medeni durum: {MARITAL_TR.get(p.get('marital_status'), 'belirtilmemiş')}",
             f"Çalışma durumu: {EMPLOYMENT_TR.get(p.get('employment_status'), 'belirtilmemiş')}"]
    if _has(p.get("sector")):
        lines.append(f"Sektör: {SECTOR_TR[p['sector']]}" + (", sigortasız (kayıt dışı)" if p.get("informal") is True else ""))
    if _has(p.get("income_decile")):
        d = int(p["income_decile"])
        lines.append(f"Hane geliri: 10 dilimden {d}. dilim ({'düşük' if d <= 3 else 'orta' if d <= 7 else 'yüksek'})")
    if _has(p.get("household_size")):
        home = f"; {TENURE_TR[p['tenure']]}" if _has(p.get("tenure")) else ""
        lines.append(f"Hane: {int(p['household_size'])} kişi{home}")
    if _has(p.get("religiosity_band")):
        lines.append(f"Din hayatında: {RELIGIOSITY_TR[p['religiosity_band']]}")
    if _has(p.get("political_leaning_band")):
        lines.append(f"Siyasette kendini: {POLITICAL_TR[p['political_leaning_band']]} görüyor")
    if p.get("concern") in CONCERN_TR:
        lines.append(f"En büyük kaygısı: {CONCERN_TR[p['concern']]}")
    if p.get("internet_user") is not None:
        lines.append("İnternet: " + ("kullanıyor" + (", yapay zekâ araçlarını da" if p.get("genai_user") is True else "")
                                     if p.get("internet_user") is True else "kullanmıyor"))
    return "\n".join(f"- {line}" for line in lines)


def prompt(p: dict, question: str) -> str:
    return (
        "Aşağıda tanımlanan kişisin. 2026'da Türkiye'de yaşıyorsun.\n\n"
        f"KİM OLDUĞUN:\n{describe(p)}\n\n"
        f"Soru: {question}\n\n"
        "Bu kişi olarak cevap ver. Sorunun SENİN gündelik hayatına somut etkisini düşün: evin, işin, "
        "gelirin, hanen. Genel toplumsal argümanlara sığınma, kendi durumundan konuş. Rakam, kanun ya da "
        "tarih uydurma. Profilini sayıp dökme. Günlük konuşma dilinde, 2-3 cümle, düz metin.\n"
        "Tam olarak şu biçimde yaz:\n"
        "TUTUM: OLUMLU, OLUMSUZ ya da KARARSIZ\n"
        "YORUM: <yorumun>"
    )


_REPLY = re.compile(r"TUTUM:\s*(OLUMLU|OLUMSUZ|KARARSIZ)\s*[\r\n]+\s*YORUM:\s*(.+)", re.IGNORECASE | re.DOTALL)


def parse(text: str) -> tuple[str, str] | None:
    m = _REPLY.search(text or "")
    if not m:
        return None
    comment = re.sub(r"[*_#]", "", m.group(2)).strip()
    return (m.group(1).upper(), comment) if comment else None


def sample(personas: pd.DataFrame, question: str, n: int = N_PERSONAS) -> pd.DataFrame:
    """``n`` distinct personas drawn by weight; the same question draws the same people."""
    seed = int(hashlib.sha256(question.strip().lower().encode()).hexdigest()[:8], 16)
    w = personas["weight"].to_numpy(float)
    idx = np.random.default_rng(seed).choice(len(personas), size=min(n, len(personas)), replace=False, p=w / w.sum())
    return personas.iloc[sorted(idx)]


def _records(frame: pd.DataFrame) -> list[dict]:
    rows = frame.astype(object).where(frame.notna(), None).to_dict("records")
    for r in rows:  # CSV booleans arrive as strings
        for k, v in r.items():
            if v in ("True", "False"):
                r[k] = v == "True"
    return rows


def ask(question: str, personas_path=paths.PERSONAS_SYNTHETIC_CSV, n: int = N_PERSONAS,
        model_snapshot: str = MODEL, client=None) -> dict:
    """Comments from ``n`` synthetic personas on ``question``."""
    model = AnthropicModel(model_snapshot, max_calls=n, client=client)
    people = _records(sample(pd.read_csv(personas_path), question, n))

    def one(p):
        model._reserve()
        resp = model._client.messages.create(model=model_snapshot, max_tokens=MAX_TOKENS, thinking={"type": "disabled"},
                                             messages=[{"role": "user", "content": prompt(p, question)}])
        return "".join(b.text for b in resp.content if b.type == "text")

    with ThreadPoolExecutor(n) as pool:
        replies = list(pool.map(one, people))

    comments, seen = [], set()
    dropped = {"unreadable": 0, "inconsistent": 0, "duplicate": 0}
    for p, reply in zip(people, replies):
        parsed = parse(reply)
        if parsed is None:
            dropped["unreadable"] += 1
            continue
        stance, text = parsed
        if rules.check_text(text, p):
            dropped["inconsistent"] += 1
            continue
        key = " ".join(re.findall(r"\w+", text.lower()))
        if key in seen:
            dropped["duplicate"] += 1
            continue
        seen.add(key)
        comments.append({"persona_id": p["persona_id"], "facts": facts(p), "stance": stance, "text": text})
    return {"question": question, "model": model_snapshot, "n_asked": len(people), "comments": comments,
            "dropped": dropped, "stances": {s: sum(c["stance"] == s for c in comments) for s in STANCES}}


def main():
    ap = argparse.ArgumentParser(description="Synthetic personas comment on a question (live model, costs money).")
    ap.add_argument("question")
    ap.add_argument("-n", type=int, default=N_PERSONAS)
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()
    print(json.dumps(ask(args.question, n=args.n, model_snapshot=args.model), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
