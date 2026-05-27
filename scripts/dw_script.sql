-- =============================================================================
-- DSS P01 — Wide World Importers Data Mart
-- Consolidated DW SQL Script (Appendix B of the report)
-- =============================================================================
-- Section 1: Schemas (medallion architecture)
-- Section 2: Bronze metadata table (_load_control)
-- Section 3: Gold dimensions (SCD2 + DimDate)
-- Section 4: Gold fact tables
-- Section 5: Indexes and partial-unique constraints
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Section 1 — Schemas
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- -----------------------------------------------------------------------------
-- Section 2 — Bronze metadata: load control
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze._load_control (
    table_name      VARCHAR(100) NOT NULL,
    strategy        VARCHAR(20)  NOT NULL,
    snapshot_id     INT,
    watermark_date  DATE,
    loaded_at       TIMESTAMP    NOT NULL,
    rows_total      INT,
    rows_inserted   INT,
    rows_updated    INT,
    rows_deleted    INT,
    status          VARCHAR(20)  NOT NULL,
    PRIMARY KEY (table_name, loaded_at)
);

-- -----------------------------------------------------------------------------
-- Section 3 — Gold dimensions
-- -----------------------------------------------------------------------------

-- SCD Type 2: DimEmployee
CREATE TABLE IF NOT EXISTS gold.DimEmployee (
    EmployeeKey   SERIAL PRIMARY KEY,
    version       INT NOT NULL,
    date_from     TIMESTAMP NOT NULL,
    date_to       TIMESTAMP,
    PersonID      INT NOT NULL,
    FullName      VARCHAR(255),
    IsSalesperson INT
);

-- SCD Type 2: DimCustomer
CREATE TABLE IF NOT EXISTS gold.DimCustomer (
    CustomerKey  SERIAL PRIMARY KEY,
    version      INT NOT NULL,
    date_from    TIMESTAMP NOT NULL,
    date_to      TIMESTAMP,
    CustomerID   INT NOT NULL,
    CustomerName VARCHAR(255),
    Category     VARCHAR(255)
);

-- SCD Type 2: DimLocation
CREATE TABLE IF NOT EXISTS gold.DimLocation (
    LocationKey    SERIAL PRIMARY KEY,
    version        INT NOT NULL,
    date_from      TIMESTAMP NOT NULL,
    date_to        TIMESTAMP,
    LocationID     INT NOT NULL,
    City           VARCHAR(255),
    State          VARCHAR(255),
    Country        VARCHAR(255),
    SalesTerritory VARCHAR(50)
);

-- DimDate (snapshot, no SCD)
CREATE TABLE IF NOT EXISTS gold.DimDate (
    DateKey INT PRIMARY KEY,
    Date    DATE,
    Year    INT,
    Month   INT,
    Day     INT
);

-- SCD Type 2: DimProduct
CREATE TABLE IF NOT EXISTS gold.DimProduct (
    ProductKey    SERIAL PRIMARY KEY,
    version       INT NOT NULL,
    date_from     TIMESTAMP NOT NULL,
    date_to       TIMESTAMP,
    StockItemID   INT NOT NULL,
    StockItemName VARCHAR(255),
    Brand         VARCHAR(255)
);

-- SCD Type 2: DimDeliveryMethod
CREATE TABLE IF NOT EXISTS gold.DimDeliveryMethod (
    DeliveryMethodKey  SERIAL PRIMARY KEY,
    version            INT NOT NULL,
    date_from          TIMESTAMP NOT NULL,
    date_to            TIMESTAMP,
    DeliveryMethodID   INT NOT NULL,
    DeliveryMethodName VARCHAR(255)
);

-- SCD Type 2: DimPaymentMethod
CREATE TABLE IF NOT EXISTS gold.DimPaymentMethod (
    PaymentMethodKey   SERIAL PRIMARY KEY,
    version            INT NOT NULL,
    date_from          TIMESTAMP NOT NULL,
    date_to            TIMESTAMP,
    PaymentMethodID    INT NOT NULL,
    PaymentMethodName  VARCHAR(255)
);

-- -----------------------------------------------------------------------------
-- Section 4 — Gold fact tables
-- -----------------------------------------------------------------------------

-- FactSales — grain: invoice line
CREATE TABLE IF NOT EXISTS gold.FactSales (
    SalesKey      SERIAL PRIMARY KEY,
    InvoiceID     INT,
    DateKey       INT,
    EmployeeKey   INT,
    CustomerKey   INT,
    ProductKey    INT,
    LocationKey   INT,
    Quantity      INT,
    UnitPrice     NUMERIC(10,2),
    TaxAmount     NUMERIC(10,2),
    ExtendedPrice NUMERIC(10,2),
    LineProfit    NUMERIC(10,2),
    FOREIGN KEY (DateKey)     REFERENCES gold.DimDate(DateKey),
    FOREIGN KEY (EmployeeKey) REFERENCES gold.DimEmployee(EmployeeKey),
    FOREIGN KEY (CustomerKey) REFERENCES gold.DimCustomer(CustomerKey),
    FOREIGN KEY (ProductKey)  REFERENCES gold.DimProduct(ProductKey),
    FOREIGN KEY (LocationKey) REFERENCES gold.DimLocation(LocationKey)
);

-- FactInvoices — grain: invoice header
CREATE TABLE IF NOT EXISTS gold.FactInvoices (
    InvoiceFactKey      SERIAL PRIMARY KEY,
    InvoiceID           INT,
    DateKey             INT,
    EmployeeKey         INT,
    CustomerKey         INT,
    LocationKey         INT,
    AccountsEmployeeKey INT,
    DeliveryMethodKey   INT,
    InvoiceAmount       NUMERIC(10,2),
    PaymentDelay_Days   INT,
    OutstandingBalance  NUMERIC(10,2),
    FOREIGN KEY (DateKey)             REFERENCES gold.DimDate(DateKey),
    FOREIGN KEY (EmployeeKey)         REFERENCES gold.DimEmployee(EmployeeKey),
    FOREIGN KEY (CustomerKey)         REFERENCES gold.DimCustomer(CustomerKey),
    FOREIGN KEY (LocationKey)         REFERENCES gold.DimLocation(LocationKey),
    FOREIGN KEY (AccountsEmployeeKey) REFERENCES gold.DimEmployee(EmployeeKey),
    FOREIGN KEY (DeliveryMethodKey)   REFERENCES gold.DimDeliveryMethod(DeliveryMethodKey)
);

-- -----------------------------------------------------------------------------
-- Section 5 — Indexes and partial-unique constraints
-- -----------------------------------------------------------------------------

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
CREATE INDEX IF NOT EXISTS idx_factinvoices_accountsemployeekey ON gold.factinvoices(accountsemployeekey);
CREATE INDEX IF NOT EXISTS idx_factinvoices_locationkey          ON gold.factinvoices(locationkey);
CREATE INDEX IF NOT EXISTS idx_factinvoices_deliverymethodkey    ON gold.factinvoices(deliverymethodkey);

-- DimDate index
CREATE INDEX IF NOT EXISTS idx_dimdate_date ON gold.dimdate(date);

-- Partial-unique indexes for SCD2 current rows
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimemployee_personid_current        ON gold.dimemployee(personid)        WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimcustomer_customerid_current      ON gold.dimcustomer(customerid)      WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimlocation_locationid_current      ON gold.dimlocation(locationid)      WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimproduct_stockitemid_current      ON gold.dimproduct(stockitemid)      WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimdeliverymethod_deliverymethodid_current ON gold.dimdeliverymethod(deliverymethodid) WHERE date_to IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dimpaymentmethod_paymentmethodid_current   ON gold.dimpaymentmethod(paymentmethodid)   WHERE date_to IS NULL;
