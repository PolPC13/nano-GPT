# step2_parse_structured_entries_improved.py
# Versió millorada i més robusta per parsejar blocs d'entrada lexicogràfica
import re, json
from pathlib import Path
from collections import Counter

# ---------- CONFIG ----------
INPUT_FILE = Path("/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/step1_output/clean_corpus_improved.txt")
OUTPUT_DIR = Path("/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/step2_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "structured_entries.jsonl"
LOG_FILE = OUTPUT_DIR / "parsing_log.json"
UNMATCHED_FILE = OUTPUT_DIR / "unmatched_examples.jsonl"

# Millor llista (ampliable) d'abreviatures de categories
CATEGORIES = [
    "s\\.", "s\\.\\s*f\\.", "s\\.\\s*m\\.", "s\\.\\s*pl\\.", "v\\.", "v\\.\\s*tr\\.", "v\\.\\s*intr\\.",
    "v\\.\\s*refl\\.", "v\\.\\s*aux\\.", "adj\\.", "adv\\.", "prep\\.", "loc\\.", "loc\\.\\s*prep\\.",
    "interj\\.", "conj\\.", "pr\\.", "fr\\.", "mod\\.", "num\\.", "art\\.", "abbr\\.", "int\\."
]
# ordena per longitud per evitar captures prematures (llargs primer)
CATEGORIES = sorted(CATEGORIES, key=lambda s: -len(s))
CATEGORIES_RE = r"(?:\b" + r"\b|\b".join(CATEGORIES) + r"\b)"

# Patró per detectar cites (tant cometes rectes com tipogràfiques i guillemets)
QUOTE_OPEN = r'["“«\']'
QUOTE_CLOSE = r'["”»\']'
QUOTE_PAIR_RE = re.compile(r'(["“«\'])(.+?)((?<!\\)\1)', flags=re.DOTALL)  # captura parells identics (simplificat)

# Funcions helpers
def find_first_category_index(s):
    """
    Retorna l'índex on apareix la primera 'categoria' dins la línia, o -1 si cap.
    """
    m = re.search(CATEGORIES_RE, s, flags=re.IGNORECASE)
    return m.start() if m else -1

def extract_lemma_line(lema_line):
    """
    Intent robust per extreure Lema, Variant, Categoria i notes curtes.
    """
    raw = lema_line.strip()
    # eliminar indexes numèrics inicials (p.e. '1. ')
    raw = re.sub(r'^\s*\d+\.\s*', '', raw)

    idx = find_first_category_index(raw)
    if idx == -1:
        return None  # no s'ha detectat categoria

    before = raw[:idx].strip()
    after = raw[idx:].strip()

    # extreu la categoria (primer token que coincideix)
    cat_match = re.match(r'(' + CATEGORIES_RE + r')', after, flags=re.IGNORECASE)
    categoria = cat_match.group(1).strip() if cat_match else None

    # variant en claudàtors [] dins de 'before'
    variant = None
    var_m = re.search(r'\[(.*?)\]', before)
    if var_m:
        variant = var_m.group(1).strip()
        # eliminar la variant de before per netejar lema
        before = before[:var_m.start()] + before[var_m.end():]
        before = before.strip()

    # Lemma principal: normalment el primer token(s) abans de la variant
    # si hi ha múltiples formes separades per ',' o ' / ' escollim la primera
    lema = before.split(',')[0].split('/')[0].strip()

    return {"Lema": lema or None, "Variant": variant, "Categoria": categoria, "raw_before": before, "raw_after": after}

def split_examples_and_font(body_text):
    """
    Extreu exemples (entre cometes rectes o tipogràfiques) i torna la resta com a possible font.
    Retorna (examples_list, remaining_text)
    """
    examples = []
    # primer, busquem totes les ocurrències de cometes tipogràfiques o rectes
    # acceptem "..." i “...” i '...' i «...»
    # anem buscant parells amb una regex tolerant (DOTALL)
    # per seguretat capturem també cometes simples
    for m in re.finditer(r'(["“«\'])(.+?)(["”»\'])', body_text, flags=re.DOTALL):
        examples.append(m.group(2).strip())

    # eliminar les cites trobades per obtenir el text restant
    remaining = re.sub(r'(["“«\'])(.+?)(["”»\'])', '', body_text, flags=re.DOTALL).strip()
    return examples, remaining

def build_sequence_text(entry):
    """
    Construeix la seqüència textual que serà usada per l'entrenament.
    Manté marcatge explícit.
    """
    lema = entry.get("Lema","")
    cat = entry.get("Categoria","") or ""
    variant = entry.get("Variant","") or ""
    definicio = entry.get("Definicio","") or ""
    exemples = " ".join(entry.get("Exemple", [])) if entry.get("Exemple") else ""
    # incloem tags per a nano-GPT
    seq = f"<ENTRY> {lema} [{cat}] {variant} <DEF> {definicio} <EX> {exemples} <END>"
    # reduirem espais consecutius
    seq = re.sub(r'\s{2,}', ' ', seq).strip()
    return seq

# Parser de bloc d'entrada
def parse_entry_block(block, line_start=0):
    lines = [ln for ln in (l.rstrip() for l in block.splitlines()) if ln.strip()!='']
    if not lines:
        return None

    entry = {
        "Lema": None, "Variant": None, "Categoria": None,
        "Definicio": None, "Exemple": [], "Font": None,
        "raw_block": block.strip(), "line_start": line_start, "warnings": []
    }

    # primera línia intesa com a "head" (si la primera línia és massa llarga i conté punts, hi ha casos edge)
    head = lines[0]
    lemma_data = extract_lemma_line(head)

    if lemma_data:
        entry["Lema"] = lemma_data["Lema"]
        entry["Variant"] = lemma_data["Variant"]
        entry["Categoria"] = lemma_data["Categoria"]
        # eliminem la capça processada
        body_lines = lines[1:]
    else:
        # pot ser que la primera línia no sigui un head; intentem emparellar amb la primera línia no molt llarga
        # o tractem com Unmatched
        # Recolzem amb heurística: si la línia conté una coma seguida de 'adj.' o 's.' al final
        heur = re.search(CATEGORIES_RE, head, flags=re.IGNORECASE)
        if heur:
            # intenteu una segona pass
            lemma_data = extract_lemma_line(head)
            if lemma_data:
                entry["Lema"] = lemma_data["Lema"]
                entry["Variant"] = lemma_data["Variant"]
                entry["Categoria"] = lemma_data["Categoria"]
                body_lines = lines[1:]
            else:
                entry["warnings"].append("Head not parsed; heuristic fallback")
                return {"type":"Unmatched_Entry", "content": block.strip(), "line_start": line_start}
        else:
            # si la línia és curt i amb un punt final, podria ser capçalera de secció
            if len(head) < 60 and head.endswith('.'):
                return {"type":"Section_Header", "content": head, "line_start": line_start}
            return {"type":"Unmatched_Entry", "content": block.strip(), "line_start": line_start}

    full_body = "\n".join(body_lines).strip()

    # si no hi ha cos, pot ser que la definició estigui a la mateixa capça (excepcional)
    if not full_body:
        entry["Definicio"] = ""
        return entry

    # extreure exemples i text restant
    exemples, remaining = split_examples_and_font(full_body)
    entry["Exemple"] = exemples

    # heurística per a definició: el text fins a la primera barra '—' o guió llarg o fins a la primera citació
    # si hi ha una línia amb '—' considerem part esquerra com definició
    if '—' in remaining:
        parts = remaining.split('—', 1)
        entry["Definicio"] = parts[0].strip()
        # el costat dret és sovint la font o comentari
        entry["Font"] = parts[1].strip()
    else:
        # si tenim exemples, la definició pot estar abans d'ells: trobem la posició de la primera cita
        if exemples:
            # cercar la primera aparició de la primera cita en el body original
            first_quote_pos = re.search(r'(["“«\'])(.+?)(["”»\'])', full_body, flags=re.DOTALL)
            if first_quote_pos:
                entry["Definicio"] = full_body[:first_quote_pos.start()].strip()
                # restem per trobar la possible font
                non_example_rest = re.sub(r'(["“«\'])(.+?)(["”»\'])', '', full_body, flags=re.DOTALL).strip()
                # la font sovint és l'última línia si sembla bibliogràfica (conté noms, anys...)
                if non_example_rest:
                    lines_non = [ln.strip() for ln in non_example_rest.splitlines() if ln.strip()]
                    if lines_non:
                        # preferim línies que continguin majúscules i noms o números d'any
                        cand = None
                        for ln in reversed(lines_non):
                            if re.search(r'\b[A-ZÀ-Ú][a-zà-ú]{2,}', ln) or re.search(r'\d{3,4}', ln):
                                cand = ln; break
                        entry["Font"] = cand or lines_non[-1]
                    else:
                        entry["Font"] = None
                else:
                    entry["Font"] = None
            else:
                entry["Definicio"] = full_body
        else:
            # sense exemples ni guions, considerem tot com a definició
            entry["Definicio"] = remaining

    # neteja final: eliminar llargues seqüències de "V. ..." dins la definició
    entry["Definicio"] = re.sub(r'\bV\.\s+[A-Z]\w.*', '', entry["Definicio"]).strip()

    return entry

# ---------- Pipeline principal ----------
text = INPUT_FILE.read_text(encoding='utf-8')
# separar en blocs per 2 o més salts de línia (més robust)
entry_blocks = re.split(r'\n{2,}', text)

structured_data = []
parsing_log = {
    "total_blocks": len(entry_blocks),
    "processed_entries": 0,
    "section_headers": [],
    "unmatched_entries_count": 0,
    "unmatched_samples": [],
    "warnings_counter": Counter()
}

line_cursor = 1
for block in entry_blocks:
    if not block.strip():
        # contar salts per estimar el següent line_cursor
        line_cursor += block.count('\n') + 1
        continue

    result = parse_entry_block(block, line_start=line_cursor)

    # actualitzar line_cursor: el bloc té N línies
    line_cursor += block.count('\n') + 1

    if not result:
        continue

    if isinstance(result, dict) and result.get("type") == "Section_Header":
        parsing_log["section_headers"].append(result["content"])
    elif isinstance(result, dict) and result.get("type") == "Unmatched_Entry":
        parsing_log["unmatched_entries_count"] += 1
        # guarda mostra per revisió
        parsing_log["unmatched_samples"].append({"line_start": result.get("line_start"), "content": result.get("content")})
    else:
        # entrada normal
        # si hi ha warnings, acumular
        if result.get("warnings"):
            for w in result["warnings"]:
                parsing_log["warnings_counter"][w] += 1
        structured_data.append(result)
        parsing_log["processed_entries"] += 1

# escriure JSONL de sortida amb seq per nano-GPT
with OUTPUT_FILE.open('w', encoding='utf-8') as f_out:
    for i, e in enumerate(structured_data):
        seq_text = build_sequence_text(e)
        out = {"id": i+1, "line_start": e.get("line_start"), "text": seq_text, "meta": {"Lema": e.get("Lema"), "Categoria": e.get("Categoria")}}
        f_out.write(json.dumps(out, ensure_ascii=False) + '\n')

# escriure unmatched exemples per revisió manual (limit)
with UNMATCHED_FILE.open('w', encoding='utf-8') as f_um:
    for item in parsing_log["unmatched_samples"][:500]:
        f_um.write(json.dumps(item, ensure_ascii=False) + '\n')

# escriure log resum
parsing_log_summary = {
    "total_blocks": parsing_log["total_blocks"],
    "processed_entries": parsing_log["processed_entries"],
    "section_headers_count": len(parsing_log["section_headers"]),
    "unmatched_entries_count": parsing_log["unmatched_entries_count"],
    "warnings": dict(parsing_log["warnings_counter"])
}
LOG_FILE.write_text(json.dumps(parsing_log_summary, ensure_ascii=False, indent=2), encoding='utf-8')

print("Parseig complet.")
print("Entrades processades:", parsing_log["processed_entries"])
print("Entrades no coincidents (mostres al fitxer):", parsing_log["unmatched_entries_count"])
print("Sortida JSONL:", OUTPUT_FILE)
print("Unmatched exemples:", UNMATCHED_FILE)
print("Log resum:", LOG_FILE)