from bot.models.other import Donation
from bot.modules.donation import give_reward
from bot.modules.cryptobot import get_cryptobot_client
from bot.taskmanager import add_task
from bot.config import conf
from bot.modules.logs import log

async def check_pending_cryptobot_payments():
    pending_donations = await Donation.find(Donation.status == "new").to_list()
    if not pending_donations:
        return
        
    client = get_cryptobot_client()
    if not client:
        return
        
    invoice_ids = []
    donation_map = {}
    for donation in pending_donations:
        if donation.donation_id and donation.donation_id.isdigit():
            inv_id = int(donation.donation_id)
            invoice_ids.append(inv_id)
            donation_map[inv_id] = donation

    if not invoice_ids:
        return
        
    try:
        invoices = await client.get_invoices(invoice_ids=invoice_ids)
        if not invoices:
            return
            
        if not isinstance(invoices, list):
            invoices = [invoices]
            
        for inv in invoices:
            if inv.status == "paid":
                donation = donation_map.get(inv.invoice_id)
                if donation and (donation.status != "done" or not donation.issued_reward):
                    donation.status = "done"
                    donation.expire_at = None  # Prevent TTL deletion
                    await donation.save()
                    await give_reward(donation.userid, donation.product, donation.col, donation.code)
                    log(f"CryptoBot Polling: Payment success for user {donation.userid}, product {donation.product} x{donation.col}", lvl=1)
    except Exception as e:
        log(f"Error checking pending CryptoBot payments: {e}", lvl=3)

if __name__ != '__main__':
    if conf.active_tasks:
        # Run every 15 seconds
        add_task(check_pending_cryptobot_payments, repeat_time=15.0, delay=5.0)
