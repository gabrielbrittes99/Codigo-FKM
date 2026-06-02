import numpy as np
import pandas as pd
import pytest

from src.loaders.excel_loader import preparar_resumos


def test_preparar_resumos_ignora_arla_no_km_mas_mantem_custo():
    # Cria dados de entrada com hodômetros simulando Arla
    dados = {
        "Placa": ["ABC1234", "ABC1234", "XYZ9876", "XYZ9876"],
        "Combustivel": ["Diesel S10", "Arla 32", "Diesel S10", "Arla 32"],
        "Estabelecimento": ["Posto 1", "Posto 1", "Posto 2", "Posto 2"],
        "Litragem": [100.0, 20.0, 50.0, 10.0],
        "Valor total": [500.0, 50.0, 250.0, 25.0],
        # Hodômetro do Diesel e Arla para ABC1234
        "Hodometro/Horimetro": [1000, 0, 500, 50],
        "Hodometro/Horimetro anterior": [900, 0, 450, 40],
    }
    df = pd.DataFrame(dados)

    resumo_combustivel, resumo_arla, resumo_posto = preparar_resumos(df)

    # Validações do Resumo de Combustível (Apenas Diesel)
    # A última linha é "Total Geral", então pegamos a linha da Placa ABC1234
    linha_abc = resumo_combustivel[
        resumo_combustivel["Rótulos de Linha"] == "ABC1234"
    ].iloc[0]

    # Arla não deve entrar na litragem do Diesel
    assert linha_abc["Soma de Litragem"] == 100.0
    assert linha_abc["Soma de Valor total"] == 500.0

    # O KM deve ignorar o 0, 0 do Arla (pegando só min=900, max=1000 do Diesel)
    assert linha_abc["Min. de Hodometro/Horimetro anterior"] == 900.0
    assert linha_abc["Máx. de Hodometro/Horimetro"] == 1000.0

    # Validações do Resumo Arla
    linha_abc_arla = resumo_arla[resumo_arla["Rótulos de Linha"] == "ABC1234"].iloc[0]
    assert linha_abc_arla["Soma de Valor total"] == 50.0

    # Validações do Total Geral
    linha_total = resumo_combustivel[
        resumo_combustivel["Rótulos de Linha"] == "Total Geral"
    ].iloc[0]
    assert linha_total["Soma de Litragem"] == 150.0  # 100 + 50
    assert linha_total["Soma de Valor total"] == 750.0


def test_preparar_resumos_ignora_hodometro_zerado():
    dados = {
        "Placa": ["ABC1234", "ABC1234"],
        "Combustivel": ["Diesel S10", "Diesel S10"],
        "Estabelecimento": ["Posto 1", "Posto 1"],
        "Litragem": [100.0, 50.0],
        "Valor total": [500.0, 250.0],
        # O segundo registro foi digitado errado pelo frentista (0)
        "Hodometro/Horimetro": [1000, 0],
        "Hodometro/Horimetro anterior": [900, 0],
    }
    df = pd.DataFrame(dados)

    resumo_combustivel, _, _ = preparar_resumos(df)

    linha_abc = resumo_combustivel[
        resumo_combustivel["Rótulos de Linha"] == "ABC1234"
    ].iloc[0]

    # O valor do combustível e litro entra normalmente (100 + 50)
    assert linha_abc["Soma de Litragem"] == 150.0
    assert linha_abc["Soma de Valor total"] == 750.0

    # O hodômetro ignora o zero, usando o primeiro registro apenas
    assert linha_abc["Min. de Hodometro/Horimetro anterior"] == 900.0
    assert linha_abc["Máx. de Hodometro/Horimetro"] == 1000.0
