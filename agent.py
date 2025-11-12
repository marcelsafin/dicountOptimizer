"""
Discount Optimizer Agent - Optimerar matinköp baserat på erbjudanden och preferenser
"""

from typing import List, Dict, Any
import json


# Mock data för tester
MOCK_DISCOUNTS = {
    "Stockholm": [
        {"store": "ICA Maxi", "product": "Tortillas", "original_price": 25, "discount_price": 18, "discount_percent": 28},
        {"store": "Coop", "product": "Köttfärs", "original_price": 89, "discount_price": 69, "discount_percent": 22},
        {"store": "Willys", "product": "Tomatpuré", "original_price": 15, "discount_price": 10, "discount_percent": 33},
        {"store": "ICA Maxi", "product": "Ost", "original_price": 45, "discount_price": 35, "discount_percent": 22},
        {"store": "Coop", "product": "Gräddfil", "original_price": 22, "discount_price": 16, "discount_percent": 27},
    ],
    "Göteborg": [
        {"store": "Willys", "product": "Tortillas", "original_price": 25, "discount_price": 20, "discount_percent": 20},
        {"store": "ICA", "product": "Köttfärs", "original_price": 89, "discount_price": 65, "discount_percent": 27},
        {"store": "Coop", "product": "Salsa", "original_price": 30, "discount_price": 22, "discount_percent": 27},
    ],
    "Malmö": [
        {"store": "Hemköp", "product": "Tortillas", "original_price": 25, "discount_price": 19, "discount_percent": 24},
        {"store": "Willys", "product": "Köttfärs", "original_price": 89, "discount_price": 70, "discount_percent": 21},
    ]
}


def get_discounts_by_location(location: str) -> List[Dict[str, Any]]:
    """
    Hämtar aktuella erbjudanden baserat på användarens plats.
    
    Args:
        location: Stad eller område där användaren vill handla
        
    Returns:
        Lista med erbjudanden i området
    """
    discounts = MOCK_DISCOUNTS.get(location, [])
    return discounts


def filter_products_by_preferences(
    discounts: List[Dict[str, Any]], 
    preferences: List[str]
) -> List[Dict[str, Any]]:
    """
    Filtrerar produkter baserat på användarens preferenser och matrecept.
    
    Args:
        discounts: Lista med tillgängliga erbjudanden
        preferences: Lista med önskade produkter/ingredienser
        
    Returns:
        Filtrerad lista med relevanta erbjudanden
    """
    if not preferences:
        return discounts
    
    filtered = []
    for discount in discounts:
        product_name = discount["product"].lower()
        for pref in preferences:
            if pref.lower() in product_name:
                filtered.append(discount)
                break
    
    return filtered


def optimize_shopping_plan(
    location: str,
    meal_type: str,
    preferences: List[str] = None
) -> Dict[str, Any]:
    """
    Skapar en optimerad inköpsplan baserat på plats, måltidstyp och preferenser.
    
    Args:
        location: Stad där användaren vill handla
        meal_type: Typ av måltid (t.ex. "tacos", "pasta", "sallad")
        preferences: Valfria preferenser eller restriktioner
        
    Returns:
        Optimerad inköpsplan med butiker, produkter och besparingar
    """
    # Hämta erbjudanden för platsen
    discounts = get_discounts_by_location(location)
    
    if not discounts:
        return {
            "success": False,
            "message": f"Inga erbjudanden hittades för {location}",
            "plan": []
        }
    
    # Filtrera baserat på måltidstyp
    meal_keywords = {
        "tacos": ["tortillas", "köttfärs", "ost", "gräddfil", "salsa", "tomatpuré"],
        "pasta": ["pasta", "köttfärs", "tomatpuré", "ost", "grädde"],
        "sallad": ["sallad", "tomat", "gurka", "ost", "dressing"]
    }
    
    keywords = meal_keywords.get(meal_type.lower(), [])
    if preferences:
        keywords.extend(preferences)
    
    filtered_discounts = filter_products_by_preferences(discounts, keywords)
    
    # Gruppera per butik och beräkna besparingar
    stores = {}
    total_savings = 0
    
    for discount in filtered_discounts:
        store = discount["store"]
        if store not in stores:
            stores[store] = {
                "products": [],
                "total_original": 0,
                "total_discount": 0,
                "savings": 0
            }
        
        stores[store]["products"].append(discount)
        stores[store]["total_original"] += discount["original_price"]
        stores[store]["total_discount"] += discount["discount_price"]
        stores[store]["savings"] += (discount["original_price"] - discount["discount_price"])
        total_savings += (discount["original_price"] - discount["discount_price"])
    
    # Hitta bästa butiken
    best_store = max(stores.items(), key=lambda x: x[1]["savings"]) if stores else None
    
    return {
        "success": True,
        "location": location,
        "meal_type": meal_type,
        "total_savings": total_savings,
        "best_store": best_store[0] if best_store else None,
        "stores": stores,
        "recommendation": f"Handla på {best_store[0]} och spara {best_store[1]['savings']} kr!" if best_store else "Inga erbjudanden hittades"
    }


# Root agent definition (för ADK)
def root_agent():
    """
    Huvudagent som optimerar matinköp utifrån erbjudanden, användarens plats och preferenser.
    
    Agenten kan:
    - Hitta bästa erbjudanden i din stad
    - Föreslå optimerade inköpsplaner för olika måltider
    - Beräkna potentiella besparingar
    - Rekommendera vilken butik du ska handla i
    """
    return {
        "name": "discount_optimizer",
        "description": "En hjälpsam agent som optimerar matinköp utifrån erbjudanden, användarens plats och preferenser",
        "tools": [
            get_discounts_by_location,
            filter_products_by_preferences,
            optimize_shopping_plan
        ]
    }


# Test-funktion
if __name__ == "__main__":
    # Testa agenten
    print("=== Test: Discount Optimizer Agent ===\n")
    
    result = optimize_shopping_plan(
        location="Stockholm",
        meal_type="tacos",
        preferences=[]
    )
    
    print(f"Plats: {result['location']}")
    print(f"Måltid: {result['meal_type']}")
    print(f"Total besparing: {result['total_savings']} kr")
    print(f"Rekommendation: {result['recommendation']}\n")
    
    if result['best_store']:
        best = result['stores'][result['best_store']]
        print(f"Produkter på {result['best_store']}:")
        for product in best['products']:
            print(f"  - {product['product']}: {product['discount_price']} kr (spara {product['original_price'] - product['discount_price']} kr)")
