"""
Teste para verificar consolidação de filiais CWB
"""
from filial_mapping import normalizar_filial

# Testes de normalização
testes = [
    ("GRITSCH - CWB (ECT)", "GRITSCH - CWB (BASE)"),
    ("GRITSCH - CWB (BASE)", "GRITSCH - CWB (BASE)"),
    ("GRITSCH - CWB (DIR)", "GRITSCH - CWB (DIR)"),
    ("GRITSCH - CTB", "GRITSCH - CTB"),
    ("GRITSCH - POA", "GRITSCH - POA"),
]

print("="*80)
print("TESTE DE NORMALIZAÇÃO DE FILIAIS")
print("="*80)

todos_passaram = True
for entrada, esperado in testes:
    resultado = normalizar_filial(entrada)
    passou = resultado == esperado
    todos_passaram = todos_passaram and passou
    
    status = "✅" if passou else "❌"
    print(f"{status} {entrada:30} → {resultado:30} (esperado: {esperado})")

print("\n" + "="*80)
if todos_passaram:
    print("✅ TODOS OS TESTES PASSARAM!")
else:
    print("❌ ALGUNS TESTES FALHARAM!")
print("="*80)
