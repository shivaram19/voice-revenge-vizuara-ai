"""
Hospitality-specific tools for the voice receptionist.

Each tool is self-contained: schema definition, execution, and voice-friendly
formatting. Tools operate on in-memory mock data so the domain can be
exercised without external dependencies.

Ref: OpenAI Function Calling API [^13]; ADR-009.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.receptionist.tools.base import Tool, ToolResult
from src.domains.hospitality.seed import (
    HOSPITALITY_FAQ,
    HOSPITALITY_ROOMS,
    HOSPITALITY_MENU,
    HOSPITALITY_RECOMMENDATIONS,
    HOSPITALITY_BOOKINGS,
    RoomRecord,
    BookingRecord,
    MenuItem,
    Recommendation,
    FAQRecord,
)


# ---------------------------------------------------------------------------
# Check Room Availability Tool
# ---------------------------------------------------------------------------

class CheckRoomAvailabilityTool(Tool):
    """
    Check available rooms by date range and optional room type.

    Searches the in-memory room inventory and booking ledger to determine
    availability. Production: integrate with property management system (PMS)
    API such as Opera, Mews, or Cloudbeds.
    """

    def __init__(
        self,
        rooms: Optional[List[RoomRecord]] = None,
        bookings: Optional[List[BookingRecord]] = None,
    ):
        self._rooms = rooms or list(HOSPITALITY_ROOMS)
        self._bookings = bookings or list(HOSPITALITY_BOOKINGS)

    @property
    def name(self) -> str:
        return "check_room_availability"

    @property
    def description(self) -> str:
        return (
            "Check hotel room availability for a given date range. "
            "Optionally filter by room type: standard, deluxe, or suite. "
            "Returns available room types, nightly rates, and occupancy limits."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "check_in_date": {
                    "type": "string",
                    "description": "Check-in date in YYYY-MM-DD format.",
                },
                "check_out_date": {
                    "type": "string",
                    "description": "Check-out date in YYYY-MM-DD format.",
                },
                "room_type": {
                    "type": "string",
                    "description": "Optional room type filter: standard, deluxe, or suite.",
                },
            },
            "required": ["check_in_date", "check_out_date"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        check_in = kwargs.get("check_in_date", "").strip()
        check_out = kwargs.get("check_out_date", "").strip()
        room_type_filter = kwargs.get("room_type", "").strip().lower()

        if not check_in or not check_out:
            return ToolResult(
                success=False,
                message="Please provide both a check-in and check-out date.",
                error="missing_dates",
            )

        try:
            check_in_dt = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_dt = datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            return ToolResult(
                success=False,
                message="I didn't understand the dates. Please say them clearly, for example, May tenth through May fifteenth.",
                error="invalid_date_format",
            )

        if check_out_dt <= check_in_dt:
            return ToolResult(
                success=False,
                message="Check-out date must be after check-in date.",
                error="invalid_date_range",
            )

        available: List[RoomRecord] = []
        for room in self._rooms:
            if room_type_filter and room.room_type.lower() != room_type_filter:
                continue
            booked_count = self._count_bookings(room.room_type, check_in_dt, check_out_dt)
            if booked_count < room.total_count:
                available.append(room)

        if not available:
            if room_type_filter:
                return ToolResult(
                    success=False,
                    message=f"I'm sorry, we have no {room_type_filter} rooms available for those dates. Would you like to check another room type?",
                    error="no_availability",
                )
            return ToolResult(
                success=False,
                message="I'm sorry, we have no rooms available for those dates. Would you like to check alternative dates?",
                error="no_availability",
            )

        lines: List[str] = []
        for r in available:
            free_count = r.total_count - self._count_bookings(r.room_type, check_in_dt, check_out_dt)
            lines.append(
                f"{r.room_type.capitalize()}: {free_count} room{'s' if free_count > 1 else ''} available "
                f"at ${r.nightly_rate_usd:,.0f} per night. {r.description} Max occupancy: {r.max_occupancy}."
            )
        message = " ".join(lines)
        return ToolResult(
            success=True,
            message=message,
            data={
                "available_rooms": [
                    {
                        "room_type": r.room_type,
                        "available_count": r.total_count - self._count_bookings(r.room_type, check_in_dt, check_out_dt),
                        "nightly_rate_usd": r.nightly_rate_usd,
                        "max_occupancy": r.max_occupancy,
                    }
                    for r in available
                ],
            },
        )

    def _count_bookings(self, room_type: str, check_in, check_out) -> int:
        """Count overlapping confirmed bookings for a room type."""
        count = 0
        for b in self._bookings:
            if b.room_type.lower() != room_type.lower():
                continue
            if b.status in ("cancelled",):
                continue
            b_in = datetime.strptime(b.check_in_date, "%Y-%m-%d").date()
            b_out = datetime.strptime(b.check_out_date, "%Y-%m-%d").date()
            # Overlap check: [check_in, check_out) overlaps with [b_in, b_out)
            if b_in < check_out and b_out > check_in:
                count += 1
        return count


# ---------------------------------------------------------------------------
# Book Reservation Tool
# ---------------------------------------------------------------------------

class BookReservationTool(Tool):
    """
    Book a room reservation for a guest.

    Validates dates, checks availability against the in-memory booking ledger,
    and creates a confirmed reservation. Production: integrate with PMS or
    central reservation system (CRS).

    Ref: idempotency keys prevent double-booking under retry [^44].
    """

    def __init__(
        self,
        rooms: Optional[List[RoomRecord]] = None,
        bookings: Optional[List[BookingRecord]] = None,
    ):
        self._rooms = rooms or list(HOSPITALITY_ROOMS)
        self._bookings = bookings or list(HOSPITALITY_BOOKINGS)

    @property
    def name(self) -> str:
        return "book_reservation"

    @property
    def description(self) -> str:
        return (
            "Book a room reservation for a guest. Requires guest name, check-in date, "
            "check-out date, and room type. Confirm availability before saving."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "guest_name": {
                    "type": "string",
                    "description": "Full name of the guest making the reservation.",
                },
                "check_in_date": {
                    "type": "string",
                    "description": "Check-in date in YYYY-MM-DD format.",
                },
                "check_out_date": {
                    "type": "string",
                    "description": "Check-out date in YYYY-MM-DD format.",
                },
                "room_type": {
                    "type": "string",
                    "description": "Desired room type: standard, deluxe, or suite.",
                },
            },
            "required": ["guest_name", "check_in_date", "check_out_date", "room_type"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        guest_name = kwargs.get("guest_name", "").strip()
        check_in = kwargs.get("check_in_date", "").strip()
        check_out = kwargs.get("check_out_date", "").strip()
        room_type = kwargs.get("room_type", "").strip().lower()

        if not guest_name:
            return ToolResult(
                success=False,
                message="I need the guest's name to make a reservation.",
                error="missing_guest_name",
            )

        try:
            check_in_dt = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_dt = datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            return ToolResult(
                success=False,
                message="I didn't understand the dates. Please say them clearly, for example, June tenth through June fifteenth.",
                error="invalid_date_format",
            )

        if check_out_dt <= check_in_dt:
            return ToolResult(
                success=False,
                message="Check-out date must be after check-in date.",
                error="invalid_date_range",
            )

        room = next((r for r in self._rooms if r.room_type.lower() == room_type), None)
        if not room:
            return ToolResult(
                success=False,
                message=f"We do not offer '{room_type}' rooms. Our room types are standard, deluxe, and suite.",
                error="invalid_room_type",
            )

        # Check availability
        booked_count = self._count_bookings(room_type, check_in_dt, check_out_dt)
        if booked_count >= room.total_count:
            return ToolResult(
                success=False,
                message=f"I'm sorry, all {room_type} rooms are booked for those dates. Would you like to check another room type or date?",
                error="room_unavailable",
            )

        booking = BookingRecord(
            booking_id=f"BK-{uuid.uuid4().hex[:8].upper()}",
            guest_name=guest_name,
            room_type=room_type,
            check_in_date=check_in,
            check_out_date=check_out,
            status="confirmed",
        )
        self._bookings.append(booking)

        nights = (check_out_dt - check_in_dt).days
        total = nights * room.nightly_rate_usd
        message = (
            f"Your reservation is confirmed, {guest_name}. "
            f"{room_type.capitalize()} room from {check_in_dt.strftime('%A, %B %d')} to {check_out_dt.strftime('%A, %B %d')}. "
            f"That's {nights} night{'s' if nights > 1 else ''} at ${room.nightly_rate_usd:,.0f} per night, "
            f"total estimated stay cost ${total:,.0f} plus tax. Your confirmation number is {booking.booking_id}."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "booking_id": booking.booking_id,
                "guest_name": booking.guest_name,
                "room_type": booking.room_type,
                "check_in_date": booking.check_in_date,
                "check_out_date": booking.check_out_date,
                "nights": nights,
                "total_estimate_usd": total,
            },
        )

    def _count_bookings(self, room_type: str, check_in, check_out) -> int:
        """Count overlapping confirmed bookings for a room type."""
        count = 0
        for b in self._bookings:
            if b.room_type.lower() != room_type.lower():
                continue
            if b.status in ("cancelled",):
                continue
            b_in = datetime.strptime(b.check_in_date, "%Y-%m-%d").date()
            b_out = datetime.strptime(b.check_out_date, "%Y-%m-%d").date()
            if b_in < check_out and b_out > check_in:
                count += 1
        return count


# ---------------------------------------------------------------------------
# Room Service Tool
# ---------------------------------------------------------------------------

class RoomServiceTool(Tool):
    """
    Order room service items by name and room number.

    Searches the in-memory menu. Production: integrate with hotel POS
    or room-service management system.
    """

    def __init__(self, menu: Optional[List[MenuItem]] = None):
        self._menu = menu or list(HOSPITALITY_MENU)

    @property
    def name(self) -> str:
        return "order_room_service"

    @property
    def description(self) -> str:
        return (
            "Place a room service order. Requires item name and room number. "
            "Optionally specify quantity. Returns confirmation and estimated delivery time."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "Name of the menu item to order, e.g., Classic Burger or Breakfast Combo.",
                },
                "room_number": {
                    "type": "string",
                    "description": "Guest room number for delivery.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of servings. Defaults to 1.",
                    "default": 1,
                },
            },
            "required": ["item_name", "room_number"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        item_name = kwargs.get("item_name", "").strip()
        room_number = kwargs.get("room_number", "").strip()
        quantity = kwargs.get("quantity", 1)

        if not item_name:
            return ToolResult(
                success=False,
                message="Please tell me which menu item you would like to order.",
                error="missing_item_name",
            )
        if not room_number:
            return ToolResult(
                success=False,
                message="I need your room number to deliver the order.",
                error="missing_room_number",
            )

        match = next(
            (m for m in self._menu if item_name.lower() in m.item_name.lower()),
            None,
        )

        if not match:
            available = ", ".join(m.item_name for m in self._menu[:5])
            return ToolResult(
                success=False,
                message=f"I couldn't find '{item_name}' on the menu. Popular items include: {available}. Would you like the full menu?",
                error="item_not_found",
            )

        qty = max(1, int(quantity))
        total = match.price_usd * qty
        message = (
            f"Order confirmed. {qty} {match.item_name}{'s' if qty > 1 else ''} to room {room_number}. "
            f"Total is ${total:,.0f}. Estimated delivery time is thirty to forty-five minutes."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "item": match.item_name,
                "room_number": room_number,
                "quantity": qty,
                "total_usd": total,
                "category": match.category,
            },
        )


# ---------------------------------------------------------------------------
# Concierge Tool
# ---------------------------------------------------------------------------

class ConciergeTool(Tool):
    """
    Provide local recommendations for restaurants, attractions, and transport.

    Searches the in-memory recommendation list. Production: integrate with
    Google Places, TripAdvisor, or local tourism board API.
    """

    def __init__(self, recommendations: Optional[List[Recommendation]] = None):
        self._recommendations = recommendations or list(HOSPITALITY_RECOMMENDATIONS)

    @property
    def name(self) -> str:
        return "get_recommendations"

    @property
    def description(self) -> str:
        return (
            "Get local recommendations for restaurants, attractions, or transport. "
            "Optionally filter by category or search by keyword."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter: restaurant, attraction, or transport.",
                },
                "query": {
                    "type": "string",
                    "description": "Optional keyword search, e.g., sushi, park, or taxi.",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs) -> ToolResult:
        category_filter = kwargs.get("category", "").strip().lower()
        query = kwargs.get("query", "").strip().lower()

        matches: List[Recommendation] = []
        for rec in self._recommendations:
            if category_filter and rec.category.lower() != category_filter:
                continue
            if query and query not in rec.name.lower() and query not in rec.description.lower():
                continue
            matches.append(rec)

        if not matches:
            return ToolResult(
                success=False,
                message="I couldn't find a recommendation matching that request. I can suggest restaurants, attractions, or transport options nearby.",
                error="no_recommendations",
            )

        lines: List[str] = []
        for rec in matches[:3]:
            lines.append(
                f"{rec.name} — {rec.category}. {rec.description} "
                f"About {rec.distance_miles} mile{'s' if rec.distance_miles != 1 else ''} away. Cost: {rec.approximate_cost_usd}."
            )
        message = " ".join(lines)
        return ToolResult(
            success=True,
            message=message,
            data={
                "recommendations": [
                    {
                        "name": r.name,
                        "category": r.category,
                        "description": r.description,
                        "distance_miles": r.distance_miles,
                        "cost": r.approximate_cost_usd,
                    }
                    for r in matches
                ],
            },
        )


# ---------------------------------------------------------------------------
# FAQ Search Tool
# ---------------------------------------------------------------------------

class FAQTool(Tool):
    """
    Search the hotel FAQ knowledge base.

    Uses simple keyword matching. Production: upgrade to FAISS semantic
    search per ADR-003 [^14][^37].
    """

    def __init__(self, faqs: Optional[List[FAQRecord]] = None):
        self._faqs = faqs or list(HOSPITALITY_FAQ)

    @property
    def name(self) -> str:
        return "search_faq"

    @property
    def description(self) -> str:
        return "Search the hotel knowledge base for answers about parking, Wi-Fi, pets, cancellation, amenities, and policies."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The caller's question or keywords to search for.",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").lower()
        if not query:
            return ToolResult(
                success=False,
                message="What would you like to know?",
                error="missing_query",
            )

        query_words = set(re.findall(r"\b\w+\b", query))
        scored: List[tuple] = []

        for faq in self._faqs:
            text = f"{faq.question} {faq.answer}".lower()
            text_words = set(re.findall(r"\b\w+\b", text))
            score = len(query_words & text_words)
            # Category match is a strong signal [^16]
            if query in faq.category.lower():
                score += 5
            if score > 0:
                scored.append((score, faq))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:1]

        if not top:
            return ToolResult(
                success=False,
                message="I don't have that information right now. I can connect you with the front desk.",
                error="no_faq_match",
            )

        answer = top[0][1].answer
        # Truncate to two sentences for voice brevity [^16]
        sentences = re.split(r"[.!?]+\s+", answer)
        voice_answer = ". ".join(sentences[:2]).strip()
        if voice_answer and not voice_answer.endswith("."):
            voice_answer += "."

        return ToolResult(
            success=True,
            message=voice_answer,
            data={"question": top[0][1].question, "answer": answer},
        )


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^14]: Qiu, J., et al. (2026). VoiceAgentRAG. arXiv:2603.02206.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^37]: Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
# [^44]: Stripe. (2023). Idempotency Keys API Design. stripe.com/docs/api/idempotent_requests.
