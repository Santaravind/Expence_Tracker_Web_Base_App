"""
Full End-to-End Verification of Rendered HTML and Workflows
"""
import unittest
from app import app

class E2EVerification(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_complete_user_journey(self):
        # 1. Access Home Page
        home_res = self.client.get('/home')
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b'Expense<span>Flow</span>', home_res.data)
        self.assertIn(b'Smart Expense Tracking for', home_res.data)
        self.assertIn(b'Monthly Overview', home_res.data)
        self.assertIn(b'Master Your Money in 3 Easy Steps', home_res.data)

        # 2. Register New User
        import time
        test_email = f"alex_{int(time.time() * 1000)}@example.com"
        reg_res = self.client.post('/registation', data={
            'name': 'Alex Morgan',
            'email': test_email,
            'currency': '$',
            'budget': '45000',
            'password': 'mypassword123',
            'confirm_password': 'mypassword123'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b'Account successfully created', reg_res.data)

        # 3. Login with New User
        login_res = self.client.post('/login', data={
            'email': test_email,
            'password': 'mypassword123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome back, Alex Morgan', login_res.data)
        self.assertIn(b'Total Spent This Month', login_res.data)
        self.assertIn(b'Remaining Budget', login_res.data)

        # 4. Add Expense 1: Food
        add_res1 = self.client.post('/add-expense', data={
            'title': 'Italian Restaurant Dinner',
            'amount': '85.50',
            'category': 'Food',
            'payment_method': 'Credit Card',
            'date': '2026-09-08',
            'notes': 'Dinner with Alex and team'
        }, follow_redirects=True)
        self.assertEqual(add_res1.status_code, 200)
        self.assertIn(b'Italian Restaurant Dinner', add_res1.data)
        self.assertIn(b'85.50', add_res1.data)

        # 5. Add Expense 2: Transport
        add_res2 = self.client.post('/add-expense', data={
            'title': 'Uber City Taxi',
            'amount': '32.00',
            'category': 'Transport',
            'payment_method': 'UPI',
            'date': '2026-09-08',
            'notes': 'Trip to office'
        }, follow_redirects=True)
        self.assertEqual(add_res2.status_code, 200)
        self.assertIn(b'Uber City Taxi', add_res2.data)

        # 6. Update Monthly Budget
        budget_res = self.client.post('/update-budget', data={
            'currency': '$',
            'monthly_budget': '60000'
        }, follow_redirects=True)
        self.assertEqual(budget_res.status_code, 200)
        self.assertIn(b'Monthly budget settings updated successfully', budget_res.data)

        # 7. Access Monthly Reports
        rep_res = self.client.get('/reports', follow_redirects=True)
        self.assertEqual(rep_res.status_code, 200)
        self.assertIn(b'Monthly Financial Report', rep_res.data)
        self.assertIn(b'reportsCategoryChart', rep_res.data)
        self.assertIn(b'reportsDailyTrendChart', rep_res.data)
        self.assertIn(b'reportsPaymentChart', rep_res.data)
        self.assertIn(b'Italian Restaurant Dinner', rep_res.data)

        # 8. Export CSV for current month
        csv_res = self.client.get('/export-csv?month=2026-09')
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn(b'Italian Restaurant Dinner', csv_res.data)
        self.assertIn(b'Uber City Taxi', csv_res.data)

        # 9. Logout
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'signed out safely', logout_res.data)

if __name__ == '__main__':
    unittest.main()
