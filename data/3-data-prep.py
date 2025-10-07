# parse_vocabulari_final.py
# Script definitivo para crear dataset de catalán medieval

import re
import json

print("Procesando vocabulario catalán medieval...")

# Leer archivo
with open('/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/step1_output/clean_corpus_improved.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Patrón de entrada: MAYÚSCULAS + categoría
entry_pattern = re.compile(
    r'^([A-ZÀÈÉÍÒÓÚ][A-ZÀÈÉÍÒÓÚÏÜ\s\'\-\(\)]+?)(\d*)\s*(?:,\s*\[([^\]]+)\])?\s+(s\.|v\.|adj\.|adv\.|prep\.|interj\.|conj\.|loc\.|fr\.|num\.|art\.|un\.\s*pluri\.|v\.\s*[atr]\.|v\.\s*refl\.|v\.\s*intr\.)',
    re.MULTILINE
)

# Detectar posiciones de entradas
entries = []
for match in entry_pattern.finditer(content):
    entries.append({
        'start': match.start(),
        'end': match.end(),
        'lema': match.group(1).strip(),
        'variante': match.group(3),
        'categoria': match.group(4).strip()
    })

print(f"Entradas detectadas: {len(entries)}")

# Procesar cada entrada
dataset_lines = []
for i, entry in enumerate(entries):
    start = entry['end']
    end = entries[i+1]['start'] if i < len(entries)-1 else len(content)
    body = content[start:end].strip()
    
    # Extraer texto entre comillas (todos los tipos posibles)
    ejemplos = re.findall(r'[""«]([^""»]+)[""»]', body, re.DOTALL)
    ejemplos_clean = [' '.join(ej.split()) for ej in ejemplos if len(ej) > 20]
    
    # Definición: texto antes del primer ejemplo
    if ejemplos:
        idx = body.find(ejemplos[0])
        definicion = body[:idx].strip() if idx > 0 else body.split('\n')[0]
    else:
        definicion = ' '.join(body.split('\n')[:2])
    
    definicion = ' '.join(definicion.split())[:250]
    
    # Crear secuencia para entrenamiento
    lema = entry['lema']
    cat = entry['categoria']
    var = f" [{entry['variante']}]" if entry['variante'] else ""
    
    # Formato: <LEMA> palabra [categoría] variante <DEF> definición <EX> ejemplo1 ejemplo2
    seq = f"<LEMA> {lema}{var} [{cat}] <DEF> {definicion}"
    if ejemplos_clean:
        ejemplos_text = " ".join(ejemplos_clean[:2])[:400]
        seq += f" <EX> {ejemplos_text}"
    seq += " <END>"
    
    dataset_lines.append(seq)

# Guardar dataset para nanoGPT
output_file = 'catalan_medieval_dataset.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(dataset_lines))

# Guardar también JSON estructurado
json_file = 'catalan_medieval_structured.jsonl'
with open(json_file, 'w', encoding='utf-8') as f:
    for i, line in enumerate(dataset_lines):
        json.dump({'id': i+1, 'text': line}, f, ensure_ascii=False)
        f.write('\n')

print(f"\n✓ Dataset creado: {output_file}")
print(f"✓ JSON estructurado: {json_file}")
print(f"✓ Total de entradas procesadas: {len(dataset_lines)}")
print(f"\nPrimeras 3 líneas del dataset:\n")
for line in dataset_lines[:3]:
    print(line[:150] + "...\n")