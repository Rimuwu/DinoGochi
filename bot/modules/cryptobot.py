import time
from typing import Optional, Tuple
from aiocryptopay import AioCryptoPay, Networks
from bot.config import conf
from bot.modules.logs import log
from bot.models.other import Donation
from bot.modules.donation import give_reward
from bot.exec import bot

_cryptobot_client: Optional[AioCryptoPay] = None

def get_cryptobot_client() -> Optional[AioCryptoPay]:
    global _cryptobot_client
    if _cryptobot_client is not None:
        return _cryptobot_client
    
    token = getattr(conf, 'crypto_pay_token', '')
    if not token:
        log("CryptoBot token is not configured in config.json/env", lvl=2)
        return None
        
    network_str = getattr(conf, 'crypto_pay_network', 'mainnet')
    network = Networks.TEST_NET if network_str == 'testnet' else Networks.MAIN_NET
    
    _cryptobot_client = AioCryptoPay(token=token, network=network)
    log(f"CryptoBot client initialized on {network_str}", lvl=1)
    return _cryptobot_client

async def create_cryptobot_payment(
    user_id: int,
    user_first_name: str,
    product_key: str,
    col: str,
    usdt_amount: float,
    asset: str,
    lang: str
) -> Optional[Tuple[str, str]]:
    """
    Creates a CryptoBot invoice, saves a pending Donation to the database,
    and returns a tuple of (payment_url, donation_code).
    """
    client = get_cryptobot_client()
    if not client:
        return None

    # Generate unique donation code
    from bot.modules.data_format import random_code
    code = f"{random_code(5)}_{user_id}"

    # Get bot link for the paid button redirect
    bot_info = await bot.get_me()
    bot_url = f"https://t.me/{bot_info.username}"

    description = f"Purchase {product_key} x{col} in DinoGochi"

    # Convert amount if asset is TON
    charge_amount = usdt_amount
    if asset == 'TON':
        try:
            rates = await client.get_exchange_rates()
            ton_to_usd_rate = next((r.rate for r in rates if r.source == 'TON' and r.target == 'USD'), None)
            if ton_to_usd_rate:
                charge_amount = round(usdt_amount / ton_to_usd_rate, 6)
            else:
                charge_amount = round(usdt_amount / 7.0, 6)
        except Exception as e:
            log(f"Error converting to TON: {e}", lvl=2)
            charge_amount = round(usdt_amount / 7.0, 6)

    try:
        invoice = await client.create_invoice(
            amount=charge_amount,
            asset=asset,
            payload=code,
            description=description,
            paid_btn_name='openBot',
            paid_btn_url=bot_url
        )
        
        # Save pending Donation
        from datetime import datetime, timedelta
        expire_at = datetime.utcnow() + timedelta(days=1)

        data = Donation(
            code=code,
            userid=user_id,
            user_first_name=user_first_name,
            amount=int(usdt_amount * 100),  # store in cents/units for consistency
            product=product_key,
            issued_reward=False,
            send_notification=False,
            time=int(time.time()),
            col=col,
            donation_id=str(invoice.invoice_id),
            status="new",
            provider="cryptobot",
            expire_at=expire_at
        )
        await data.insert()
        
        return invoice.bot_invoice_url, code
    except Exception as e:
        log(f"Error creating CryptoBot payment for user {user_id}: {e}", lvl=3)
        return None

async def check_cryptobot_payment(code: str) -> bool:
    """
    Checks the status of a pending CryptoBot payment.
    If paid, processes the reward and returns True.
    """
    donation = await Donation.find_one(Donation.code == code)
    if not donation:
        return False
        
    if donation.status == "done":
        if not donation.issued_reward:
            await give_reward(donation.userid, donation.product, donation.col, donation.code)
        return True
        
    client = get_cryptobot_client()
    if not client:
        return False
        
    try:
        invoice = await client.get_invoices(invoice_ids=int(donation.donation_id))
        # get_invoices can return a single Invoice, list, or None
        if not invoice:
            return False
            
        if isinstance(invoice, list):
            invoice = invoice[0]
            
        if invoice.status == "paid":
            donation.status = "done"
            donation.expire_at = None  # Prevent TTL deletion
            await donation.save()
            await give_reward(donation.userid, donation.product, donation.col, donation.code)
            log(f"CryptoBot Payment: Manual check success for user {donation.userid}, product {donation.product}")
            return True
            
    except Exception as e:
        log(f"Error checking CryptoBot invoice {donation.donation_id}: {e}", lvl=3)
        
    return False
