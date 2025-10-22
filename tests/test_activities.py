from fastapi.testclient import TestClient
import pytest
from src.app import app, activities

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    """Save and restore activities data before/after each test"""
    # Store initial state
    initial_activities = {name: {**details} for name, details in activities.items()}
    for name, details in initial_activities.items():
        details["participants"] = details["participants"].copy()
    
    yield
    
    # Restore initial state
    activities.clear()
    activities.update(initial_activities)

def test_get_activities_returns_dict():
    """Test GET /activities returns properly structured data"""
    res = client.get("/activities")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
    # Check specific activity structure
    chess_club = data["Chess Club"]
    assert isinstance(chess_club, dict)
    assert all(key in chess_club for key in ["description", "schedule", "max_participants", "participants"])
    assert isinstance(chess_club["participants"], list)


def test_signup_and_unregister_cycle():
    """Test complete signup -> duplicate check -> unregister flow"""
    activity_name = "Chess Club"
    email = "test.student@mergington.edu"

    # Sign up
    res = client.post(f"/activities/{activity_name}/signup?email={email}")
    assert res.status_code == 200
    body = res.json()
    assert "Signed up" in body.get("message", "")
    assert email in activities[activity_name]["participants"]

    # Attempt duplicate signup should return 400
    res_dup = client.post(f"/activities/{activity_name}/signup?email={email}")
    assert res_dup.status_code == 400
    assert "already signed up" in res_dup.json()["detail"].lower()

    # Unregister
    res_del = client.delete(f"/activities/{activity_name}/participants?email={email}")
    assert res_del.status_code == 200
    body = res_del.json()
    assert "Unregistered" in body.get("message", "")
    assert email not in activities[activity_name]["participants"]

def test_activity_not_found():
    """Test handling of non-existent activity"""
    fake_activity = "Non-Existent Club"
    email = "test@mergington.edu"
    
    # Try to signup
    res_signup = client.post(f"/activities/{fake_activity}/signup?email={email}")
    assert res_signup.status_code == 404
    assert "not found" in res_signup.json()["detail"].lower()
    
    # Try to unregister
    res_del = client.delete(f"/activities/{fake_activity}/participants?email={email}")
    assert res_del.status_code == 404
    assert "not found" in res_del.json()["detail"].lower()

def test_unregister_nonexistent_participant():
    """Test unregistering a participant that isn't signed up"""
    activity_name = "Programming Class"
    email = "no.one@mergington.edu"

    res = client.delete(f"/activities/{activity_name}/participants?email={email}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_activity_capacity():
    """Test activity reaches max capacity"""
    activity_name = "Chess Club"
    max_participants = activities[activity_name]["max_participants"]
    
    # Fill up to capacity
    emails = [f"student{i}@mergington.edu" for i in range(max_participants)]
    activities[activity_name]["participants"] = emails
    
    # Try to add one more
    res = client.post(f"/activities/{activity_name}/signup?email=extra@mergington.edu")
    assert res.status_code == 400
    assert "maximum capacity" in res.json()["detail"].lower()