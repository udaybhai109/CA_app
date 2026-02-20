from app.compliance_engine import calculate_net_gst_liability, calculate_output_gst


def test_sale_intra_state_gst_example():
    sale_gst = calculate_output_gst(
        amount=100000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )

    assert sale_gst["cgst"] == 9000.0
    assert sale_gst["sgst"] == 9000.0
    assert sale_gst["igst"] == 0.0
    assert sale_gst["total_gst"] == 18000.0
    assert sale_gst["type"] == "output"


def test_purchase_intra_state_and_net_liability_example():
    sale_gst = calculate_output_gst(
        amount=100000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )
    purchase_gst = calculate_output_gst(
        amount=50000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
    )

    assert purchase_gst["cgst"] == 4500.0
    assert purchase_gst["sgst"] == 4500.0
    assert purchase_gst["igst"] == 0.0
    assert purchase_gst["total_gst"] == 9000.0
    assert purchase_gst["type"] == "input"

    net = calculate_net_gst_liability(
        output_gst_total=sale_gst["total_gst"],
        input_gst_total=purchase_gst["total_gst"],
    )

    assert net["net_payable"] == 9000.0
