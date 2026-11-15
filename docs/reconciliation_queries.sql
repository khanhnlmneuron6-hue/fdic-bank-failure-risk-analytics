-- SQL examples for data extraction, testing and financial reconciliation.
-- Financials is a typed quarterly view; amounts are thousand USD.
SELECT REPDTE, COUNT(*) AS reports, COUNT(DISTINCT CERT) AS banks,
       SUM(CASE WHEN ASSET IS NULL OR ASSET <= 0 THEN 1 ELSE 0 END) AS invalid_asset_denominator,
       SUM(CASE WHEN ABS(ASSET-LIAB-EQ) > 0.001*ABS(ASSET) THEN 1 ELSE 0 END) AS balance_sheet_exceptions
FROM financials
GROUP BY REPDTE ORDER BY REPDTE;

-- An exception is investigated, not automatically deleted.
SELECT CERT, REPDTE, ASSET, LIAB, EQ, ASSET-LIAB-EQ AS reconciliation_gap
FROM financials WHERE ABS(ASSET-LIAB-EQ) > 0.001*ABS(ASSET)
ORDER BY ABS(ASSET-LIAB-EQ) DESC;

-- Calendar-quarter join: never use the previous row as the previous quarter.
SELECT a.CERT, a.qi, a.NETINC,
       CASE WHEN MOD(a.qi,4)=0 THEN a.NETINC ELSE a.NETINC-b.NETINC END AS derived_net_income_quarter
FROM financials_with_qi a LEFT JOIN financials_with_qi b
ON a.CERT=b.CERT AND a.qi=b.qi+1;
