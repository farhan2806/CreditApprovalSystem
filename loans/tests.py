"""
Unit tests for the Credit Approval System.
"""
from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Customer, Loan
from .services import (
    calculate_approved_limit,
    calculate_credit_score,
    calculate_monthly_installment,
    check_loan_eligibility,
)


class TestCalculateApprovedLimit(TestCase):
    def test_basic_calculation(self):
        # 36 * 50000 = 1,800,000 -> rounds to nearest lakh = 1,800,000
        self.assertEqual(calculate_approved_limit(50000), 1800000)

    def test_rounding_to_lakh(self):
        # 36 * 30000 = 1,080,000 -> rounds to 1,100,000
        result = calculate_approved_limit(30000)
        self.assertEqual(result % 100000, 0)

    def test_low_salary(self):
        # 36 * 10000 = 360,000
        self.assertEqual(calculate_approved_limit(10000), 400000)


class TestCalculateMonthlyInstallment(TestCase):
    def test_standard_loan(self):
        # 100000 at 10% annual for 12 months
        emi = calculate_monthly_installment(100000, 10, 12)
        self.assertGreater(emi, 8000)
        self.assertLess(emi, 9000)

    def test_zero_interest(self):
        emi = calculate_monthly_installment(120000, 0, 12)
        self.assertAlmostEqual(emi, 10000.0, places=2)


class TestCalculateCreditScore(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            age=30,
            phone_number=1234567890,
            monthly_salary=50000,
            approved_limit=1800000,
        )

    def test_new_customer_gets_default_score(self):
        score = calculate_credit_score(self.customer)
        self.assertEqual(score, 50)

    def test_score_zero_when_loans_exceed_limit(self):
        # Create a loan that exceeds the approved limit
        Loan.objects.create(
            customer=self.customer,
            loan_amount=2000000,  # > approved_limit
            tenure=12,
            interest_rate=10,
            monthly_repayment=175000,
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )
        score = calculate_credit_score(self.customer)
        self.assertEqual(score, 0)

    def test_good_payment_history_increases_score(self):
        # Create loan with good payment history
        Loan.objects.create(
            customer=self.customer,
            loan_amount=100000,
            tenure=12,
            interest_rate=10,
            monthly_repayment=8791,
            emis_paid_on_time=12,  # All paid on time
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=30),
        )
        score = calculate_credit_score(self.customer)
        self.assertGreater(score, 50)


class TestCheckLoanEligibility(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            age=35,
            phone_number=9876543210,
            monthly_salary=80000,
            approved_limit=2900000,
        )

    def test_new_customer_gets_approved_with_default_score(self):
        customer_obj, approval, interest_rate, corrected_rate, emi = check_loan_eligibility(
            self.customer.id, 100000, 15, 12
        )
        self.assertTrue(approval)

    def test_nonexistent_customer(self):
        customer_obj, approval, interest_rate, corrected_rate, emi = check_loan_eligibility(
            99999, 100000, 15, 12
        )
        self.assertIsNone(customer_obj)
        self.assertFalse(approval)

    def test_emi_exceeds_50_percent_salary(self):
        # Create existing loans that already use up 60% of salary in EMIs
        Loan.objects.create(
            customer=self.customer,
            loan_amount=500000,
            tenure=12,
            interest_rate=10,
            monthly_repayment=50000,  # 62.5% of salary
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )
        customer_obj, approval, interest_rate, corrected_rate, emi = check_loan_eligibility(
            self.customer.id, 100000, 10, 12
        )
        self.assertFalse(approval)


class TestRegisterView(APITestCase):
    def test_register_customer(self):
        data = {
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'age': 28,
            'monthly_income': 60000,
            'phone_number': 1234567890,
        }
        response = self.client.post('/register', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('customer_id', response.data)
        self.assertIn('approved_limit', response.data)
        # Approved limit should be rounded to lakh
        self.assertEqual(response.data['approved_limit'] % 100000, 0)

    def test_register_missing_fields(self):
        data = {'first_name': 'Bob'}
        response = self.client.post('/register', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestCheckEligibilityView(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='User',
            age=30,
            phone_number=1234567890,
            monthly_salary=50000,
            approved_limit=1800000,
        )

    def test_check_eligibility_existing_customer(self):
        data = {
            'customer_id': self.customer.id,
            'loan_amount': 100000,
            'interest_rate': 15,
            'tenure': 12,
        }
        response = self.client.post('/check-eligibility', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('approval', response.data)
        self.assertIn('corrected_interest_rate', response.data)

    def test_check_eligibility_nonexistent_customer(self):
        data = {
            'customer_id': 99999,
            'loan_amount': 100000,
            'interest_rate': 15,
            'tenure': 12,
        }
        response = self.client.post('/check-eligibility', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestCreateLoanView(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Loan',
            last_name='Taker',
            age=40,
            phone_number=9876543210,
            monthly_salary=100000,
            approved_limit=3600000,
        )

    def test_create_loan_approved(self):
        data = {
            'customer_id': self.customer.id,
            'loan_amount': 200000,
            'interest_rate': 15,
            'tenure': 24,
        }
        response = self.client.post('/create-loan', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['loan_approved'])
        self.assertIsNotNone(response.data['loan_id'])


class TestViewLoanView(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='View',
            last_name='Test',
            age=25,
            phone_number=1122334455,
            monthly_salary=70000,
            approved_limit=2500000,
        )
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=150000,
            tenure=12,
            interest_rate=12,
            monthly_repayment=13300,
            emis_paid_on_time=3,
            start_date=date.today(),
        )

    def test_view_loan(self):
        response = self.client.get(f'/view-loan/{self.loan.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('customer', response.data)
        self.assertIn('loan_amount', response.data)

    def test_view_loans_by_customer(self):
        response = self.client.get(f'/view-loans/{self.customer.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn('repayments_left', response.data[0])

    def test_view_nonexistent_loan(self):
        response = self.client.get('/view-loan/99999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)