import pytest

from app.compliance_engine import calculate_net_gst_liability, calculate_output_gst, calculate_tds


def test_calculate_output_gst_purchase_interstate_returns_input_type():
    result = calculate_output_gst(
        amount=50000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=True,
    )

    assert result == {
        "cgst": 0.0,
        "sgst": 0.0,
        "igst": 9000.0,
        "total_gst": 9000.0,
        "type": "input",
    }


def test_calculate_output_gst_invalid_transaction_type_raises():
    with pytest.raises(ValueError, match="transaction_type must be 'sale' or 'purchase'"):
        calculate_output_gst(
            amount=1000.0,
            gst_rate=18.0,
            transaction_type="other",
            is_interstate=False,
        )


def test_calculate_tds_threshold_and_vendor_rules():
    at_threshold = calculate_tds(amount=30000.0, vendor_type="professional")
    below_threshold = calculate_tds(amount=25000.0, vendor_type="professional")
    non_professional = calculate_tds(amount=50000.0, vendor_type="contractor")

    assert at_threshold["tds_rate"] == 0.0
    assert at_threshold["tds_amount"] == 0.0
    assert below_threshold["tds_rate"] == 0.0
    assert non_professional["tds_rate"] == 0.0


def test_net_gst_liability_can_be_negative_for_excess_itc():
    result = calculate_net_gst_liability(output_gst_total=5000.0, input_gst_total=7000.0)
    assert result == {"net_payable": -2000.0}
