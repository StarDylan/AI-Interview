"""
Tests for the ticket-based authentication system.
"""

import time
from interview_helper.security.tickets import TicketStore, Ticket


def test_ticket_generation():
    """Test basic ticket generation."""
    store = TicketStore(default_expiration_seconds=300)
    
    user_id = "test_user_123"
    client_ip = "192.168.1.100"
    
    ticket = store.generate_ticket(user_id, client_ip)
    
    assert ticket.user_id == user_id
    assert ticket.client_ip == client_ip
    assert not ticket.used
    assert ticket.is_valid()
    assert ticket.ticket_id is not None
    assert len(ticket.ticket_id) > 20  # Ensure it's a reasonably long token


def test_ticket_validation_success():
    """Test successful ticket validation."""
    store = TicketStore(default_expiration_seconds=300)
    
    user_id = "test_user_123"
    client_ip = "192.168.1.100"
    
    # Generate ticket
    ticket = store.generate_ticket(user_id, client_ip)
    ticket_id = ticket.ticket_id
    
    # Validate ticket
    validated_ticket = store.validate_ticket(ticket_id, client_ip)
    
    assert validated_ticket is not None
    assert validated_ticket.user_id == user_id
    assert validated_ticket.client_ip == client_ip
    assert validated_ticket.used  # Should be marked as used after validation


def test_ticket_single_use():
    """Test that tickets can only be used once."""
    store = TicketStore(default_expiration_seconds=300)
    
    user_id = "test_user_123"
    client_ip = "192.168.1.100"
    
    # Generate ticket
    ticket = store.generate_ticket(user_id, client_ip)
    ticket_id = ticket.ticket_id
    
    # First validation should succeed
    validated_ticket = store.validate_ticket(ticket_id, client_ip)
    assert validated_ticket is not None
    
    # Second validation should fail (ticket already used)
    validated_ticket_2 = store.validate_ticket(ticket_id, client_ip)
    assert validated_ticket_2 is None


def test_ticket_ip_validation():
    """Test that tickets validate client IP addresses."""
    store = TicketStore(default_expiration_seconds=300)
    
    user_id = "test_user_123"
    client_ip = "192.168.1.100"
    wrong_ip = "192.168.1.200"
    
    # Generate ticket
    ticket = store.generate_ticket(user_id, client_ip)
    ticket_id = ticket.ticket_id
    
    # Validation with correct IP should succeed
    validated_ticket = store.validate_ticket(ticket_id, client_ip)
    assert validated_ticket is not None
    
    # Generate another ticket for wrong IP test
    ticket2 = store.generate_ticket(user_id, client_ip)
    ticket_id2 = ticket2.ticket_id
    
    # Validation with wrong IP should fail
    validated_ticket_wrong = store.validate_ticket(ticket_id2, wrong_ip)
    assert validated_ticket_wrong is None


def test_ticket_expiration():
    """Test that tickets expire correctly."""
    # Create store with very short expiration (1 second)
    store = TicketStore(default_expiration_seconds=1)
    
    user_id = "test_user_123"
    client_ip = "192.168.1.100"
    
    # Generate ticket
    ticket = store.generate_ticket(user_id, client_ip)
    ticket_id = ticket.ticket_id
    
    # Should be valid immediately
    assert ticket.is_valid()
    
    # Wait for expiration
    time.sleep(2)
    
    # Should be expired
    assert ticket.is_expired()
    assert not ticket.is_valid()
    
    # Validation should fail
    validated_ticket = store.validate_ticket(ticket_id, client_ip)
    assert validated_ticket is None


def test_ticket_cleanup():
    """Test automatic cleanup of expired tickets."""
    store = TicketStore(default_expiration_seconds=1)
    
    user_id = "test_user_123"
    client_ip = "192.168.1.100"
    
    # Generate multiple tickets
    ticket1 = store.generate_ticket(user_id, client_ip)
    ticket2 = store.generate_ticket(user_id, client_ip)
    
    # Should have 2 active tickets
    assert store.get_active_tickets_count() == 2
    
    # Wait for expiration
    time.sleep(2)
    
    # Generate new ticket (should trigger cleanup)
    ticket3 = store.generate_ticket(user_id, client_ip)
    
    # Should only have 1 active ticket (the new one)
    assert store.get_active_tickets_count() == 1


def test_ticket_cleanup_method():
    """Test manual ticket cleanup."""
    store = TicketStore(default_expiration_seconds=300)
    
    user_id = "test_user_123"
    client_ip = "192.168.1.100"
    
    # Generate ticket
    ticket = store.generate_ticket(user_id, client_ip)
    ticket_id = ticket.ticket_id
    
    # Should be able to validate
    validated_ticket = store.validate_ticket(ticket_id, client_ip)
    assert validated_ticket is not None
    
    # Generate new ticket for cleanup test
    ticket2 = store.generate_ticket(user_id, client_ip)
    ticket_id2 = ticket2.ticket_id
    
    # Manually cleanup the ticket
    store.cleanup_ticket(ticket_id2)
    
    # Should not be able to validate after cleanup
    validated_ticket_2 = store.validate_ticket(ticket_id2, client_ip)
    assert validated_ticket_2 is None


if __name__ == "__main__":
    # Run basic tests
    test_ticket_generation()
    test_ticket_validation_success()
    test_ticket_single_use()
    test_ticket_ip_validation()
    test_ticket_expiration()
    test_ticket_cleanup()
    test_ticket_cleanup_method()
    print("All ticket tests passed!")