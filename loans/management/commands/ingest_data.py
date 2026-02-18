"""
Management command to trigger data ingestion via Celery tasks.
"""
import os
from django.core.management.base import BaseCommand
from loans.tasks import ingest_customer_data, ingest_loan_data


class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files using background tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customer-file',
            type=str,
            # default='/app/data/customer_data.xlsx',
            default='data/customer_data.xlsx',
            help='Path to customer data Excel file'
        )
        # C:\Users\mdans\Desktop\CreditApprovalSystem\data\customer_data.xlsx
        parser.add_argument(
            '--loan-file',
            type=str,
            # default='/app/data/loan_data.xlsx',
            default='data/loan_data.xlsx',
            help='Path to loan data Excel file'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run synchronously instead of via Celery'
        )

    def handle(self, *args, **options):
        customer_file = options['customer_file']
        loan_file = options['loan_file']
        sync = options['sync']

        if not os.path.exists(customer_file):
            self.stdout.write(
                self.style.WARNING(f'Customer file not found: {customer_file}')
            )
        else:
            self.stdout.write(f'Ingesting customer data from: {customer_file}')
            if sync:
                result = ingest_customer_data(customer_file)
                self.stdout.write(
                    self.style.SUCCESS(f'Customer ingestion complete: {result}')
                )
            else:
                task = ingest_customer_data.delay(customer_file)
                self.stdout.write(
                    self.style.SUCCESS(f'Customer ingestion task queued: {task.id}')
                )

        if not os.path.exists(loan_file):
            self.stdout.write(
                self.style.WARNING(f'Loan file not found: {loan_file}')
            )
        else:
            self.stdout.write(f'Ingesting loan data from: {loan_file}')
            if sync:
                result = ingest_loan_data(loan_file)
                self.stdout.write(
                    self.style.SUCCESS(f'Loan ingestion complete: {result}')
                )
            else:
                task = ingest_loan_data.delay(loan_file)
                self.stdout.write(
                    self.style.SUCCESS(f'Loan ingestion task queued: {task.id}')
                )