"""
Demo script för Discount Optimizer Agent
Kör detta för att se agenten i action!
"""

from agent import optimize_shopping_plan, get_discounts_by_location


def demo_basic():
    """Grundläggande demo av agenten"""
    print("=" * 60)
    print("DISCOUNT OPTIMIZER AGENT - DEMO")
    print("=" * 60)
    print()
    
    # Scenario 1: Tacos i Stockholm
    print("📍 Scenario 1: Tacos i Stockholm")
    print("-" * 60)
    result = optimize_shopping_plan("Stockholm", "tacos")
    
    if result['success']:
        print(f"✅ {result['recommendation']}")
        print(f"💰 Total besparing: {result['total_savings']} kr")
        print()
        
        # Visa produkter från bästa butiken
        if result['best_store']:
            best = result['stores'][result['best_store']]
            print(f"🛒 Inköpslista från {result['best_store']}:")
            for product in best['products']:
                savings = product['original_price'] - product['discount_price']
                print(f"   • {product['product']}: {product['discount_price']} kr (spara {savings} kr, -{product['discount_percent']}%)")
            print()
    
    # Scenario 2: Jämför olika städer
    print("📍 Scenario 2: Jämför erbjudanden i olika städer")
    print("-" * 60)
    
    cities = ["Stockholm", "Göteborg", "Malmö"]
    for city in cities:
        discounts = get_discounts_by_location(city)
        total_discount = sum(d['original_price'] - d['discount_price'] for d in discounts)
        print(f"{city}: {len(discounts)} erbjudanden, upp till {total_discount} kr i besparingar")
    
    print()
    print("=" * 60)
    print("Demo klar! Testa själv med: python agent.py")
    print("=" * 60)


if __name__ == "__main__":
    demo_basic()
