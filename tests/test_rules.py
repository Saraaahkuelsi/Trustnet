import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rules import apply_business_rules 
def test_transaction_normale():
    tx = {
        "Country": "USA",
        "Category": "Electronics",
        "Value": 145000,
        "Quantity": 12,
        "Weight": 420,
        "Payment_Terms": "NET30",
        "Country_Origine": "South Korea"
    }
    violations = apply_business_rules(tx)
    assert len(violations) == 0

def test_pays_embargo():
    tx = {
        "Country": "Iran",
        "Category": "Chemicals",
        "Value": 50000,
        "Quantity": 10,
        "Weight": 300,
        "Payment_Terms": "CASH",
        "Country_Origine": "Unknown"
    }
    violations = apply_business_rules(tx)
    assert len(violations) > 0

def test_valeur_zero():
    tx = {
        "Country": "Germany",
        "Category": "Machinery",
        "Value": 0,
        "Quantity": 5,
        "Weight": 200,
        "Payment_Terms": "NET60",
        "Country_Origine": "Germany"
    }
    violations = apply_business_rules(tx)
    assert any("0" in v for v in violations)

def test_valeur_zero():
    tx = {
        "Country": "Germany",
        "Category": "Machinery",
        "Value": 0,
        "Quantity": 5,
        "Weight": 200,
        "Payment_Terms": "NET60",
        "Country_Origine": "Germany"
    }
    violations = apply_business_rules(tx)
    assert any("0" in v for v in violations)


def test_cash_grosse_valeur():
    tx = {
        "Country": "France",
        "Category": "Clothing",
        "Value": 200000,
        "Quantity": 10,
        "Weight": 300,
        "Payment_Terms": "CASH",
        "Country_Origine": "France"
    }
    violations = apply_business_rules(tx)
    assert any("cash" in v.lower() for v in violations)
