def calculate_output_gst(
    amount: float, gst_rate: float, transaction_type: str, is_interstate: bool
) -> dict:
    gst_base = amount * gst_rate / 100

    if is_interstate:
        cgst = 0.0
        sgst = 0.0
        igst = gst_base
    else:
        cgst = gst_base / 2
        sgst = gst_base / 2
        igst = 0.0

    if transaction_type == "sale":
        gst_type = "output"
    elif transaction_type == "purchase":
        gst_type = "input"
    else:
        raise ValueError("transaction_type must be 'sale' or 'purchase'")

    total_gst = cgst + sgst + igst
    return {
        "cgst": float(cgst),
        "sgst": float(sgst),
        "igst": float(igst),
        "total_gst": float(total_gst),
        "type": gst_type,
    }


def calculate_net_gst_liability(output_gst_total: float, input_gst_total: float) -> dict:
    return {"net_payable": float(output_gst_total - input_gst_total)}


def calculate_tds(amount: float, vendor_type: str) -> dict:
    if vendor_type == "professional" and amount > 30000:
        tds_rate = 10
    else:
        tds_rate = 0

    tds_amount = amount * tds_rate / 100
    net_payable = amount - tds_amount

    return {
        "tds_rate": float(tds_rate),
        "tds_amount": float(tds_amount),
        "net_payable": float(net_payable),
    }
