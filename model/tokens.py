import torch
import torch.nn as nn
from torch.nn import functional as F

# Configuramos el dispositivo
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Estamos usando: {device}")

# Para reproducibilidad
torch.manual_seed(1337)

# Carga de datos
with open('/Users/polpedrajas/Desktop/PythonProjects/nano-GPT/data/catalan_medieval_train.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("Longitud del dataset en caracteres: ", len(text))
print("\n--- Primeros 700 caracteres del dataset ---")
print(text[:700])