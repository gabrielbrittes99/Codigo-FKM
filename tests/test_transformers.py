import numpy as np
import pandas as pd
import pandera.errors
import pytest

from src.transformers.fuel_transformer import (
    limpar_e_converter_hodometro,
    limpar_e_converter_numero,
    transformar_dados_combustivel,
)


def test_limpar_numero_float():
    assert limpar_e_converter_numero(123.45) == 123.45
    assert limpar_e_converter_numero(1000) == 1000.0


def test_limpar_numero_texto_com_r_cifrao():
    assert limpar_e_converter_numero("R$ 1.234,56") == 1234.56
    assert limpar_e_converter_numero(" R$ 50,00 ") == 50.0


def test_limpar_numero_vazio():
    assert limpar_e_converter_numero(np.nan) == 0.0
    assert limpar_e_converter_numero(None) == 0.0


def test_limpar_hodometro_multiplica_por_1000():
    assert limpar_e_converter_hodometro("251,132") == 251132
    assert limpar_e_converter_hodometro(251.132) == 251132
    assert limpar_e_converter_hodometro(576) == 576
    assert limpar_e_converter_hodometro(576.0) == 576


def test_transformar_dados_valida_pandera():
    # Criar DataFrame "sujo"
    dados_sujos = {
        "Placa": [" ABC-1234 ", "def5678", None],  # Tem nulo, vai quebrar ou arrumar
        "Litragem": ["R$ 50,00", 100.5, np.nan],
        "Valor total": ["1.500,20", "150,00", 0],
        "Preco": [10.0, 5.0, 0],
        "Hodometro/Horimetro": ["251,132", 100, 0],
        "Hodometro/Horimetro anterior": [250, 50, 0],
        "Combustivel": ["Diesel S10", "Arla 32", "Gasolina"],
        "Garagem": ["Filial A", "Filial B", "Filial C"],
    }
    df = pd.DataFrame(dados_sujos)

    # Remover o None da placa para o teste de sucesso (o schema exige placa não nula)
    df.loc[2, "Placa"] = "GHI9012"

    # Executar pipeline de transformação
    df_limpo = transformar_dados_combustivel(df)

    # Validações
    assert df_limpo["Placa_Clean"].iloc[0] == "ABC1234"  # Hífen e espaços removidos
    assert df_limpo["Litragem"].iloc[0] == 50.0
    assert df_limpo["Valor total"].iloc[0] == 1500.20
    assert df_limpo["Hodometro/Horimetro"].iloc[0] == 251132


def test_transformar_dados_falha_pandera_litragem_negativa():
    dados_sujos = {
        "Placa": ["ABC1234"],
        "Litragem": [-10],  # Litragem negativa viola o contrato (ge=0)
        "Litragem": [-10], # Litragem negativa viola o contrato (ge=0)
        "Litragem": [-10],  # Litragem negativa viola o contrato (ge=0)
        "Hodometro/Horimetro": [100],
        "Hodometro/Horimetro anterior": [90],
    }
    df = pd.DataFrame(dados_sujos)

    # Pandera deve lançar SchemaError
    with pytest.raises(pandera.errors.SchemaError):
        transformar_dados_combustivel(df)
