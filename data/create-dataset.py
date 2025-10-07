import pdfplumber

def extract_text_from_pdf(pdf_path):
    all_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)
    return "\n".join(all_text)

def clean_text(raw_text):
    # Ejemplo simple: eliminar líneas vacías y espacios innecesarios
    lines = raw_text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip() != '']
    return '\n'.join(cleaned_lines)

if __name__ == "__main__":
    pdf_path = "/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/mots-catala-antic.pdf" 
    raw_text = extract_text_from_pdf(pdf_path)
    cleaned_text = clean_text(raw_text)
    
    # Guarda el texto limpio en un archivo txt para usar como dataset
    with open("dataset_catalan_medieval.txt", "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    print("Texto extraído y limpio guardado en dataset_catalan_medieval.txt")
