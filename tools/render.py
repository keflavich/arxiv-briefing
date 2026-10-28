import re, sys, os, subprocess, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pron
from kokoro_onnx import Kokoro

# Semantic rewrites only (units, symbols, names said as words). Acronym letter-reading and
# stress are handled by pron.py: initialisms get end stress, plurals get "-z"/"-ez".
SPEAK = [
    (r"3I ATLAS", "three I ATLAS"), (r"\b3I\b", "three I"), (r"q < 0\.1", "q less than zero point one"),
    (r"(\d+)\^3", r"\1 cubed"), (r"1000%", "one thousand percent"),
    (r"HI-to-H2", "H one to H two"), (r"\bNIR\b", "near-infrared"), (r"\bCRs\b", "cosmic rays"),
    (r"\bDR(\d)\b", r"DR \1"), (r"GWTC-(\d)", r"GWTC \1"), (r"ASAS-SN", "assassin"),
    (r"\bHII\b|\bH II\b", "H two"), (r"\bHI\b(?!-)|\bH I\b", "H one"), (r"SDSS-V", "SDSS five"),
    (r"\bMyr\b", "million years"), (r"\bGyr\b", "billion years"),
    (r"\bSgr A( star|\*)", "Sagittarius eigh star"), (r"\bSgr A\b", "Sagittarius eigh"), (r"\bSgr B2\b", "Sagittarius B two"),
    (r"\bSgr ([B-Z])\b", r"Sagittarius \1"),
    (r"\barXiv", "archive"), (r"\bOrion A\b", "Orion eigh"), (r"\bau\b", "AU"),
    (r"\bkpc\b", "kiloparsecs"), (r"\bMpc\b", "megaparsecs"), (r"\bpc\b", "parsecs"), (r"\bmas\b", "milliarcseconds"),
    (r"∼", " about "), (r"(\d)σ", r"\1 sigma"), (r"γ-ray", "gamma ray"), (r"\bkm/s\b", "kilometers per second"),
    (r"\bmJy\b", "millijansky"), (r"\bμJy\b", "microjansky"), (r"\bMJy\b", "megajansky"), (r"\bJy\b", "jansky"),
    (r"μm\b", " microns"), (r"\bHα\b", "H alpha"), (r"\bHβ\b", "H beta"), (r"\bLyα\b", "Lyman alpha"),
    (r"\[CII\]", "C two"), (r"\[OIII\]", "O three"), (r"\[NII\]", "N two"), (r"\[OI\]", "O one"),
    (r"ΛCDM", "lambda CDM"), (r"\bSNe Ia\b", "type one eigh supernovae"), (r"\bSN Ia\b", "type one eigh supernova"),
    (r"\bSNe\b", "supernovae"), (r"R\(V\)", "R of V"), (r"E\(B-V\)", "E of B minus V"),
    (r"STARLINK-(\d\d)(\d\d\d)", r"Starlink \1 \2"),
    (r"\b11 305\b", "eleven thousand three hundred five"), (r"C-H-bearing", "CH bearing"),
    (r"\bHi-GAL\b|\bHI-Gal\b", "HiGAL"), (r"\bV(\d)(\d\d)\b", r"V \1 \2"),
    (r"%", " percent"),
]
def _pairs(d):
    d = d.lstrip("0") or "0"
    if len(d) == 4: return d[:2] + " " + ("oh " + d[3] if d[2] == "0" else d[2:])
    if len(d) == 3: return d[0] + " " + ("oh " + d[2] if d[1] == "0" else d[1:])
    return d
def _frb(m):
    d = m.group(1); return "FRB " + _pairs(d[:4]) + " " + " ".join(("oh" if c == "0" else c) for c in d[4:]) + " " + m.group(2)
EXTRA = [
    (r"\bNGC (\d{3,4})\b", lambda m: "NGC " + _pairs(m.group(1))),
    (r"\bIC (\d{3,4})\b", lambda m: "IC " + _pairs(m.group(1))),
    (r"\bFRB (\d{8})([A-Z])\b", _frb), (r"CHIME/FRB", "CHIME FRB"),
]
def speakable(t):
    for a, b in EXTRA + SPEAK: t = re.sub(a, b, t)
    return t

def kokoro():
    T = os.path.expanduser("~/tts/"); return Kokoro(T + "kokoro-v1.0.onnx", T + "voices-v1.0.bin")

def phonemes(k, text):
    return pron.to_phonemes(speakable(text), lambda s: k.tokenizer.phonemize(s, "en-us"))

def main(src, out, speed=1.15, voice="af_heart"):
    k = kokoro()
    paras = [p.strip() for p in open(src).read().split("\n\n") if p.strip()]; chunks = []; sr = 24000
    for p in paras:
        a, sr = k.create(phonemes(k, p), voice=voice, speed=float(speed), lang="en-us", is_phonemes=True); chunks.append(a)
        pause = 1.2 if (p.startswith(("Part ", "Deep dive", "Number")) or len(p) < 40) else 0.6
        chunks.append(np.zeros(int(sr * pause), dtype=a.dtype))
    wav = out.rsplit(".", 1)[0] + ".wav"; sf.write(wav, np.concatenate(chunks), sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-b:a", "64k", out], check=True)
    print("duration_min", sum(len(c) for c in chunks) / sr / 60)

if __name__ == "__main__":
    if sys.argv[1] == "--report":   # python3 render.py --report script.txt
        k = kokoro(); txt = speakable(open(sys.argv[2]).read())
        for tok, (kind, ipa) in sorted(pron.report(txt).items()):
            print(f"{tok:14s} {kind:8s} {ipa or k.tokenizer.phonemize(tok, 'en-us')}")
    else:
        main(*sys.argv[1:])
