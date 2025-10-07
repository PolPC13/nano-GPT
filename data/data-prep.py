import re
from pathlib import Path
import json

def remove_header_blocks(text, header_patterns, min_repetition_for_removal=3):
    # crea regex línia-a-línia (case-insensitive, multiline)
    parts = []
    for pat in header_patterns:
        # si l'usuari ja ha passat un regex (conté ^ o $ o \\d) el fem servir tal qual,
        # sinó escapem literals
        if any(ch in pat for ch in "^$\\"):
            parts.append(pat)
        else:
            parts.append(re.escape(pat))
    combined = r"(?im)^(?:" + r"|".join(parts) + r")\s*$"
    # eliminar totes les línies que coincideixin
    cleaned = re.sub(combined + r"\n?", "", text)
    # després, col·lapsar blocs de capçaleres restants (p. ex. varies línies buides)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, combined

def remove_metadata_markers(text):
    # patrons específics detectats en la teva anàlisi
    patterns = [
        r"\[source:\s*\d{1,3}\]",        # [source: 12]
        r"\[font:\s*\d{1,3}\]",          # [font: 3]
        r"\[fonte:\s*\d{1,3}\]",         # variants
        r"\[\s*Nota:\s*.*?\]",           # [Nota: ...]
        r"\s*\[\s*\d+\s*\]\s*$",         # [12] al final de línia
        r"\s*\(\*\)\s*$",                # (*) al final
    ]
    removed_examples = []
    for pat in patterns:
        # captura contexts per auditoria
        for m in re.finditer(r".{0,50}" + pat + r".{0,50}", text, flags=re.IGNORECASE):
            removed_examples.append(m.group(0))
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    return text, removed_examples

def fix_hyphenation_contextual(text):
    """
    Elimina hifenació (guions de separació) només si està entre lletres.
    S'eviten rangs Unicode problemàtics.
    """
    # Llista explícita i rangs Unicode segurs (sense Ø-ö).
    # Només cal A-Z, a-z i la llista de caràcters catalans/llatins més habituals.
    letters = r"A-Za-zÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝŸàáâãäåæçèéêëìíîïñòóôõöùúûüýÿç"
    
    # El teu codi original intentava fer això:
    # letters = r"A-Za-zÀ-ÖØ-öø-ÿÀÈÌÒÙàèìòùáéíóúàèçïäëöüâêîôû"
    # L'hem substituït per una llista més segura.
    
    # Patró: lletra + guió + newline + possible spaces + lletra
    # Ús de lookbehind/lookahead (necessita que `letters` no tingui rangs dolents)
    pattern = re.compile(
        r"(?<=[" + letters + r"])-\s*\n\s*(?=[" + letters + r"])", 
        flags=re.UNICODE | re.IGNORECASE  # Afegim IGNORECASE per a ser més segurs
    )
    
    new_text = pattern.sub("", text)
    return new_text

def collapse_blank_lines_preserve_entries(text):
    # col·lapsa múltiples salts de línia a com a molt 2 (un separador d'entrada)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)   # fins a 2 salts
    # elimina espais en línies i evita deixar línies només amb spaces
    text = "\n".join([ln.rstrip() for ln in text.splitlines()])
    text = re.sub(r"^[ \t]+$", "", text, flags=re.MULTILINE)
    return text

# Exemple d'ús integrat:
def enhanced_cleaning_pipeline(raw_text, header_patterns):
    outlog = {}
    t1, header_regex = remove_header_blocks(raw_text, header_patterns)
    outlog['header_regex'] = header_regex

    t2, removed_meta_examples = remove_metadata_markers(t1)
    outlog['removed_meta_examples'] = removed_meta_examples[:100]

    t3 = fix_hyphenation_contextual(t2)
    outlog['hyphenation_before'] = len(re.findall(r"-\s*\n\s*", t2))
    outlog['hyphenation_after'] = len(re.findall(r"-\s*\n\s*", t3))

    t4 = collapse_blank_lines_preserve_entries(t3)

    # comprovacions finals ràpides
    outlog['chars_before'] = len(raw_text)
    outlog['chars_after'] = len(t4)
    return t4, outlog

# Defineix el directori de sortida (necessitem la Path completa de la secció de prova)
OUTPUT_DIR = Path("/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/step1_output")

# --- SOLUCIÓ CLAU: Crear el directori recursivament ---
OUTPUT_DIR.mkdir(parents=True, exist_ok=True) 

# Secció de prova amb les correccions
raw = Path("/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/dataset_catalan_medieval.txt").read_text(encoding="utf-8")
header_patterns = ["Vocabulari_Lluis_Faraudo", "Vocabulari", r"^\s*els mots\s*$", "indd"]

cleaned_text, log = enhanced_cleaning_pipeline(raw, header_patterns)

# Ara que el directori existeix, podem escriure sense problemes
Path(OUTPUT_DIR / "clean_corpus_improved.txt").write_text(cleaned_text, encoding="utf-8")
Path(OUTPUT_DIR / "clean_log_improved.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Procés completat. Fitxers de sortida a: {OUTPUT_DIR}")