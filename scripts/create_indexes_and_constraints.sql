-- Indexes and partial-unique constraints for SCD2 current rows.
-- Apply after bulk loads to avoid slowing down inserts.

-- FactSales indexes
CREATE INDEX IF NOT EXISTS idx_factsales_datekey      ON gold.factsales(datekey);
CREATE INDEX IF NOT EXISTS idx_factsales_customerkey  ON gold.factsales(customerkey);
CREATE INDEX IF NOT EXISTS idx_factsales_employeekey  ON gold.factsales(employeekey);
CREATE INDEX IF NOT EXISTS idx_factsales_productkey   ON gold.factsales(productkey);
CREATE INDEX IF NOT EXISTS idx_factsales_locationkey  ON gold.factsales(locationkey);

-- FactInvoices indexes
CREATE INDEX IF NOT EXISTS idx_factinvoices_datekey              ON gold.factinvoices(datekey);
CREATE INDEX IF NOT EXISTS idx_factinvoices_customerkey          ON gold.factinvoices(customerkey);
CREATE INDEX IF NOT EXISTS idx_factinvoices_employeekey          ON gold.factinvoices(employeekey);
CREATE INDEX IF NOT EXISTS idx_factinvoices_accountsemployeekey  ON gold.factinvoices(accountsemployeekey);
CREATE INDEX IF NOT EXISTS idx_factinvoices_locationkey          ON gold.factinvoices(locationkey);
CREATE INDEX IF NOT EXISTS idx_factinvoices_deliverymethodkey    ON gold.factinvoices(deliverymethodkey);

-- DimDate index for date filters
CREATE INDEX IF NOT EXISTS idx_dimdate_date ON gold.dimdate(date);

-- Partial-unique indexes — at most one active (current) row per business key
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimemployee_personid_current        ON gold.dimemployee(personid)        WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimcustomer_customerid_current      ON gold.dimcustomer(customerid)      WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimlocation_locationid_current      ON gold.dimlocation(locationid)      WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimproduct_stockitemid_current      ON gold.dimproduct(stockitemid)      WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimdeliverymethod_deliverymethodid_current ON gold.dimdeliverymethod(deliverymethodid) WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimpaymentmethod_paymentmethodid_current   ON gold.dimpaymentmethod(paymentmethodid)   WHERE date_to IS NULL;
