"""
OutputFormatter component for the Shopping Optimizer.
Formats shopping recommendations into human-readable output.
"""

from collections import defaultdict
from datetime import UTC, date, datetime

from .models import Purchase, ShoppingRecommendation


def get_today() -> date:
    """Get today's date in a timezone-aware manner."""
    return datetime.now(UTC).date()


class OutputFormatter:
    """Formats shopping recommendations into human-readable output."""

    def group_by_store_and_day(
        self, purchases: list[Purchase]
    ) -> dict[str, dict[date, list[Purchase]]]:
        """
        Organize purchases by store and then by day.

        Args:
            purchases: List of Purchase objects

        Returns:
            Dictionary with structure: {store_name: {date: [purchases]}}
        """
        grouped: dict[str, dict[date, list[Purchase]]] = defaultdict(lambda: defaultdict(list))

        for purchase in purchases:
            grouped[purchase.store_name][purchase.purchase_day].append(purchase)

        return dict(grouped)

    def generate_tips(self, purchases: list[Purchase]) -> list[str]:
        """
        Generate actionable tips for time-sensitive discounts and organic recommendations.
        Limits to top 3 most impactful tips.

        Args:
            purchases: List of Purchase objects

        Returns:
            List of tip strings (max 3)
        """
        tips = []

        # Find time-sensitive discounts (expiring within 3 days)
        today = get_today()
        time_sensitive = []

        for purchase in purchases:
            days_until_expiry = (purchase.purchase_day - today).days
            if 0 <= days_until_expiry <= 3:
                time_sensitive.append((purchase, days_until_expiry))

        # Sort by urgency (soonest expiry first)
        time_sensitive.sort(key=lambda x: x[1])

        # Add time-sensitive tips
        for purchase, days in time_sensitive[:2]:  # Max 2 time-sensitive tips
            if days == 0:
                tips.append(
                    f"Buy {purchase.product_name} at {purchase.store_name} today - discount expires soon!"
                )
            elif days == 1:
                tips.append(
                    f"Buy {purchase.product_name} at {purchase.store_name} tomorrow - discount expires in 1 day"
                )
            else:
                tips.append(
                    f"Buy {purchase.product_name} at {purchase.store_name} within {days} days for best savings"
                )

        # Find organic products with good value
        organic_products = [
            p
            for p in purchases
            if "økologisk" in p.product_name.lower() or "organic" in p.product_name.lower()
        ]

        if organic_products and len(tips) < 3:
            # Find the organic product with highest savings
            best_organic = max(organic_products, key=lambda p: p.savings)
            if best_organic.savings > 10:  # Only recommend if savings are significant
                tips.append(
                    f"Great organic deal: {best_organic.product_name} saves you {best_organic.savings:.0f} kr!"
                )

        # Add store consolidation tip if shopping at multiple stores
        if len(tips) < 3:
            stores = {p.store_name for p in purchases}
            if len(stores) > 2:
                # Find which store has the most items
                store_counts = defaultdict(int)
                for p in purchases:
                    store_counts[p.store_name] += 1
                main_store = max(store_counts.items(), key=lambda x: x[1])
                tips.append(
                    f"Consider shopping mainly at {main_store[0]} - they have {main_store[1]} of your items"
                )

        return tips[:3]  # Limit to top 3

    def generate_motivation(self, total_savings: float, time_savings: float) -> str:
        """
        Generate a conversational motivational message explaining the optimization results.

        Args:
            total_savings: Total monetary savings in currency
            time_savings: Estimated time savings in hours

        Returns:
            Motivational message string
        """
        if total_savings > 100:
            savings_msg = f"You're saving {total_savings:.0f} kr - that's fantastic!"
        elif total_savings > 50:
            savings_msg = f"You're saving {total_savings:.0f} kr - nice work!"
        else:
            savings_msg = f"You're saving {total_savings:.0f} kr on this shop."

        if time_savings > 0.5:
            time_msg = f" Plus, you'll save about {time_savings:.1f} hours by shopping smart."
        elif time_savings > 0:
            time_msg = f" And you'll save around {int(time_savings * 60)} minutes too."
        else:
            time_msg = " Your optimized route keeps shopping convenient."

        return f"{savings_msg}{time_msg} Happy shopping!"

    def format_recommendation(self, recommendation: ShoppingRecommendation) -> str:
        """
        Format the complete recommendation into human-readable output.

        Args:
            recommendation: ShoppingRecommendation object with all data

        Returns:
            Formatted string with shopping list, savings, and tips
        """
        output_lines = []

        # Header
        output_lines.append("=" * 60)
        output_lines.append("YOUR OPTIMIZED SHOPPING PLAN")
        output_lines.append("=" * 60)
        output_lines.append("")

        # Group purchases by store and day
        grouped = self.group_by_store_and_day(recommendation.purchases)

        # Shopping list section
        output_lines.append("SHOPPING LIST")
        output_lines.append("-" * 60)

        for store_name in sorted(grouped.keys()):
            output_lines.append(f"\n📍 {store_name}")

            days = grouped[store_name]
            for purchase_day in sorted(days.keys()):
                day_str = purchase_day.strftime("%A, %B %d")
                output_lines.append(f"  📅 {day_str}")

                for purchase in days[purchase_day]:
                    savings_str = (
                        f"(save {purchase.savings:.0f} kr)" if purchase.savings > 0 else ""
                    )
                    meal_str = (
                        f"for {purchase.meal_association}" if purchase.meal_association else ""
                    )
                    output_lines.append(
                        f"    • {purchase.product_name} - {purchase.price:.0f} kr {savings_str} {meal_str}".strip()
                    )

        output_lines.append("")

        # Savings summary section
        output_lines.append("=" * 60)
        output_lines.append("SAVINGS SUMMARY")
        output_lines.append("-" * 60)
        output_lines.append(f"💰 Total Savings: {recommendation.total_savings:.0f} kr")
        output_lines.append(f"⏱️  Time Savings: {recommendation.time_savings:.1f} hours")
        output_lines.append("")

        # Tips section
        if recommendation.tips:
            output_lines.append("=" * 60)
            output_lines.append("TIPS & RECOMMENDATIONS")
            output_lines.append("-" * 60)
            for i, tip in enumerate(recommendation.tips, 1):
                output_lines.append(f"{i}. {tip}")
            output_lines.append("")

        # Motivation message
        output_lines.append("=" * 60)
        output_lines.append(recommendation.motivation_message)
        output_lines.append("=" * 60)

        return "\n".join(output_lines)
