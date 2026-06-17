import io
from decimal import Decimal

from ofxparse import OfxParser

from app.importers.csv_importer import ParsedRow


def parse(content: bytes) -> list[ParsedRow]:
    ofx = OfxParser.parse(io.BytesIO(content))
    parsed: list[ParsedRow] = []
    for txn in ofx.account.statement.transactions:
        transaction_date = (txn.user_date or txn.date).date()
        post_date = txn.date.date() if txn.date else None
        parsed.append(
            ParsedRow(
                transaction_date=transaction_date,
                amount=Decimal(str(txn.amount)),
                payee_raw=txn.payee or None,
                memo=txn.memo or None,
                post_date=post_date,
                external_id=txn.id or None,
            )
        )
    return parsed
