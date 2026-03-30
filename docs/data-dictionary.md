# Data Dictionary

## Tables

### `stores`
Retail store locations across Canada.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Auto-increment ID |
| store_code | VARCHAR(10) | UNIQUE, NOT NULL | e.g., "CTC-001" |
| name | VARCHAR(100) | NOT NULL | Full store name |
| city | VARCHAR(50) | NOT NULL | Toronto, Vancouver, Calgary, Montreal, Ottawa |
| province | VARCHAR(2) | NOT NULL | Two-letter code: ON, BC, AB, QC |
| latitude | DECIMAL(9,6) | NOT NULL | GPS latitude |
| longitude | DECIMAL(9,6) | NOT NULL | GPS longitude |
| store_type | VARCHAR(20) | NOT NULL | standard, warehouse, express |
| opened_date | DATE | NOT NULL | Store opening date |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |

**Row count:** 10 stores

---

### `categories`
Product categories with seasonal metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Auto-increment ID |
| name | VARCHAR(50) | UNIQUE, NOT NULL | e.g., "Winter Tires" |
| department | VARCHAR(50) | NOT NULL | e.g., "Automotive" |
| is_seasonal | BOOLEAN | DEFAULT FALSE | Whether demand varies by season |
| peak_season | VARCHAR(20) | NULLABLE | winter, summer, spring, fall |

**Row count:** 14 categories

---

### `products`
Individual SKUs within categories.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Auto-increment ID |
| sku | VARCHAR(20) | UNIQUE, NOT NULL | e.g., "RP-WT-0001" |
| name | VARCHAR(100) | NOT NULL | Product name |
| category_id | INTEGER | FK -> categories(id) | Parent category |
| unit_price | DECIMAL(10,2) | NOT NULL | Retail price |
| unit_cost | DECIMAL(10,2) | NOT NULL | Cost to store |
| is_active | BOOLEAN | DEFAULT TRUE | Active product flag |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |

**Row count:** 56 products

---

### `transactions`
Individual sales records (fact table).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | Auto-increment ID |
| store_id | INTEGER | FK -> stores(id), INDEXED | Selling store |
| product_id | INTEGER | FK -> products(id), INDEXED | Product sold |
| transaction_date | DATE | NOT NULL, INDEXED | Sale date |
| quantity | INTEGER | NOT NULL, CHECK > 0 | Units sold |
| unit_price | DECIMAL(10,2) | NOT NULL | Price at time of sale |
| total_amount | DECIMAL(12,2) | NOT NULL | quantity x unit_price |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |

**Indexes:** Composite on (store_id, product_id, transaction_date), separate on transaction_date.

**Row count:** ~139,000 (2 years of daily data)

---

### `weather_daily`
Daily weather per store location. Historical data is synthetic; current data can be fetched from OpenWeatherMap.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | Auto-increment ID |
| store_id | INTEGER | FK -> stores(id) | Store location |
| date | DATE | NOT NULL | Weather date |
| temp_high_c | DECIMAL(5,2) | | Daily high temperature (Celsius) |
| temp_low_c | DECIMAL(5,2) | | Daily low temperature |
| temp_mean_c | DECIMAL(5,2) | | Daily mean temperature |
| precipitation_mm | DECIMAL(7,2) | | Rain + melted snow |
| snowfall_cm | DECIMAL(7,2) | | Snow accumulation |
| wind_speed_kmh | DECIMAL(5,1) | | Wind speed |
| weather_code | VARCHAR(20) | | OpenWeatherMap icon code |
| weather_description | VARCHAR(50) | | e.g., "heavy snow", "clear sky" |
| fetched_at | TIMESTAMPTZ | DEFAULT NOW() | When data was cached |

**Unique constraint:** (store_id, date)

**Row count:** ~7,300 (10 stores x 730 days)

---

### `holidays`
Canadian public holidays. Fetched from Nager.Date API (real data).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Auto-increment ID |
| date | DATE | NOT NULL | Holiday date |
| name | VARCHAR(100) | NOT NULL | e.g., "Canada Day" |
| country_code | VARCHAR(2) | DEFAULT 'CA' | Always CA |
| province_code | VARCHAR(2) | NULLABLE | NULL = national, "ON" = Ontario-only |
| is_public | BOOLEAN | DEFAULT TRUE | Public holiday flag |
| holiday_type | VARCHAR(20) | | Public, Bank, Observance |

**Unique constraint:** (date, name, province_code)

**Row count:** ~106 (2 years of Canadian holidays)

---

### `events`
Local events per city (synthetic). Includes sports games, festivals, concerts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Auto-increment ID |
| name | VARCHAR(200) | NOT NULL | Event name |
| event_type | VARCHAR(30) | NOT NULL | sports, festival, concert |
| city | VARCHAR(50) | NOT NULL | City name (matches stores) |
| venue | VARCHAR(100) | | Venue name |
| start_date | DATE | NOT NULL | Event start |
| end_date | DATE | NULLABLE | NULL for single-day events |
| estimated_attendance | INTEGER | | Approximate crowd size |
| source | VARCHAR(20) | | "synthetic" for generated data |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |

**Row count:** ~388

---

### `daily_aggregates`
Pre-computed daily rollups by store and category. This is the primary table consumed by the ML pipeline.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | Auto-increment ID |
| store_id | INTEGER | FK -> stores(id) | Store |
| category_id | INTEGER | FK -> categories(id) | Product category |
| date | DATE | NOT NULL | Aggregation date |
| total_quantity | INTEGER | NOT NULL | Total units sold |
| total_revenue | DECIMAL(12,2) | NOT NULL | Total revenue |
| transaction_count | INTEGER | NOT NULL | Number of transactions |
| avg_basket_size | DECIMAL(10,2) | | Average revenue per transaction |

**Unique constraint:** (store_id, category_id, date)

**Row count:** ~69,000

---

## Entity Relationships

```
stores (1) ----< (N) transactions (N) >---- (1) products (N) >---- (1) categories
stores (1) ----< (N) weather_daily
stores (1) ----< (N) daily_aggregates (N) >---- (1) categories
holidays (standalone, joined by date + province)
events (standalone, joined by date + city)
```

## ML Feature Matrix

The feature builder joins `daily_aggregates`, `weather_daily`, `holidays`, and `events` to produce 30 features:

| Feature Group | Features | Source Table |
|---------------|----------|--------------|
| Temporal | day_of_week, month, week_of_year, is_weekend, quarter | date |
| Weather | temp_high/low/mean_c, precipitation_mm, snowfall_cm, wind_speed_kmh, is_snow_day, is_rain_day, is_extreme_cold, is_hot_day, temp_deviation | weather_daily |
| Holiday | is_holiday, days_to_next_holiday, days_from_prev_holiday, days_to_christmas | holidays |
| Events | event_count_3day, event_attendance_3day | events |
| Lag | rolling_7d_qty, rolling_28d_qty, lag_7d_qty, lag_14d_qty, lag_364d_qty | daily_aggregates |
| Category | is_seasonal, category_peak_match | categories |

**Target variable:** `total_quantity` from daily_aggregates
