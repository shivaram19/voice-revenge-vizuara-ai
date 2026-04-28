"""
Hospitality domain seed data and database initializer.

Provides sample FAQ entries, room inventory, room-service menu, and local
recommendations for demonstration and integration testing. All data is
in-memory; production deployments swap this for a real property management
system (PMS) or channel manager API.

Ref: SigArch 2026 [^16]; OpenAI Function Calling API [^13].
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class RoomRecord:
    """A single room type in the hotel inventory."""
    room_type: str          # e.g., "standard", "deluxe", "suite"
    total_count: int        # Total rooms of this type
    nightly_rate_usd: float
    description: str
    max_occupancy: int
    amenities: List[str]


@dataclass
class BookingRecord:
    """A confirmed room reservation."""
    booking_id: str
    guest_name: str
    room_type: str
    check_in_date: str      # YYYY-MM-DD
    check_out_date: str     # YYYY-MM-DD
    status: str             # "confirmed", "cancelled", "checked-in"


@dataclass
class MenuItem:
    """A single item on the room-service menu."""
    item_name: str
    category: str           # e.g., "main", "breakfast", "dessert", "beverage"
    price_usd: float
    description: str
    available_hours: str    # e.g., "06:00-23:00"


@dataclass
class Recommendation:
    """A local attraction, restaurant, or transport option."""
    name: str
    category: str           # "restaurant", "attraction", "transport"
    description: str
    distance_miles: float
    approximate_cost_usd: str


@dataclass
class FAQRecord:
    """A single hotel FAQ entry."""
    question: str
    answer: str
    category: str           # e.g., "parking", "wifi", "pets", "policy"


# ---------------------------------------------------------------------------
# Sample FAQ entries
# ---------------------------------------------------------------------------

HOSPITALITY_FAQ: List[FAQRecord] = [
    FAQRecord(
        question="Is parking available at the hotel?",
        answer=(
            "Yes. We offer complimentary valet parking for all registered guests. "
            "Self-parking is available in the adjacent garage for fifteen dollars per night. "
            "Oversized vehicles may incur an additional fee."
        ),
        category="parking",
    ),
    FAQRecord(
        question="Is Wi-Fi included in the room rate?",
        answer=(
            "High-speed Wi-Fi is complimentary throughout the hotel for all guests. "
            "Select the 'GrandVoice-Guest' network and authenticate with your room number and last name. "
            "Premium bandwidth for video conferencing is available upon request."
        ),
        category="wifi",
    ),
    FAQRecord(
        question="Do you allow pets?",
        answer=(
            "We are a pet-friendly hotel. Dogs and cats up to fifty pounds are welcome. "
            "A one-time cleaning fee of seventy-five dollars applies per stay. "
            "Please notify the front desk at check-in if you are travelling with a pet."
        ),
        category="pets",
    ),
    FAQRecord(
        question="What is the cancellation policy?",
        answer=(
            "Reservations may be cancelled without penalty up to forty-eight hours before the scheduled check-in time. "
            "Cancellations within forty-eight hours are subject to a charge equal to one night's room rate plus tax. "
            "Non-refundable rates cannot be modified or cancelled."
        ),
        category="policy",
    ),
    FAQRecord(
        question="What amenities are included with the room?",
        answer=(
            "All rooms include a smart TV, mini-bar, in-room safe, coffee maker, iron and ironing board, "
            "and luxury bath amenities. Deluxe rooms and suites also feature a balcony and complimentary bottled water."
        ),
        category="amenities",
    ),
    FAQRecord(
        question="What time is breakfast served?",
        answer=(
            "Breakfast is served daily from six thirty AM to ten thirty AM in the Grand Terrace restaurant. "
            "Room service breakfast is available twenty-four hours with a limited overnight menu."
        ),
        category="dining",
    ),
    FAQRecord(
        question="Is there a fitness centre or pool?",
        answer=(
            "Our fitness centre is open twenty-four hours on the third floor and features cardio machines, "
            "free weights, and yoga equipment. The heated outdoor pool is open from seven AM to ten PM daily."
        ),
        category="amenities",
    ),
    FAQRecord(
        question="Do you offer airport shuttle service?",
        answer=(
            "Yes. Our complimentary airport shuttle runs every thirty minutes from five AM to midnight. "
            "Please reserve your seat at least two hours in advance through the front desk or mobile app."
        ),
        category="transport",
    ),
    FAQRecord(
        question="Can I request a late check-out?",
        answer=(
            "Late check-out is available upon request and subject to availability. "
            "Checkout by one PM is complimentary; checkout by three PM incurs a half-day charge. "
            "Please contact the front desk before ten AM on your departure day to arrange."
        ),
        category="policy",
    ),
]


# ---------------------------------------------------------------------------
# Sample room inventory
# ---------------------------------------------------------------------------

HOSPITALITY_ROOMS: List[RoomRecord] = [
    RoomRecord(
        room_type="standard",
        total_count=40,
        nightly_rate_usd=149.0,
        description="Comfortable queen or king room with city view, work desk, and en-suite bath.",
        max_occupancy=2,
        amenities=["Wi-Fi", "Smart TV", "Coffee maker", "Mini-bar"],
    ),
    RoomRecord(
        room_type="deluxe",
        total_count=20,
        nightly_rate_usd=219.0,
        description="Spacious room with balcony, premium linens, and separate seating area.",
        max_occupancy=3,
        amenities=["Wi-Fi", "Smart TV", "Coffee maker", "Mini-bar", "Balcony", "Bathrobe"],
    ),
    RoomRecord(
        room_type="suite",
        total_count=8,
        nightly_rate_usd=389.0,
        description="One-bedroom suite with living room, kitchenette, and panoramic views.",
        max_occupancy=4,
        amenities=["Wi-Fi", "Smart TV", "Kitchenette", "Mini-bar", "Balcony", "Bathrobe", "Nespresso machine"],
    ),
]


# ---------------------------------------------------------------------------
# Sample room-service menu
# ---------------------------------------------------------------------------

HOSPITALITY_MENU: List[MenuItem] = [
    MenuItem(
        item_name="Classic Burger",
        category="main",
        price_usd=18.0,
        description="Beef patty with cheddar, lettuce, tomato, and house sauce on a brioche bun. Served with fries.",
        available_hours="11:00-23:00",
    ),
    MenuItem(
        item_name="Truffle Pasta",
        category="main",
        price_usd=24.0,
        description="Fettuccine in a creamy truffle parmesan sauce with wild mushrooms.",
        available_hours="17:00-23:00",
    ),
    MenuItem(
        item_name="Caesar Salad",
        category="main",
        price_usd=14.0,
        description="Romaine lettuce, parmesan crisps, croutons, and classic Caesar dressing with grilled chicken.",
        available_hours="11:00-23:00",
    ),
    MenuItem(
        item_name="Breakfast Combo",
        category="breakfast",
        price_usd=16.0,
        description="Two eggs any style, bacon or sausage, hash browns, and toast. Served with orange juice.",
        available_hours="06:00-11:00",
    ),
    MenuItem(
        item_name="Pancake Stack",
        category="breakfast",
        price_usd=13.0,
        description="Three fluffy pancakes with maple syrup, butter, and fresh berries.",
        available_hours="06:00-11:00",
    ),
    MenuItem(
        item_name="Grilled Salmon",
        category="main",
        price_usd=28.0,
        description="Atlantic salmon fillet with lemon herb butter, asparagus, and wild rice.",
        available_hours="17:00-23:00",
    ),
    MenuItem(
        item_name="Margherita Pizza",
        category="main",
        price_usd=17.0,
        description="Wood-fired pizza with San Marzano tomato sauce, fresh mozzarella, and basil.",
        available_hours="11:00-23:00",
    ),
    MenuItem(
        item_name="Chocolate Lava Cake",
        category="dessert",
        price_usd=10.0,
        description="Warm chocolate cake with a molten centre, served with vanilla bean ice cream.",
        available_hours="11:00-23:00",
    ),
    MenuItem(
        item_name="Fresh Smoothie",
        category="beverage",
        price_usd=8.0,
        description="Blended seasonal fruits with Greek yoghurt and honey.",
        available_hours="06:00-23:00",
    ),
]


# ---------------------------------------------------------------------------
# Sample local recommendations
# ---------------------------------------------------------------------------

HOSPITALITY_RECOMMENDATIONS: List[Recommendation] = [
    Recommendation(
        name="The Sapphire Grill",
        category="restaurant",
        description="Upscale steakhouse with dry-aged cuts and an extensive wine cellar. Reservations recommended.",
        distance_miles=0.3,
        approximate_cost_usd="$$$",
    ),
    Recommendation(
        name="Bella Notte",
        category="restaurant",
        description="Authentic Italian trattoria known for handmade pasta and wood-fired Neapolitan pizza.",
        distance_miles=0.5,
        approximate_cost_usd="$$",
    ),
    Recommendation(
        name="Harbourview Park",
        category="attraction",
        description="Waterfront park with walking trails, a lighthouse, and sunset viewing decks. Free entry.",
        distance_miles=1.2,
        approximate_cost_usd="Free",
    ),
    Recommendation(
        name="City Art Museum",
        category="attraction",
        description="Contemporary and classical art collections with rotating exhibits. Open Tuesday through Sunday.",
        distance_miles=0.8,
        approximate_cost_usd="$15",
    ),
    Recommendation(
        name="Metro Light Rail",
        category="transport",
        description="Efficient light-rail service connecting downtown, the airport, and major shopping districts.",
        distance_miles=0.2,
        approximate_cost_usd="$2.50",
    ),
    Recommendation(
        name="Coastal Bike Trail",
        category="attraction",
        description="Scenic ten-mile cycling and jogging path along the shoreline with bike rental stations.",
        distance_miles=0.6,
        approximate_cost_usd="$10/hour rental",
    ),
    Recommendation(
        name="Seaside Sushi Bar",
        category="restaurant",
        description="Omakase-style sushi with locally sourced seafood. Intimate twelve-seat counter.",
        distance_miles=0.4,
        approximate_cost_usd="$$$$",
    ),
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

HOSPITALITY_BOOKINGS: List[BookingRecord] = [
    BookingRecord(
        booking_id="BK-2026-001",
        guest_name="Alice Johnson",
        room_type="deluxe",
        check_in_date="2026-05-01",
        check_out_date="2026-05-05",
        status="confirmed",
    ),
    BookingRecord(
        booking_id="BK-2026-002",
        guest_name="Bob Smith",
        room_type="standard",
        check_in_date="2026-05-03",
        check_out_date="2026-05-04",
        status="confirmed",
    ),
    BookingRecord(
        booking_id="BK-2026-003",
        guest_name="Carol White",
        room_type="suite",
        check_in_date="2026-04-30",
        check_out_date="2026-05-02",
        status="confirmed",
    ),
]


def seed_hospitality_db() -> Dict[str, Any]:
    """
    Initialise and return the in-memory hospitality database.

    Returns a dictionary containing room inventory, booking ledger,
    room-service menu, local recommendations, and FAQ entries. This
    structure is consumed by the hospitality-domain tools at receptionist
    start-up.

    Returns:
        A dict with keys: ``rooms``, ``bookings``, ``menu``, ``recommendations``, ``faqs``.
    """
    return {
        "rooms": list(HOSPITALITY_ROOMS),
        "bookings": list(HOSPITALITY_BOOKINGS),
        "menu": list(HOSPITALITY_MENU),
        "recommendations": list(HOSPITALITY_RECOMMENDATIONS),
        "faqs": list(HOSPITALITY_FAQ),
    }


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
