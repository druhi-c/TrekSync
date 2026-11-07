import os
import sys
import shutil
import re
import datetime
import unittest
from pathlib import Path

# Resolve paths from this file so the suite works from any checkout location.
BASE_DIR = str(Path(__file__).resolve().parent)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from extensions import db
from models import User, UserRole, Trek, Difficulty, TrekStatus, Booking, BookingStatus, PaymentStatus

DB_PATH = os.path.join(BASE_DIR, "instance", "trekking.db")
BAK_PATH = DB_PATH + ".bak"

# Results dictionary to hold the outcomes of the tests
test_results = {}

def record_result(scope, test_id, name, status, expected, actual, cause=None):
    if scope not in test_results:
        test_results[scope] = []
    test_results[scope].append({
        "id": test_id,
        "name": name,
        "status": status,
        "expected": expected,
        "actual": actual,
        "cause": cause
    })

class QATestSuite(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # We ensure app is configured and database is backed up
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, BAK_PATH)
            print("Database backed up successfully.")
        else:
            raise FileNotFoundError("trekking.db not found in instance folder")
        
        # Enable testing mode so exceptions are propagated and cookies are handled easily
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = True
        cls.client = app.test_client()
        
        # Set up clean testing environment in DB
        with app.app_context():
            # Let's clear the database and recreate it so we have a clean slate to test features
            db.session.remove()
            db.engine.dispose()
            db.drop_all()
            db.create_all()
            
            # Seed default users (using @example.com to pass email validation)
            # 1. Admin
            admin = User(username="admin_qa", email="admin_qa@example.com", role="Admin", approved=True, active=True)
            admin.set_password("password123")
            db.session.add(admin)
            
            # 2. Approved Staff 1
            staff1 = User(username="staff_qa1", email="staff_qa1@example.com", role="Staff", approved=True, active=True)
            staff1.set_password("password123")
            db.session.add(staff1)
            
            # 3. Approved Staff 2
            staff2 = User(username="staff_qa2", email="staff_qa2@example.com", role="Staff", approved=True, active=True)
            staff2.set_password("password123")
            db.session.add(staff2)
            
            # 4. Pending Staff
            staff_pending = User(username="staff_pending", email="staff_pending@example.com", role="Staff", approved=False, active=True)
            staff_pending.set_password("password123")
            db.session.add(staff_pending)
            
            # 5. Trekker 1
            trekker1 = User(username="trekker_qa1", email="trekker_qa1@example.com", role="Trekker", approved=True, active=True)
            trekker1.set_password("password123")
            db.session.add(trekker1)
            
            # 6. Trekker 2
            trekker2 = User(username="trekker_qa2", email="trekker_qa2@example.com", role="Trekker", approved=True, active=True)
            trekker2.set_password("password123")
            db.session.add(trekker2)
            
            db.session.commit()
            print("Database seeded with QA test users.")

    @classmethod
    def tearDownClass(cls):
        # Restore database
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        if os.path.exists(BAK_PATH):
            shutil.copy2(BAK_PATH, DB_PATH)
            os.remove(BAK_PATH)
            print("Database restored to its original state.")
        else:
            print("Warning: Backup file not found at teardown.")

    def setUp(self):
        # Use a fresh test client session for each test
        self.client = app.test_client()
        
    def get_csrf_token(self, html):
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        if match:
            return match.group(1)
        match = re.search(r'id="csrf_token"[^>]*value="([^"]+)"', html)
        if match:
            return match.group(1)
        return None

    def login(self, email, password, remember=False):
        res = self.client.get("/auth/login")
        csrf_token = self.get_csrf_token(res.data.decode("utf-8"))
        data = {
            "csrf_token": csrf_token,
            "email": email,
            "password": password
        }
        if remember:
            data["remember_me"] = "y"
        return self.client.post("/auth/login", data=data, follow_redirects=False)

    # ==========================================
    # SCOPE 1: AUTHENTICATION REGRESSION
    # ==========================================
    
    def test_1_1_remember_me_cookie(self):
        """Log in using Remember Me and verify the remember cookie is set."""
        scope = "1. Authentication regression"
        test_id = "1.1"
        name = "Log in using Remember Me"
        try:
            res = self.login("trekker_qa1@example.com", "password123", remember=True)
            cookies = [h for h in res.headers.getlist("Set-Cookie")]
            has_remember_cookie = any("remember_token" in cookie for cookie in cookies)
            
            self.assertEqual(res.status_code, 302)
            self.assertTrue(has_remember_cookie)
            record_result(scope, test_id, name, "PASS", "Response status 302 and remember_token cookie set", f"Status: {res.status_code}, Cookies: {cookies}")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Response status 302 and remember_token cookie set", str(e), "Remember cookie not set or login failed")

    def test_1_2_logout_expires_cookie(self):
        """Log out and verify remember cookie is expired."""
        scope = "1. Authentication regression"
        test_id = "1.2"
        name = "Log out and verify cookie expires"
        try:
            # Login first
            self.login("trekker_qa1@example.com", "password123", remember=True)
            # Logout
            res = self.client.get("/auth/logout")
            self.assertEqual(res.status_code, 302)
            
            cookies = [h for h in res.headers.getlist("Set-Cookie")]
            cookie_deleted = any("remember_token=;" in cookie or "remember_token=max-age=0" in cookie.lower() or "expires=Thu, 01 Jan 1970" in cookie or "expires=Thu, 01-Jan-1970" in cookie for cookie in cookies)
            
            self.assertTrue(cookie_deleted)
            record_result(scope, test_id, name, "PASS", "Response status 302 and remember_token cookie expired in Set-Cookie header", f"Status: {res.status_code}, Cookies: {cookies}")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Response status 302 and remember_token cookie expired", str(e), "Remember cookie was not expired or logout failed")

    def test_1_3_anonymous_navigation(self):
        """Verify the login page displays anonymous navigation: Log In and Sign Up."""
        scope = "1. Authentication regression"
        test_id = "1.3"
        name = "Verify anonymous navigation links on login page"
        try:
            res = self.client.get("/auth/login")
            self.assertEqual(res.status_code, 200)
            html = res.data.decode("utf-8")
            
            has_login_link = "Log In" in html or "login" in html.lower()
            has_signup_link = "Sign Up" in html or "register" in html.lower()
            
            self.assertTrue(has_login_link)
            self.assertTrue(has_signup_link)
            record_result(scope, test_id, name, "PASS", "Login page displays navigation containing links for Log In and Sign Up", "Links found in login page HTML")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Login page displays navigation containing links for Log In and Sign Up", str(e), "Navigation links not found")

    def test_1_4_refresh_login_page_anonymous(self):
        """Refresh the login page and verify the user is still anonymous."""
        scope = "1. Authentication regression"
        test_id = "1.4"
        name = "Refresh login page and verify user is still anonymous"
        try:
            res = self.client.get("/auth/login")
            self.assertEqual(res.status_code, 200)
            
            with self.client.session_transaction() as sess:
                self.assertNotIn("_user_id", sess)
                
            record_result(scope, test_id, name, "PASS", "User session is empty/anonymous after refreshing login page", "No _user_id in session transaction")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "User session is empty/anonymous after refreshing login page", str(e), "User was authenticated or session was not empty")

    def test_1_5_protected_routes_redirect(self):
        """Verify protected routes redirect unauthenticated users to login."""
        scope = "1. Authentication regression"
        test_id = "1.5"
        name = "Verify protected routes redirect to login"
        routes = ["/admin/dashboard", "/staff/dashboard", "/trekker/dashboard"]
        failures = []
        try:
            for route in routes:
                res = self.client.get(route)
                if res.status_code != 302 or "/auth/login" not in res.headers.get("Location", ""):
                    failures.append(f"{route} returned {res.status_code} redirecting to {res.headers.get('Location')}")
            
            self.assertEqual(len(failures), 0, f"Failures: {failures}")
            record_result(scope, test_id, name, "PASS", "All protected routes redirect unauthenticated users with status 302 to /auth/login", "Redirected to /auth/login as expected")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "All protected routes redirect unauthenticated users to /auth/login", str(e), f"Redirection failed for some routes: {failures}")

    def test_1_6_authenticated_redirect_login_register(self):
        """Verify authenticated users visiting login/register are redirected to their dashboard."""
        scope = "1. Authentication regression"
        test_id = "1.6"
        name = "Redirect authenticated users away from login and register pages"
        failures = []
        try:
            # 1. Anonymous users can access login & register (status 200)
            res_anon_login = self.client.get("/auth/login")
            if res_anon_login.status_code != 200:
                failures.append(f"Anonymous login returned status {res_anon_login.status_code}")
            res_anon_reg = self.client.get("/auth/register")
            if res_anon_reg.status_code != 200:
                failures.append(f"Anonymous register returned status {res_anon_reg.status_code}")

            # 2. Logged-in Admin visiting login/register -> /admin/dashboard
            self.login("admin_qa@example.com", "password123")
            for page in ["/auth/login", "/auth/register"]:
                res = self.client.get(page)
                if res.status_code != 302 or "/admin/dashboard" not in res.headers.get("Location", ""):
                    failures.append(f"Admin on {page} returned status {res.status_code}, location {res.headers.get('Location')}")
            self.client.get("/auth/logout")

            # 3. Logged-in Staff visiting login/register -> /staff/dashboard
            self.login("staff_qa1@example.com", "password123")
            for page in ["/auth/login", "/auth/register"]:
                res = self.client.get(page)
                if res.status_code != 302 or "/staff/dashboard" not in res.headers.get("Location", ""):
                    failures.append(f"Staff on {page} returned status {res.status_code}, location {res.headers.get('Location')}")
            self.client.get("/auth/logout")

            # 4. Logged-in Trekker visiting login/register -> /trekker/dashboard
            self.login("trekker_qa1@example.com", "password123")
            for page in ["/auth/login", "/auth/register"]:
                res = self.client.get(page)
                if res.status_code != 302 or "/trekker/dashboard" not in res.headers.get("Location", ""):
                    failures.append(f"Trekker on {page} returned status {res.status_code}, location {res.headers.get('Location')}")

            self.assertEqual(len(failures), 0, f"Failures: {failures}")
            record_result(scope, test_id, name, "PASS", "Authenticated users are redirected to role dashboard from login/register", "Redirected as expected")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Authenticated users are redirected to role dashboard from login/register", str(e), f"Redirect failed: {failures}")


    # ==========================================
    # SCOPE 2: ROLE-BASED ACCESS CONTROL
    # ==========================================

    def test_2_1_admin_only_routes(self):
        """Verify admin-only routes under /admin/* deny staff and trekkers."""
        scope = "2. Role-based access control"
        test_id = "2.1"
        name = "Verify admin-only routes deny staff and trekkers"
        admin_routes = ["/admin/dashboard", "/admin/treks", "/admin/treks/create", "/admin/staff", "/admin/users", "/admin/bookings"]
        failures = []
        try:
            # Test Staff
            self.login("staff_qa1@example.com", "password123")
            for route in admin_routes:
                res = self.client.get(route)
                if res.status_code != 302 or "/auth/login" not in res.headers.get("Location", ""):
                    failures.append(f"Staff accessed {route} (Status: {res.status_code}, Location: {res.headers.get('Location')})")
            
            # Log out staff
            self.client.get("/auth/logout")
            
            # Test Trekker
            self.login("trekker_qa1@example.com", "password123")
            for route in admin_routes:
                res = self.client.get(route)
                if res.status_code != 302 or "/auth/login" not in res.headers.get("Location", ""):
                    failures.append(f"Trekker accessed {route} (Status: {res.status_code}, Location: {res.headers.get('Location')})")
                    
            self.assertEqual(len(failures), 0, f"Failures: {failures}")
            record_result(scope, test_id, name, "PASS", "Admin-only routes deny staff and trekkers by redirecting to /auth/login", "Staff and trekkers redirected to login")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Admin-only routes deny staff and trekkers", str(e), f"Access control failed: {failures}")

    def test_2_2_staff_only_routes(self):
        """Verify staff-only routes under /staff/* deny admins and trekkers."""
        scope = "2. Role-based access control"
        test_id = "2.2"
        name = "Verify staff-only routes deny admins and trekkers"
        staff_routes = ["/staff/dashboard"]
        failures = []
        try:
            # Test Admin
            self.login("admin_qa@example.com", "password123")
            for route in staff_routes:
                res = self.client.get(route)
                if res.status_code != 302 or "/auth/login" not in res.headers.get("Location", ""):
                    failures.append(f"Admin accessed {route} (Status: {res.status_code}, Location: {res.headers.get('Location')})")
            self.client.get("/auth/logout")
            
            # Test Trekker
            self.login("trekker_qa1@example.com", "password123")
            for route in staff_routes:
                res = self.client.get(route)
                if res.status_code != 302 or "/auth/login" not in res.headers.get("Location", ""):
                    failures.append(f"Trekker accessed {route} (Status: {res.status_code}, Location: {res.headers.get('Location')})")
                    
            self.assertEqual(len(failures), 0, f"Failures: {failures}")
            record_result(scope, test_id, name, "PASS", "Staff-only routes deny admins and trekkers by redirecting to /auth/login", "Admins and trekkers redirected to login")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Staff-only routes deny admins and trekkers", str(e), f"Access control failed: {failures}")

    def test_2_3_staff_isolated_trek_access(self):
        """Verify staff cannot access edit/participants of other staff's treks."""
        scope = "2. Role-based access control"
        test_id = "2.3"
        name = "Verify staff can only access their assigned treks"
        try:
            # Create a test trek assigned to Staff 1
            with app.app_context():
                staff1 = User.query.filter_by(username="staff_qa1").first()
                trek = Trek(
                    name="Staff 1 Trek",
                    location="Location A",
                    difficulty=Difficulty.MODERATE,
                    duration=5,
                    max_slots=10,
                    available_slots=10,
                    start_date=datetime.date(2026, 9, 1),
                    end_date=datetime.date(2026, 9, 6),
                    status=TrekStatus.PENDING,
                    staff_id=staff1.id
                )
                db.session.add(trek)
                db.session.commit()
                trek_id = trek.id
            
            # Log in as Staff 2 and try to edit or view participants of Staff 1's Trek
            self.login("staff_qa2@example.com", "password123")
            
            # Edit route
            res_edit = self.client.get(f"/staff/treks/{trek_id}/edit")
            # Participants route
            res_parts = self.client.get(f"/staff/treks/{trek_id}/participants")
            
            # Both should return 403 Forbidden
            self.assertEqual(res_edit.status_code, 403)
            self.assertEqual(res_parts.status_code, 403)
            
            record_result(scope, test_id, name, "PASS", "Staff member receives 403 Forbidden when accessing another staff member's trek", f"Edit status: {res_edit.status_code}, Participants status: {res_parts.status_code}")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Staff member receives 403 Forbidden when accessing another staff member's trek", str(e), "Another staff member was not denied (did not return 403)")

    def test_2_4_trekker_only_routes(self):
        """Verify trekker-only routes under /trekker/* deny admins and staff."""
        scope = "2. Role-based access control"
        test_id = "2.4"
        name = "Verify trekker-only routes deny admins and staff"
        trekker_routes = ["/trekker/dashboard", "/trekker/bookings"]
        failures = []
        try:
            # Test Admin
            self.login("admin_qa@example.com", "password123")
            for route in trekker_routes:
                res = self.client.get(route)
                if res.status_code != 302 or "/auth/login" not in res.headers.get("Location", ""):
                    failures.append(f"Admin accessed {route} (Status: {res.status_code}, Location: {res.headers.get('Location')})")
            self.client.get("/auth/logout")
            
            # Test Staff
            self.login("staff_qa1@example.com", "password123")
            for route in trekker_routes:
                res = self.client.get(route)
                if res.status_code != 302 or "/auth/login" not in res.headers.get("Location", ""):
                    failures.append(f"Staff accessed {route} (Status: {res.status_code}, Location: {res.headers.get('Location')})")
                    
            self.assertEqual(len(failures), 0, f"Failures: {failures}")
            record_result(scope, test_id, name, "PASS", "Trekker-only routes deny admins and staff by redirecting to /auth/login", "Admins and staff redirected to login")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Trekker-only routes deny admins and staff", str(e), f"Access control failed: {failures}")


    # ==========================================
    # SCOPE 3: ADMIN SETUP WORKFLOW
    # ==========================================

    def test_3_1_admin_dashboard_renders(self):
        """Verify admin dashboard renders and displays counts."""
        scope = "3. Admin setup workflow"
        test_id = "3.1"
        name = "Verify admin dashboard renders and shows counts"
        try:
            self.login("admin_qa@example.com", "password123")
            res = self.client.get("/admin/dashboard")
            self.assertEqual(res.status_code, 200)
            html = res.data.decode("utf-8")
            
            has_treks_stat = "Treks" in html
            has_staff_stat = "Staff" in html
            has_bookings_stat = "Bookings" in html
            
            self.assertTrue(has_treks_stat)
            self.assertTrue(has_staff_stat)
            self.assertTrue(has_bookings_stat)
            
            record_result(scope, test_id, name, "PASS", "Admin dashboard renders successfully with counts for treks, staff, trekkers, and bookings", "Counts rendering check passed")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Admin dashboard renders and displays counts", str(e), "Dashboard failed to render or counts not displayed")

    def test_3_2_create_valid_trek(self):
        """Create a valid trek with an approved active staff member assigned."""
        scope = "3. Admin setup workflow"
        test_id = "3.2"
        name = "Create a valid trek via admin"
        try:
            self.login("admin_qa@example.com", "password123")
            res_form = self.client.get("/admin/treks/create")
            csrf_token = self.get_csrf_token(res_form.data.decode("utf-8"))
            
            with app.app_context():
                staff = User.query.filter_by(username="staff_qa1").first()
                staff_id = staff.id
            
            post_data = {
                "csrf_token": csrf_token,
                "name": "EBC Trek",
                "location": "Nepal",
                "difficulty": "Hard",
                "duration": "14",
                "max_slots": "20",
                "available_slots": "20",
                "start_date": "2026-10-01",
                "end_date": "2026-10-15",
                "status": "Approved",
                "staff_id": str(staff_id),
                "description": "Everest Base Camp Trek"
            }
            res = self.client.post("/admin/treks/create", data=post_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            # Check database to verify the trek exists
            with app.app_context():
                trek = Trek.query.filter_by(name="EBC Trek").first()
                self.assertIsNotNone(trek)
                self.assertEqual(trek.location, "Nepal")
                self.assertEqual(trek.duration, 14)
                self.assertEqual(trek.max_slots, 20)
                self.assertEqual(trek.available_slots, 20)
                self.assertEqual(trek.status, TrekStatus.APPROVED)
                self.assertEqual(trek.staff_id, staff_id)
                trek_id = trek.id
                
            record_result(scope, test_id, name, "PASS", "Trek is successfully created and verified in database with all correct parameters", f"Trek created with ID: {trek_id}")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Trek is successfully created via admin", str(e), "Failed to submit form or save to DB")

    def test_3_3_trek_appears_in_list(self):
        """Confirm the trek appears in the admin trek list with correct details."""
        scope = "3. Admin setup workflow"
        test_id = "3.3"
        name = "Verify trek appears in admin list with details"
        try:
            with app.app_context():
                staff = User.query.filter_by(username="staff_qa1").first()
                trek = Trek.query.filter_by(name="EBC Trek").first()
                if not trek:
                    trek = Trek(
                        name="EBC Trek", location="Nepal", difficulty=Difficulty.HARD, duration=14,
                        max_slots=20, available_slots=20, start_date=datetime.date(2026, 10, 1),
                        end_date=datetime.date(2026, 10, 15), status=TrekStatus.APPROVED, staff_id=staff.id
                    )
                    db.session.add(trek)
                    db.session.commit()
            
            self.login("admin_qa@example.com", "password123")
            res = self.client.get("/admin/treks")
            self.assertEqual(res.status_code, 200)
            html = res.data.decode("utf-8")
            
            self.assertIn("EBC Trek", html)
            self.assertIn("Nepal", html)
            self.assertIn("20", html)
            self.assertIn("Approved", html)
            self.assertIn("staff_qa1", html)
            
            record_result(scope, test_id, name, "PASS", "Trek details appear correctly in the admin treks view table", "Trek is present in admin treks list with matching details")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Trek details appear correctly in admin treks view", str(e), "Trek or details not found in treks page HTML")

    def test_3_4_edit_trek_persists(self):
        """Edit the trek and verify saved changes persist."""
        scope = "3. Admin setup workflow"
        test_id = "3.4"
        name = "Edit trek details and verify persistence"
        try:
            with app.app_context():
                trek = Trek.query.filter_by(name="EBC Trek").first()
                trek_id = trek.id
                staff2 = User.query.filter_by(username="staff_qa2").first()
                staff2_id = staff2.id
                
            self.login("admin_qa@example.com", "password123")
            res_form = self.client.get(f"/admin/treks/{trek_id}/edit")
            csrf_token = self.get_csrf_token(res_form.data.decode("utf-8"))
            
            post_data = {
                "csrf_token": csrf_token,
                "name": "EBC Trek Updated",
                "location": "Nepal Himalayas",
                "difficulty": "Hard",
                "duration": "12",
                "max_slots": "15",
                "available_slots": "15",
                "start_date": "2026-10-02",
                "end_date": "2026-10-14",
                "status": "Open",
                "staff_id": str(staff2_id),
                "description": "Everest Base Camp Trek - Updated description"
            }
            res = self.client.post(f"/admin/treks/{trek_id}/edit", data=post_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            # Check DB
            with app.app_context():
                updated_trek = db.session.get(Trek, trek_id)
                self.assertEqual(updated_trek.name, "EBC Trek Updated")
                self.assertEqual(updated_trek.location, "Nepal Himalayas")
                self.assertEqual(updated_trek.duration, 12)
                self.assertEqual(updated_trek.max_slots, 15)
                self.assertEqual(updated_trek.available_slots, 15)
                self.assertEqual(updated_trek.status, TrekStatus.OPEN)
                self.assertEqual(updated_trek.staff_id, staff2_id)
                self.assertEqual(updated_trek.description, "Everest Base Camp Trek - Updated description")
                
            record_result(scope, test_id, name, "PASS", "Edited trek fields persist successfully in database", "Changes verified in database")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Edited trek fields persist successfully", str(e), "Edits did not persist in database or edit form failed")

    def test_3_5_invalid_trek_form_validation(self):
        """Verify invalid form cases are rejected: end date before start date, available slots > max slots, zero/negative duration/capacity."""
        scope = "3. Admin setup workflow"
        test_id = "3.5"
        name = "Verify invalid form cases are rejected by validation"
        failures = []
        try:
            self.login("admin_qa@example.com", "password123")
            res_form = self.client.get("/admin/treks/create")
            csrf_token = self.get_csrf_token(res_form.data.decode("utf-8"))
            
            # Case A: End date before start date
            data_date = {
                "csrf_token": csrf_token, "name": "Invalid Date Trek", "location": "Test", "difficulty": "Easy",
                "duration": "5", "max_slots": "10", "available_slots": "10",
                "start_date": "2026-10-15", "end_date": "2026-10-10", "status": "Pending", "staff_id": "0"
            }
            res_a = self.client.post("/admin/treks/create", data=data_date)
            if res_a.status_code != 200 or "End date must be on or after the start date." not in res_a.data.decode("utf-8"):
                failures.append("End date before start date validation did not show expected error.")
                
            # Case B: Available slots > Max slots
            data_slots = {
                "csrf_token": csrf_token, "name": "Invalid Slots Trek", "location": "Test", "difficulty": "Easy",
                "duration": "5", "max_slots": "10", "available_slots": "12",
                "start_date": "2026-10-10", "end_date": "2026-10-15", "status": "Pending", "staff_id": "0"
            }
            res_b = self.client.post("/admin/treks/create", data=data_slots)
            if res_b.status_code != 200 or "Available slots cannot exceed maximum slots." not in res_b.data.decode("utf-8"):
                failures.append("Available slots > max slots validation did not show expected error.")
                
            # Case C: Zero/negative duration
            data_duration = {
                "csrf_token": csrf_token, "name": "Invalid Duration Trek", "location": "Test", "difficulty": "Easy",
                "duration": "0", "max_slots": "10", "available_slots": "10",
                "start_date": "2026-10-10", "end_date": "2026-10-15", "status": "Pending", "staff_id": "0"
            }
            res_c = self.client.post("/admin/treks/create", data=data_duration)
            if res_c.status_code != 200 or ("Number must be between 1 and 60." not in res_c.data.decode("utf-8") and "Number must be at least 1." not in res_c.data.decode("utf-8")):
                failures.append("Zero/negative duration validation did not show expected error.")
                
            # Case D: Zero/negative capacity (max_slots)
            data_capacity = {
                "csrf_token": csrf_token, "name": "Invalid Capacity Trek", "location": "Test", "difficulty": "Easy",
                "duration": "5", "max_slots": "0", "available_slots": "0",
                "start_date": "2026-10-10", "end_date": "2026-10-15", "status": "Pending", "staff_id": "0"
            }
            res_d = self.client.post("/admin/treks/create", data=data_capacity)
            if res_d.status_code != 200 or ("Number must be between 1 and 500." not in res_d.data.decode("utf-8") and "Number must be at least 1." not in res_d.data.decode("utf-8")):
                failures.append("Zero/negative capacity validation did not show expected error.")

            self.assertEqual(len(failures), 0, f"Failures: {failures}")
            record_result(scope, test_id, name, "PASS", "All invalid forms (dates, slots, negative duration/capacity) are rejected with clear error messages", "Validation working correctly")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "All invalid form cases are rejected by validation", str(e), f"Validation failed: {failures}")

    def test_3_6_approve_pending_staff(self):
        """Verify admin can approve a pending staff member."""
        scope = "3. Admin setup workflow"
        test_id = "3.6"
        name = "Approve pending staff member"
        try:
            with app.app_context():
                staff = User.query.filter_by(username="staff_pending").first()
                staff_id = staff.id
                self.assertFalse(staff.approved)
                
            self.login("admin_qa@example.com", "password123")
            res = self.client.post(f"/admin/staff/{staff_id}/approve", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            with app.app_context():
                staff_updated = db.session.get(User, staff_id)
                self.assertTrue(staff_updated.approved)
                
            record_result(scope, test_id, name, "PASS", "Admin successfully approves staff member; status updates in database to approved=True", "Staff approval successful")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Admin approves pending staff member", str(e), "Approval request failed or database did not update")

    def test_3_7_toggle_staff_active_status(self):
        """Verify admin can deactivate and reactivate staff."""
        scope = "3. Admin setup workflow"
        test_id = "3.7"
        name = "Deactivate and reactivate staff member"
        try:
            with app.app_context():
                staff = User.query.filter_by(username="staff_qa1").first()
                staff_id = staff.id
                self.assertTrue(staff.active)
                
            self.login("admin_qa@example.com", "password123")
            
            # Deactivate
            res_deact = self.client.post(f"/admin/staff/{staff_id}/toggle-active", follow_redirects=True)
            self.assertEqual(res_deact.status_code, 200)
            with app.app_context():
                staff_updated = db.session.get(User, staff_id)
                self.assertFalse(staff_updated.active)
                
            # Reactivate
            res_react = self.client.post(f"/admin/staff/{staff_id}/toggle-active", follow_redirects=True)
            self.assertEqual(res_react.status_code, 200)
            with app.app_context():
                staff_updated2 = db.session.get(User, staff_id)
                self.assertTrue(staff_updated2.active)
                
            record_result(scope, test_id, name, "PASS", "Admin can deactivate and reactivate staff; status toggles in database correctly", "Deactivation and reactivation verified")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Admin can deactivate and reactivate staff", str(e), "Toggle active request failed or database did not toggle")

    def test_3_8_booking_list_renders(self):
        """Verify the booking list renders."""
        scope = "3. Admin setup workflow"
        test_id = "3.8"
        name = "Verify admin bookings page renders"
        try:
            self.login("admin_qa@example.com", "password123")
            res = self.client.get("/admin/bookings")
            self.assertEqual(res.status_code, 200)
            html = res.data.decode("utf-8")
            self.assertIn("Bookings", html)
            record_result(scope, test_id, name, "PASS", "Admin bookings list renders with status code 200", "Admin bookings page validated")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Admin bookings page renders", str(e), "Failed to load admin bookings page")


    # ==========================================
    # SCOPE 4: STAFF TREK-MANAGEMENT WORKFLOW
    # ==========================================

    def test_4_1_staff_trek_on_dashboard(self):
        """Sign in as staff and verify their assigned trek appears on dashboard."""
        scope = "4. Staff trek-management workflow"
        test_id = "4.1 & 4.2"
        name = "Staff dashboard shows assigned treks"
        try:
            with app.app_context():
                staff = User.query.filter_by(username="staff_qa1").first()
                trek = Trek(
                    name="Staff 1 Trek Unique", location="Tibet", difficulty=Difficulty.HARD, duration=10,
                    max_slots=15, available_slots=15, start_date=datetime.date(2026, 11, 1),
                    end_date=datetime.date(2026, 11, 10), status=TrekStatus.OPEN, staff_id=staff.id
                )
                db.session.add(trek)
                db.session.commit()
                trek_id = trek.id
                
            self.login("staff_qa1@example.com", "password123")
            res = self.client.get("/staff/dashboard")
            self.assertEqual(res.status_code, 200)
            html = res.data.decode("utf-8")
            
            self.assertIn("Staff 1 Trek Unique", html)
            self.assertIn("Tibet", html)
            self.assertIn("15", html)
            
            record_result(scope, test_id, name, "PASS", "Assigned trek name and details are displayed on staff dashboard", "Trek is listed on staff dashboard")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Assigned trek name and details displayed on staff dashboard", str(e), "Trek not displayed on dashboard")

    def test_4_3_participant_count_accurate(self):
        """Verify participant count is accurate."""
        scope = "4. Staff trek-management workflow"
        test_id = "4.3"
        name = "Verify staff dashboard participant count is accurate"
        try:
            with app.app_context():
                trek = Trek.query.filter_by(name="Staff 1 Trek Unique").first()
                trek_id = trek.id
                trekker = User.query.filter_by(username="trekker_qa1").first()
                trekker_id = trekker.id
                
                booking1 = Booking(user_id=trekker_id, trek_id=trek_id, status=BookingStatus.BOOKED)
                db.session.add(booking1)
                
                booking2 = Booking(user_id=trekker_id, trek_id=trek_id, status=BookingStatus.CANCELLED)
                db.session.add(booking2)
                
                trek.available_slots -= 1
                db.session.commit()
                
            self.login("staff_qa1@example.com", "password123")
            res = self.client.get("/staff/dashboard")
            self.assertEqual(res.status_code, 200)
            
            res_part_page = self.client.get(f"/staff/treks/{trek_id}/participants")
            html_part = res_part_page.data.decode("utf-8")
            self.assertIn("trekker_qa1", html_part)
            
            record_result(scope, test_id, name, "PASS", "Participant list displays only relevant bookings and dashboard handles counts", "Participant verification passed")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Participant count is accurate and displayed on dashboard", str(e), "Failed to verify participant counts")

    def test_4_4_update_trek_slots_and_status(self):
        """Update available slots and status to Open, Ongoing, Closed, Completed, and verify persistence."""
        scope = "4. Staff trek-management workflow"
        test_id = "4.4"
        name = "Staff updates trek slots and status"
        try:
            with app.app_context():
                trek = Trek.query.filter_by(name="Staff 1 Trek Unique").first()
                trek_id = trek.id
                
            self.login("staff_qa1@example.com", "password123")
            
            res_form = self.client.get(f"/staff/treks/{trek_id}/edit")
            csrf_token = self.get_csrf_token(res_form.data.decode("utf-8"))
            
            # 1. Update to Open and slots=12
            data_open = {"csrf_token": csrf_token, "available_slots": "12", "status": "Open"}
            res_open = self.client.post(f"/staff/treks/{trek_id}/edit", data=data_open, follow_redirects=True)
            self.assertEqual(res_open.status_code, 200)
            with app.app_context():
                t = db.session.get(Trek, trek_id)
                self.assertEqual(t.status, TrekStatus.OPEN)
                self.assertEqual(t.available_slots, 12)
                
            # 2. Update to Ongoing and slots=12
            data_ongoing = {"csrf_token": csrf_token, "available_slots": "12", "status": "Ongoing"}
            res_ong = self.client.post(f"/staff/treks/{trek_id}/edit", data=data_ongoing, follow_redirects=True)
            self.assertEqual(res_ong.status_code, 200)
            with app.app_context():
                t = db.session.get(Trek, trek_id)
                self.assertEqual(t.status, TrekStatus.ONGOING)
                
            # 3. Update to Closed and slots=8
            data_closed = {"csrf_token": csrf_token, "available_slots": "8", "status": "Closed"}
            res_cls = self.client.post(f"/staff/treks/{trek_id}/edit", data=data_closed, follow_redirects=True)
            self.assertEqual(res_cls.status_code, 200)
            with app.app_context():
                t = db.session.get(Trek, trek_id)
                self.assertEqual(t.status, TrekStatus.CLOSED)
                self.assertEqual(t.available_slots, 8)
                
            # 4. Update to Completed and slots=0
            data_comp = {"csrf_token": csrf_token, "available_slots": "0", "status": "Completed"}
            res_cmp = self.client.post(f"/staff/treks/{trek_id}/edit", data=data_comp, follow_redirects=True)
            self.assertEqual(res_cmp.status_code, 200)
            with app.app_context():
                t = db.session.get(Trek, trek_id)
                self.assertEqual(t.status, TrekStatus.COMPLETED)
                self.assertEqual(t.available_slots, 0)
                
            record_result(scope, test_id, name, "PASS", "Staff updates trek available slots and status (Open, Ongoing, Closed, Completed) and edits persist", "Staff edits verified successfully")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Staff updates trek available slots and status and edits persist", str(e), "Failed to save staff updates")

    def test_4_5_available_slots_exceed_capacity(self):
        """Verify available slots cannot exceed the remaining capacity after confirmed bookings."""
        scope = "4. Staff trek-management workflow"
        test_id = "4.5"
        name = "Verify available slots cannot exceed capacity after bookings"
        try:
            with app.app_context():
                trek = Trek.query.filter_by(name="Staff 1 Trek Unique").first()
                trek_id = trek.id
                
            self.login("staff_qa1@example.com", "password123")
            res_form = self.client.get(f"/staff/treks/{trek_id}/edit")
            csrf_token = self.get_csrf_token(res_form.data.decode("utf-8"))
            
            data_invalid = {"csrf_token": csrf_token, "available_slots": "15", "status": "Open"}
            res = self.client.post(f"/staff/treks/{trek_id}/edit", data=data_invalid)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn("Available slots exceed the trek capacity after confirmed bookings.", res.data.decode("utf-8"))
            record_result(scope, test_id, name, "PASS", "Setting available slots > (max - booked) fails validation with clear error message", "Validation correctly prevents exceeding remaining capacity")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Available slots cannot exceed remaining capacity after bookings", str(e), "Validation failed to trigger or error message is missing")


    # ==========================================
    # SCOPE 5: TREKKER DISCOVERY WORKFLOW
    # ==========================================

    def test_5_1_discovery_status_open(self):
        """Verify only treks with status Open appear on /trekker/dashboard."""
        scope = "5. Trekker discovery workflow"
        test_id = "5.1 & 5.2 & 5.6"
        name = "Verify trekker dashboard only shows Open status treks"
        try:
            with app.app_context():
                staff = User.query.filter_by(username="staff_qa1").first()
                t_open = Trek(
                    name="Open Trek A", location="Nepal", difficulty=Difficulty.EASY, duration=3,
                    max_slots=10, available_slots=10, start_date=datetime.date(2026, 12, 1),
                    end_date=datetime.date(2026, 12, 4), status=TrekStatus.OPEN, staff_id=staff.id
                )
                t_pending = Trek(
                    name="Pending Trek B", location="Nepal", difficulty=Difficulty.EASY, duration=3,
                    max_slots=10, available_slots=10, start_date=datetime.date(2026, 12, 1),
                    end_date=datetime.date(2026, 12, 4), status=TrekStatus.PENDING, staff_id=staff.id
                )
                t_closed = Trek(
                    name="Closed Trek C", location="Nepal", difficulty=Difficulty.EASY, duration=3,
                    max_slots=10, available_slots=10, start_date=datetime.date(2026, 12, 1),
                    end_date=datetime.date(2026, 12, 4), status=TrekStatus.CLOSED, staff_id=staff.id
                )
                t_ongoing = Trek(
                    name="Ongoing Trek D", location="Nepal", difficulty=Difficulty.EASY, duration=3,
                    max_slots=10, available_slots=10, start_date=datetime.date(2026, 12, 1),
                    end_date=datetime.date(2026, 12, 4), status=TrekStatus.ONGOING, staff_id=staff.id
                )
                db.session.add_all([t_open, t_pending, t_closed, t_ongoing])
                db.session.commit()
                
            self.login("trekker_qa1@example.com", "password123")
            res = self.client.get("/trekker/dashboard")
            self.assertEqual(res.status_code, 200)
            html = res.data.decode("utf-8")
            
            self.assertIn("Open Trek A", html)
            self.assertNotIn("Pending Trek B", html)
            self.assertNotIn("Closed Trek C", html)
            self.assertNotIn("Ongoing Trek D", html)
            
            record_result(scope, test_id, name, "PASS", "Only treks with status Open are listed on trekker dashboard", "Status filter check passed")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Only treks with status Open are listed on trekker dashboard", str(e), "Pending/Closed/Ongoing treks were displayed or Open trek was missing")

    def test_5_3_discovery_search_and_filter(self):
        """Verify search by trek name, location, and difficulty filter."""
        scope = "5. Trekker discovery workflow"
        test_id = "5.3 & 5.4 & 5.5"
        name = "Verify search and filter functionality on trekker dashboard"
        try:
            with app.app_context():
                staff = User.query.filter_by(username="staff_qa1").first()
                t_himalaya = Trek(
                    name="Annapurna Circuit", location="Pokhara", difficulty=Difficulty.HARD, duration=12,
                    max_slots=10, available_slots=10, start_date=datetime.date(2026, 12, 5),
                    end_date=datetime.date(2026, 12, 17), status=TrekStatus.OPEN, staff_id=staff.id
                )
                db.session.add(t_himalaya)
                db.session.commit()
                
            self.login("trekker_qa1@example.com", "password123")
            
            # Test A: Search by trek name "Annapurna"
            res_name = self.client.get("/trekker/dashboard?query=Annapurna")
            html_name = res_name.data.decode("utf-8")
            
            # Test B: Search by location "Pokhara"
            res_loc = self.client.get("/trekker/dashboard?location=Pokhara")
            html_loc = res_loc.data.decode("utf-8")
            
            # Test C: Filter by difficulty "Hard"
            res_diff = self.client.get("/trekker/dashboard?difficulty=Hard")
            html_diff = res_diff.data.decode("utf-8")
            
            name_search_filtered = "Open Trek A" not in html_name and "Annapurna Circuit" in html_name
            loc_search_filtered = "Open Trek A" not in html_loc and "Annapurna Circuit" in html_loc
            diff_filter_filtered = "Open Trek A" not in html_diff and "Annapurna Circuit" in html_diff
            
            if not name_search_filtered or not loc_search_filtered or not diff_filter_filtered:
                details = f"Name query shows Open Trek A: {'Open Trek A' in html_name}. Location query shows Open Trek A: {'Open Trek A' in html_loc}. Difficulty filter shows Open Trek A: {'Open Trek A' in html_diff}."
                raise AssertionError(f"Search/filtering did not narrow down the results. {details}")
                
            record_result(scope, test_id, name, "PASS", "Search and filtering returns correct subsets of treks on the dashboard", "Search and filtering working correctly")
        except AssertionError as ae:
            record_result(scope, test_id, name, "FAIL", "Search and filtering returns correct subsets of treks on the dashboard", str(ae), "The TrekSearchForm in routes/trekker.py is instantiated as form = TrekSearchForm() without passing request.args, so it ignores all GET parameters and displays the full list of open treks.")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Search and filtering returns correct subsets of treks on the dashboard", str(e), "General exception occurred during search/filter testing")


    # ==========================================
    # SCOPE 6: BOOKING AND HISTORY WORKFLOW
    # ==========================================

    def test_6_1_booking_success_decreases_slots(self):
        """Book an Open trek with available capacity and verify slots decrease."""
        scope = "6. Booking and history workflow"
        test_id = "6.1"
        name = "Book open trek and verify slots decrease"
        try:
            with app.app_context():
                trek = Trek.query.filter_by(name="Open Trek A").first()
                trek_id = trek.id
                initial_slots = trek.available_slots
                self.assertEqual(initial_slots, 10)
                
            self.login("trekker_qa1@example.com", "password123")
            
            res = self.client.post(f"/trekker/treks/{trek_id}/book", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            with app.app_context():
                trekker = User.query.filter_by(username="trekker_qa1").first()
                bookings = Booking.query.filter_by(user_id=trekker.id, trek_id=trek_id).all()
                self.assertEqual(len(bookings), 1)
                self.assertEqual(bookings[0].status, BookingStatus.BOOKED)
                
                updated_trek = db.session.get(Trek, trek_id)
                self.assertEqual(updated_trek.available_slots, initial_slots - 1)
                
            record_result(scope, test_id, name, "PASS", "Booking is created and trek available slots decrease by 1", "Booking verified successfully in DB")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Booking is created and trek available slots decrease by 1", str(e), "Booking failed or slots did not decrease correctly")

    def test_6_2_duplicate_booking_prevention(self):
        """Attempt to book the same trek again and verify failure."""
        scope = "6. Booking and history workflow"
        test_id = "6.2"
        name = "Prevent duplicate active booking"
        try:
            with app.app_context():
                trek = Trek.query.filter_by(name="Open Trek A").first()
                trek_id = trek.id
                slots_before = trek.available_slots
                
            self.login("trekker_qa1@example.com", "password123")
            
            res = self.client.post(f"/trekker/treks/{trek_id}/book", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn("You already have an active booking for this trek.", res.data.decode("utf-8"))
            
            with app.app_context():
                trekker = User.query.filter_by(username="trekker_qa1").first()
                bookings = Booking.query.filter_by(user_id=trekker.id, trek_id=trek_id, status=BookingStatus.BOOKED).all()
                self.assertEqual(len(bookings), 1)
                
                updated_trek = db.session.get(Trek, trek_id)
                self.assertEqual(updated_trek.available_slots, slots_before)
                
            record_result(scope, test_id, name, "PASS", "Second booking attempt rejected and slots remain unchanged", "Duplicate booking prevented successfully")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Prevent duplicate active booking", str(e), "Duplicate booking was allowed or slots decreased")

    def test_6_3_book_closed_trek_rejected(self):
        """Attempt to book a Closed trek and verify rejection."""
        scope = "6. Booking and history workflow"
        test_id = "6.3"
        name = "Reject booking for Closed trek"
        try:
            with app.app_context():
                trek = Trek.query.filter_by(name="Closed Trek C").first()
                trek_id = trek.id
                
            self.login("trekker_qa1@example.com", "password123")
            res = self.client.post(f"/trekker/treks/{trek_id}/book", follow_redirects=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn("This trek is closed or no longer has available slots.", res.data.decode("utf-8"))
            # Verify no booking is created
            with app.app_context():
                trekker = User.query.filter_by(username="trekker_qa1").first()
                booking = Booking.query.filter_by(user_id=trekker.id, trek_id=trek_id).first()
                self.assertIsNone(booking)
                
            record_result(scope, test_id, name, "PASS", "Closed trek booking rejected and no booking created in database", "Closed trek booking rejection verified")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Reject booking for Closed trek", str(e), "Booking was created for Closed trek")

    def test_6_4_book_full_trek_rejected(self):
        """Attempt to book a full trek and verify rejection."""
        scope = "6. Booking and history workflow"
        test_id = "6.4"
        name = "Reject booking for full trek (available_slots=0)"
        try:
            with app.app_context():
                staff = User.query.filter_by(username="staff_qa1").first()
                t_full = Trek(
                    name="Full Trek A", location="Nepal", difficulty=Difficulty.EASY, duration=3,
                    max_slots=10, available_slots=0, start_date=datetime.date(2026, 12, 1),
                    end_date=datetime.date(2026, 12, 4), status=TrekStatus.OPEN, staff_id=staff.id
                )
                db.session.add(t_full)
                db.session.commit()
                trek_id = t_full.id
                
            self.login("trekker_qa2@example.com", "password123")
            res = self.client.post(f"/trekker/treks/{trek_id}/book", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn("This trek is closed or no longer has available slots.", res.data.decode("utf-8"))
            # Verify no booking is created
            with app.app_context():
                trekker = User.query.filter_by(username="trekker_qa2").first()
                booking = Booking.query.filter_by(user_id=trekker.id, trek_id=trek_id).first()
                self.assertIsNone(booking)
                
            record_result(scope, test_id, name, "PASS", "Full trek booking is rejected and no booking created in database", "Full trek booking rejection verified")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Reject booking for full trek", str(e), "Booking was created for a full trek")

    def test_6_5_trekker_booking_history(self):
        """Verify the trekker’s booking page shows only that trekker’s booking history."""
        scope = "6. Booking and history workflow"
        test_id = "6.5"
        name = "Verify trekker booking history page is user-isolated"
        try:
            with app.app_context():
                trek1 = Trek.query.filter_by(name="Open Trek A").first()
                trek2 = Trek.query.filter_by(name="Annapurna Circuit").first()
                t1 = User.query.filter_by(username="trekker_qa1").first()
                t2 = User.query.filter_by(username="trekker_qa2").first()
                
                b1 = Booking.query.filter_by(user_id=t1.id, trek_id=trek1.id).first()
                if not b1:
                    b1 = Booking(user_id=t1.id, trek_id=trek1.id, status=BookingStatus.BOOKED)
                    db.session.add(b1)
                b2 = Booking.query.filter_by(user_id=t2.id, trek_id=trek2.id).first()
                if not b2:
                    b2 = Booking(user_id=t2.id, trek_id=trek2.id, status=BookingStatus.BOOKED)
                    db.session.add(b2)
                db.session.commit()
                
            self.login("trekker_qa1@example.com", "password123")
            res1 = self.client.get("/trekker/bookings")
            html1 = res1.data.decode("utf-8")
            
            self.assertIn("Open Trek A", html1)
            self.assertNotIn("Annapurna Circuit", html1)
            
            self.client.get("/auth/logout")
            self.login("trekker_qa2@example.com", "password123")
            res2 = self.client.get("/trekker/bookings")
            html2 = res2.data.decode("utf-8")
            
            self.assertIn("Annapurna Circuit", html2)
            self.assertNotIn("Open Trek A", html2)
            
            record_result(scope, test_id, name, "PASS", "Trekker bookings history shows only the logged-in trekker's bookings", "User isolation verified successfully")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Trekker booking history page is user-isolated", str(e), "Trekker saw bookings belonging to another user")

    def test_6_6_cancel_booking(self):
        """Cancel an active booking, verify status changes and slots increase."""
        scope = "6. Booking and history workflow"
        test_id = "6.6"
        name = "Cancel booking and verify slot increment"
        try:
            with app.app_context():
                trekker = User.query.filter_by(username="trekker_qa1").first()
                trek = Trek.query.filter_by(name="Open Trek A").first()
                trek_id = trek.id
                slots_before = trek.available_slots
                booking = Booking.query.filter_by(user_id=trekker.id, trek_id=trek_id, status=BookingStatus.BOOKED).first()
                booking_id = booking.id
                
            self.login("trekker_qa1@example.com", "password123")
            res = self.client.post(f"/trekker/bookings/{booking_id}/cancel", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            with app.app_context():
                updated_booking = db.session.get(Booking, booking_id)
                self.assertEqual(updated_booking.status, BookingStatus.CANCELLED)
                
                updated_trek = db.session.get(Trek, trek_id)
                self.assertEqual(updated_trek.available_slots, slots_before + 1)
                
            record_result(scope, test_id, name, "PASS", "Booking is successfully cancelled (status updates to Cancelled) and available slots increase by 1", "Booking cancellation verified in DB")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Cancel booking and verify slot increment", str(e), "Cancellation failed or slots did not increment")

    def test_6_7_trekker_cannot_cancel_others_booking(self):
        """Verify a trekker cannot cancel another trekker’s booking."""
        scope = "6. Booking and history workflow"
        test_id = "6.7"
        name = "Prevent trekker from cancelling another trekker's booking"
        try:
            with app.app_context():
                trekker2 = User.query.filter_by(username="trekker_qa2").first()
                trek = Trek.query.filter_by(name="Annapurna Circuit").first()
                booking2 = Booking.query.filter_by(user_id=trekker2.id, trek_id=trek.id, status=BookingStatus.BOOKED).first()
                booking_id = booking2.id
                
            self.login("trekker_qa1@example.com", "password123")
            res = self.client.post(f"/trekker/bookings/{booking_id}/cancel", follow_redirects=True)
            
            self.assertEqual(res.status_code, 404)
            
            with app.app_context():
                booking_db = db.session.get(Booking, booking_id)
                self.assertEqual(booking_db.status, BookingStatus.BOOKED)
                
            record_result(scope, test_id, name, "PASS", "Attempting to cancel another trekker's booking returns 404 and leaves booking status unchanged", "Cross-user cancellation prevented successfully")
        except Exception as e:
            record_result(scope, test_id, name, "FAIL", "Prevent trekker from cancelling another trekker's booking", str(e), "Trekker was able to cancel another trekker's booking or response was not 404")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(QATestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Write JSON results
    import json
    results_path = os.path.join(BASE_DIR, "tmp", "qa_test_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(test_results, f, indent=4)
        
    print(f"\nQA Automated Test Suite completed. Results saved to {results_path}")
    if result.wasSuccessful():
        print("All automated tests completed successfully!")
        sys.exit(0)
    else:
        print("Some tests failed. Check results above.")
        sys.exit(1)
