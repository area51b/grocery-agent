"""Page selectors for shengsiong.com.sg.

These are calibration points, not stable facts: the site's DOM is only known
from manual inspection, and every selector here must be confirmed against the
live site during tasks 4.2-4.5. All selectors live in this one module so a
site redesign is a single-file fix.
"""

# Elements that indicate the login form is being shown.
LOGIN_INDICATORS = [
    "input[type='password']",
    "form[action*='login' i]",
    "text=Login",
]

# Elements that indicate an authenticated session.
LOGGED_IN_INDICATORS = [
    "text=Sign Out",
    "text=Logout",
    "text=Log Out",
    "text=My Account",
]

# The Transactions page lives at a stable URL (confirmed 2026-11-11).
ORDER_HISTORY_PATH = "account/order-history"

# Tabs / sections for the two transaction kinds.
ONLINE_TRANSACTIONS_TAB = "text=Online"
INSTORE_TRANSACTIONS_TAB = "text=In-Store"

# A single transaction row in the listing. Calibrate on the live site.
TRANSACTION_ROW = "[class*='transaction']"

# Row fields, relative to a transaction row.
TRANSACTION_ID = "[class*='id'], [data-transaction-id]"
TRANSACTION_DATE = "[class*='date']"
TRANSACTION_STORE = "[class*='store'], [class*='location']"
TRANSACTION_TOTAL = "[class*='total']"

# The control that opens a transaction's detail view.
TRANSACTION_DETAIL_LINK = "a:has-text('View'), button:has-text('View')"

# Fields inside a transaction detail view.
DETAIL_ITEM = "[class*='item']"
DETAIL_PRODUCT_NAME = "[class*='name']"
DETAIL_QUANTITY = "[class*='qty'], [class*='quantity']"
DETAIL_UNIT_PRICE = "[class*='unit']"
DETAIL_LINE_TOTAL = "[class*='total']"
DETAIL_PROMOTION = "[class*='promo']"
DETAIL_DISCOUNT = "[class*='discount']"
