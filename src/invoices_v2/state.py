"""
Invoice v2 - Conversation States
"""
from enum import IntEnum


class InvoiceV2State(IntEnum):
    """Conversation states for Invoice v2"""
    SEARCH_USER = 1
    SELECT_USER = 2
    ITEM_MODE = 3
    SEARCH_STORE_ITEM = 4
    SELECT_STORE_ITEM = 5
    CUSTOM_ITEM_NAME = 6
    CUSTOM_ITEM_RATE = 7
    ITEM_QUANTITY = 8
    ITEM_DISCOUNT = 9
    ITEM_CONFIRM = 10
    SHIPPING = 11
    FINAL_REVIEW = 12
    SEND_INVOICE = 13
