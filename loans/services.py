"""
Core business logic for credit approval system.
"""
import math
from datetime import date
from decimal import Decimal

from .models import Customer, Loan


def calculate_approved_limit(monthly_salary: int) -> int:
    """
    Calculate approved limit: 36 * monthly_salary, rounded to nearest lakh (100,000).
    """
    raw = 36 * monthly_salary
    # Round to nearest lakh
    rounded = round(raw / 100000) * 100000
    return rounded


def calculate_monthly_installment(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    Calculate EMI using compound interest formula:
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r = monthly interest rate, n = tenure in months
    """
    if annual_rate == 0:
        return principal / tenure_months

    monthly_rate = annual_rate / (12 * 100)
    emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / \
          ((1 + monthly_rate) ** tenure_months - 1)
    return round(emi, 2)


def calculate_credit_score(customer: Customer) -> int:
    """
    Calculate credit score out of 100 based on historical loan data.

    Components:
    1. Past loans paid on time
    2. Number of loans taken in past
    3. Loan activity in current year
    4. Loan approved volume
    5. If current loans > approved limit, score = 0
    """
    loans = customer.loans.all()

    # Component 5: If sum of current loans > approved limit, return 0
    current_loans = loans.filter(end_date__gte=date.today())
    total_current_loan_amount = sum(float(l.loan_amount) for l in current_loans)

    if total_current_loan_amount > float(customer.approved_limit):
        return 0

    total_loans = loans.count()
    if total_loans == 0:
        return 50  # Default score for new customers

    # Component 1: Past loans paid on time (35 points)
    total_emis = sum(l.tenure for l in loans)
    total_paid_on_time = sum(l.emis_paid_on_time for l in loans)
    on_time_ratio = total_paid_on_time / total_emis if total_emis > 0 else 0
    on_time_score = on_time_ratio * 35

    # Component 2: Number of loans taken in past (20 points)
    # Fewer loans = better; max benefit at <= 3 loans
    if total_loans <= 3:
        loan_count_score = 20
    elif total_loans <= 6:
        loan_count_score = 15
    elif total_loans <= 10:
        loan_count_score = 10
    else:
        loan_count_score = 5

    # Component 3: Loan activity in current year (20 points)
    current_year = date.today().year
    current_year_loans = loans.filter(start_date__year=current_year).count()
    if current_year_loans == 0:
        activity_score = 20
    elif current_year_loans <= 2:
        activity_score = 15
    elif current_year_loans <= 4:
        activity_score = 10
    else:
        activity_score = 5

    # Component 4: Loan approved volume (25 points)
    total_loan_volume = sum(float(l.loan_amount) for l in loans)
    approved_limit = float(customer.approved_limit)
    volume_ratio = total_loan_volume / approved_limit if approved_limit > 0 else 1
    if volume_ratio <= 0.5:
        volume_score = 25
    elif volume_ratio <= 1.0:
        volume_score = 20
    elif volume_ratio <= 2.0:
        volume_score = 10
    else:
        volume_score = 5

    total_score = on_time_score + loan_count_score + activity_score + volume_score
    return min(100, int(total_score))


def check_loan_eligibility(customer_id: int, loan_amount: float, interest_rate: float, tenure: int):
    """
    Check if a loan can be approved based on credit score.
    Returns: (approval, corrected_interest_rate, monthly_installment)
    """
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return None, False, interest_rate, interest_rate, 0

    # Check if sum of all current EMIs > 50% of monthly salary
    current_loans = customer.loans.filter(end_date__gte=date.today())
    total_current_emis = sum(float(l.monthly_repayment) for l in current_loans)
    monthly_salary = float(customer.monthly_salary)

    if total_current_emis > 0.5 * monthly_salary:
        monthly_installment = calculate_monthly_installment(loan_amount, interest_rate, tenure)
        return customer, False, interest_rate, interest_rate, monthly_installment

    credit_score = calculate_credit_score(customer)

    # Determine approval and corrected interest rate based on credit score
    approval = False
    corrected_rate = interest_rate

    if credit_score > 50:
        approval = True
        corrected_rate = interest_rate
    elif 30 < credit_score <= 50:
        if interest_rate > 12:
            approval = True
            corrected_rate = interest_rate
        else:
            approval = True
            corrected_rate = 12.0
    elif 10 < credit_score <= 30:
        if interest_rate > 16:
            approval = True
            corrected_rate = interest_rate
        else:
            approval = True
            corrected_rate = 16.0
    else:  # credit_score <= 10
        approval = False
        corrected_rate = interest_rate

    monthly_installment = calculate_monthly_installment(loan_amount, corrected_rate, tenure)
    return customer, approval, interest_rate, corrected_rate, monthly_installment