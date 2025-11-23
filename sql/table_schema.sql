DROP TABLE IF EXISTS __TABLE_NAME__;

CREATE TABLE __TABLE_NAME__ (
    creation_date DATE,
    purchase_date DATE,
    fiscal_year TEXT,
    lpa_number TEXT,
    purchase_order_number TEXT,
    requisition_number TEXT,
    acquisition_type TEXT,
    sub_acquisition_type TEXT,
    acquisition_method TEXT,
    sub_acquisition_method TEXT,
    department_name TEXT,
    supplier_code TEXT,
    supplier_name TEXT,
    supplier_qualifications TEXT,
    supplier_zip_code TEXT,
    calcard TEXT,
    item_name TEXT,
    item_description TEXT,
    quantity NUMERIC,
    unit_price NUMERIC(18, 2),
    total_price NUMERIC(18, 2),
    classification_codes TEXT,
    normalized_unspsc NUMERIC,
    commodity_title TEXT,
    class NUMERIC,
    class_title TEXT,
    family NUMERIC,
    family_title TEXT,
    segment NUMERIC,
    segment_title TEXT,
    location TEXT
);

-- INDEXES FOR FASTER QUERY RESOLUTION
-- Index 1: Filtering by Department and Date (Common analytical queries)
CREATE INDEX idx___TABLE_NAME___dept_date ON __TABLE_NAME__ (department_name, purchase_date);

-- Index 2: Searching by Supplier (Common lookup)
CREATE INDEX idx___TABLE_NAME___supplier_name ON __TABLE_NAME__ (supplier_name);

-- Index 3: Filtering by Contract/LPA Number (Used for contract spend analysis)
CREATE INDEX idx___TABLE_NAME___lpa_num ON __TABLE_NAME__ (lpa_number);

-- Index 4: Filtering/Grouping by Acquisition Type
CREATE INDEX idx___TABLE_NAME___acq_type ON __TABLE_NAME__ (acquisition_type);

-- Index 5: Filtering/Grouping by Fiscal Year
CREATE INDEX idx___TABLE_NAME___fiscal_year ON __TABLE_NAME__ (fiscal_year);