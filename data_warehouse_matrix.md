 # Data Warehouse Matrix

 Columns: Source Table | Source PK | Source Business Key(s) | Key Source Columns (example) | Target Table | Target PK | Target Business Key | Key Target Columns (example) | Transform / Rule | SCD | Notes

 ---

 customers | `customerid` | `customerid` | `customername, customercategoryid, deliverymethodid, deliverylocation, deliveryaddressline1` | `gold.dimcustomer` (SCD2) / `silver.stg_customers` | `customerkey` (surrogate) | `customerid` | `customerid, customername, category, deliverylocation` | Normalize strings, coalesce address lines, map `customercategoryid`→category lookup | SCD2 | Snapshot source in `tmp_snapshots/customers.csv` (663 rows)

 stockitems | `stockitemid` | `stockitemid` | `stockitemname, brand, size, unitprice` | `gold.dimproduct` / `silver.stg_products` | `productkey` (surrogate) | `stockitemid` | `stockitemid, stockitemname, brand, size` | Clean names, extract brand, json->attributes from `customfields` | SCD2 | Snapshot in `tmp_snapshots/stockitems.csv` (227 rows)

 paymentmethods | `paymentmethodid` | `paymentmethodid` | `paymentmethodname` | `gold.dimpaymentmethod` / `silver.stg_paymentmethods` | `paymentmethodkey` | `paymentmethodid` | `paymentmethodid, paymentmethodname` | Direct lookup; small dimension seeded from snapshot | SCD2 (small) | Snapshot in `tmp_snapshots/paymentmethods.csv` (4 rows). Populated also from `customertransactions` usage.

 customertransactions | `customertransactionid` | `customertransactionid` | `customerid, transactiontypeid, invoiceid, paymentmethodid, transactiondate, transactionamount` | `gold.factpayments` (optional) / `silver.stg_customertransactions` | `transactionid` (surrogate) | `customertransactionid` | `customerid, paymentmethodid, invoiceid, amount, date` | Map paymentmethodid -> `dimpaymentmethod` FK; amounts normalized; date -> `dimdate` | No | Source for `DimPaymentMethod` and payment analysis (97,147 rows)

 deliverymethods | `deliverymethodid` | `deliverymethodid` | `deliverymethodname` | `gold.dimdeliverymethod` / `silver.stg_deliverymethods` | `deliverymethodkey` | `deliverymethodid` | `deliverymethodname` | Direct mapping; small dimension | SCD2 (small) | Snapshot in `tmp_snapshots/deliverymethods.csv` (10 rows)

 countries | `countryid` | `countryid` | `ountryname (typo in snapshot), formalname, isoalpha3code` | `gold.dimlocation` (part) / `silver.stg_locations` | `locationkey` | `countryid` | `country, formalname, isoalpha3code` | Map `ountryname`→`country`; normalize names | No (part of location SCD) | Snapshot has `ountryname` typo; corrected in silver (190 rows)

 stateprovinces | `stateprovinceid` | `stateprovinceid` | `stateprovincename, countryid, salesterritory` | `gold.dimlocation` (part) / `silver.stg_locations` | `locationkey` | `stateprovinceid` | `stateprovincename, countryid` | Join country/state to compose location; sales_territory preserved | No (part of location SCD) | Snapshot in `tmp_snapshots/stateprovinces.csv` (53 rows)

 people | `personid` | `personid` | `fullname, isemployee, issalesperson, emailaddress` | `gold.dimemployee` / `silver.stg_employees` | `employeekey` | `personid` | `fullname, isemployee, issalesperson, contact` | Normalize names; flag sales employees; hash sensitive fields if needed | SCD2 | Snapshot in `tmp_snapshots/people.csv` (1,111 rows)

 transactiontypes | `transactiontypeid` | `transactiontypeid` | `transactiontypename` | `gold.dimtransactiontype` / `silver.stg_transactiontypes` | `transactiontypekey` | `transactiontypeid` | `transactiontypename` | Direct mapping; used to interpret `customertransactions`/invoices | No | Snapshot in `tmp_snapshots/transactiontypes.csv` (13 rows)

 invoices | `invoiceid` | `invoiceid` | `customerid, invoicedate, invoiceamount, deliverymethodid` | `gold.factinvoices` / `silver.stg_invoices` | `invoicefactkey` | `invoiceid` | `invoiceid, customerkey, datekey, deliverymethodkey, invoiceamount` | Build surrogate keys via lookups; paymentmethod may be NULL — use `customertransactions` to join payments | No | Profiled: 70,510 rows (in source)

 invoicelines | `invoicelineid` | `invoicelineid` | `invoiceid, stockitemid, quantity, unitprice, taxamount` | `gold.factsales` / `silver.stg_invoicelines` | `saleskey` | `invoicelineid` | `invoiceid, productkey, quantity, extendedprice` | Compute extended price; compute line-level `row_hash()` for SCD2-driven dedup/changes | No | Profiled: 228,265 rows

 customercategories | `customercategoryid` | `customercategoryid` | `customercategoryname` | `gold.dimcustomercategory` / `silver.stg_customercategories` | `categorykey` | `customercategoryid` | `customercategoryname` | Direct mapping | No | Snapshot present (8 rows)

 ---

 Notes:
 - Counts and table lists from `scripts/data_profiling.md` (see Table 1). Use `99_verification.py` outputs to fill final row counts in the Gold layer.
 - `SCD2` indicates whether the target dimension implements slowly-changing-dimension type 2 semantics (surrogate keys + date_from/date_to + current flag). For small lookup dims, SCD2 is used for consistency but can be treated as static.

 If you want a CSV version for import to Excel, tell me and I'll add `data_warehouse_matrix.csv`.
