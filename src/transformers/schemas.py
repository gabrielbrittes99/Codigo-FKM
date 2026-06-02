import pandera.pandas as pa
from pandera.typing import Series


class FuelCleanSchema(pa.DataFrameModel):
    """
    Contrato de dados para o DataFrame de Combustível APÓS a transformação básica.
    Garante que os tipos numéricos estejam corretos e sem valores inválidos que
    poderiam quebrar os cálculos agregados lá na frente.
    """

    Placa_Clean: Series[str] = pa.Field(nullable=False)
    Litragem: Series[float] = pa.Field(ge=0, nullable=False)
    Valor_total: Series[float] = pa.Field(ge=0, nullable=False, alias="Valor total")

    # Hodômetros podem ser nulos, mas se existirem, queremos que sejam float
    Hodometro_Horimetro: Series[float] = pa.Field(
        nullable=True, alias="Hodometro/Horimetro"
    )
    Hodometro_Horimetro_anterior: Series[float] = pa.Field(
        nullable=True, alias="Hodometro/Horimetro anterior"
    )

    # Informações cadastrais
    Combustivel: Series[str] = pa.Field(nullable=True)
    Garagem: Series[str] = pa.Field(nullable=True)

    class Config:
        coerce = True
        strict = False  # Aceita colunas extras vindas do arquivo original
