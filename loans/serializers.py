from rest_framework import serializers
from .models import Customer, Loan


class CustomerRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField()
    monthly_income = serializers.IntegerField()
    phone_number = serializers.IntegerField()


class CustomerRegistrationResponseSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    monthly_income = serializers.DecimalField(
        source='monthly_salary', max_digits=15, decimal_places=2
    )

    class Meta:
        model = Customer
        fields = ['customer_id', 'name', 'age', 'monthly_income', 'approved_limit', 'phone_number']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['customer_id'] = instance.id
        return data


class CheckEligibilityRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField()
    interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()


class CheckEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.FloatField()
    corrected_interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()
    monthly_installment = serializers.FloatField()


class CreateLoanRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField()
    interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()


class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField(allow_blank=True)
    monthly_installment = serializers.FloatField()


class CustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'age']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data


class ViewLoanSerializer(serializers.ModelSerializer):
    customer = CustomerDetailSerializer()

    class Meta:
        model = Loan
        fields = ['id', 'customer', 'loan_amount', 'interest_rate', 'monthly_repayment', 'tenure']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['loan_id'] = data.pop('id')
        data['monthly_installment'] = data.pop('monthly_repayment')
        return data


class LoanListItemSerializer(serializers.ModelSerializer):
    repayments_left = serializers.IntegerField()

    class Meta:
        model = Loan
        fields = ['id', 'loan_amount', 'interest_rate', 'monthly_repayment', 'repayments_left']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['loan_id'] = data.pop('id')
        data['monthly_installment'] = data.pop('monthly_repayment')
        return data