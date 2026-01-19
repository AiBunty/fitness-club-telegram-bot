"""
Event registry: immutable event keys and allowed placeholders per event.
"""
EVENT_KEYS = {
    'USER_WELCOME',
    'ATTENDANCE_SUCCESS',
    'ATTENDANCE_DENIED_UNPAID',
    'ATTENDANCE_DENIED_GEOFENCE',
    'SUBSCRIPTION_PAID',
    'SUBSCRIPTION_PARTIAL',
    'SUBSCRIPTION_CREDIT',
    'PAYMENT_REMINDER_1',
    'PAYMENT_REMINDER_2',
    'PAYMENT_FINAL_NOTICE',
    'STORE_ORDER_PLACED',
    'STORE_ORDER_PARTIAL',
    'STORE_ORDER_CREDIT',
    'STORE_ORDER_COMPLETED',
    'ADMIN_OVERRIDE_APPLIED'
}

# Allowed placeholders per event (keys that templates may use)
ALLOWED_PLACEHOLDERS = {
    'USER_WELCOME': {'name'},
    'ATTENDANCE_SUCCESS': {'name', 'class_name', 'time'},
    'ATTENDANCE_DENIED_UNPAID': {'name', 'due_amount'},
    'ATTENDANCE_DENIED_GEOFENCE': {'name'},
    'SUBSCRIPTION_PAID': {'name', 'amount'},
    'SUBSCRIPTION_PARTIAL': {'name', 'amount', 'balance'},
    'SUBSCRIPTION_CREDIT': {'name', 'amount', 'terms'},
    'PAYMENT_REMINDER_1': {'name', 'amount', 'due_date'},
    'PAYMENT_REMINDER_2': {'name', 'amount', 'due_date'},
    'PAYMENT_FINAL_NOTICE': {'name', 'amount', 'due_date'},
    'STORE_ORDER_PLACED': {'name', 'order_id', 'amount'},
    'STORE_ORDER_PARTIAL': {'name', 'order_id', 'amount', 'balance'},
    'STORE_ORDER_CREDIT': {'name', 'order_id', 'amount', 'terms'},
    'STORE_ORDER_COMPLETED': {'name', 'order_id'},
    'ADMIN_OVERRIDE_APPLIED': {'admin_name', 'reason'}
}

# Default templates (fallbacks to preserve current behavior)
DEFAULT_TEMPLATES = {
    'USER_WELCOME': "🏋️ *Welcome to Wani's Level Up Club!* 💪\n\nHey there, Champion! 👋\n\nLet's get started! Tap below to register and begin your Level Up journey today.",
    'ATTENDANCE_SUCCESS': "Hi {{name}}, your attendance for {{class_name}} at {{time}} is confirmed.",
    'ATTENDANCE_DENIED_UNPAID': "Hi {{name}}, attendance denied — outstanding due: {{due_amount}}.",
    'ATTENDANCE_DENIED_GEOFENCE': "Hi {{name}}, you're outside the allowed location for check-in.",
    'SUBSCRIPTION_PAID': "Thanks {{name}} — payment received: {{amount}}.",
    'PAYMENT_REMINDER_1': "Hi {{name}}, friendly reminder: you owe {{amount}} due by {{due_date}}.",
    'STORE_ORDER_PLACED': "Order {{order_id}} placed. Total: {{amount}}.",
}
