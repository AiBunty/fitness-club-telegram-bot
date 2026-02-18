"""
Subscription Module Constants

Conversation states for subscription flow management
"""

# Conversation states for user subscription flow
SELECT_PLAN = 0
CONFIRM_PLAN = 1
SELECT_PAYMENT = 2
ENTER_UPI_VERIFICATION = 3
ENTER_SPLIT_UPI_AMOUNT = 7
ENTER_SPLIT_CONFIRM = 8

# Conversation states for admin approval flow
ADMIN_APPROVE_SUB = 4
ADMIN_ENTER_AMOUNT = 5
ADMIN_SELECT_DATE = 6
ADMIN_ENTER_BILL = 9
ADMIN_ENTER_UPI_RECEIVED = 10
ADMIN_ENTER_CASH_RECEIVED = 11
ADMIN_FINAL_CONFIRM = 12
