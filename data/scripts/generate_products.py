"""Generate product categories and products for Canadian retail simulation."""

from decimal import Decimal

from data.scripts.db.models import Category, Product

CATEGORIES = [
    Category(name="Winter Tires", department="Automotive", is_seasonal=True, peak_season="winter"),
    Category(name="All-Season Tires", department="Automotive", is_seasonal=False, peak_season=None),
    Category(
        name="Snow Blowers", department="Outdoor Power", is_seasonal=True, peak_season="winter"
    ),
    Category(
        name="BBQ Grills & Accessories", department="Living", is_seasonal=True, peak_season="summer"
    ),
    Category(
        name="Patio Furniture", department="Living", is_seasonal=True, peak_season="summer"
    ),
    Category(
        name="Hockey Equipment", department="Sports", is_seasonal=True, peak_season="fall"
    ),
    Category(name="Camping Gear", department="Sports", is_seasonal=True, peak_season="summer"),
    Category(
        name="Christmas Decor", department="Living", is_seasonal=True, peak_season="winter"
    ),
    Category(
        name="Garden & Lawn", department="Outdoor Living", is_seasonal=True, peak_season="spring"
    ),
    Category(name="Tools & Hardware", department="Tools", is_seasonal=False, peak_season=None),
    Category(name="Paint & Supplies", department="Home", is_seasonal=True, peak_season="spring"),
    Category(name="Plumbing", department="Home", is_seasonal=False, peak_season=None),
    Category(name="Electrical", department="Home", is_seasonal=False, peak_season=None),
    Category(
        name="Automotive Accessories", department="Automotive", is_seasonal=False, peak_season=None
    ),
]

# (category_name, sku_prefix, products: list of (name, price, cost))
PRODUCT_CATALOG: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    ("Winter Tires", "WT", [
        ("Blizzak WS90 205/55R16", "189.99", "120.00"),
        ("X-Ice Snow 225/65R17", "219.99", "140.00"),
        ("WinterContact SI 195/65R15", "159.99", "100.00"),
        ("Observe GSi-6 215/60R16", "174.99", "110.00"),
    ]),
    ("All-Season Tires", "AT", [
        ("Assurance WeatherReady 215/55R17", "199.99", "130.00"),
        ("CrossClimate2 225/65R17", "229.99", "150.00"),
        ("Defender T+H 205/65R15", "169.99", "108.00"),
    ]),
    ("Snow Blowers", "SB", [
        ('PowerSmart 24" Two-Stage', "899.99", "580.00"),
        ('Husqvarna ST224 24"', "1199.99", "780.00"),
        ('Toro Power Clear 21"', "549.99", "350.00"),
        ("EGO SNT2400 Electric", "1099.99", "720.00"),
    ]),
    ("BBQ Grills & Accessories", "BG", [
        ("Weber Spirit II E-310", "649.99", "420.00"),
        ("Napoleon Prestige 500", "1299.99", "850.00"),
        ("Char-Broil Performance 4-Burner", "449.99", "280.00"),
        ("BBQ Cover Universal Fit", "49.99", "22.00"),
        ("Grilling Tool Set 18-Piece", "39.99", "18.00"),
    ]),
    ("Patio Furniture", "PF", [
        ("6-Piece Wicker Conversation Set", "999.99", "580.00"),
        ("Cantilever Patio Umbrella 10ft", "249.99", "140.00"),
        ("Adirondack Chair Resin", "129.99", "65.00"),
        ("Outdoor Dining Table 60in", "449.99", "260.00"),
    ]),
    ("Hockey Equipment", "HK", [
        ("Bauer Vapor X3 Skates", "349.99", "220.00"),
        ("CCM Jetspeed FT6 Pro Stick", "289.99", "180.00"),
        ("Warrior Alpha DX Gloves", "99.99", "55.00"),
        ("Bauer RE-AKT 85 Helmet", "149.99", "88.00"),
        ("Hockey Tape Cloth 1in 3-Pack", "9.99", "3.50"),
    ]),
    ("Camping Gear", "CG", [
        ("Woods Pinnacle 4-Person Tent", "299.99", "175.00"),
        ("Coleman 50-Degree Sleeping Bag", "59.99", "30.00"),
        ("Yeti Tundra 45 Cooler", "399.99", "260.00"),
        ("Camping Chair Folding Quad", "44.99", "20.00"),
    ]),
    ("Christmas Decor", "XD", [
        ("7ft Pre-Lit Spruce Tree", "299.99", "150.00"),
        ("LED String Lights 100ct", "19.99", "7.50"),
        ("Outdoor Inflatable Santa 6ft", "89.99", "38.00"),
        ("Wreath 24in Natural Pine", "49.99", "22.00"),
    ]),
    ("Garden & Lawn", "GL", [
        ("Honda HRN216 Self-Propelled Mower", "599.99", "400.00"),
        ("Scotts Turf Builder 12kg", "49.99", "25.00"),
        ("Garden Hose 100ft Expandable", "39.99", "16.00"),
        ("Raised Garden Bed Cedar 4x8", "129.99", "65.00"),
        ("Pruning Shear Set 3-Piece", "24.99", "10.00"),
    ]),
    ("Tools & Hardware", "TH", [
        ("DeWalt 20V Drill/Driver Kit", "199.99", "125.00"),
        ("Socket Set 200-Piece Mechanic", "149.99", "78.00"),
        ("Mastercraft Screwdriver Set 50pc", "29.99", "12.00"),
        ("Tape Measure 25ft Stanley", "14.99", "6.00"),
    ]),
    ("Paint & Supplies", "PS", [
        ("Behr Premium Plus Interior Gallon", "49.99", "25.00"),
        ("Paint Roller Kit 9-Piece", "19.99", "8.00"),
        ("Painter's Tape Blue 2in x 60yd", "8.99", "3.50"),
        ("Drop Cloth Canvas 9x12", "24.99", "11.00"),
    ]),
    ("Plumbing", "PL", [
        ("Moen Engage Showerhead Chrome", "89.99", "48.00"),
        ("Toilet Repair Kit Universal", "14.99", "5.50"),
        ("Pipe Wrench 14in Heavy Duty", "34.99", "17.00"),
    ]),
    ("Electrical", "EL", [
        ("LED Bulb 60W Equivalent 8-Pack", "12.99", "5.00"),
        ("Power Bar 6-Outlet Surge Protector", "24.99", "10.00"),
        ("Smart Plug Wi-Fi 2-Pack", "29.99", "13.00"),
    ]),
    ("Automotive Accessories", "AA", [
        ("Booster Cable 16ft 6-Gauge", "39.99", "18.00"),
        ("Windshield Washer Fluid -40C 3.78L", "4.99", "1.80"),
        ("Floor Mat Set All-Weather 4pc", "69.99", "32.00"),
        ("Ice Scraper Deluxe Telescoping", "14.99", "5.50"),
    ]),
]


def generate_categories() -> list[Category]:
    """Return list of Category ORM objects."""
    return CATEGORIES


def generate_products(categories: list[Category]) -> list[Product]:
    """Generate Product ORM objects linked to persisted categories."""
    cat_map = {c.name: c.id for c in categories}
    products: list[Product] = []
    sku_counter: dict[str, int] = {}

    for cat_name, prefix, items in PRODUCT_CATALOG:
        cat_id = cat_map.get(cat_name)
        if cat_id is None:
            continue
        sku_counter[prefix] = 0
        for prod_name, price, cost in items:
            sku_counter[prefix] += 1
            products.append(
                Product(
                    sku=f"RP-{prefix}-{sku_counter[prefix]:04d}",
                    name=prod_name,
                    category_id=cat_id,
                    unit_price=Decimal(price),
                    unit_cost=Decimal(cost),
                )
            )

    return products
