"""Domain constants for expense categories and subcategories."""

SUBCATEGORIES = [
    "Career",
    "Clothing & Shoes",
    "Dining",
    "Education",
    "Electricity",
    "Entertainment",
    "Essentials",
    "Gift",
    "Groceries",
    "Health",
    "Hobbies",
    "Internet",
    "Misc",
    "Phone",
    "Skincare & Makeup",
    "Special Events",
    "Subscriptions",
    "Taxes",
    "Transportation",
    "Travel - Flight",
    "Travel - Food & Dining",
    "Travel - Hotel",
    "Travel - Misc",
    "Travel - Special Events",
    "Travel - Transportation",
    "Water & Garbage",
]

SUBCATEGORY_TO_CATEGORY = {
    "Career": "Career & Learning",
    "Clothing & Shoes": "Personal Care",
    "Dining": "Food & Dining",
    "Education": "Career & Learning",
    "Electricity": "Utilities",
    "Entertainment": "Entertainment & Events",
    "Essentials": "Essentials",
    "Gift": "Gift",
    "Groceries": "Food & Dining",
    "Health": "Health",
    "Hobbies": "Career & Learning",
    "Internet": "Utilities",
    "Misc": "Misc",
    "Phone": "Utilities",
    "Skincare & Makeup": "Personal Care",
    "Special Events": "Entertainment & Events",
    "Subscriptions": "Subscriptions",
    "Taxes": "Taxes",
    "Transportation": "Transportation",
    "Travel - Flight": "Travel",
    "Travel - Food & Dining": "Travel",
    "Travel - Hotel": "Travel",
    "Travel - Misc": "Travel",
    "Travel - Special Events": "Travel",
    "Travel - Transportation": "Travel",
    "Water & Garbage": "Utilities",
}


def derive_category(subcategory: str) -> str:
    """Derive the parent category from a subcategory. Falls back to 'Misc'."""
    return SUBCATEGORY_TO_CATEGORY.get(subcategory, "Misc")
