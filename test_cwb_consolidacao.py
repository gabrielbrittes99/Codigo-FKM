"""
Teste completo de consolidação CWB com dados reais
"""
import pandas as pd
from filial_mapping import criar_mapa_filiais, normalizar_filial

print("="*80)
print("TESTE DE CONSOLIDAÇÃO CWB COM DADOS REAIS")
print("="*80)

# Testar mapeamento de filiais
print("\n1. Testando criar_mapa_filiais()...")
mapa_filiais, mapa_datas = criar_mapa_filiais("Manutencao 0126.xlsx")

# Verificar filiais CWB no mapa
filiais_cwb = [f for f in mapa_filiais.values() if 'CWB' in str(f)]
filiais_cwb_unicas = list(set(filiais_cwb))

print(f"\n📊 Filiais CWB encontradas no mapeamento:")
for filial in sorted(filiais_cwb_unicas):
    count = filiais_cwb.count(filial)
    print(f"   - {filial}: {count} placas")

# Verificar se CWB (ECT) foi eliminada
if any('CWB (ECT)' in str(f) for f in filiais_cwb_unicas):
    print("\n❌ ERRO: CWB (ECT) ainda existe no mapeamento!")
else:
    print("\n✅ SUCESSO: CWB (ECT) foi consolidada em CWB (BASE)")

# Testar com dados de combustível
print("\n2. Testando normalização em dados de combustível...")
df_comb = pd.read_excel("Combustivel 0126.xlsx")

# Normalizar garagem
df_comb["Garagem_Normalizada"] = df_comb["Garagem"].apply(normalizar_filial)

# Verificar garagens CWB
garagens_cwb_antes = df_comb[df_comb["Garagem"].str.contains("CWB", na=False)]["Garagem"].unique()
garagens_cwb_depois = df_comb[df_comb["Garagem_Normalizada"].str.contains("CWB", na=False)]["Garagem_Normalizada"].unique()

print(f"\n📊 Garagens CWB ANTES da normalização:")
for g in sorted(garagens_cwb_antes):
    count = (df_comb["Garagem"] == g).sum()
    print(f"   - {g}: {count} registros")

print(f"\n📊 Garagens CWB DEPOIS da normalização:")
for g in sorted(garagens_cwb_depois):
    count = (df_comb["Garagem_Normalizada"] == g).sum()
    print(f"   - {g}: {count} registros")

if any('CWB (ECT)' in str(g) for g in garagens_cwb_depois):
    print("\n❌ ERRO: CWB (ECT) ainda existe após normalização!")
else:
    print("\n✅ SUCESSO: Todas as referências a CWB (ECT) foram consolidadas!")

print("\n" + "="*80)
print("TESTE CONCLUÍDO")
print("="*80)
