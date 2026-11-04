"""Pronunciation layer for the arXiv briefing (Kokoro TTS).

Converts script text to Kokoro's own phoneme alphabet. Order of precedence:
  1. LEX: fixed pronunciations for acronyms said as words and astronomy terms.
  2. initialisms (JWST, CMZ, PAHs ...): letter names, primary stress on the LAST letter;
     a trailing lowercase "s" is the plural.
  3. chemical formulas (SiO, CH3OH, C18O, C18H12 ...): letters and numbers, last stressed.
     Multi-digit numbers are whole numbers: C18O is "C eighteen O".
  4. Kokoro's own pronunciation lexicon (misaki us_gold + us_silver), with plural,
     past-tense and -ing forms derived from it.
  5. espeak as the last resort, converted to Kokoro's alphabet. report() flags every word
     that reaches this step, because espeak mangles English ("accretion": ack-RESH-un).
"""
import json, os, re

_NATIVE = [("ɜːɹ", "ɜɹ"), ("ɜː", "ɜɹ"), ("ɚ", "əɹ"), ("ɝ", "ɜɹ"), ("tʃ", "ʧ"), ("dʒ", "ʤ"),
           ("eɪ", "A"), ("aɪ", "I"), ("oʊ", "O"), ("aʊ", "W"), ("ɔɪ", "Y"), ("əʊ", "Q"),
           ("ː", ""), ("ɐ", "ə"), ("r", "ɹ")]


def native(ipa):
    """Convert espeak-style IPA to the alphabet Kokoro was trained on."""
    for a, b in _NATIVE:
        ipa = ipa.replace(a, b)
    return ipa


# ---------------------------------------------------------------- letters
_L = {  # IPA for letter names; "{S}" marks where the stress mark goes
    "A": "{S}eɪ", "B": "b{S}iː", "C": "s{S}iː", "D": "d{S}iː", "E": "{S}iː", "F": "{S}ɛf",
    "G": "dʒ{S}iː", "H": "{S}eɪtʃ", "I": "{S}aɪ", "J": "dʒ{S}eɪ", "K": "k{S}eɪ", "L": "{S}ɛl",
    "M": "{S}ɛm", "N": "{S}ɛn", "O": "{S}oʊ", "P": "p{S}iː", "Q": "kj{S}uː", "R": "{S}ɑːɹ",
    "S": "{S}ɛs", "T": "t{S}iː", "U": "j{S}uː", "V": "v{S}iː", "W": "d{S}ʌbəljuː", "X": "{S}ɛks",
    "Y": "w{S}aɪ", "Z": "z{S}iː",
}
_SIBILANT_END = ("s", "ʃ", "ʧ", "ʤ", "ks", "z", "ʒ")
_ONES = ["zˌiɹO", "wˌʌn", "tˌu", "θɹˌi", "fˌɔɹ", "fˌIv", "sˌɪks", "sˌɛvən", "ˌAt", "nˌIn", "tˌɛn",
         "ᵻlˌɛvən", "twˌɛlv", "θˌɜɹtin", "fˌɔɹtin", "fˌɪftin", "sˌɪkstin", "sˌɛvəntin", "ˌAtin", "nˌIntin"]
_TENS = {2: "twˌɛnti", 3: "θˌɜɹdi", 4: "fˌɔɹdi", 5: "fˌɪfti", 6: "sˌɪksti", 7: "sˌɛvənti", 8: "ˌAdi", 9: "nˌInti"}


def number_ipa(u):
    """A digit string in a formula: whole number up to 99, otherwise digit by digit."""
    n = int(u)
    if len(u) == 1 or (len(u) == 2 and u[0] != "0"):
        if n < 20:
            return _ONES[n]
        t, o = divmod(n, 10)
        return _TENS[t] + (" " + _ONES[o] if o else "")
    return " ".join(_ONES[int(c)] for c in u)


def _units_ipa(units, plural=False):
    """units: list of letters or digit-strings. Last unit gets primary stress."""
    out = []
    for i, u in enumerate(units):
        last = i == len(units) - 1
        if u.isdigit():
            ipa = number_ipa(u)
            if last:
                ipa = ipa[::-1].replace("ˌ", "ˈ", 1)[::-1]
        else:
            ipa = native(_L[u.upper()].replace("{S}", "ˈ" if last else "ˌ"))
        out.append(ipa)
    s = "".join(out)
    if plural:
        s += "ᵻz" if s.endswith(_SIBILANT_END) else ("s" if s.endswith("f") else "z")
    return s


def initialism(word):
    plural = word.endswith("s") and word[:-1].isupper()
    core = word[:-1] if plural else word
    units = re.findall(r"[A-Z]|\d+", core)
    return _units_ipa(units, plural)


def formula(word):
    # element symbols are read letter by letter (Si -> S I), digits as numbers
    units = re.findall(r"[A-Za-z]|\d+", word.rstrip("+-"))
    ipa = _units_ipa(units)
    if word.endswith("+"):
        ipa += " plˈʌs"
    return ipa


# ------------------------------------------------- acronyms said as words
# Conventional pronunciations used in talks / podcasts (US astronomy usage).
LEX = {
    "ALMA": "ˈælmə", "SPHEREx": "sfˈɪɹɛks", "eROSITA": "ˌiːɹoʊsˈiːtə", "MIRI": "mˈɪɹi",
    "NIRSpec": "nˈɪɹspɛk", "NIRCam": "nˈɪɹkæm", "NIRISS": "nˈɪɹɪs", "LIGO": "lˈaɪɡoʊ",
    "KAGRA": "kˈɑːɡɹə", "LISA": "lˈiːsə", "MeerKAT": "mˈɪɹkæt", "ASKAP": "ˈæskæp",
    "LOFAR": "lˈoʊfɑːɹ", "CHIME": "tʃˈaɪm", "DESI": "dˈɛzi", "Gaia": "ɡˈaɪə", "TESS": "tˈɛs",
    "WISE": "wˈaɪz", "NEOWISE": "nˌiːoʊwˈaɪz", "GALEX": "ɡˈæləks", "ROSAT": "ɹˈoʊzæt",
    "NuSTAR": "nˈuːstɑːɹ", "XRISM": "kɹˈɪzəm", "SOFIA": "soʊfˈiːə", "APEX": "ˈeɪpɛks",
    "IRAM": "ˈiːɹæm", "NOEMA": "noʊˈeɪmə", "SCUBA": "skˈuːbə", "MUSE": "mjˈuːz",
    "NASA": "nˈæsə", "ESA": "ˈiːsə", "JAXA": "dʒˈæksə", "ESO": "ˈiːsoʊ", "ATLAS": "ˈætləs",
    "LHAASO": "lˈɑːsoʊ", "HAWC": "hˈɔːk", "MESA": "mˈeɪsə", "MIST": "mˈɪst", "CASA": "kˈɑːsə",
    "RAMSES": "ɹˈæmsiːz", "AREPO": "ɐɹˈeɪpoʊ", "QUBO": "kjˈuːboʊ", "RADEX": "ɹˈeɪdɛks",
    "HEALPix": "hˈiːlpɪks", "ZAMS": "zˈæmz", "UMAP": "jˈuːmæp", "SPOTS": "spˈɑːts",
    "PARSEC": "pˈɑːɹsɛk", "POETS": "pˈoʊɪts", "FLAMES": "flˈeɪmz", "AGILE": "ˈædʒəl",
    "INTEGRAL": "ˈɪntəɡɹəl", "ASTRA": "ˈæstɹə", "HOP": "hˈɑːp", "KMOS": "kˈeɪmɑːs",
    "COMs": "kˈɑːmz", "CRIRES": "kɹˈaɪɚz", "SINFONI": "sɪnfˈoʊni",
    "SPHERE": "sfˈɪɹ", "GRAVITY": "ɡɹˈævɪɾi", "MATISSE": "mætˈiːs", "Euclid": "jˈuːklɪd",
    "FAST": "fˈæst", "GLIMPSE": "ɡlˈɪmps", "MIPSGAL": "mˈɪpsɡæl", "ATLASGAL": "ˈætləsɡæl",
    "HiGAL": "hˈaɪɡæl", "CHIMPS": "tʃˈɪmps", "SEDIGISM": "sˈɛdɪdʒˌɪzəm",
    "ACES": "ˈeɪsᵻz", "CMZoom": "sˌiːˌɛmzˈuːm", "MALT90": "mˈɔːlt nˈaɪnti", "BGPS": "bˌiːdʒˌiːpˌiːˈɛs",
    "HOPS": "hˈɑːps", "NIKA2": "nˈiːkə tˈuː", "WINERED": "wˈaɪnɹɛd", "DALI": "dˈɑːli", "Spektr": "spˈɛktəɹ",
    "LuSEE": "lˈuːsi", "CEN": "sˈɛn", "Teide": "tˈeɪdeɪ", "EGRET": "ˈiːɡɹɛt", "GOTHAM": "ɡˈɑːθəm", "Sirocco": "sɪɹˈɑːkoʊ",
    # astronomy words missing from the lexicon (these are already in Kokoro's alphabet)
    "isotopologue": "ˌIsətˈɑpəlˌɔɡ", "isotopologues": "ˌIsətˈɑpəlˌɔɡz", "protostellar": "pɹˌOɾOstˈɛləɹ",
    "protostars": "pɹˈOɾOstˌɑɹz", "prestellar": "pɹˌistˈɛləɹ", "circumstellar": "sˌɜɹkəmstˈɛləɹ",
    "protoplanetary": "pɹˌOɾOplˈænətˌɛɹi", "planetesimal": "plˌænətˈɛsəməl", "planetesimals": "plˌænətˈɛsəməlz",
    "metallicities": "mˌɛɾᵊlˈɪsəɾiz", "nucleosynthesis": "nˌukliOsˈɪnθəsəs", "bremsstrahlung": "bɹˈɛmʃtɹˌɑləŋ",
    "exoplanet": "ˈɛksOplˌænət", "exoplanets": "ˈɛksOplˌænəts", "hypervelocity": "hˌIpəɹvəlˈɑsəɾi",
    "Herbig": "hˈɜɹbɪɡ", "Kippenhahn": "kˈɪpənhˌɑn", "Serpens": "sˈɜɹpənz", "Planck": "plˈɑŋk",
    "Fermi": "fˈɛɹmi", "Chandra": "ʧˈɑndɹə", "Hipparcos": "hɪpˈɑɹkəs", "PANOSETI": "pˌænOsˈɛɾi", "SETI": "sˈɛɾi",
    "Dark100": "dˈɑɹk wˈʌn hˈʌndɹəd", "AtLAST": "ˈætlˌæst", "Korg": "kˈɔɹɡ", "Kreutz": "kɹˈYts",
    "Haumea": "hˌWmˈAə", "Pismis": "pˈɪʃmɪʃ", "proplyd": "pɹˈOplɪd", "proplyds": "pɹˈOplɪdz", "Sharpless": "ʃˈɑɹpləs",
    "OASIS": "OˈAsɪs", "NICER": "nˈIsəɹ", "SVOM": "ˌɛsvˈɑm", "DSA": "dˌiˌɛsˈA", "ELT": "ˌiˌɛlˈti",
    "redshift": "ɹˈɛdʃˌɪft", "redshifts": "ɹˈɛdʃˌɪfts", "redshifted": "ɹˈɛdʃˌɪftᵻd", "blueshift": "blˈuʃˌɪft",
    "blueshifts": "blˈuʃˌɪfts", "blueshifted": "blˈuʃˌɪftᵻd", "kiloparsecs": "kˈɪləpˌɑɹsˌɛks", "megaparsecs": "mˈɛɡəpˌɑɹsˌɛks",
    "gigahertz": "ɡˈɪɡəhˌɜɹts", "megahertz": "mˈɛɡəhˌɜɹts", "triphenylene": "tɹIfˈɛnəlˌin", "cyanotriphenylenes": "sˌInOtɹIfˈɛnəlˌinz",
    "midplane": "mˈɪdplˌAn", "snowline": "snˈOlˌIn", "Gaussian": "ɡˈWsiən", "Gaussians": "ɡˈWsiənz", "Paschen": "pˈɑʃən",
    "Lyman": "lˈImən", "Eddington": "ˈɛdɪŋtən", "Kerr": "kˈɜɹ", "eigh": "ˈA", "Bootis": "bOˈOtɪs", "Tycho": "tˈIkO",
    "asteroseismic": "ˌæstəɹOsˈIzmɪk", "eigenmodes": "ˈIɡənmˌOdz", "barrierless": "bˈɛɹiəɹləs", "interarm": "ˈɪntəɹˌɑɹm",
    "multi": "mˈʌlti", "non": "nˈɑn", "Afrho": "ˈAfɹˌO", "formamide": "fˈɔɹməmˌId", "sungrazer": "sˈʌnɡɹˌAzəɹ",
    "sungrazing": "sˈʌnɡɹˌAzɪŋ", "collapsar": "kəlˈæpsˌɑɹ", "ytterbium": "ɪtˈɜɹbiəm", "proper": "pɹˈɑpəɹ",
    "arcsecond": "ˈɑɹksˌɛkənd", "arcseconds": "ˈɑɹksˌɛkəndz", "milliarcsecond": "mˈɪliˌɑɹksˌɛkənd", "milliarcseconds": "mˈɪliˌɑɹksˌɛkəndz",
    "virial": "vˈɪɹiəl", "virially": "vˈɪɹiəli", "unevolved": "ˌʌnəvˈɑlvd", "misspecified": "mˌɪsspˈɛsəfˌId",
    "gravothermal": "ɡɹˌævOθˈɜɹməl", "Lorentz": "lˈɔɹənts", "microgauss": "mˈIkɹOɡˌWs", "Yukawa": "jukˈɑwə",
    "Balmer": "bˈɑlməɹ", "Hubble": "hˈʌbəl", "Tauri": "tˈɔɹi", "Palomar": "pˈæləmˌɑɹ", "Rubin": "ɹˈubən", "CARMA": "kˈɑɹmə",
    "MeerKAT+": "mˈɪɹkæt plˈʌs", "SiO": formula("SiO"), "NaCl": formula("NaCl"), "KCl": formula("KCl"),
}
# all-caps tokens of 5+ letters that are still spelled out
FORCE_INIT = {"FWHM", "SDSS", "LSST", "HMYSO", "HMYSOs", "NRAO", "JCMT", "VLBA", "VLBI", "IXPE",
              "NLTE", "CSIRO", "GWTC", "SMBH", "SMBHs", "LMXB", "HMXB", "ULIRG", "ULIRGs", "JWST", "GRMHD"}
# plain words that look like formulas but aren't
NOT_FORMULA = {"He", "In", "As", "No", "Be", "At", "So", "Co", "Ca", "Na", "Ne", "Ar", "Hi", "GHz", "MHz", "TeV", "GeV", "keV", "MeV"}

_TOKEN = re.compile(
    r"(?P<spaced>(?<![\w])(?:[A-Z] ){1,7}[A-Z](?:s)?(?![\w]))"      # J W S T, P A Hs
    r"|(?P<word>(?<![\w])[A-Za-z][\w+]*[\w+](?![\w]))"            # any multi-char token (hyphens split)
)


def classify(tok):
    """Return (kind, ipa) or None to leave the token to espeak."""
    if tok in LEX:
        return "lex", LEX[tok]
    if re.fullmatch(r"[A-Z0-9]*[A-Z][A-Z0-9]*s?", tok) and sum(c.isupper() for c in tok) >= 2:
        core = tok[:-1] if tok.endswith("s") and tok[:-1].isupper() else tok
        if tok in FORCE_INIT or core in FORCE_INIT:
            return "init", initialism(tok)
        letters = re.sub(r"\d", "", core)
        if len(letters) >= 5 and re.search(r"[AEIOUY]", letters) and not re.search(r"\d", core):
            return None                                   # long pronounceable acronym -> espeak word
        return "init", initialism(tok)
    if (tok not in NOT_FORMULA and re.fullmatch(r"(?:[A-Z][a-z]?\d*){2,}[+-]?|(?:[A-Z][a-z]?\d*)+\d+[A-Za-z\d]*[+-]?", tok)
            and (re.search(r"\d", tok) or re.search(r"[A-Z][a-z][A-Z]|[A-Z][A-Z][a-z]", tok))):
        return "formula", formula(tok)
    return None


# ------------------------------------------------- English words from Kokoro's lexicon
_LEXICON = {}


def _load():
    if not _LEXICON:
        try:
            import misaki
        except ImportError:                       # only its data files are used, so no dependencies
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", "--no-deps", "misaki"], check=True)
            import importlib
            importlib.invalidate_caches()
            import misaki
        d = os.path.join(os.path.dirname(misaki.__file__), "data")
        _LEXICON.update(json.load(open(os.path.join(d, "us_silver.json"))))
        _LEXICON.update(json.load(open(os.path.join(d, "us_gold.json"))))
    return _LEXICON


_WEAK = {"a": "ə", "an": "ən", "the": "ðə", "to": "tə", "of": "əv", "for": "fəɹ"}
_VERB_AFTER = {"to", "will", "would", "can", "could", "may", "might", "must", "should", "we", "they", "not"}
_BRIT = {"ionised": "ionized", "ionise": "ionize", "ionisation": "ionization", "normalised": "normalized",
         "favours": "favors", "favour": "favor", "favoured": "favored", "colour": "color", "colours": "colors",
         "centre": "center", "centres": "centers", "synthesised": "synthesized", "characterised": "characterized",
         "modelling": "modeling", "disc": "disk", "discs": "disks"}


def _entry(w, prev):
    v = _load().get(w)
    if isinstance(v, dict):
        return v.get("VERB") if prev in _VERB_AFTER and v.get("VERB") else v.get("DEFAULT")
    return v


def _s(p):
    if p.endswith(_SIBILANT_END):
        return p + "ᵻz"
    return p + ("s" if p[-1:] in "ptkfθ" else "z")


def _ed(p):
    if p[-1:] in "td":
        return p + "ᵻd"
    return p + ("t" if p[-1:] in "pkfθsʃʧ" else "d")


def _stem(w, prev):
    """Plural, past and -ing forms of a word the lexicon holds only in base form."""
    if w.endswith("ies") and _entry(w[:-3] + "y", prev):
        return _s(_entry(w[:-3] + "y", prev))
    if w.endswith(("ses", "xes", "zes", "ches", "shes")) and _entry(w[:-2], prev):
        return _s(_entry(w[:-2], prev))
    if w.endswith("s") and not w.endswith("ss") and _entry(w[:-1], prev):
        return _s(_entry(w[:-1], prev))
    if w.endswith("ed"):
        for c in (w[:-1], w[:-2], w[:-3] if w[-3:-2] == w[-4:-3] else None):
            b = c and _entry(c, prev)
            if b:
                return _ed(b)
    if w.endswith("ing"):
        for c in (w[:-3], w[:-3] + "e", w[:-4] if w[-4:-3] == w[-5:-4] else None):
            b = c and _entry(c, prev)
            if b:
                return b + "ɪŋ"
    return None


def english(word, prev="", nxt=""):
    """Kokoro-lexicon phonemes for one word, or None if it has to go to espeak."""
    w, poss = word, False
    if w.endswith(("'s", "’s")):
        w, poss = w[:-2], True
    lo = _BRIT.get(w.lower(), w.lower())
    if lo == "the" and nxt[:1].lower() in tuple("aeiou") and not nxt.lower().startswith(("one", "once", "uni", "use", "us", "eu", "ur")):
        return "ði"
    if lo in LEX:
        return native(LEX[lo])                    # sentence-initial astronomy words
    if lo in _WEAK:
        return _WEAK[lo]
    p = _entry(w, prev) if w != lo else None      # names keep their capitalized entry
    p = p or _entry(lo, prev) or _stem(lo, prev)
    return _s(p) if p and poss else p


_WORD = re.compile(r"[A-Za-z]+(?:['’][a-z]+)?")


def _espeak(text, phonemize):
    return native(phonemize(text)) if re.search(r"[A-Za-z0-9]", text) else text.strip()


def _speak_text(text, phonemize):
    """Plain English with no override tokens: lexicon word by word, espeak for the rest."""
    out, pos = [], 0
    ms = list(_WORD.finditer(text))
    for i, m in enumerate(ms):
        prev = ms[i - 1].group(0).lower() if i else ""
        nxt = ms[i + 1].group(0) if i + 1 < len(ms) else ""
        p = english(m.group(0), prev, nxt)
        if p is None:
            continue
        gap = text[pos:m.start()]
        if gap.strip():
            out.append(_espeak(gap, phonemize))
        out.append(p)
        pos = m.end()
    if text[pos:].strip():
        out.append(_espeak(text[pos:], phonemize))
    return " ".join(x.strip() for x in out if x.strip())


def to_phonemes(text, phonemize):
    """text: speakable text. phonemize: callable(str)->ipa (espeak, last resort only)."""
    out, pos, buf = [], 0, []
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        res = ("init", initialism(tok.replace(" ", ""))) if m.group("spaced") else classify(tok)
        if res is None:
            continue
        buf.append(text[pos:m.start()])
        out.append(("text", "".join(buf)))
        buf = []
        out.append(res)
        pos = m.end()
    buf.append(text[pos:])
    out.append(("text", "".join(buf)))
    parts = []
    for kind, val in out:
        if kind == "text":
            if val.strip():
                parts.append(_speak_text(val, phonemize))
        else:
            parts.append(native(val))
    s = re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", s)


def report(text):
    """List every acronym/formula, plus every word that falls through to espeak."""
    seen = {}
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        res = ("init", initialism(tok.replace(" ", ""))) if m.group("spaced") else classify(tok)
        if res:
            seen[tok] = (res[0], native(res[1]))
    plain = _TOKEN.sub(lambda m: " " if m.group(0) in seen else m.group(0), text)
    for m in _WORD.finditer(plain):
        if english(m.group(0)) is None:
            seen[m.group(0)] = ("espeak", "")
    return seen
