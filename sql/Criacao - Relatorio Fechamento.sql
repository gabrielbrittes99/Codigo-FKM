/*
RELATORIO FKM DATA DE EMISSAO - COM FILIAL DA OCORRENCIA
VERSAO OTIMIZADA v1
- Correcao 1: filtro de data movido para dentro da CTE BASE (antes dos APPLYs)
- Correcao 4: MAPEAMENTO e USUARIOS_FILIAIS_ID materializados em #temp tables com PK
*/

USE referencia;

-- ============================================================
-- 1) Tabelas temporarias de lookup (com PK -> usa indice)
-- ============================================================

IF OBJECT_ID('tempdb..#Mapeamento') IS NOT NULL DROP TABLE #Mapeamento;
IF OBJECT_ID('tempdb..#UsuariosFiliais') IS NOT NULL DROP TABLE #UsuariosFiliais;

CREATE TABLE #Mapeamento (
    DescricaoCompleta   VARCHAR(200) NOT NULL PRIMARY KEY,
    NaturezaVinculada   VARCHAR(200) NOT NULL
);

INSERT INTO #Mapeamento (DescricaoCompleta, NaturezaVinculada) VALUES
('01.01 - DIREÇÃO', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('01.02 - FREIOS', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('01.03 - INJEÇÃO E ALIMENTAÇÃO', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('01.04 - MOTOR', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('01.05 - SUSPENSÃO', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('01.06 - TRANSMISSÃO', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('01.07 - AR-CONDICIONADO', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('02.01 - ADITIVOS E FLUIDOS', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('02.02 - ARLA', '02.02 - ARLA'),
('02.03 - FILTROS', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('02.04 - ÓLEOS E LUBRIFICANTES', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('03.01 - BATERIA', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('03.02 - LANTERNAS E FARÓIS', '03.02 - LATARIA E PINTURA'),
('03.03 - RASTREAMENTO E MONITORAMENTO DE VEÍCULO', '04.01 - RASTREAMENTO E MONITORAMENTO DE VEÍCULO'),
('03.04 - SISTEMA ELÉTRICO', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('04.01 - ALINHAMENTO E BALANCEAMENTO', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('04.02 - PNEUS', '03.05 - RODAS E PNEUS'),
('04.03 - RODAS', '03.05 - RODAS E PNEUS'),
('05.01 - ACESSÓRIOS DE VEÍCULOS', '03.04 - ACESSÓRIOS DE VEÍCULOS'),
('05.02 - LATARIA E PINTURA', '03.02 - LATARIA E PINTURA'),
('05.03 - LAVAGEM E HIGIENIZAÇÃO', '03.01 - LAVAGEM'),
('05.04 - VIDROS E PARABRISAS', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('05.05 - DEDETIZAÇÃO DE VEÍCULO', '07.07 - DEDETIZAÇÃO DE VEÍCULO'),
('06.01 - IPVA (ANUAL)', '07.02 - IPVA (ANUAL)'),
('06.02 - IPVA (AQUISIÇÃO DE VEÍCULOS)', '07.06 - IPVA (AQUISIÇÃO DE VEÍCULOS)'),
('06.03 - LICENCIAMENTO', '07.03 - LICENCIAMENTO'),
('07.01 - SEGURO DE VEÍCULOS (FACULTATIVO)', '06.01 - SEGURO DE VEÍCULOS (FACULTATIVO)'),
('07.02 - VMI', '15.11 - REEMBOLSO CLIENTE (AVARIAS)'),
('08.01 - ASSISTÊNCIA 24 HORAS', '05.03 - ASSISTÊNCIA 24 HORAS'),
('08.02 - COMBUSTÍVEL', '02.01 - COMBUSTÍVEL'),
('08.03 - ESTACIONAMENTO', '08.01 - ESTACIONAMENTO'),
('08.04 - FRETES E CARRETOS', '05.01 - FRETES E CARRETOS'),
('08.05 - GUINCHO', '05.03 - ASSISTÊNCIA 24 HORAS'),
('08.06 - SERVIÇO DE DESLOCAMENTO', '16.01 - TAXI'),
('08.07 - SUBLOCAÇÃO DE VEÍCULOS', '09.01 - SUBCONTRATAÇÃO DE LOCAÇÃO DE VEÍCULOS'),
('03.03 - MANUTENÇÃO DE VEÍCULOS', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('09.02 - MÃO DE OBRA - PREVENTIVA', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('03.01 - LAVAGEM', '03.01 - LAVAGEM'),
('09.01 - MÃO DE OBRA - CORRETIVA', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('15.03 - TAXAS DIVERSAS', '15.03 - TAXAS DIVERSAS'),
('03.06 - MANUTENÇÃO PREVENTIVA', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('03.22 - VIDROS E PARABRISAS', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('03.07 - ADITIVOS E FLUÍDOS', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('03.10 - BATERIA', '03.03 - MANUTENÇÃO DE VEÍCULOS'),
('04.01 - RASTREAMENTO E MONITORAMENTO DE VEÍCULO', '04.01 - RASTREAMENTO E MONITORAMENTO DE VEÍCULO'),
('05.03 - ASSISTÊNCIA 24 HORAS', '05.03 - ASSISTÊNCIA 24 HORAS'),
('03.02 - LATARIA E PINTURA', '03.02 - LATARIA E PINTURA'),
('03.04 - ACESSÓRIOS DE VEÍCULOS', '03.04 - ACESSÓRIOS DE VEÍCULOS'),
('03.05 - RODAS E PNEUS', '03.05 - RODAS E PNEUS'),
('09.01 - SUBLOCAÇÃO DE VEÍCULOS', '09.01 - SUBCONTRATAÇÃO DE LOCAÇÃO DE VEÍCULOS'),
('05.05 - GUINCHO', '05.03 - ASSISTÊNCIA 24 HORAS'),
('05.01 - FRETES E CARRETOS', '05.01 - FRETES E CARRETOS'),
('07.06 - IPVA (AQUISIÇÃO DE VEÍCULOS)', '07.06 - IPVA (AQUISIÇÃO DE VEÍCULOS)');

CREATE TABLE #UsuariosFiliais (
    IdUsuario       INT NOT NULL PRIMARY KEY,
    UnidadeForcada  VARCHAR(100) NOT NULL
);

INSERT INTO #UsuariosFiliais (IdUsuario, UnidadeForcada) VALUES
(22930,'REFERÊNCIA GOIÂNIA LOJA'),
(22946,'REFERÊNCIA CUIABÁ LOJA'),
(22958,'REFERÊNCIA MARINGÁ'),
(22967,'REFERÊNCIA SALVADOR'),
(22970,'REFERÊNCIA VILHENA'),
(22972,'REFERÊNCIA LUIS EDUARDO MAGALHÃES'),
(22978,'REFERÊNCIA SINOP'),
(22986,'REFERÊNCIA FOZ DO IGUAÇU'),
(22993,'REFERÊNCIA ARAGUAÍNA'),
(23004,'REFERÊNCIA CUIABÁ LOJA'),
(23011,'REFERÊNCIA FOZ DO IGUAÇU'),
(23029,'REFERÊNCIA SALVADOR'),
(23030,'REFERÊNCIA GOIÂNIA LOJA'),
(23033,'REFERÊNCIA SALVADOR'),
(23039,'REFERÊNCIA GOIÂNIA LOJA'),
(23044,'REFERÊNCIA MARINGÁ'),
(23047,'REFERÊNCIA LUIS EDUARDO MAGALHÃES'),
(23063,'REFERÊNCIA SINOP'),
(23072,'REFERÊNCIA CUIABÁ LOJA'),
(23074,'REFERÊNCIA BRASILIA'),
(23089,'REFERÊNCIA GOIÂNIA LOJA'),
(23090,'REFERÊNCIA SÃO PAULO'),
(23095,'REFERÊNCIA CUIABÁ LOJA'),
(23097,'REFERÊNCIA SÃO PAULO'),
(23102,'REFERÊNCIA VILHENA'),
(23108,'REFERÊNCIA GOIÂNIA LOJA'),
(23110,'REFERÊNCIA SINOP'),
(23111,'REFERÊNCIA GOIÂNIA LOJA'),
(23114,'REFERÊNCIA RIBEIRAO PRETO'),
(23126,'REFERÊNCIA BALSAS'),
(23134,'REFERÊNCIA SINOP'),
(23135,'REFERÊNCIA BRASILIA'),
(23137,'REFERÊNCIA LUIS EDUARDO MAGALHÃES'),
(23165,'REFERÊNCIA SÃO PAULO'),
(23177,'REFERÊNCIA VILHENA'),
(23274,'REFERÊNCIA SINOP'),
(23447,'REFERÊNCIA BALSAS'),
(24247,'REFERÊNCIA SÃO PAULO'),
(25815,'REFERÊNCIA SÃO PAULO'),
(26240,'REFERÊNCIA SÃO PAULO'),
(26823,'REFERÊNCIA SINOP'),
(26919,'REFERÊNCIA SINOP'),
(26977,'REFERÊNCIA BRASILIA'),
(27638,'REFERÊNCIA SÃO PAULO'),
(27639,'REFERÊNCIA SÃO PAULO');

-- ============================================================
-- 2) Variaveis de janela de data (avalia uma vez so)
-- ============================================================
DECLARE @DataIni DATETIME = DATEADD(month, DATEDIFF(month, 0, GETDATE()) - 1, 0);
DECLARE @DataFim DATETIME = DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0);

-- ============================================================
-- 3) Query principal
-- ============================================================
WITH BASE AS (
    SELECT
        OS.IdNF,
        NF.NumeroNF,
        NF.TipoOrdemCompra,
        OS.OrdemServico,
        OS.Ocorrencia,
        OS.OrdemCompra,
        OS.Placa,
        OS.DescricaoItem,
        OS.TipoItem,
        OS.Tipo,
        NF.TipoNF,
        OS.IdGrupoDespesa,
        OS.GrupoDespesa,
        GP.CodigoCompleto,
        GP.DescricaoCompleta,
        MAP.NaturezaVinculada,
        OS.Quantidade,
        OS.ValorUnitario,
        OS.ValorTotal,
        OS.SituacaoOrdemServico,
        NF.IdUnidadeDeFaturamento,
        NF.UnidadeDeFaturamento,
        VC.IdFilialOperacional,
        VC.FilialOperacional,
        OS.IdVeiculo,
        VC.SituacaoVeiculo,
        OS.CriadoPor,
        OS.DataCriacaoOrdemServico,
        OS.DataCriacaoOcorrencia,
        NF.DataEmissao,
        NF.DataEntrada,
        OS.SituacaoOcorrencia,
        NF.IdFornecedor,
        OS.Fornecedor,
        LC.Natureza AS NaturezaFinanceira,
        NF.DataCriacao,
        OS.IdOcorrencia,
        OC.IdContratoComercial,
        CO.UnidadeDeFaturamento AS UnidadeDeFaturamentoContrato,
        USU.IdUsuario,
        USU.Nome,
        m.unidade_movimentada,
        m.Unidade_de_Destino AS MovFilialDestino,
        UF.UnidadeForcada,
        HV.DataVenda,
        OC.IdFilialOperacional AS IdFilialOperacionalOcorrencia,
        FO.FilialOperacional AS FilialOperacionalOcorrencia
    FROM
        dbo.ItensOrdemServico AS OS
        INNER JOIN dbo.NotasFiscais AS NF ON NF.IdNF = OS.IdNF
        INNER JOIN dbo.GruposDespesa AS GP ON GP.IdGrupoDespesas = OS.IdGrupoDespesa
        INNER JOIN dbo.Veiculos AS VC ON VC.Placa = OS.Placa
        INNER JOIN dbo.NaturezasFinanceiras AS LC ON GP.IdNaturezaFinanceira = LC.IdNaturezaFinanceira
        LEFT JOIN dbo.OcorrenciasManutencao AS OC ON OC.IdOcorrencia = OS.IdOcorrencia
        LEFT JOIN dbo.ContratosComerciais AS CO ON CO.IdContratoComercial = OC.IdContratoComercial
        LEFT JOIN #Mapeamento AS MAP
            ON UPPER(TRIM(GP.DescricaoCompleta)) = UPPER(TRIM(MAP.DescricaoCompleta))
        LEFT JOIN #UsuariosFiliais AS UF ON UF.IdUsuario = OC.IdUsuarioCriacao
        LEFT JOIN (
            SELECT
                Placa,
                MIN(UltimaAtualizacao) AS DataVenda
            FROM dbo.HistoricoSituacaoVeiculos
            WHERE SituacaoVeiculo = 'Vendido'
            GROUP BY Placa
        ) HV ON HV.Placa = OS.Placa
        OUTER APPLY (
            SELECT TOP 1
                FilialOperacional
            FROM dbo.Veiculos
            WHERE IdFilialOperacional = OC.IdFilialOperacional
        ) FO
        OUTER APPLY (
            SELECT TOP 1
                Unidade_de_Destino,
                unidade_movimentada
            FROM dbo.Movimentos
            WHERE Placa = OS.Placa
                AND Data_da_movimentação <= OS.DataCriacaoOcorrencia
                AND unidade_movimentada = 'OPERAÇÃO'
            ORDER BY Data_da_movimentação DESC
        ) m
        OUTER APPLY (
            SELECT TOP 1
                IdUsuario,
                Nome
            FROM dbo.Usuarios
            WHERE IdUsuario = OC.IdUsuarioCriacao
        ) AS USU
    WHERE
        -- ================================================
        -- CORRECAO 1: filtros aqui dentro, antes dos APPLYs
        -- ================================================
        NF.DataCriacao >= @DataIni
        AND NF.DataCriacao <  @DataFim
),

DADOS_CALCULADOS AS (
    SELECT
        b.*,
        CASE
            -- Forcar filial por placa
            WHEN b.Placa IN (
                'UBN-9E24','UBN-9E26','UBK-4B56','UBR-9B03','TAV-9E95',
                'UBN-9E25','UBR-9B07','SFD-4I64','SFG-4I64','UBR-9B05'
            ) THEN 'GRITSCH - PET'

            WHEN b.Placa IN (
                'SDU-F954','SEP-3C43','SEY-8A97','SFI-4A19','SFK-OF56',
                'UBD-6131','UBF-1G63','UBF-1G85','UBF-1G87','TAS-4H02'
            ) THEN 'GRITSCH - CXJ'

            WHEN b.Placa IN (
                'RHS-8D34','SDR-4D98','SDR-8E04','SDR-8E58','SDX-2J14',
                'SEN-1C55','SEN-1C56','SFL-1E46'
            ) THEN 'GRITSCH - PMW'

            -- Regras originais
            WHEN b.DataVenda IS NOT NULL AND b.DataCriacaoOcorrencia >= b.DataVenda
                THEN 'VEÍCULOS VENDIDOS'
            WHEN b.UnidadeForcada IS NOT NULL
                THEN b.UnidadeForcada
            WHEN b.UnidadeDeFaturamentoContrato IS NOT NULL
                THEN b.UnidadeDeFaturamentoContrato
            WHEN b.MovFilialDestino IS NOT NULL
                THEN b.MovFilialDestino
            WHEN b.FilialOperacionalOcorrencia IS NOT NULL
                THEN b.FilialOperacionalOcorrencia
            WHEN b.MovFilialDestino IS NULL
                 AND b.UnidadeDeFaturamento IS NOT NULL
                 AND b.UnidadeDeFaturamento NOT LIKE '%MATRIZ%'
                 AND b.UnidadeDeFaturamento <> b.FilialOperacional
                THEN b.FilialOperacional
            WHEN b.SituacaoVeiculo LIKE '%Disponível para Venda%'
                THEN b.FilialOperacional
            WHEN b.SituacaoVeiculo LIKE '%Vendido%'
                THEN 'VEÍCULOS VENDIDOS'
            WHEN b.FilialOperacional LIKE '%DEFINIR%' THEN
                CASE
                    WHEN (b.UnidadeDeFaturamento LIKE '%REF%' OR b.UnidadeDeFaturamentoContrato LIKE '%REF%')
                        THEN 'RATEIO - REF'
                    ELSE 'GRITSCH - MATRIZ'
                END
            ELSE b.FilialOperacional
        END AS FILIAL
    FROM BASE b
),

AJUSTE_FINAL AS (
    SELECT
        dc.*,
        CASE
            WHEN UPPER(TRIM(dc.TipoItem)) = 'PRODUTO' AND UPPER(dc.DescricaoItem) LIKE '%LAMPADA%'
                THEN '03.03 - MANUTENÇÃO DE VEÍCULOS'
            WHEN dc.NaturezaVinculada = '03.05 - RODAS E PNEUS'
                 AND ((UPPER(TRIM(dc.TipoItem)) = 'PRODUTO' AND UPPER(dc.DescricaoItem) LIKE '%PNEU%')
                      OR (UPPER(TRIM(dc.TipoItem)) = 'SERVIÇO' AND UPPER(dc.DescricaoItem) LIKE '%RECAPAR%'))
                THEN '03.05 - RODAS E PNEUS'
            WHEN dc.NaturezaVinculada = '03.05 - RODAS E PNEUS'
                THEN '03.03 - MANUTENÇÃO DE VEÍCULOS'
            ELSE dc.NaturezaVinculada
        END AS Natureza_Correta
    FROM DADOS_CALCULADOS dc
)

SELECT
    IdNF, NumeroNF, TipoOrdemCompra, OrdemServico, Ocorrencia, OrdemCompra, Placa,
    DescricaoItem, TipoItem, Tipo, TipoNF, IdGrupoDespesa, GrupoDespesa, CodigoCompleto,
    DescricaoCompleta, Quantidade, ValorUnitario, ValorTotal, SituacaoOrdemServico,
    IdUnidadeDeFaturamento, UnidadeDeFaturamento, IdFilialOperacional, FilialOperacional,
    IdVeiculo, SituacaoVeiculo, CriadoPor, DataCriacaoOrdemServico, DataCriacaoOcorrencia,
    DataEmissao, DataEntrada, SituacaoOcorrencia, IdFornecedor, Fornecedor,
    NaturezaFinanceira, DataCriacao, IdOcorrencia, IdContratoComercial, UnidadeDeFaturamentoContrato,
    IdUsuario, Nome, MovFilialDestino, UnidadeForcada, DataVenda,
    IdFilialOperacionalOcorrencia,
    FilialOperacionalOcorrencia,
    FILIAL,
    Natureza_Correta
FROM
    AJUSTE_FINAL
WHERE
    Natureza_Correta IN (
        '03.03 - MANUTENÇÃO DE VEÍCULOS',
        '03.05 - RODAS E PNEUS',
        '03.02 - LATARIA E PINTURA'
    )
ORDER BY
    DataCriacao DESC;

-- limpeza opcional
-- DROP TABLE #Mapeamento;
-- DROP TABLE #UsuariosFiliais;
