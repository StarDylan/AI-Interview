"""
Ticket-based authentication system for WebSocket connections.

This module implements a secure ticket system that replaces direct JWT token
validation for WebSocket connections. Tickets are single-use, time-limited
tokens that provide an additional layer of security.
"""

import secrets
import time
from typing import Dict, Optional
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class Ticket:
    """Represents an authentication ticket for WebSocket connections."""

    ticket_id: str
    user_id: str
    client_ip: str
    created_at: float
    expires_at: float
    used: bool = False

    def is_expired(self, current_time: float = time.time()) -> bool:
        """Check if the ticket has expired."""
        return current_time >= self.expires_at

    def is_valid(self, current_time: float = time.time()) -> bool:
        """Check if the ticket is valid (not used and not expired)."""
        return not self.used and not self.is_expired(current_time)


class TicketRequest(BaseModel):
    """Request model for ticket generation."""

    pass  # No additional fields needed, user info comes from JWT


class TicketResponse(BaseModel):
    """Response model for ticket generation."""

    ticket_id: str
    expires_in: int  # seconds until expiration


class TicketStore:
    """In-memory store for authentication tickets."""

    def __init__(self, default_expiration_seconds: int = 300):  # 5 minutes
        self._tickets: Dict[str, Ticket] = {}
        self._default_expiration = default_expiration_seconds

    def generate_ticket(
        self, user_id: str, client_ip: str, current_time: float = time.time()
    ) -> Ticket:
        """Generate a new authentication ticket."""
        ticket_id = secrets.token_urlsafe(32)
        expires_at = current_time + self._default_expiration

        ticket = Ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            client_ip=client_ip,
            created_at=current_time,
            expires_at=expires_at,
        )

        self._tickets[ticket_id] = ticket

        # Clean up expired tickets
        self._cleanup_expired(current_time)

        return ticket

    def validate_ticket(
        self, ticket_id: str, client_ip: str, current_time: float = time.time()
    ) -> Optional[Ticket]:
        """
        Validate a ticket and mark it as used if valid.

        Returns the ticket if valid, None otherwise.
        """
        ticket = self._tickets.get(ticket_id)

        if not ticket:
            return None

        # Check if ticket is valid
        if not ticket.is_valid():
            # Remove invalid ticket
            self._tickets.pop(ticket_id, None)
            return None

        # Check if client IP matches
        if ticket.client_ip != client_ip:
            return None

        # Mark ticket as used (single-use)
        ticket.used = True

        return ticket

    def cleanup_ticket(self, ticket_id: str) -> None:
        """Remove a specific ticket from the store."""
        self._tickets.pop(ticket_id, None)

    def _cleanup_expired(self, current_time: float) -> None:
        """Remove expired tickets from the store."""
        expired_tickets = [
            ticket_id
            for ticket_id, ticket in self._tickets.items()
            if ticket.expires_at < current_time
        ]

        for ticket_id in expired_tickets:
            self._tickets.pop(ticket_id, None)

    def get_active_tickets_count(self, current_time: float = time.time()) -> int:
        """Get the number of active (valid) tickets."""
        self._cleanup_expired(current_time)
        return len([t for t in self._tickets.values() if t.is_valid(current_time)])
