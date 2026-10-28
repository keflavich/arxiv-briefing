"""Technical pronunciation layer for the arXiv briefing (Kokoro TTS).

Converts script text to a phoneme string, overriding espeak for:
  * initialisms (JWST, CMZ, PAHs ...) -> letter names, secondary stress on every
    letter and primary stress on the LAST letter, the way people say them
    ("jay-double-you-ess-TEE"); a trailing lowercase "s" is the plural ("P A H-ez").
  * acronyms said as words (ALMA, SPHEREx, LIGO ...) -> fixed IPA from LEX.
  * chemical formulas (SiO, CH3OH, HC3N, NaCl ...) -> letters and numbers, last stressed.
Everything else goes to espeak via kokoro's tokenizer.
"""
import re

# ---------------------------------------------------------------- letters
_L = {  # IPA for letter names; "{S}" marks where the stress mark goes
    "A": "{S}eɪ", "B": "b{S}iː", "C": "s{S}iː", "D": "d{S}iː", "E": "{S}iː", "F": "{S}ɛf",
    "G": "dʒ{S}iː", "H": "{S}eɪtʃ", "I": "{S}aɪ", "J": "dʒ{S}eɪ", "K": "k{S}eɪ", "L": "{S}ɛl",
    "M": "{S}ɛm", "N": "{S}ɛn", "O": "{S}oʊ", "P": "p{S}iː", "Q": "kj{S}uː", "R": "{S}ɑːɹ",
    "S": "{S}ɛs", "T": "t{S}iː", "U": "j{S}uː", "V": "v{S}iː", "W": "d{S}ʌbəljuː", "X": "{S}ɛks",
    "Y": "w{S}aɪ", "Z": "z{S}iː",
}
_SIBILANT_END = ("s", "ʃ", "tʃ", "dʒ", "ks", "z")
_NUM = {"0": "zˌiəɹoʊ", "1": "wˌʌn", "2": "tˌuː", "3": "θɹˌiː", "4": "fˌɔːɹ", "5": "fˌaɪv",
        "6": "sˌɪks", "7": "sˌɛvən", "8": "ˌeɪt", "9": "nˌaɪn"}


def _units_ipa(units, plural=False):
    """units: list of letters or digit-strings. Last unit gets primary stress."""
    out = []
    for i, u in enumerate(units):
        last = i == len(units) - 1
        if u.isdigit():
            ipa = " ".join(_NUM[c] for c in u) if len(u) > 1 else _NUM[u]
            if last:
                ipa = ipa.replace("ˌ", "ˈ")
        else:
            ipa = _L[u.upper()].replace("{S}", "ˈ" if last else "ˌ")
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
    "MeerKAT+": "mˈɪɹkæt plˈʌs", "SiO": formula("SiO"), "NaCl": formula("NaCl"), "KCl": formula("KCl"),
}
# all-caps tokens of 5+ letters that are still spelled out
FORCE_INIT = {"FWHM", "SDSS", "LSST", "HMYSO", "HMYSOs", "NRAO", "JCMT", "VLBA", "VLBI", "IXPE",
              "NLTE", "CSIRO", "GWTC", "SMBH", "SMBHs", "LMXB", "HMXB", "ULIRG", "ULIRGs", "JWST"}
# plain words that look like formulas but aren't
NOT_FORMULA = {"He", "In", "As", "No", "Be", "At", "So", "Co", "Ca", "Na", "Ne", "Ar", "Hi"}

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
        if len(letters) >= 5 and re.search(r"[AEIOUY]", letters):
            return None                                   # long pronounceable acronym -> espeak word
        return "init", initialism(tok)
    if (tok not in NOT_FORMULA and re.fullmatch(r"(?:[A-Z][a-z]?\d*){2,}[+-]?|(?:[A-Z][a-z]?\d*)+\d+[A-Za-z\d]*[+-]?", tok)
            and (re.search(r"\d", tok) or re.search(r"[A-Z][a-z][A-Z]|[A-Z][A-Z][a-z]", tok))):
        return "formula", formula(tok)
    return None


def to_phonemes(text, phonemize):
    """text: speakable text. phonemize: callable(str)->ipa (kokoro tokenizer)."""
    out, pos, buf = [], 0, []
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        if m.group("spaced"):
            res = ("init", initialism(tok.replace(" ", "")))
        else:
            res = classify(tok)
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
                parts.append(phonemize(val).strip())
        else:
            parts.append(val)
    s = re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", s)


def report(text):
    """List every acronym/formula and how it will be treated."""
    seen = {}
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        res = ("init", initialism(tok.replace(" ", ""))) if m.group("spaced") else classify(tok)
        if res:
            seen[tok] = res
        elif re.search(r"[A-Z].*[A-Z]", tok):
            seen[tok] = ("espeak", "")
    return seen
