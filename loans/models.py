from django.db import models


class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    phone_number = models.BigIntegerField()
    monthly_salary = models.DecimalField(max_digits=15, decimal_places=2)
    approved_limit = models.DecimalField(max_digits=15, decimal_places=2)
    current_debt = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'customers'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    tenure = models.IntegerField(help_text="Tenure in months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_repayment = models.DecimalField(max_digits=15, decimal_places=2)
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'loans'

    def __str__(self):
        return f"Loan {self.id} - Customer {self.customer_id}"

    @property
    def repayments_left(self):
        """Calculate remaining EMIs."""
        return max(0, self.tenure - self.emis_paid_on_time)