"""Synthetic demo data generator (pure Python, no database).

DEMONSTRATION DATA ONLY. Every customer, order and return is invented. The
behaviour profiles below are simplified patterns chosen for a demo; they do not
describe real fraud. The same seed and as_of date always give the same data.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

CATEGORIES = {
    # category: (base return propensity multiplier, typical price range)
    "Fashion": (1.6, (15, 120)),
    "Shoes": (1.5, (30, 160)),
    "Electronics": (1.1, (40, 900)),
    "Home & Kitchen": (0.8, (10, 250)),
    "Beauty": (0.7, (5, 60)),
    "Sports": (0.9, (15, 300)),
    "Toys": (0.8, (10, 90)),
    "Books": (0.4, (5, 45)),
}

PRODUCT_NOUNS = {
    "Fashion": [
        "Linen Shirt",
        "Denim Jacket",
        "Summer Dress",
        "Wool Sweater",
        "Chino Trousers",
        "Silk Scarf",
        "Hoodie",
        "Maxi Skirt",
    ],
    "Shoes": ["Running Shoes", "Leather Boots", "Canvas Sneakers", "Sandals", "Loafers", "Hiking Boots"],
    "Electronics": [
        "Wireless Earbuds",
        "Bluetooth Speaker",
        "Smartwatch",
        "Power Bank",
        "USB-C Hub",
        "Mechanical Keyboard",
        "Noise-Cancelling Headphones",
        "Action Camera",
    ],
    "Home & Kitchen": [
        "Chef Knife",
        "Air Fryer",
        "Coffee Grinder",
        "Bedsheet Set",
        "Table Lamp",
        "Cookware Set",
    ],
    "Beauty": ["Face Serum", "Hair Dryer", "Perfume", "Makeup Kit", "Beard Trimmer"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Cycling Helmet", "Tennis Racket", "Fitness Band"],
    "Toys": ["Building Blocks", "Puzzle Set", "RC Car", "Board Game", "Plush Toy"],
    "Books": ["Novel", "Cookbook", "Biography", "Science Guide", "Comic Collection"],
}
ADJECTIVES = ["Classic", "Pro", "Eco", "Urban", "Premium", "Everyday", "Compact", "Deluxe"]

FIRST = [
    "Aarav",
    "Diya",
    "Rohan",
    "Ananya",
    "Kabir",
    "Isha",
    "Vivaan",
    "Meera",
    "Arjun",
    "Saanvi",
    "Liam",
    "Emma",
    "Noah",
    "Olivia",
    "Mateo",
    "Sofia",
    "Yuki",
    "Hana",
    "Omar",
    "Layla",
    "Lucas",
    "Mia",
    "Ethan",
    "Zara",
    "Kai",
    "Nora",
    "Ravi",
    "Priya",
    "Samuel",
    "Amara",
    "Leo",
    "Chloe",
    "Ibrahim",
    "Fatima",
    "Daniel",
    "Aisha",
]
LAST = [
    "Sharma",
    "Patel",
    "Iyer",
    "Khan",
    "Singh",
    "Gupta",
    "Reddy",
    "Das",
    "Smith",
    "Garcia",
    "Kim",
    "Nguyen",
    "Müller",
    "Rossi",
    "Okafor",
    "Silva",
    "Tanaka",
    "Haddad",
    "Novak",
    "Brown",
    "Lopez",
    "Mensah",
    "Costa",
    "Ali",
    "Fischer",
    "Joshi",
    "Mehta",
    "Chen",
]

EXPLAINED_TEXT = {
    "SIZE_FIT": ["Too small around the shoulders", "Runs a full size large", "Length too short for me"],
    "DAMAGED_IN_TRANSIT": ["Box crushed, item cracked on arrival", "Package arrived wet and torn"],
    "DEFECTIVE": [
        "Left earbud stops charging after one day",
        "Zip broke on first use",
        "Screen has dead pixels",
    ],
    "NOT_WORKING": ["Does not power on with the supplied cable", "Bluetooth will not pair with any device"],
    "NOT_AS_DESCRIBED": [
        "Colour is much darker than the photos",
        "Material is polyester, listing says cotton",
    ],
    "WRONG_ITEM": ["Received the blue version instead of black", "Different model number than ordered"],
    "CHANGED_MIND": ["Found a better fit elsewhere", "No longer needed for the trip"],
    "OTHER": ["Gift recipient already had one"],
}


@dataclass
class Profile:
    name: str
    suspicious: bool
    share: float
    orders: tuple[int, int]
    return_prob: tuple[float, float]
    window: tuple[int, int]
    reasons: dict[str, float]
    explain_prob: float
    mismatch_prob: float
    high_rating_prob: float
    fashion_bias: float = 0.0
    recent_bias: float = 0.0


PROFILES = [
    Profile(
        "ordinary",
        False,
        0.50,
        (2, 9),
        (0.02, 0.09),
        (3, 20),
        {
            "SIZE_FIT": 3,
            "DEFECTIVE": 2,
            "DAMAGED_IN_TRANSIT": 2,
            "NOT_AS_DESCRIBED": 2,
            "CHANGED_MIND": 1,
            "NOT_WORKING": 1,
        },
        0.8,
        0.01,
        0.15,
    ),
    Profile(
        "frequent_honest",
        False,
        0.16,
        (6, 14),
        (0.18, 0.32),
        (2, 14),
        {"SIZE_FIT": 5, "NOT_AS_DESCRIBED": 2, "DAMAGED_IN_TRANSIT": 1, "DEFECTIVE": 1},
        0.85,
        0.02,
        0.2,
        fashion_bias=0.5,
    ),
    Profile(
        "new_customer",
        False,
        0.14,
        (1, 2),
        (0.1, 0.3),
        (2, 15),
        {"SIZE_FIT": 2, "CHANGED_MIND": 1, "DEFECTIVE": 1, "OTHER": 1},
        0.5,
        0.02,
        0.2,
    ),
    Profile(
        "wardrober",
        True,
        0.08,
        (7, 15),
        (0.42, 0.65),
        (0, 3),
        {"CHANGED_MIND": 2, "NOT_AS_DESCRIBED": 2, "OTHER": 2, "SIZE_FIT": 1},
        0.25,
        0.05,
        0.6,
        fashion_bias=0.7,
        recent_bias=0.5,
    ),
    Profile(
        "vague_serial_returner",
        True,
        0.07,
        (7, 15),
        (0.35, 0.55),
        (1, 8),
        {"NOT_WORKING": 3, "DEFECTIVE": 3, "OTHER": 2},
        0.1,
        0.08,
        0.3,
        recent_bias=0.3,
    ),
    Profile(
        "mismatch_abuser",
        True,
        0.05,
        (6, 13),
        (0.28, 0.45),
        (1, 6),
        {"WRONG_ITEM": 3, "NOT_WORKING": 2, "DEFECTIVE": 1},
        0.4,
        0.55,
        0.2,
        recent_bias=0.3,
    ),
]


@dataclass
class GenProduct:
    product_id: str
    product_name: str
    category: str
    price_range: tuple[int, int]
    category_risk: Decimal = Decimal("0")


@dataclass
class GenOrder:
    order_id: str
    customer_idx: int
    product_idx: int
    order_date: date
    delivery_date: date | None
    order_amount: Decimal
    order_status: str
    customer_rating: int | None


@dataclass
class GenReturn:
    return_id: str
    order_idx: int
    customer_idx: int
    reason_code: str
    reason_text: str | None
    return_date: date
    days_to_return: int
    mismatch_flag: bool
    refund_amount: Decimal
    return_status: str


@dataclass
class GenCustomer:
    customer_id: str
    name: str
    email: str
    profile: str
    suspicious: bool
    created_at: date


@dataclass
class Dataset:
    customers: list[GenCustomer] = field(default_factory=list)
    products: list[GenProduct] = field(default_factory=list)
    orders: list[GenOrder] = field(default_factory=list)
    returns: list[GenReturn] = field(default_factory=list)


def _weighted(rng: random.Random, weights: dict[str, float]) -> str:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def generate(seed: int = 42, n_customers: int = 300, as_of: date | None = None) -> Dataset:
    rng = random.Random(seed)
    as_of = as_of or date.today()
    ds = Dataset()

    for category, (_, price_range) in CATEGORIES.items():
        for noun in PRODUCT_NOUNS[category]:
            idx = len(ds.products) + 1
            ds.products.append(
                GenProduct(f"PROD{idx:03d}", f"{rng.choice(ADJECTIVES)} {noun}", category, price_range)
            )
    by_category: dict[str, list[int]] = {}
    for i, p in enumerate(ds.products):
        by_category.setdefault(p.category, []).append(i)

    profile_names = [p.name for p in PROFILES]
    profile_weights = [p.share for p in PROFILES]
    used_emails: set[str] = set()

    for c in range(n_customers):
        profile = PROFILES[profile_names.index(rng.choices(profile_names, weights=profile_weights)[0])]
        first, last = rng.choice(FIRST), rng.choice(LAST)
        email = f"{first.lower()}.{last.lower()}{c + 1}@example.com".replace("ü", "u")
        used_emails.add(email)
        created = as_of - timedelta(days=rng.randint(380, 900))
        ds.customers.append(
            GenCustomer(
                f"CUST{c + 1:04d}", f"{first} {last}", email, profile.name, profile.suspicious, created
            )
        )

        # Noise: some honest customers look a bit suspicious and vice versa.
        n_orders = rng.randint(*profile.orders)
        return_prob = rng.uniform(*profile.return_prob)
        if profile.suspicious and rng.random() < 0.2:
            return_prob *= 0.5

        for _ in range(n_orders):
            if rng.random() < profile.fashion_bias:
                category = rng.choice(["Fashion", "Shoes"])
            else:
                category = rng.choice(list(CATEGORIES))
            p_idx = rng.choice(by_category[category])
            product = ds.products[p_idx]
            recent = rng.random() < profile.recent_bias
            age = rng.randint(5, 90) if recent else rng.randint(5, 360)
            order_date = as_of - timedelta(days=age)
            status_roll = rng.random()
            if status_roll < 0.04:
                status, delivery = "CANCELLED", None
            elif age < 7 and status_roll < 0.5:
                status, delivery = "SHIPPED", None
            else:
                status, delivery = "DELIVERED", order_date + timedelta(days=rng.randint(1, 6))
                if delivery > as_of:
                    status, delivery = "SHIPPED", None
            amount = Decimal(str(round(rng.uniform(*product.price_range) * 80, 2)))  # INR (ranges are ~USD x 80)
            rating = rng.randint(1, 5) if status == "DELIVERED" and rng.random() < 0.6 else None
            ds.orders.append(
                GenOrder(
                    f"ORD{len(ds.orders) + 1:05d}", c, p_idx, order_date, delivery, amount, status, rating
                )
            )
            o_idx = len(ds.orders) - 1

            if status != "DELIVERED":
                continue
            category_mult = CATEGORIES[category][0]
            if rng.random() >= min(0.95, return_prob * category_mult):
                continue
            window = rng.randint(*profile.window)
            if not profile.suspicious and rng.random() < 0.1:
                window = rng.randint(0, 1)  # honest customers sometimes return fast too
            return_date = delivery + timedelta(days=window)
            if return_date > as_of:
                return_date, window = as_of, (as_of - delivery).days
            code = _weighted(rng, profile.reasons)
            text = rng.choice(EXPLAINED_TEXT[code]) if rng.random() < profile.explain_prob else None
            mismatch = rng.random() < profile.mismatch_prob
            if rng.random() < profile.high_rating_prob:
                ds.orders[o_idx].customer_rating = rng.randint(4, 5)
            elif ds.orders[o_idx].customer_rating and ds.orders[o_idx].customer_rating >= 4:
                ds.orders[o_idx].customer_rating = rng.randint(1, 3)
            ret_status = rng.choices(["REFUNDED", "APPROVED", "REQUESTED", "REJECTED"], [70, 15, 10, 5])[0]
            refund = amount if ret_status in ("REFUNDED", "APPROVED") else Decimal("0")
            if mismatch and ret_status == "REFUNDED" and rng.random() < 0.5:
                ret_status, refund = "REJECTED", Decimal("0")
            ds.returns.append(
                GenReturn(
                    f"RET{len(ds.returns) + 1:05d}",
                    o_idx,
                    c,
                    code,
                    text,
                    return_date,
                    window,
                    mismatch,
                    refund,
                    ret_status,
                )
            )

    # category_risk = observed return rate per category among delivered orders.
    delivered: dict[str, int] = {}
    returned: dict[str, int] = {}
    for o in ds.orders:
        if o.order_status == "DELIVERED":
            cat = ds.products[o.product_idx].category
            delivered[cat] = delivered.get(cat, 0) + 1
    for r in ds.returns:
        cat = ds.products[ds.orders[r.order_idx].product_idx].category
        returned[cat] = returned.get(cat, 0) + 1
    for p in ds.products:
        rate = returned.get(p.category, 0) / delivered[p.category] if delivered.get(p.category) else 0
        p.category_risk = Decimal(str(round(rate, 3)))
    return ds
