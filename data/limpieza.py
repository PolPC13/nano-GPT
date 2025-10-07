import re
import json
print("="*80)
print("LIMPIEZA LIGERA DEL DATASET V4")
print("="*80)

# Leer dataset V4
with open('catalan_medieval_dataset_v4.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Separar en bloques
bloques_raw = [b.strip() for b in content.split('\n\n') if b.strip()]
print(f"\nBloques originales: {len(bloques_raw)}")

# Estadísticas de limpieza
stats = {
    'original': len(bloques_raw),
    'corregidos': 0,
    'eliminados': 0,
    'sin_cambios': 0
}

bloques_limpios = []

for i, bloque in enumerate(bloques_raw, 1):
    # Verificar longitud extrema (>2500 caracteres indica problema)
    if len(bloque) > 2500:
        stats['eliminados'] += 1
        print(f"  ⚠ Entrada {i} eliminada (demasiado larga: {len(bloque)} chars)")
        continue
    
    # Extraer componentes
    lema_match = re.search(r'<LEMA>\s*([^<]+?)(?:\s*<DEF>|$)', bloque)
    
    if not lema_match:
        # Sin LEMA válido, eliminar
        stats['eliminados'] += 1
        print(f"  ⚠ Entrada {i} eliminada (sin LEMA válido)")
        continue
    
    lema_raw = lema_match.group(1).strip()
    
    # Detectar y corregir lemas mal formateados
    # Caso 1: LEMA[categoria... -> necesita espacio antes de [
    if '[' in lema_raw and not re.search(r'\s+\[', lema_raw):
        # Buscar dónde termina realmente el lema
        # El lema debería terminar antes del primer [ sin espacio
        parts = re.split(r'(\[)', lema_raw, maxsplit=1)
        if len(parts) >= 2:
            lema_limpio = parts[0].strip()
            resto = ''.join(parts[1:])
            
            # Reconstruir el bloque con el lema corregido
            bloque_nuevo = bloque.replace(
                f'<LEMA> {lema_raw}',
                f'<LEMA> {lema_limpio} <DEF> {resto}'
            )
            
            bloques_limpios.append(bloque_nuevo)
            stats['corregidos'] += 1
            
            if stats['corregidos'] <= 5:  # Mostrar solo primeros 5
                print(f"  ✓ Entrada {i} corregida:")
                print(f"    Antes: <LEMA> {lema_raw[:60]}...")
                print(f"    Después: <LEMA> {lema_limpio} <DEF> {resto[:40]}...")
            continue
    
    # Caso 2: Lemas extremadamente largos (>50 chars) sin [
    if len(lema_raw) > 50 and '[' not in lema_raw:
        # Intentar extraer solo la primera palabra o palabras clave
        # Patrón: tomar hasta la primera coma, punto o paréntesis
        match = re.match(r'^([A-ZÀÈÉÍÒÓÚÏÜ\s\-\'\(\)]+?)(?:\s+[a-z]|,|\.|;)', lema_raw)
        if match:
            lema_limpio = match.group(1).strip()
            resto = lema_raw[len(lema_limpio):].strip()
            
            # Reconstruir
            bloque_nuevo = bloque.replace(
                f'<LEMA> {lema_raw}',
                f'<LEMA> {lema_limpio} <DEF> {resto}'
            )
            
            bloques_limpios.append(bloque_nuevo)
            stats['corregidos'] += 1
            
            if stats['corregidos'] <= 5:
                print(f"  ✓ Entrada {i} corregida (lema largo):")
                print(f"    Antes: {lema_raw[:60]}...")
                print(f"    Después: {lema_limpio}")
            continue
    
    # Caso 3: Lemas muy cortos (<3 chars) pero el bloque es válido
    if len(lema_raw) < 3:
        # Intentar extraer más contexto si está disponible
        # Si hay DEF inmediatamente después, podría ser que el lema esté incompleto
        def_match = re.search(r'<DEF>\s*([A-ZÀÈÉÍÒÓÚ]+)', bloque)
        if def_match:
            posible_lema = def_match.group(1).strip()
            if 3 <= len(posible_lema) <= 30:
                # Parece un lema válido, usarlo
                lema_completo = lema_raw + posible_lema
                resto = bloque[def_match.end():]
                
                bloque_nuevo = f"<LEMA> {lema_completo} <DEF> {resto}"
                bloques_limpios.append(bloque_nuevo)
                stats['corregidos'] += 1
                continue
    
    # Si no necesita corrección, mantener tal cual
    bloques_limpios.append(bloque)
    stats['sin_cambios'] += 1

# Generar dataset final limpio
print(f"\n{'='*80}")
print("RESULTADOS DE LA LIMPIEZA:")
print('='*80)
print(f"Entradas originales: {stats['original']}")
print(f"Entradas corregidas: {stats['corregidos']}")
print(f"Entradas eliminadas: {stats['eliminados']}")
print(f"Entradas sin cambios: {stats['sin_cambios']}")
print(f"Total final: {len(bloques_limpios)}")

# Calcular estadísticas del dataset limpio
total_chars = sum(len(b) for b in bloques_limpios)
entradas_con_ejemplos = sum(1 for b in bloques_limpios if '<EX>' in b)

print(f"\n### ESTADÍSTICAS FINALES")
print(f"Total de caracteres: {total_chars:,}")
print(f"Promedio por entrada: {total_chars/len(bloques_limpios):.1f} caracteres")
print(f"Entradas con ejemplos: {entradas_con_ejemplos}/{len(bloques_limpios)} ({entradas_con_ejemplos/len(bloques_limpios)*100:.1f}%)")

# Guardar dataset limpio
output_txt = 'catalan_medieval_FINAL.txt'
with open(output_txt, 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(bloques_limpios))

# Guardar JSONL
output_jsonl = 'catalan_medieval_FINAL.jsonl'
with open(output_jsonl, 'w', encoding='utf-8') as f:
    for i, bloque in enumerate(bloques_limpios, 1):
        # Extraer lema para metadata
        lema_match = re.search(r'<LEMA>\s*([^<\n]+?)(?:\s*<DEF>|<END>)', bloque)
        lema = lema_match.group(1).strip() if lema_match else "UNKNOWN"
        
        json.dump({
            'id': i,
            'lema': lema[:50],  # Limitar a 50 chars para metadata
            'has_example': '<EX>' in bloque,
            'length': len(bloque),
            'text': bloque
        }, f, ensure_ascii=False)
        f.write('\n')

# Guardar log de limpieza
log_file = 'cleaning_light_log.json'
with open(log_file, 'w', encoding='utf-8') as f:
    json.dump({
        'stats': stats,
        'final_entries': len(bloques_limpios),
        'final_chars': total_chars,
        'avg_chars': total_chars / len(bloques_limpios),
        'entries_with_examples': entradas_con_ejemplos,
        'example_coverage': entradas_con_ejemplos / len(bloques_limpios) * 100
    }, f, ensure_ascii=False, indent=2)

# Mostrar muestra final
print(f"\n{'='*80}")
print("MUESTRA DE 5 ENTRADAS FINALES:")
print('='*80)

for i, bloque in enumerate(bloques_limpios[:5], 1):
    print(f"\n{i}. {bloque[:200]}..." if len(bloque) > 200 else f"\n{i}. {bloque}")

print(f"\n{'='*80}")
print("✅ LIMPIEZA COMPLETADA")
print('='*80)
print(f"Archivos generados:")
print(f"  • {output_txt} - Dataset final para entrenamiento")
print(f"  • {output_jsonl} - Dataset estructurado en JSON")
print(f"  • {log_file} - Log de limpieza")
print('='*80)