-- =============================================================================
-- fix_dup.sql — Remove duplicação causada pela execução 2x do load incremental
-- =============================================================================
-- Rode no SQL Editor do Supabase (ou via psql). Idempotente: rodar de novo não
-- causa dano (TRUNCATE em tabela vazia é no-op).
-- =============================================================================

-- 0) Diagnóstico ANTES (opcional — para registrar o estado atual)
SELECT 'antes' AS quando,
       (SELECT COUNT(*) FROM bronze.invoices)        AS bronze_invoices,
       (SELECT COUNT(*) FROM bronze.invoicelines)    AS bronze_invoicelines,
       (SELECT COUNT(*) FROM silver.stg_fact_sales)  AS silver_sales,
       (SELECT COUNT(*) FROM silver.stg_fact_invoices) AS silver_invoices,
       (SELECT COUNT(*) FROM gold.factsales)         AS gold_sales,
       (SELECT COUNT(*) FROM gold.factinvoices)      AS gold_invoices;

-- 1) Esvazia as tabelas de fatos no GOLD (CASCADE não é estritamente necessário
--    aqui pois não há FK apontando pra elas, mas mantemos por segurança).
TRUNCATE gold.factsales, gold.factinvoices RESTART IDENTITY CASCADE;

-- 2) Esvazia o staging fact no SILVER (DROP+CREATE acontece no 02_silver, mas
--    truncar agora deixa o estado consistente antes do replay).
TRUNCATE silver.stg_fact_sales, silver.stg_fact_invoices;

-- 3) Esvazia incremental do BRONZE (origem da duplicação).
TRUNCATE bronze.invoices, bronze.invoicelines RESTART IDENTITY;

-- 4) Limpa o controle de carga incremental para que o watermark volte ao zero
--    e a próxima execução do 01_bronze pegue TODO o histórico de invoices.
DELETE FROM bronze._load_control
 WHERE table_name IN ('invoices', 'invoicelines');

-- 5) Diagnóstico DEPOIS — todas as 6 contagens devem ser 0.
SELECT 'depois' AS quando,
       (SELECT COUNT(*) FROM bronze.invoices)        AS bronze_invoices,
       (SELECT COUNT(*) FROM bronze.invoicelines)    AS bronze_invoicelines,
       (SELECT COUNT(*) FROM silver.stg_fact_sales)  AS silver_sales,
       (SELECT COUNT(*) FROM silver.stg_fact_invoices) AS silver_invoices,
       (SELECT COUNT(*) FROM gold.factsales)         AS gold_sales,
       (SELECT COUNT(*) FROM gold.factinvoices)      AS gold_invoices;
