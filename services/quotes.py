import httpx
from xml.etree import ElementTree as ET
import logging

async def get_cbr_usd_rate() -> float | None:
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
        root = ET.fromstring(response.content)
        usd_node = root.find(".//Valute[CharCode='USD']")
        if usd_node is not None:
            value_str = usd_node.find('Value').text.replace(',', '.')
            return float(value_str)
    except Exception as e:
        logging.error(f"Error fetching CBR rate: {e}")
        return None

async def _get_moex_data(ticker: str) -> float | None:
    url = f"https://iss.moex.com/iss/engines/currency/markets/selt/securities/{ticker}.json"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        for block_name in ['marketdata', 'securities']:
            block = data.get(block_name, {})
            if block.get('data'):
                cols = block.get('columns', [])
                for row in block['data']:
                    if 'BOARDID' in cols and row[cols.index('BOARDID')] == 'CETS':
                        for field in ['LAST', 'MARKETPRICE', 'WAPRICE', 'PREVWAPRICE', 'PREVPRICE']:
                            if field in cols and (price := row[cols.index(field)]) is not None:
                                logging.info(f"Found price for {ticker} in {block_name}.{field}: {price}")
                                return float(price)
    except Exception as e:
        logging.error(f"Error fetching MOEX data for {ticker}: {e}")
    logging.warning(f"Could not find any price for {ticker}")
    return None

async def get_moex_usd_rate() -> float | None:
    return await _get_moex_data('USD000UTSTOM')

async def get_moex_gold_rub_rate() -> float | None:
    return await _get_moex_data('GLDRUB_TOM')