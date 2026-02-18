import logging
from datetime import date

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Customer, Loan
from .serializers import (
    CheckEligibilityRequestSerializer,
    CreateLoanRequestSerializer,
    CustomerRegistrationSerializer,
    LoanListItemSerializer,
    ViewLoanSerializer,
)
from .services import (
    calculate_approved_limit,
    calculate_monthly_installment,
    check_loan_eligibility,
)

logger = logging.getLogger(__name__)


class RegisterCustomerView(APIView):
    """
    POST /register
    Register a new customer.
    """
    @extend_schema(
        request=CustomerRegistrationSerializer,
        responses={201: {
            'type': 'object',
            'properties': {
                'customer_id': {'type': 'integer'},
                'name': {'type': 'string'},
                'age': {'type': 'integer'},
                'monthly_income': {'type': 'number'},
                'approved_limit': {'type': 'number'},
                'phone_number': {'type': 'integer'},
            }
        }}
    )

    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        approved_limit = calculate_approved_limit(data['monthly_income'])

        customer = Customer.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            phone_number=data['phone_number'],
            monthly_salary=data['monthly_income'],
            approved_limit=approved_limit,
        )

        return Response(
            {
                'customer_id': customer.id,
                'name': f"{customer.first_name} {customer.last_name}",
                'age': customer.age,
                'monthly_income': float(customer.monthly_salary),
                'approved_limit': float(customer.approved_limit),
                'phone_number': customer.phone_number,
            },
            status=status.HTTP_201_CREATED
        )


class CheckEligibilityView(APIView):
    """
    POST /check-eligibility
    Check loan eligibility based on credit score.
    """
    @extend_schema(
        request=CheckEligibilityRequestSerializer,
        responses={200: {
            'type': 'object',
            'properties': {
                'customer_id': {'type': 'integer'},
                'approval': {'type': 'boolean'},
                'interest_rate': {'type': 'number'},
                'corrected_interest_rate': {'type': 'number'},
                'tenure': {'type': 'integer'},
                'monthly_installment': {'type': 'number'},
            }
        }}
    )

    def post(self, request):
        serializer = CheckEligibilityRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            customer = Customer.objects.get(id=data['customer_id'])
        except Customer.DoesNotExist:
            return Response(
                {'error': f"Customer with id {data['customer_id']} not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        customer_obj, approval, interest_rate, corrected_rate, monthly_installment = check_loan_eligibility(
            data['customer_id'],
            data['loan_amount'],
            data['interest_rate'],
            data['tenure']
        )

        return Response(
            {
                'customer_id': data['customer_id'],
                'approval': approval,
                'interest_rate': interest_rate,
                'corrected_interest_rate': corrected_rate,
                'tenure': data['tenure'],
                'monthly_installment': monthly_installment,
            },
            status=status.HTTP_200_OK
        )


class CreateLoanView(APIView):
    """
    POST /create-loan
    Process and create a new loan if eligible.
    """
    @extend_schema(
        request=CreateLoanRequestSerializer,
        responses={201: {
            'type': 'object',
            'properties': {
                'loan_id': {'type': 'integer', 'nullable': True},
                'customer_id': {'type': 'integer'},
                'loan_approved': {'type': 'boolean'},
                'message': {'type': 'string'},
                'monthly_installment': {'type': 'number'},
            }
        }}
    )

    def post(self, request):
        serializer = CreateLoanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            customer = Customer.objects.get(id=data['customer_id'])
        except Customer.DoesNotExist:
            return Response(
                {'error': f"Customer with id {data['customer_id']} not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        customer_obj, approval, interest_rate, corrected_rate, monthly_installment = check_loan_eligibility(
            data['customer_id'],
            data['loan_amount'],
            data['interest_rate'],
            data['tenure']
        )

        if not approval:
            return Response(
                {
                    'loan_id': None,
                    'customer_id': data['customer_id'],
                    'loan_approved': False,
                    'message': 'Loan not approved based on credit score and eligibility criteria.',
                    'monthly_installment': monthly_installment,
                },
                status=status.HTTP_200_OK
            )

        # Create the loan
        loan = Loan.objects.create(
            customer=customer,
            loan_amount=data['loan_amount'],
            tenure=data['tenure'],
            interest_rate=corrected_rate,
            monthly_repayment=monthly_installment,
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=None,
        )

        return Response(
            {
                'loan_id': loan.id,
                'customer_id': data['customer_id'],
                'loan_approved': True,
                'message': 'Loan approved successfully.',
                'monthly_installment': monthly_installment,
            },
            status=status.HTTP_201_CREATED
        )


class ViewLoanView(APIView):
    """
    GET /view-loan/<loan_id>
    View loan details along with customer info.
    """
    @extend_schema(responses={200: ViewLoanSerializer})

    def get(self, request, loan_id):
        loan = get_object_or_404(Loan, id=loan_id)
        serializer = ViewLoanSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ViewLoansByCustomerView(APIView):
    """
    GET /view-loans/<customer_id>
    View all current loans for a customer.
    """
    @extend_schema(responses={200: LoanListItemSerializer(many=True)})

    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, id=customer_id)
        loans = Loan.objects.filter(customer=customer)
        serializer = LoanListItemSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)