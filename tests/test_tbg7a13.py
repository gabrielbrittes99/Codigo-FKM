"""
Teste rápido para verificar se TBG7A13 está sendo alocada para CTB
"""
import pandas as pd
from src.filial_mapping import aplicar_filial_manutencao, criar_mapa_filiais

# Criar mapa de filiais
mapa_filiais, mapa_datas = criar_mapa_filiais("Manutencao 0126.xlsx")

# Ler dados de combustível
df = pd.read_excel("Combustivel 0126.xlsx")

# Aplicar mapeamento de filiais
df = aplicar_filial_manutencao(
    df, 
    mapa_filiais, 
    mapa_datas_manutencao=mapa_datas,
    coluna_placa="Placa", 
    coluna_garagem="Garagem",
    coluna_data="Data da transacao"
)

# Filtrar apenas TBG7A13
df_tbg = df[df["Placa"].str.contains("TBG7A13", case=False, na=False)]

print("\n" + "="*80)
print("VERIFICAÇÃO: TBG7A13")
print("="*80)

if len(df_tbg) > 0:
    print(f"\n✅ Encontrados {len(df_tbg)} registros da placa TBG7A13")
    print(f"\nFiliais aplicadas:")
    print(df_tbg[["Placa", "Garagem", "Filial_Final"]].drop_duplicates())
    
    filiais_finais = df_tbg["Filial_Final"].unique()
    print(f"\n📊 Filiais únicas em Filial_Final: {filiais_finais}")
    
    if "GRITSCH - CTB" in filiais_finais and len(filiais_finais) == 1:
        print("\n✅ SUCESSO! Todos os registros estão alocados para GRITSCH - CTB")
    else:
        print("\n❌ ERRO! Nem todos os registros estão em GRITSCH - CTB")
        print(df_tbg[["Placa", "Garagem", "Filial_Final"]].value_counts())
else:
    print("\n⚠️ Nenhum registro encontrado para TBG7A13")
