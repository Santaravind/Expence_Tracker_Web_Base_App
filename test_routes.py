"""
Unit and Integration Test for ExpenseFlow Web Application
"""
import unittest
from app import app, get_db

class ExpenseFlowTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ExpenseFlow', response.data)
        self.assertIn(b'Take Control of Your Daily Expenses', response.data)

    def test_about_page(self):
        response = self.client.get('/about')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Architecture', response.data)

    def test_contact_page(self):
        response = self.client.get('/contect')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Send Us a Message', response.data)

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome Back', response.data)

    def test_register_and_auth_flow(self):
        # 1. Login with Demo User
        login_res = self.client.post('/login', data={
            'email': 'demo@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Dashboard', login_res.data)
        self.assertIn(b'Welcome back', login_res.data)

        # 2. Add New Expense
        add_res = self.client.post('/add-expense', data={
            'title': 'Test Grocery Purchase',
            'amount': '1500.50',
            'category': 'Shopping',
            'payment_method': 'UPI',
            'date': '2026-09-08',
            'notes': 'Bought snacks and fruits'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        self.assertIn(b'Test Grocery Purchase', add_res.data)

        # 3. View Reports
        reports_res = self.client.get('/reports', follow_redirects=True)
        self.assertEqual(reports_res.status_code, 200)
        self.assertIn(b'Monthly Financial Report', reports_res.data)

        # 4. Export CSV
        csv_res = self.client.get('/export-csv')
        self.assertEqual(csv_res.status_code, 200)
        self.assertEqual(csv_res.mimetype, 'text/csv')
        self.assertIn(b'Test Grocery Purchase', csv_res.data)

        # 5. Logout
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'signed out safely', logout_res.data)

if __name__ == '__main__':
    unittest.main()
