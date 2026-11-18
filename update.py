#!/usr/bin/env python3
"""Parola del giorno Treccani -> wallpaper PNG + sito statico.
Uso: python3 update.py [--push]
"""
import json, re, sys, os, subprocess, datetime, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def strip_html(s):
    s = re.sub(r"<style[^>]*>.*?</style>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&#8220;", "\u201c").replace("&#8221;", "\u201d")
    return re.sub(r"\s+", " ", s).strip()

def today_word_url():
    """Link della parola del giorno dalla component 'Today' dell'homepage."""
    h = get("https://www.treccani.it/")
    i = h.find('"component":"Today"')
    if i < 0:
        raise RuntimeError("component Today non trovata in homepage")
    m = re.search(r'"url":"(https://www\.treccani\.it/vocabolario/[^"]+)"', h[i:i+8000])
    if not m:
        m = re.search(r'href="(/vocabolario/[^"?]+/)"', h[i-9000:i+100])
        if not m: raise RuntimeError("link parola non trovato")
        return "https://www.treccani.it" + m.group(1)
    return m.group(1)

def parse_entry(url):
    h = get(url)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    data = json.loads(m.group(1))["props"]["pageProps"]["data"]
    c = data["content"]
    # etimologia grezza con markup -> separiamo prima della parte definita
    m = re.search(r"<b>(.+?)</b>\s*(agg\.|s\.m\.|s\.f\.|v\.|sm\.|s\.)\s*\[(.+?)\]", c)
    if m:
        lemma, pos, etimo_raw = m.group(1), m.group(2), m.group(3)
        tail = c[m.end():]
    else:
        m2 = re.search(r"\[(dal|der\.|comp\.|var\.|lat\.|gr\.)", c)
        lemma = strip_html(re.search(r"<b>(.+?)</b>", c).group(1))
        pos, etimo_raw = "", strip_html(c[m2.start():c.find("] –") if "] –" in c else m2.start()+400])
        tail = c[c.find("] –") + 3:] if "] –" in c else c
    # etimo: conserva i link testuali (es. rinvio a estravagante)
    etimo_links = re.findall(r'href="[^"]*/vocabolario/([^"/]+)/?"[^>]*>([^<]+)</a>', etimo_raw)
    etimo = strip_html(etimo_raw)
    # sensi: numeri + glossa tra parentesi quadre
    senses = []
    parts = re.split(r"<b>(\d+\.)</b>", tail)
    if len(parts) < 3:
        parts = re.split(r"(?:^|\s)(\d+\.)\s", strip_html(tail))
    labels = re.findall(r"(letter\. o raro\.|estroso|estensione)", "")
    for i in range(1, len(parts), 2):
        num = parts[i].rstrip(".")
        chunk = parts[i+1]
        txt = strip_html(chunk)
        g = re.search(r"\[([^\]]{15,200})\]", txt)
        qual = re.match(r"^\s*((?:letter|raro|estens|banch\.|non com\.)[^,\[]*?(?:o (?:raro|letter\.))?[^,\[]*)", strip_html(chunk))
        if g:
            gloss = g.group(1).strip()
        else:
            head = txt.lstrip()
            mcap = re.search(r"\b[A-ZÀ-Ù][^.;:]{14,190}", head)
            gloss = (mcap.group(0) if mcap else re.split(r"[:;]|\.\s", head)[0])[:190].strip()
        q = ""
        raw_head = strip_html(chunk)[:60]
        mq = re.match(r"^(letter\.\s+o\s+raro\.|letter\.|estroso|raro|non com\.)", raw_head)
        if mq: q = mq.group(1)
        senses.append({"num": num, "gloss": gloss, "qual": q})
    # forme derivate con sillabazione (per accento sul lemma)
    derived = re.findall(r"(\w+?)\s*\[([\w·]+(?:´|\b)[\w·]+[a-zéèìòùá][\w·]*)\]", strip_html(tail))
    derived = [(w, s) for w, s in derived if w.startswith(lemma.rstrip("e")) or lemma in w]
    return {"url": url, "lemma": lemma.strip(), "pos": pos.strip(),
            "etimo": etimo, "etimo_links": etimo_links,
            "senses": senses[:2], "derived": derived[:1],
            "opera": data.get("opera", ""), "fetched": datetime.datetime.now().isoformat()}

# --- struttura etimologia: lingua d'origine + parole componenti ---
LANG = r"(?:lat\. mediev\.|lat\. volg\.|lat\.|gr\.|fr\.|ant\.fr\.|altofr\.|ingl\.|spagn\.|tedesco|arab\.|neerl\.|gallo-|longob\.|franc\.)"
def etimo_parts(etimo):
    """lingua+forma d'origine, componenti (forma « glossa), eventuale rinvio."""
    lang = ""
    ml = re.search(LANG, etimo)
    if ml:
        lang = ml.group(0)
        rest = etimo[ml.end():]
        mf = re.match(r"\s*([A-Za-z\-À-Ùà-ù' ]+?)(?=[:,]|\s(?:comp\.|der\.|v\.|di )|$)", rest)
        form = mf.group(1).strip() if mf else ""
        source = (lang + (" " + form if form else "")).strip()
    else:
        source = etimo.split(",")[0][:120]
    comps = []
    mc = re.search(r"(?:comp\. di|der\. (?:da|di))\s+(.+?)$", etimo)
    if mc:
        body = mc.group(1)
        for piece in re.split(r"\s+e\s+", body):
            piece = piece.strip(" .")
            if not piece:
                continue
            mg = re.match(r"(.*?)[«]([^»»]+)[»]", piece)
            if mg:
                comps.append({"form": mg.group(1).strip(), "gloss": mg.group(2)})
            else:
                comps.append({"form": piece, "gloss": ""})
    xref = re.search(r"v\.\s+([A-Za-zà-ù]+)", etimo)
    return source, comps, (xref.group(1) if xref else "")

VOW = "aeiouòàèéìùá"
def stressed_index(w):
    """indice della vocale della penultima/terzultima parola (tronca)."""
    groups = [m.start() for m in re.finditer(f"[{VOW}]+", w)]
    if not groups: return -1
    tail = w[groups[-1]:]
    if re.fullmatch(f"[{VOW}]+(e|o|a)?[^aeiou]*", tail) and len(groups) >= 3 and w.endswith(("nte","ne","le","re","te","che","ghi")):
        return groups[-2]
    return groups[-1]

ONSET = ("str|spr|scr|dr|br|pr|tr|cr|gr|fr|vr|bl|cl|fl|gl|pl|chl|gn"
         "|sc|ch|gh|int|in|im|il|ir|is|ac|ad|af|ag|ap|ar|as|at|bi|di|gi")
def syllabic(lemma):
    """sillabazione italiana semplificata; accento a fine sillaba tonica."""
    i = stressed_index(lemma)
    if i < 0: return "", -1
    cuts = []
    for m in re.finditer(f"(?<=[{VOW}])([^aeiou]+)(?=[{VOW}])", lemma):
        cs = m.group(1)
        if len(cs) == 1:
            cuts.append(m.start())
        else:
            best = None
            for k in range(1, len(cs)):
                if re.fullmatch(f"(?:{ONSET})[^aeiou]*", cs[k:]) if False else re.match(f"(?:{ONSET})$|^(?:{ONSET})(?=[^aeiou]*[{VOW}])", cs[k:]):
                    best = k; break
            if best is None and re.match(f"(?:{ONSET})", cs) and len(cs) > 2:
                m2 = re.match(f"(?:{ONSET})", cs)
                cuts.append(m.start() + m2.end())
            elif best is not None:
                cuts.append(m.start() + best)
            else:
                cuts.append(m.start() + len(cs) - 1)
    cuts = sorted(set(cuts))
    segs, prev = [], 0
    for c in cuts:
        segs.append(lemma[prev:c]); prev = c
    segs.append(lemma[prev:])
    k = len(segs) - 3 if len(segs) >= 3 else 0
    out = list(segs); out[k] += "\u00b4"
    return "\u00b7".join(out), k

if __name__ == "__main__":
    url = today_word_url()
    e = parse_entry(url)
    e["today"] = datetime.date.today().isoformat()
    src, comps, xref = etimo_parts(e["etimo"])
    e["etimo_source"], e["etimo_comps"], e["etimo_xref"] = src, comps, xref
    if xref and e["etimo_links"]:
        base_url = "https://www.treccani.it/vocabolario/" + e["etimo_links"][0][0] + "/"
        b = parse_entry(base_url)
        e["followed"] = e["etimo_links"][0][0]
        e["etimo_source"], e["etimo_comps"], _ = etimo_parts(b["etimo"])
        if not e["senses"] or len(e["senses"][0]["gloss"]) < 20:
            e["senses"] = b["senses"]
    syl = syllabic(e["lemma"])
    e["syllabic"] = syl[0] if isinstance(syl, tuple) else ""
    e["stress"] = syl[1] if isinstance(syl, tuple) else -1
    with open(os.path.join(ROOT, "word.json"), "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
    print(json.dumps(e, ensure_ascii=False, indent=2))
