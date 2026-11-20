import asyncio, os
from dotenv import load_dotenv
from telethon import TelegramClient
load_dotenv("/root/automation/telegram_channel_scraper/.env")
SESSION="/root/automation/telegram_channel_scraper/scraper_session"
api_id=int(os.environ["TELEGRAM_API_ID"]); api_hash=os.environ["TELEGRAM_API_HASH"]
CHANNELS=["sobytiyami","concerts_moscow"]
async def main():
    c=TelegramClient(SESSION, api_id, api_hash)
    await c.connect()
    if not await c.is_user_authorized():
        print("NOT AUTHORIZED"); return
    print("AUTHORIZED OK")
    for ch in CHANNELS:
        try:
            ent=await c.get_entity(ch)
            print(f"\n== {ch} -> {getattr(ent,'title',ch)} id={ent.id}")
            n=0
            async for m in c.iter_messages(ent, limit=3):
                txt=(m.text or "")[:90].replace("\n"," ")
                print(f"  msg {m.id} {m.date.date()} photo={bool(m.photo)} | {txt}")
                n+=1
            print(f"  fetched {n}")
        except Exception as e:
            print(f"  ERROR {ch}: {e}")
    await c.disconnect()
asyncio.run(main())
