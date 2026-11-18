#!/usr/bin/env python3
"""Disegna il wallpaper da word.json e genera index.html."""
import json, os, re, datetime
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H = 1170, 2532
M = 118
BG = (0, 0, 0); WHITE = (255, 255, 255); BODY = (228, 228, 228)
GREY = (150, 150, 150); DIM = (120, 120, 120); ACCENT = (232, 168, 72)
WATER = (22, 22, 22)

FD = "/Library/Fonts/"
def sf(w, s): return ImageFont.truetype(FD + f"SF-Pro-Display-{w}.otf", s)
def ny(s, wght=420):
    f = ImageFont.truetype("/System/Library/Fonts/NewYorkItalic.ttf", s)
    f.set_variation_by_axes([20, wght, 0]); return f

def main():
    e = json.load(open(os.path.join(ROOT, "word.json"), encoding="utf-8"))
    d0 = datetime.date.fromisoformat(e["today"])
    lemma = e["lemma"]; pos = e.get("pos", "")
    f_title = sf("Bold", 126); f_kick = sf("Medium", 30); f_pos = ny(46, 600)
    f_syl = ny(40, 600); f_ety = ny(34); f_etyb = ny(36, 600)
    f_num = sf("Semibold", 44); f_body = sf("Regular", 48); f_foot = sf("Medium", 30)

    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)

    def wrap(text, font, maxw):
        out, cur = [], ""
        for w_ in text.split():
            t = (cur + " " + w_).strip()
            if d.textlength(t, font) <= maxw: cur = t
            else:
                if cur: out.append(cur)
                cur = w_
        if cur: out.append(cur)
        return out

    def tracked(x, y, text, font, fill, track):
        for ch in text:
            d.text((x, y), ch, font=font, fill=fill)
            x += d.textlength(ch, font) + track
        return x

    def run(x, y, parts, font, gap=10):
        for txt, col in parts:
            d.text((x, y), txt, font=font, fill=col)
            x += d.textlength(txt, font) + gap
        return x

    # watermark con iniziale della parola, in alto a destra
    d.text((470, -340), lemma[0].upper(), font=sf("Black", 1350), fill=WATER)

    col = W - 2 * M - 70
    import PIL.ImageFont as _IF
    _probe = ImageDraw.Draw(Image.new("1", (8, 8)))
    def et_wrap_pre(line):
        rows, x, cur = [], M, []
        space = _probe.textlength(" ", f_ety)
        for t, c in line:
            for w_ in [t2 for t2 in t.split(" ") if t2]:
                wl = _probe.textlength(w_, f_ety)
                if x + (space if cur else 0) + wl > W - M:
                    rows.append(cur); cur = [(w_, c)]; x = M + wl
                else:
                    cur.append((w_, c)); x += (space if len(cur) > 1 else 0) + wl
        if cur: rows.append(cur)
        return rows
    # blocchi etimologia
    et_lines = []
    et_lines.append([("ORIGINE:  ", DIM), (e["etimo_source"], ACCENT)])
    for c in e.get("etimo_comps", []):
        parts = [(c["form"], WHITE)]
        if c.get("gloss"): parts.append(("\u00ab" + c["gloss"] + "\u00bb", ACCENT))
        et_lines.append(parts)
    if e.get("followed"):
        et_lines.append([("voce piena: " + e["followed"], GREY)])

    # (le righe etimo si calcolano dopo, vedi sotto)

    sense_lines = []
    for s in e["senses"]:
        head = s["gloss"]
        if s.get("qual"): head = s["qual"] + " \u2013 " + head
        sense_lines.append(wrap(head, f_body, col))
    def senses_h(): return sum(len(l) * 70 + 44 for l in sense_lines)

    n_et_tmp = sum(len(et_wrap_pre(line)) for line in et_lines)
    block = 40 + 150 + 60 + (n_et_tmp * 56 + 20) + 56 + senses_h()
    TOP, BOTTOM = 1258, 2250
    y = BOTTOM - block

    tracked(M, y, "PAROLA DEL GIORNO", f_kick, GREY, 6)
    d.text((W - M, y), d0.strftime("%d \u00b7 %m \u00b7 %Y"), font=f_kick, fill=DIM, anchor="ra")
    y += 70
    d.line([(M, y), (W - M, y)], fill=(55, 55, 55), width=2)
    y += 30

    d.text((M - 6, y), lemma.upper(), font=f_title, fill=WHITE)
    tb = d.textbbox((M - 6, y), lemma.upper(), font=f_title)
    assert tb[2] < W - M, ("titolo troppo lungo", tb[2])
    if tb[2] > W - M:  # riduci se serve
        f_title = sf("Bold", int(126 * (W - M - M + 6) / tb[2]))
        d.rectangle((M - 6, y, tb[2] + 4, y + 160), fill=BG)
        d.text((M - 6, y), lemma.upper(), font=f_title, fill=WHITE)
    y += 150

    syl = e.get("syllabic", "")
    if syl:
        syl = syl.replace("\u00b7\u00b4", "\u00b4")
        x = M
        parts = syl.split("\u00b7")
        for i, p_ in enumerate(parts):
            col_ = ACCENT if "\u00b4" in p_ else GREY
            d.text((x, y), p_ + ("\u00b7" if i < len(parts) - 1 else ""), font=f_syl, fill=col_)
            x += d.textlength(p_ + ("\u00b7" if i < len(parts) - 1 else ""), f_syl)
    if pos:
        d.text((W - M, y), pos, font=f_pos, fill=ACCENT, anchor="ra")
    y += 60

    def et_wrap(line):
        rows, x, cur = [], M, []
        space = d.textlength(" ", f_ety)
        for t, c in line:
            for w_ in [t2 for t2 in t.split(" ") if t2]:
                wl = d.textlength(w_, f_ety)
                if x + (space if cur else 0) + wl > W - M:
                    rows.append(cur); cur = [(w_, c)]; x = M + wl
                else:
                    cur.append((w_, c)); x += (space if len(cur) > 1 else 0) + wl
        if cur: rows.append(cur)
        return rows
    et_rows = [r for line in et_lines for r in et_wrap(line)]
    for row in et_rows:
        x = M
        for i, (w_, c) in enumerate(row):
            if i: x += d.textlength(" ", f_ety)
            d.text((x, y), w_, font=f_ety, fill=c); x += d.textlength(w_, f_ety)
        y += 56
    y += 20

    for lines, s in zip(sense_lines, e["senses"]):
        d.text((M, y + 4), s["num"] + ".", font=f_num, fill=ACCENT)
        for ln in lines:
            assert d.textlength(ln, f_body) <= col, ln
            d.text((M + 70, y), ln, font=f_body, fill=BODY); y += 70
        y += 44
    assert y <= BOTTOM + 20, y

    fy = 2315
    d.line([(M, fy), (W - M, fy)], fill=(55, 55, 55), width=2)
    d.text((M, fy + 26), "VOCE: TRECCANI \u2013 Vocabolario on line", font=f_foot, fill=DIM)
    d.text((W - M, fy + 26), lemma, font=f_foot, fill=DIM, anchor="ra")

    img.save(os.path.join(ROOT, "site", "wallpaper.png"))

    # --- index.html ---
    html = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Parola del giorno \u2013 {lemma}</title>
<meta http-equiv="refresh" content="1800">
<meta name="description" content="Sfondi di sblocco con la parola del giorno del Vocabolario Treccani, aggiornati ogni giorno.">
<style>
 body{{margin:0;background:#000;color:#e4e4e4;font-family:-apple-system,'SF Pro Text',sans-serif;display:flex;flex-direction:column;align-items:center;padding:24px 12px}}
 img{{max-width:380px;width:100%;border-radius:20px;border:1px solid #222}}
 h1{{font-size:18px;font-weight:600;letter-spacing:.04em;margin:18px 0 4px}}
 p{{font-size:13px;color:#8a8a8a;text-align:center;margin:4px 0}}
 a{{color:#e8a848;text-decoration:none}}
 .src{{margin-top:14px;font-size:13px}}
</style></head><body>
<h1>PAROLA DEL GIORNO</h1>
<img id="w" src="wallpaper.png" alt="Wallpaper parola del giorno {lemma}">
<h1>{lemma.upper()}</h1>
<p>Aggiornato ogni giorno con la parola del giorno del Vocabolario Treccani.<br>
Ultimo aggiornamento: {d0.strftime('%d/%m/%Y')}</p>
<p class="src"><a href="{e['url']}">Voce Treccani \u2192</a> &nbsp;·&nbsp; <a href="wallpaper.png">Scarica sfondo (1170\u00d72532)</a></p>
<script>document.getElementById('w').src='wallpaper.png?v='+Date.now();</script>
</body></html>"""
    open(os.path.join(ROOT, "site", "index.html"), "w", encoding="utf-8").write(html)
    print("renderito:", lemma, "| etimo:", e["etimo_source"], "| componenti:", len(e.get("etimo_comps", [])))

if __name__ == "__main__":
    main()
