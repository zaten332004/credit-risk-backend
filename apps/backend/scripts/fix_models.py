#!/usr/bin/env python3
"""Fix all Integer IDs to BigInteger to match SQL Server schema."""

import re

with open('/root/models.py', 'r') as f:
    content = f.read()

# Replacements needed for FK/PK columns
replacements = [
    ('schedule_id = Column(Integer, primary_key', 'schedule_id = Column(BigInteger, primary_key'),
    ('facility_id = Column(Integer, ForeignKey("Loan_Facility', 'facility_id = Column(BigInteger, ForeignKey("Loan_Facility'),
    ('payment_id = Column(Integer, primary_key', 'payment_id = Column(BigInteger, primary_key'),
    ('delinquency_id = Column(Integer, primary_key', 'delinquency_id = Column(BigInteger, primary_key'),
    ('alert_id = Column(Integer, primary_key', 'alert_id = Column(BigInteger, primary_key'),
    ('customer_id = Column(Integer, ForeignKey("Customer', 'customer_id = Column(BigInteger, ForeignKey("Customer'),
    ('subscription_id = Column(Integer, primary_key', 'subscription_id = Column(BigInteger, primary_key'),
    ('user_id = Column(Integer, ForeignKey("User.user_id")', 'user_id = Column(BigInteger, ForeignKey("User.user_id")'),
    ('indicator_id = Column(Integer, primary_key', 'indicator_id = Column(BigInteger, primary_key'),
    ('model_id = Column(Integer, primary_key', 'model_id = Column(BigInteger, primary_key'),
    ('model_id = Column(Integer, ForeignKey("LINEAR_MODEL', 'model_id = Column(BigInteger, ForeignKey("LINEAR_MODEL'),
    ('coefficient_id = Column(Integer, primary_key', 'coefficient_id = Column(BigInteger, primary_key'),
    ('prediction_id = Column(Integer, primary_key', 'prediction_id = Column(BigInteger, primary_key'),
    ('prediction_id = Column(Integer, ForeignKey("RISK_PREDICTION', 'prediction_id = Column(BigInteger, ForeignKey("RISK_PREDICTION'),
    ('application_id = Column(Integer, ForeignKey("Loan_Application', 'application_id = Column(BigInteger, ForeignKey("Loan_Application'),
    ('explain_id = Column(Integer, primary_key', 'explain_id = Column(BigInteger, primary_key'),
    ('chat_id = Column(Integer, primary_key', 'chat_id = Column(BigInteger, primary_key'),
    ('user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)\n    created_at = Column(DateTime',
     'user_id = Column(BigInteger, ForeignKey("User.user_id"), nullable=False)\n    created_at = Column(DateTime'),
    ('snapshot_id = Column(Integer, primary_key', 'snapshot_id = Column(BigInteger, primary_key'),
    ('audit_id = Column(Integer, primary_key', 'audit_id = Column(BigInteger, primary_key'),
    ('entity_id = Column(Integer, nullable=True)', 'entity_id = Column(BigInteger, nullable=True)'),
]

for old, new in replacements:
    content = content.replace(old, new)

print(content)
