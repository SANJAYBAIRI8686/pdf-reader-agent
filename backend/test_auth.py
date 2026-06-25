import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add current path to python search path
sys.path.append(str(Path(__file__).resolve().parent))

from app.main import app
from app.database.session import SessionLocal
from app.models.user import User

client = TestClient(app)

def test_authentication_workflow():
    print("\n=== STARTING AUTHENTICATION SUITE TESTS ===")
    
    test_email = "junior_dev_tester@example.com"
    test_password = "SecurePassword123!"
    test_name = "Junior Developer"
    
    # Pre-test cleanup: ensure database is clean of this user
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == test_email).first()
        if existing_user:
            print("Cleaning up old test user before starting...")
            db.delete(existing_user)
            db.commit()
    finally:
        db.close()

    # 1. Test registration
    print("Testing registration (POST /api/v1/auth/register)...")
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "password": test_password,
            "full_name": test_name
        }
    )
    assert reg_response.status_code == 201, f"Reg failed: {reg_response.text}"
    reg_json = reg_response.json()
    assert reg_json["email"] == test_email
    assert reg_json["full_name"] == test_name
    assert "id" in reg_json
    assert "hashed_password" not in reg_json  # Ensure password hash is filtered out!
    print("✓ Registration test passed.")

    # 2. Test duplicate email registration
    print("Testing duplicate email protection...")
    dup_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "password": "SomeOtherPassword1",
            "full_name": "Impostor Dev"
        }
    )
    assert dup_response.status_code == 400
    assert "already registered" in dup_response.json()["detail"]
    print("✓ Duplicate registration protection passed.")

    # 3. Test failed login
    print("Testing login with incorrect credentials...")
    failed_login = client.post(
        "/api/v1/auth/login",
        data={"username": test_email, "password": "WrongPassword!"}
    )
    assert failed_login.status_code == 401
    print("✓ Failed login test passed.")

    # 4. Test successful login
    print("Testing login with correct credentials (POST /api/v1/auth/login)...")
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": test_email, "password": test_password}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    login_json = login_response.json()
    assert "access_token" in login_json
    assert login_json["token_type"] == "bearer"
    token = login_json["access_token"]
    print("✓ Login credential validation passed.")

    # 5. Test protected routes authorization
    print("Testing protected route /me without credentials...")
    unauth_me = client.get("/api/v1/auth/me")
    assert unauth_me.status_code == 401
    print("✓ Unauthorized access rejection passed.")

    print("Testing protected route /me with invalid token...")
    invalid_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt-token"}
    )
    assert invalid_me.status_code == 401
    print("✓ Invalid token rejection passed.")

    print("Testing protected route /me with valid JWT token...")
    auth_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert auth_me.status_code == 200, f"Profile load failed: {auth_me.text}"
    me_json = auth_me.json()
    assert me_json["email"] == test_email
    assert me_json["full_name"] == test_name
    print("✓ Authorized profile retrieval passed.")

    # Post-test cleanup: delete user record
    print("Cleaning up test user data...")
    db = SessionLocal()
    try:
        user_record = db.query(User).filter(User.email == test_email).first()
        if user_record:
            db.delete(user_record)
            db.commit()
            print("✓ Database cleaned up.")
    except Exception as e:
        print(f"Cleanup error: {e}")
    finally:
        db.close()
        
    print("=== ALL AUTHENTICATION SUITE TESTS PASSED SUCCESSFULLY ===\n")

if __name__ == "__main__":
    test_authentication_workflow()
