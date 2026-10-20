import os
import asyncio
from pyrogram import Client, filters
from aiohttp import web

API_ID = 36950825
API_HASH = "360fce1d012b60673eaff777c981f458"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8952737540:AAHA0AWeAv67yKiZ4-rX6M_p-ElRxvsC9p8")
PORT = int(os.environ.get("PORT", 8080))
KOYEB_URL = os.environ.get("KOYEB_URL", "")

app_bot = Client("koyeb_stream_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def stream_handler(request):
    chat_id = int(request.match_info.get('chat_id'))
    message_id = int(request.match_info.get('message_id'))
    
    try:
        msg = await app_bot.get_messages(chat_id, message_id)
        media = msg.video or msg.document
        if not media:
            return web.Response(text="File Not Found", status=404)
            
        file_size = media.file_size
        range_header = request.headers.get('Range')
        
        start = 0
        end = file_size - 1
        if range_header:
            try:
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0])
                if range_match[1]:
                    end = int(range_match[1])
            except:
                pass
                
        length = end - start + 1
        status_code = 206 if range_header else 200
        
        response = web.StreamResponse(status=status_code, reason='Partial Content' if status_code == 206 else 'OK')
        response.content_type = media.mime_type or 'video/mp4'
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response.headers['Content-Length'] = str(length)
        
        await response.prepare(request)
        
        async for chunk in app_bot.stream_media(msg, offset=start, limit=length):
            await response.write(chunk)
            
        return response
    except Exception as e:
        return web.Response(text=f"Error: {str(e)}", status=500)

@app_bot.on_message(filters.video | filters.document)
async def media_receiver(client, message):
    chat_id = message.chat.id
    message_id = message.id
    file_name = message.video.file_name if message.video else (message.document.file_name if message.document else "video.mp4")
    
    host_url = KOYEB_URL if KOYEB_URL else f"http://localhost:{PORT}"
    if not host_url.startswith("http"):
        host_url = f"https://{host_url}"
        
    stream_url = f"{host_url}/stream/{chat_id}/{message_id}/{file_name}"
    
    response_text = (
        f"🎬 **Direct Stream Link Generated!**\n\n"
        f"📁 **File:** `{file_name}`\n\n"
        f"🔗 **Stream/Download URL:**\n`{stream_url}`\n\n"
        f"💡 Copy this link and paste in 1DM or VLC Player!"
    )
    await message.reply_text(response_text)

@app_bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 Send me any video file to get Koyeb Stream Link!")

async def main():
    app = web.Application()
    app.add_routes([web.get('/stream/{chat_id}/{message_id}/{file_name}', stream_handler)])
    app.add_routes([web.get('/', lambda r: web.Response(text="Bot is Running on Koyeb!"))])
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    await app_bot.start()
    print("Bot is live!")
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
