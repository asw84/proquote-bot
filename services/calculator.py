from decimal import Decimal, getcontext

getcontext().prec = 28
OUNCE_IN_GRAMS = Decimal("31.1003")

def calculate_final_deal(params: dict) -> dict | None:
    try:
        weight_kg = Decimal(str(params['weight']))
        base_supplier_price_usd = Decimal(str(params['base_supplier_price_usd']))
        buyer_discount = Decimal(str(params['buyer_discount_choice']))
        cbr_rate = Decimal(str(params['cbr_rate']))
        moex_usd_rate = Decimal(str(params['moex_usd_rate']))
        comm_usdt = Decimal(str(params.get('commission_usdt', '0')))
        comm_delivery = Decimal(str(params['commission_delivery']))
        comm_courier = Decimal(str(params['commission_courier']))
        comm_agent = Decimal(str(params['commission_agent']))
        comm_partner = Decimal(str(params['commission_partner']))
        
        buyer_price = base_supplier_price_usd * (Decimal('1') + buyer_discount / Decimal('100'))
        profit_price_diff = buyer_price - base_supplier_price_usd
        profit_rate_diff = base_supplier_price_usd * (cbr_rate - moex_usd_rate) / cbr_rate
        total_commission_percent = comm_usdt + comm_delivery - comm_courier - comm_agent + comm_partner
        profit_commission = buyer_price * total_commission_percent / Decimal("100")
        total_profit_per_ounce_usd = profit_price_diff + profit_rate_diff + profit_commission
        
        ounces_in_batch = (weight_kg * 1000) / OUNCE_IN_GRAMS
        total_profit_usd = total_profit_per_ounce_usd * ounces_in_batch
        total_profit_rub = total_profit_usd * cbr_rate
        total_cost_usd = base_supplier_price_usd * ounces_in_batch
        profit_percent = (total_profit_usd / total_cost_usd * 100) if total_cost_usd != 0 else Decimal(0)
        client_price_per_ounce_usd = base_supplier_price_usd + total_profit_per_ounce_usd
        total_client_price_usd = client_price_per_ounce_usd * ounces_in_batch
        total_client_price_rub = total_client_price_usd * cbr_rate

        return {
            "total_profit_usd": total_profit_usd,
            "total_profit_rub": total_profit_rub,
            "profit_percent": profit_percent,
            "total_client_price_rub": total_client_price_rub,
            "client_price_gram_rub": (total_client_price_rub / (weight_kg * 1000)),
            "weight_kg": weight_kg,
            "buyer_price_usd_ounce": buyer_price,
            "base_supplier_price_usd_ounce": base_supplier_price_usd,
            "cbr_rate": cbr_rate,
            "moex_usd_rate": moex_usd_rate,
        }
    except Exception:
        return None