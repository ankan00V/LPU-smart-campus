import json
from datetime import datetime, time

from sqlalchemy.orm import Session

from . import models
from .mongo import mirror_document, mirror_event

DEFAULT_AVAILABLE_FROM = time(10, 0)
DEFAULT_AVAILABLE_TO = time(21, 0)

HavmorFlavors = [
    "Vanilla",
    "Chocolate",
    "Butterscotch",
    "Strawberry",
    "Mango",
    "Black Currant",
]

FOOD_SHOPS = [
    {"name": "Domino's Pizza", "block": "UniMall — Block 17", "is_popular": False, "rating": 4.4, "average_prep_minutes": 16},
    {"name": "Wow! Momo", "block": "UniMall — Block 17", "is_popular": False, "rating": 4.2, "average_prep_minutes": 14},
    {"name": "Chicago Pizza", "block": "UniMall — Block 17", "is_popular": False, "rating": 4.1, "average_prep_minutes": 17},
    {"name": "Café Coffee Day", "block": "UniMall — Block 17", "is_popular": False, "rating": 4.3, "average_prep_minutes": 12},
    {"name": "Andhra Food House", "block": "BH-1", "is_popular": False, "rating": 4.2, "average_prep_minutes": 15},
    {"name": "AB Juice Bar", "block": "BH-1", "is_popular": False, "rating": 4.0, "average_prep_minutes": 9},
    {"name": "Telugu Vantillu", "block": "BH-1", "is_popular": False, "rating": 4.1, "average_prep_minutes": 13},
    {"name": "Campus Fusion", "block": "BH-1", "is_popular": False, "rating": 4.0, "average_prep_minutes": 16},
    {"name": "Havmor Ice Cream", "block": "BH-1", "is_popular": False, "rating": 4.3, "average_prep_minutes": 8},
    {"name": "NK Food Court", "block": "BH-2–6", "is_popular": True, "rating": 4.4, "average_prep_minutes": 14},
    {"name": "Pizza Express", "block": "BH-2–6", "is_popular": False, "rating": 4.0, "average_prep_minutes": 15},
    {"name": "Juice World", "block": "BH-2–6", "is_popular": False, "rating": 4.0, "average_prep_minutes": 9},
    {"name": "Chinese Eatery", "block": "BH-2–6", "is_popular": False, "rating": 4.1, "average_prep_minutes": 13},
    {"name": "Nand Juice", "block": "BH-2–6", "is_popular": False, "rating": 4.0, "average_prep_minutes": 9},
    {"name": "Campus Fusion", "block": "BH-2–6", "is_popular": False, "rating": 4.0, "average_prep_minutes": 16},
    {"name": "Kannu Ki Chai", "block": "Block-41", "is_popular": False, "rating": 4.2, "average_prep_minutes": 7},
    {"name": "Yippee", "block": "Block-41", "is_popular": False, "rating": 3.9, "average_prep_minutes": 8},
    {"name": "Kitchen Ette", "block": "Block-41", "is_popular": True, "rating": 4.4, "average_prep_minutes": 14},
    {"name": "AB Juice Bar", "block": "Block-41", "is_popular": False, "rating": 4.0, "average_prep_minutes": 9},
    {"name": "Basant Ice Cream Corner", "block": "Block-41", "is_popular": False, "rating": 4.1, "average_prep_minutes": 8},
    {"name": "Northern Delights", "block": "Block-34", "is_popular": False, "rating": 4.1, "average_prep_minutes": 13},
    {"name": "Bengali Bawarchi", "block": "Block-34", "is_popular": False, "rating": 4.1, "average_prep_minutes": 14},
    {"name": "Tandoor Hub", "block": "Block-34", "is_popular": False, "rating": 4.2, "average_prep_minutes": 15},
    {"name": "Nand Juice", "block": "Block-34", "is_popular": False, "rating": 4.0, "average_prep_minutes": 9},
    {"name": "Oven Express", "block": "Campus-wide", "is_popular": True, "rating": 4.5, "average_prep_minutes": 13},
]


def _menu_row(name: str, price: float, **kwargs):
    row = {
        "name": name,
        "base_price": float(price),
        "description": kwargs.get("description"),
        "is_veg": kwargs.get("is_veg", True),
        "spicy_level": int(kwargs.get("spicy_level", 0)),
        "variants": kwargs.get("variants", []),
        "addons": kwargs.get("addons", []),
        "stock_quantity": int(kwargs.get("stock_quantity", 120)),
        "sold_out": bool(kwargs.get("sold_out", False)),
        "is_active": bool(kwargs.get("is_active", True)),
    }
    return row


FOOD_MENU_BY_SHOP = {
    ("Oven Express", "Campus-wide"): [
        _menu_row("North Indian Thali", 140, description="North Indian + Multi-State Specials"),
        _menu_row("Paneer Royal Thali", 190),
        _menu_row("Dal Makhani Combo", 130),
        _menu_row("Butter Paneer + Rice", 160),
        _menu_row("Chole Kulche Plate", 120, spicy_level=1),
        _menu_row("Amritsari Kulcha", 130, spicy_level=2),
        _menu_row("Lucknowi Veg Biryani", 150, spicy_level=2),
        _menu_row("Kolkata Veg Roll", 110, spicy_level=1),
        _menu_row("Mumbai Pav Bhaji", 120, spicy_level=2),
        _menu_row("Hakka Noodles", 110, spicy_level=2),
        _menu_row("Masala Dosa", 110, spicy_level=1),
        _menu_row("Cold Coffee", 70),
        _menu_row("Sweet Lassi", 80),
        _menu_row("Salty Lassi", 80),
    ],
    ("Kitchen Ette", "Block-41"): [
        _menu_row("Mini Punjabi Thali", 120),
        _menu_row("Executive North Thali", 180),
        _menu_row("Dal Tadka", 90, spicy_level=1),
        _menu_row("Dal Makhani", 120),
        _menu_row("Shahi Paneer", 160),
        _menu_row("Kadai Paneer", 160, spicy_level=2),
        _menu_row("Rajma Chawal", 130),
        _menu_row("Chole Rice", 130, spicy_level=1),
        _menu_row("Jeera Rice", 80),
        _menu_row("Butter Naan", 35),
        _menu_row("Tandoori Roti", 20),
        _menu_row("Paneer Paratha", 100, spicy_level=1),
        _menu_row("Masala Chai", 25),
        _menu_row("Lassi (Sweet/Salted)", 90),
    ],
    ("NK Food Court", "BH-2–6"): [
        _menu_row("Mini Thali", 90),
        _menu_row("Regular Thali", 130),
        _menu_row("Deluxe Thali", 170),
        _menu_row("South Indian Thali", 150),
        _menu_row("Gujarati Thali", 160),
        _menu_row("Bengali Veg Meal", 170),
        _menu_row("Veg Fried Rice", 110, spicy_level=1),
        _menu_row("Schezwan Rice", 130, spicy_level=3),
        _menu_row("Veg Noodles", 110, spicy_level=1),
        _menu_row("Manchurian", 130, spicy_level=2),
        _menu_row("Momos", 110, spicy_level=1),
        _menu_row("Veg Burger", 100),
        _menu_row("Pizza Slice", 90),
        _menu_row("Masala Dosa", 110, spicy_level=1),
        _menu_row("Idli Vada Combo", 120),
        _menu_row("Poha", 70),
        _menu_row("Pav Bhaji", 120, spicy_level=2),
        _menu_row("Chaat Plate", 100, spicy_level=2),
        _menu_row("Milkshake", 100),
        _menu_row("Fruit Juice", 80),
        _menu_row("Sweet Lassi", 90),
        _menu_row("Salty Lassi", 90),
    ],
    ("Wow! Momo", "UniMall — Block 17"): [
        _menu_row("Veg Momos", 110, spicy_level=1),
        _menu_row("Paneer Momos", 130, spicy_level=1),
        _menu_row("Cheese Momos", 140, spicy_level=1),
        _menu_row("Fried Momos", 130, spicy_level=2),
        _menu_row("Chilli Momos", 140, spicy_level=3),
        _menu_row("Momo Platter", 170, spicy_level=2),
        _menu_row("Momo Bowl", 160, spicy_level=2),
        _menu_row("Cold Drink", 60),
    ],
    ("Chicago Pizza", "UniMall — Block 17"): [
        _menu_row("Cheese Pizza", 150),
        _menu_row("Farm Veg Pizza", 170),
        _menu_row("Paneer Pizza", 180),
        _menu_row("Corn Capsicum Pizza", 170),
        _menu_row("Garlic Bread", 100),
        _menu_row("Cheese Breadsticks", 120),
        _menu_row("Cold Drink", 60),
    ],
    ("Domino's Pizza", "UniMall — Block 17"): [
        _menu_row("Cheese Pizza", 150),
        _menu_row("Farm Veg Pizza", 170),
        _menu_row("Paneer Pizza", 180),
        _menu_row("Garlic Bread", 100),
        _menu_row("Cheese Breadsticks", 120),
        _menu_row("Cold Drink", 60),
    ],
    ("Café Coffee Day", "UniMall — Block 17"): [
        _menu_row("Cappuccino", 130),
        _menu_row("Latte", 140),
        _menu_row("Americano", 120),
        _menu_row("Cold Coffee", 160),
        _menu_row("Iced Latte", 180),
        _menu_row("Mocha", 170),
        _menu_row("Veg Sandwich", 150),
        _menu_row("Brownie", 130),
        _menu_row("Pastry", 150),
    ],
    ("AB Juice Bar", "BH-1"): [
        _menu_row("Orange Juice", 80),
        _menu_row("Apple Juice", 90),
        _menu_row("Mixed Fruit Juice", 100),
        _menu_row("Pomegranate Juice", 120),
        _menu_row("Smoothie", 120),
        _menu_row("Protein Shake", 150),
        _menu_row("Sweet Lassi", 90),
        _menu_row("Salty Lassi", 90),
    ],
    ("AB Juice Bar", "Block-41"): [
        _menu_row("Orange Juice", 80),
        _menu_row("Apple Juice", 90),
        _menu_row("Mixed Fruit Juice", 100),
        _menu_row("Pomegranate Juice", 120),
        _menu_row("Smoothie", 120),
        _menu_row("Protein Shake", 150),
        _menu_row("Sweet Lassi", 90),
        _menu_row("Salty Lassi", 90),
    ],
    ("Nand Juice", "BH-2–6"): [
        _menu_row("Seasonal Juice", 80),
        _menu_row("Fresh Juice", 90),
        _menu_row("Fruit Bowl", 110),
        _menu_row("Detox Juice", 130),
    ],
    ("Nand Juice", "Block-34"): [
        _menu_row("Seasonal Juice", 80),
        _menu_row("Fresh Juice", 90),
        _menu_row("Fruit Bowl", 110),
        _menu_row("Detox Juice", 130),
    ],
    ("Kannu Ki Chai", "Block-41"): [
        _menu_row("Cutting Chai", 20),
        _menu_row("Masala Chai", 25),
        _menu_row("Elaichi Chai", 30),
        _menu_row("Coffee", 35),
        _menu_row("Bun Maskaa", 50),
        _menu_row("Samosa", 25, spicy_level=1),
        _menu_row("Bread Pakora", 50, spicy_level=1),
    ],
    ("Yippee", "Block-41"): [
        _menu_row("Masala Noodles", 70, spicy_level=2),
        _menu_row("Cheese Noodles", 90, spicy_level=1),
        _menu_row("Veg Bowl", 110),
        _menu_row("Combo Bowl", 140, spicy_level=2),
    ],
    ("Andhra Food House", "BH-1"): [
        _menu_row("Andhra Meals", 150, spicy_level=3),
        _menu_row("Curd Rice", 100),
        _menu_row("Lemon Rice", 100, spicy_level=1),
        _menu_row("Sambar Rice", 110, spicy_level=2),
        _menu_row("Masala Dosa", 120, spicy_level=1),
        _menu_row("Idli Plate", 90),
    ],
    ("Telugu Vantillu", "BH-1"): [
        _menu_row("Meals Combo", 160, spicy_level=2),
        _menu_row("Plain Dosa", 100),
        _menu_row("Vada Plate", 90),
        _menu_row("Upma", 90),
        _menu_row("Rice + Curry", 140, spicy_level=2),
    ],
    ("Northern Delights", "Block-34"): [
        _menu_row("Dal Makhani", 120),
        _menu_row("Paneer Butter Masala", 160),
        _menu_row("Mix Veg", 100),
        _menu_row("Rice Plate", 70),
        _menu_row("Roti", 20),
        _menu_row("Thali", 150),
    ],
    ("Bengali Bawarchi", "Block-34"): [
        _menu_row("Veg Bengali Thali", 170),
        _menu_row("Aloo Posto", 130),
        _menu_row("Cholar Dal", 120),
        _menu_row("Rice Combo", 150),
        _menu_row("Mishti Dish", 100),
    ],
    ("Tandoor Hub", "Block-34"): [
        _menu_row("Paneer Tikka", 170, spicy_level=2),
        _menu_row("Veg Seekh", 150, spicy_level=2),
        _menu_row("Tandoori Mushroom", 160, spicy_level=2),
        _menu_row("Butter Naan", 40),
        _menu_row("Tandoori Roti", 25),
        _menu_row("Dal Fry", 90, spicy_level=1),
    ],
    ("Havmor Ice Cream", "BH-1"): [
        _menu_row(
            "Single Scoop",
            70,
            variants=[{"label": "Flavor", "options": HavmorFlavors}],
            addons=[{"label": "Chocolate Chips", "price": 20}, {"label": "Nuts", "price": 25}],
            spicy_level=0,
            stock_quantity=300,
        ),
        _menu_row(
            "Double Scoop",
            120,
            variants=[{"label": "Flavor", "options": HavmorFlavors}],
            addons=[{"label": "Chocolate Sauce", "price": 20}, {"label": "Waffle Cone", "price": 30}],
            spicy_level=0,
            stock_quantity=260,
        ),
        _menu_row("Sundae", 140, stock_quantity=180),
        _menu_row("Shake", 150, stock_quantity=180),
    ],
    ("Basant Ice Cream Corner", "Block-41"): [
        _menu_row("Single Scoop", 70, variants=[{"label": "Flavor", "options": HavmorFlavors}], stock_quantity=260),
        _menu_row("Double Scoop", 120, variants=[{"label": "Flavor", "options": HavmorFlavors}], stock_quantity=220),
        _menu_row("Sundae", 140, stock_quantity=140),
        _menu_row("Shake", 150, stock_quantity=140),
    ],
    ("Pizza Express", "BH-2–6"): [
        _menu_row("Cheese Pizza", 150),
        _menu_row("Farm Veg Pizza", 170),
        _menu_row("Paneer Pizza", 180),
        _menu_row("Corn Capsicum Pizza", 170),
        _menu_row("Garlic Bread", 100),
        _menu_row("Cold Drink", 60),
    ],
    ("Juice World", "BH-2–6"): [
        _menu_row("Seasonal Juice", 80),
        _menu_row("Fresh Juice", 90),
        _menu_row("Fruit Bowl", 110),
        _menu_row("Detox Juice", 130),
        _menu_row("Mixed Fruit Juice", 100),
    ],
    ("Chinese Eatery", "BH-2–6"): [
        _menu_row("Veg Fried Rice", 110, spicy_level=1),
        _menu_row("Schezwan Rice", 130, spicy_level=3),
        _menu_row("Veg Noodles", 110, spicy_level=1),
        _menu_row("Manchurian", 130, spicy_level=2),
        _menu_row("Momos", 110, spicy_level=1),
    ],
    ("Campus Fusion", "BH-1"): [
        _menu_row("North Indian Thali", 140),
        _menu_row("Paneer Royal Thali", 190),
        _menu_row("Lucknowi Veg Biryani", 150, spicy_level=2),
        _menu_row("Kolkata Veg Roll", 110, spicy_level=1),
        _menu_row("Hakka Noodles", 110, spicy_level=2),
    ],
    ("Campus Fusion", "BH-2–6"): [
        _menu_row("North Indian Thali", 140),
        _menu_row("Paneer Royal Thali", 190),
        _menu_row("Lucknowi Veg Biryani", 150, spicy_level=2),
        _menu_row("Kolkata Veg Roll", 110, spicy_level=1),
        _menu_row("Hakka Noodles", 110, spicy_level=2),
    ],
}


def _key(name: str, block: str) -> tuple[str, str]:
    return name.strip().lower(), block.strip().lower()


def bootstrap_food_hall_catalog(db: Session) -> dict:
    summary = {
        "shops_created": 0,
        "shops_updated": 0,
        "menu_created": 0,
        "menu_updated": 0,
        "items_created": 0,
        "items_updated": 0,
        "slots_created": 0,
        "slots_updated": 0,
    }
    now = datetime.utcnow()

    shops_by_key: dict[tuple[str, str], models.FoodShop] = {}
    for shop_data in FOOD_SHOPS:
        name = str(shop_data["name"]).strip()
        block = str(shop_data["block"]).strip()
        row = (
            db.query(models.FoodShop)
            .filter(models.FoodShop.name == name, models.FoodShop.block == block)
            .first()
        )
        if row is None:
            row = models.FoodShop(
                name=name,
                block=block,
                owner_user_id=None,
                is_active=True,
                is_popular=bool(shop_data.get("is_popular", False)),
                rating=float(shop_data.get("rating", 4.0)),
                average_prep_minutes=int(shop_data.get("average_prep_minutes", 18)),
                updated_at=now,
            )
            db.add(row)
            db.flush()
            summary["shops_created"] += 1
        else:
            row.is_active = True
            row.is_popular = bool(shop_data.get("is_popular", row.is_popular))
            row.rating = float(shop_data.get("rating", row.rating or 4.0))
            row.average_prep_minutes = int(shop_data.get("average_prep_minutes", row.average_prep_minutes or 18))
            row.updated_at = now
            summary["shops_updated"] += 1

        shops_by_key[_key(name, block)] = row
        mirror_document(
            "food_shops",
            {
                "id": row.id,
                "shop_id": row.id,
                "name": row.name,
                "block": row.block,
                "owner_user_id": row.owner_user_id,
                "is_active": row.is_active,
                "is_popular": row.is_popular,
                "rating": row.rating,
                "average_prep_minutes": row.average_prep_minutes,
                "updated_at": now,
                "source": "food-bootstrap",
            },
            upsert_filter={"shop_id": row.id},
        )

    for shop_tuple, item_rows in FOOD_MENU_BY_SHOP.items():
        shop_row = shops_by_key.get(_key(shop_tuple[0], shop_tuple[1]))
        if shop_row is None:
            continue

        for item_data in item_rows:
            item_name = str(item_data["name"]).strip()
            menu_row = (
                db.query(models.FoodMenuItem)
                .filter(models.FoodMenuItem.shop_id == shop_row.id, models.FoodMenuItem.name == item_name)
                .first()
            )

            variants = item_data.get("variants") or []
            addons = item_data.get("addons") or []
            if menu_row is None:
                menu_row = models.FoodMenuItem(
                    shop_id=shop_row.id,
                    name=item_name,
                    description=item_data.get("description"),
                    base_price=float(item_data["base_price"]),
                    is_veg=bool(item_data.get("is_veg", True)),
                    spicy_level=int(item_data.get("spicy_level", 0)),
                    variants_json=json.dumps(variants),
                    addons_json=json.dumps(addons),
                    available_from=DEFAULT_AVAILABLE_FROM,
                    available_to=DEFAULT_AVAILABLE_TO,
                    stock_quantity=int(item_data.get("stock_quantity", 120)),
                    sold_out=bool(item_data.get("sold_out", False)),
                    is_active=bool(item_data.get("is_active", True)),
                    updated_at=now,
                )
                db.add(menu_row)
                db.flush()
                summary["menu_created"] += 1
            else:
                menu_row.description = item_data.get("description")
                menu_row.base_price = float(item_data["base_price"])
                menu_row.is_veg = bool(item_data.get("is_veg", True))
                menu_row.spicy_level = int(item_data.get("spicy_level", 0))
                menu_row.variants_json = json.dumps(variants)
                menu_row.addons_json = json.dumps(addons)
                menu_row.available_from = DEFAULT_AVAILABLE_FROM
                menu_row.available_to = DEFAULT_AVAILABLE_TO
                menu_row.stock_quantity = int(item_data.get("stock_quantity", menu_row.stock_quantity or 120))
                menu_row.sold_out = bool(item_data.get("sold_out", False))
                menu_row.is_active = bool(item_data.get("is_active", True))
                menu_row.updated_at = now
                summary["menu_updated"] += 1

            food_item = db.query(models.FoodItem).filter(models.FoodItem.name == item_name).first()
            if food_item is None:
                food_item = models.FoodItem(name=item_name, price=float(item_data["base_price"]), is_active=True)
                db.add(food_item)
                db.flush()
                summary["items_created"] += 1
            else:
                food_item.price = float(item_data["base_price"])
                food_item.is_active = True
                summary["items_updated"] += 1

            mirror_document(
                "food_menu_items",
                {
                    "id": menu_row.id,
                    "menu_item_id": menu_row.id,
                    "shop_id": menu_row.shop_id,
                    "name": menu_row.name,
                    "description": menu_row.description,
                    "base_price": menu_row.base_price,
                    "is_veg": menu_row.is_veg,
                    "spicy_level": menu_row.spicy_level,
                    "variants": variants,
                    "addons": addons,
                    "available_from": str(menu_row.available_from) if menu_row.available_from else None,
                    "available_to": str(menu_row.available_to) if menu_row.available_to else None,
                    "stock_quantity": menu_row.stock_quantity,
                    "sold_out": menu_row.sold_out,
                    "is_active": menu_row.is_active,
                    "updated_at": now,
                    "source": "food-bootstrap",
                },
                upsert_filter={"menu_item_id": menu_row.id},
            )
            mirror_document(
                "food_items",
                {
                    "id": food_item.id,
                    "food_item_id": food_item.id,
                    "name": food_item.name,
                    "price": food_item.price,
                    "is_active": food_item.is_active,
                    "updated_at": now,
                    "source": "food-bootstrap",
                },
                upsert_filter={"food_item_id": food_item.id},
            )

    for hour in range(10, 21):
        slot_label = f"{hour:02d}:00 - {hour + 1:02d}:00"
        slot_row = db.query(models.BreakSlot).filter(models.BreakSlot.label == slot_label).first()
        if slot_row is None:
            slot_row = models.BreakSlot(
                label=slot_label,
                start_time=time(hour, 0),
                end_time=time(hour + 1, 0),
                max_orders=250,
            )
            db.add(slot_row)
            db.flush()
            summary["slots_created"] += 1
        else:
            slot_row.start_time = time(hour, 0)
            slot_row.end_time = time(hour + 1, 0)
            slot_row.max_orders = max(100, int(slot_row.max_orders or 250))
            summary["slots_updated"] += 1

        mirror_document(
            "break_slots",
            {
                "id": slot_row.id,
                "slot_id": slot_row.id,
                "label": slot_row.label,
                "start_time": str(slot_row.start_time),
                "end_time": str(slot_row.end_time),
                "max_orders": slot_row.max_orders,
                "updated_at": now,
                "source": "food-bootstrap",
            },
            upsert_filter={"slot_id": slot_row.id},
        )

    db.commit()
    mirror_event(
        "food.bootstrap",
        {
            **summary,
            "updated_at": now.isoformat(),
        },
        source="food-bootstrap",
    )
    return summary
