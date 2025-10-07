# parse_vocabulari_final_v4.py
# Script con fase de pre-procesamiento para normalizar el texto de origen.

import re
import json

print("Procesando vocabulario catalán medieval con el script v4 (con pre-procesamiento)...")

# --- CONFIGURACIÓN ---
input_file_path = '/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/step1_output/clean_corpus_improved.txt' 
output_txt_file = 'catalan_medieval_dataset_v4.txt'
output_jsonl_file = 'catalan_medieval_structured_v4.jsonl'

# --- LECTURA DEL ARCHIVO ---
try:
    with open(input_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print(f"Error: No se encontró el archivo de entrada en la ruta: {input_file_path}")
    exit()

# --- FASE DE PRE-PROCESAMIENTO ---
# 1. Soluciona el Problema 1: Añade un espacio entre una palabra y un corchete si no lo hay.
#    Ejemplo: "ALAFIA[s." -> "ALAFIA [s."
content = re.sub(r'([a-zA-ZÀ-Ú])(\[)', r'\1 \2', content)

# 2. Soluciona el Problema 2: Elimina etiquetas <DEF> o <EX> que puedan estar incrustadas en el texto.
#    Esto limpia el texto antes de que nuestro script añada las etiquetas correctas.
content = content.replace('<DEF>', '').replace('</DEF>', '')
content = content.replace('<EX>', '').replace('</EX>', '')


# --- PATRONES REGEX ---
# El patrón de entrada ahora funcionará mejor gracias al pre-procesamiento.
entry_pattern = re.compile(
    r'^([A-ZÀÈÉÍÒÓÚ][A-ZÀÈÉÍÒÓÚÏÜ\s\'\-\(\)]+)'  # 1: Lema (greedy)
    r'\s*(?:\[([^\]]+)\])?'                         # 2: Variante opcional
    r'\s*(\[?(?:s|v|adj|adv|prep|interj|conj|loc|fr|num|art|un)\.?[^\]]*\]?)?', # 3: Categoría opcional
    re.MULTILINE
)

example_pattern = re.compile(r'["«“](.*?)["»”]', re.DOTALL)

# --- PROCESAMIENTO PRINCIPAL (sin cambios) ---
entries = []
# ... (El resto del bucle de procesamiento es idéntico al de la v3)
for match in entry_pattern.finditer(content):
    lema, variante, categoria = match.groups()
    
    entries.append({
        'start': match.start(),
        'end_header': match.end(),
        'lema': lema.strip(),
        'variante': variante.strip() if variante else None,
        'categoria': categoria.strip() if categoria else None
    })

print(f"Entradas detectadas tras pre-procesamiento: {len(entries)}")

dataset_lines = []
for i, entry in enumerate(entries):
    start_body = entry['end_header']
    end_body = entries[i+1]['start'] if i < len(entries)-1 else len(content)
    body = content[start_body:end_body].strip()
    
    ejemplos = example_pattern.findall(body)
    ejemplos_clean = [' '.join(ej.split()) for ej in ejemplos if len(ej.strip()) > 10]
    
    first_example_match = example_pattern.search(body)
    if first_example_match:
        definicion_raw = body[:first_example_match.start()]
    else:
        definicion_raw = body
        
    definicion_clean = re.sub(r'^\d+\.\s*(DA:)?\s*', '', definicion_raw.strip())
    definicion_clean = ' '.join(definicion_clean.split())

    if not definicion_clean and not ejemplos_clean:
        continue

    lema = entry['lema']
    cat_str = f"[{entry['categoria']}]" if entry['categoria'] else ""
    var_str = f" [{entry['variante']}]" if entry['variante'] else ""
    
    seq_parts = [f"<LEMA> {lema}{var_str} {cat_str}".strip()]
    
    if definicion_clean:
        seq_parts.append(f"<DEF> {definicion_clean[:350]}")
        
    if ejemplos_clean:
        ejemplos_text = " ".join(ejemplos_clean[:2])[:450]
        seq_parts.append(f"<EX> {ejemplos_text}")
        
    seq_parts.append("<END>")
    
    final_seq = " ".join(seq_parts)
    final_seq = re.sub(r'\s+', ' ', final_seq).replace(' ]', ']').replace(' [', '[')
    
    dataset_lines.append(final_seq)

# --- GUARDADO DE ARCHIVOS ---
with open(output_txt_file, 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(dataset_lines))

with open(output_jsonl_file, 'w', encoding='utf-8') as f:
    for i, line in enumerate(dataset_lines):
        json.dump({'id': i+1, 'text': line}, f, ensure_ascii=False)
        f.write('\n')

# --- FINALIZACIÓN ---
print(f"\n✓ Dataset final (v4) creado: {output_txt_file}")
print(f"✓ JSON estructurado final (v4): {output_jsonl_file}")
print(f"✓ Total de entradas procesadas: {len(dataset_lines)}")
print(f"\nEjemplo de la primera línea corregida:\n")
if dataset_lines:
    print(dataset_lines[0])