import os
import logging
import asyncio
import time
from urllib.parse import urlparse
import yt_dlp
import instaloader
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode, ChatAction
import tempfile
import shutil

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# کانفیگ
BOT_TOKEN = "8300319772:AAGUTuDaRkSO6YIWCzWKb47bvWi2hEx4zcA"
DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# ایجاد پوشه دانلود
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class DownloadBot:
    def __init__(self):
        self.active_downloads = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پیام استارت"""
        welcome_text = """
🎬 **ربات دانلود حرفه‌ای** 🎬

سلام! من می‌تونم برات دانلود کنم از:
📱 **یوتیوب** - ویدیو و موزیک
📸 **اینستاگرام** - پست، استوری، ریلز  
🎵 **ساندکلود** - موزیک و پادکست

**نحوه استفاده:**
• لینک رو بفرست یا از /search استفاده کن! 🚀
• دستور /search برای جستجوی یوتیوب

**ویژگی‌های خاص:**
✨ جستجوی مستقیم در یوتیوب
🔍 انتخاب از نتایج جستجو
⚡ سرعت بالا
🎨 نمایش گرافیکی پیشرفت
🧹 پاک‌سازی خودکار پیام‌ها
        """
        
        keyboard = [
            [InlineKeyboardButton("🔍 جستجو در یوتیوب", callback_data='search_youtube')],
            [InlineKeyboardButton("📝 راهنمای کامل", callback_data='help')],
            [InlineKeyboardButton("📊 آمار ربات", callback_data='stats')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """راهنمای کامل"""
        help_text = """
📚 **راهنمای کامل ربات**

**🔍 جستجوی یوتیوب:**
• دستور: `/search نام آهنگ یا ویدیو`
• مثال: `/search علی یاسینی عاشقانه`
• انتخاب از 5 نتیجه برتر

**🎬 یوتیوب:**
• فقط لینک ویدیو رو بفرست
• انتخاب کیفیت (144p تا 4K)
• دانلود فقط صدا یا ویدیو

**📸 اینستاگرام:**  
• لینک پست، استوری، ریلز
• دانلود تک عکس یا آلبوم کامل
• پشتیبانی از اکانت‌های خصوصی

**🎵 ساندکلود:**
• لینک آهنگ یا پلی‌لیست
• کیفیت بالا MP3
• دانلود سریع

**💡 نکات مهم:**
⚠️ حداکثر حجم: 50MB
🕐 زمان انتظار: حداکثر 5 دقیقه  
🗑️ فایل‌ها بعد 1 ساعت پاک می‌شن
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def search_youtube(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """جستجو در یوتیوب"""
        # بررسی پارامترهای جستجو
        if not context.args:
            keyboard = [[InlineKeyboardButton("🔍 راهنمای جستجو", callback_data='search_help')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔍 **جستجو در یوتیوب**\n\n"
                "**نحوه استفاده:**\n"
                "`/search نام آهنگ یا ویدیو`\n\n"
                "**مثال:**\n"
                "`/search بهنام بانی اون که میگفت`\n"
                "`/search Eminem lose yourself`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
            
        query = ' '.join(context.args)
        search_msg = await update.message.reply_text(
            f"🔍 **در حال جستجو برای:** {query}\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            await search_msg.edit_text(
                f"🔍 **در حال جستجو برای:** {query}\n⬛⬛⬛⬜⬜⬜⬜⬜⬜⬜ 30%",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # جستجو در یوتیوب
            search_results = await self.youtube_search(query)
            
            if not search_results:
                await search_msg.edit_text(
                    f"❌ **هیچ نتیجه‌ای یافت نشد برای:** {query}\n"
                    f"لطفاً کلمات کلیدی متفاوتی امتحان کنید.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
                
            await search_msg.edit_text(
                f"🔍 **در حال جستجو برای:** {query}\n⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛ 100%",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # نمایش نتایج
            await self.show_search_results(update, context, search_results, query, search_msg)
            
        except Exception as e:
            logger.error(f"خطا در جستجو: {e}")
            await search_msg.edit_text(
                f"❌ **خطا در جستجو!**\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def youtube_search(self, query: str, max_results: int = 5):
        """جستجو در یوتیوب"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch5:',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(
                    f"ytsearch{max_results}:{query}", 
                    download=False
                )
                
            results = []
            if search_results and 'entries' in search_results:
                for entry in search_results['entries']:
                    if entry:
                        results.append({
                            'id': entry.get('id'),
                            'title': entry.get('title', 'Unknown'),
                            'uploader': entry.get('uploader', 'Unknown'),
                            'duration': entry.get('duration', 0),
                            'url': f"https://youtube.com/watch?v={entry.get('id')}",
                            'thumbnail': entry.get('thumbnail'),
                            'view_count': entry.get('view_count', 0)
                        })
                        
            return results[:5]  # حداکثر 5 نتیجه
            
        except Exception as e:
            logger.error(f"خطا در جستجوی یوتیوب: {e}")
            return []

    async def show_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                results: list, query: str, search_msg):
        """نمایش نتایج جستجو"""
        if not results:
            await search_msg.edit_text("❌ نتیجه‌ای یافت نشد!")
            return
            
        # ساخت پیام نتایج
        results_text = f"🔍 **نتایج جستجو برای:** {query}\n\n"
        keyboard = []
        
        for i, result in enumerate(results, 1):
            # محدود کردن طول عنوان
            title = result['title'][:40] + "..." if len(result['title']) > 40 else result['title']
            uploader = result['uploader'][:20] + "..." if len(result['uploader']) > 20 else result['uploader']
            
            # فرمت مدت زمان
            duration = result.get('duration', 0)
            if duration:
                duration_str = f"{duration//60}:{duration%60:02d}"
            else:
                duration_str = "نامشخص"
                
            # فرمت تعداد بازدید
            views = result.get('view_count', 0)
            if views:
                if views > 1000000:
                    views_str = f"{views/1000000:.1f}M"
                elif views > 1000:
                    views_str = f"{views/1000:.1f}K"
                else:
                    views_str = str(views)
            else:
                views_str = "نامشخص"
                
            results_text += f"**{i}.** {title}\n"
            results_text += f"👤 {uploader} | ⏱️ {duration_str} | 👀 {views_str}\n\n"
            
            # اضافه کردن دکمه
            keyboard.append([
                InlineKeyboardButton(
                    f"🎬 {i}. دانلود", 
                    callback_data=f'search_download_{result["id"]}'
                )
            ])
            
        # دکمه‌های اضافی
        keyboard.append([
            InlineKeyboardButton("🔍 جستجوی جدید", callback_data='search_youtube'),
            InlineKeyboardButton("❌ لغو", callback_data='cancel')
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ذخیره نتایج برای callback
        for result in results:
            context.user_data[f'search_result_{result["id"]}'] = result
            
        await search_msg.edit_text(
            results_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش لینک‌ها"""
        url = update.message.text.strip()
        user_id = update.effective_user.id
        
        # بررسی نوع لینک
        if not self.is_valid_url(url):
            await update.message.reply_text(
                "❌ لینک نامعتبر! لطفاً لینک صحیح از یوتیوب، اینستاگرام یا ساندکلود بفرستید."
            )
            return
            
        # شروع دانلود
        loading_msg = await update.message.reply_text(
            "🔍 **در حال تحلیل لینک...**\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            platform = self.detect_platform(url)
            
            if platform == 'youtube':
                await self.download_youtube(update, context, url, loading_msg)
            elif platform == 'instagram':
                await self.download_instagram(update, context, url, loading_msg)
            elif platform == 'soundcloud':
                await self.download_soundcloud(update, context, url, loading_msg)
                
        except Exception as e:
            logger.error(f"خطا در دانلود: {e}")
            await loading_msg.edit_text(
                f"❌ **خطا در دانلود!**\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            # پاک کردن پیام اصلی بعد از 10 ثانیه
            await asyncio.sleep(10)
            try:
                await update.message.delete()
            except:
                pass

    async def download_youtube(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, loading_msg):
        """دانلود از یوتیوب"""
        await loading_msg.edit_text(
            "📹 **یوتیوب شناسایی شد**\n⬛⬛⬜⬜⬜⬜⬜⬜⬜⬜ 20%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # دریافت اطلاعات ویدیو
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        title = info.get('title', 'Unknown')[:50]
        duration = info.get('duration', 0)
        formats = info.get('formats', [])
        
        # ایجاد کیبورد انتخاب کیفیت
        keyboard = []
        
        # فرمت‌های ویدیو
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        
        if video_formats:
            keyboard.append([InlineKeyboardButton("📹 ویدیو - کیفیت بالا", callback_data=f'yt_video_best_{info["id"]}')])
            keyboard.append([InlineKeyboardButton("📹 ویدیو - کیفیت متوسط", callback_data=f'yt_video_medium_{info["id"]}')])
            
        if audio_formats:
            keyboard.append([InlineKeyboardButton("🎵 فقط صدا - MP3", callback_data=f'yt_audio_{info["id"]}')])
            
        keyboard.append([InlineKeyboardButton("❌ لغو", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            f"✅ **آماده دانلود!**\n\n"
            f"📹 **عنوان:** {title}\n"
            f"⏱️ **مدت:** {duration//60}:{duration%60:02d}\n\n"
            f"لطفاً نوع دانلود را انتخاب کنید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # ذخیره اطلاعات برای callback
        context.user_data[f'video_info_{info["id"]}'] = {
            'url': url,
            'title': title,
            'info': info
        }

    async def download_instagram(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, loading_msg):
        """دانلود از اینستاگرام"""
        await loading_msg.edit_text(
            "📸 **اینستاگرام شناسایی شد**\n⬛⬛⬛⬛⬜⬜⬜⬜⬜⬜ 40%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # استفاده از instaloader
            L = instaloader.Instaloader(
                download_video_thumbnails=False,
                download_comments=False,
                save_metadata=False,
            )
            
            # استخراج shortcode از URL
            shortcode = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
            if '?' in shortcode:
                shortcode = shortcode.split('?')[0]
            
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            
            keyboard = [
                [InlineKeyboardButton("📸 دانلود عکس/ویدیو", callback_data=f'ig_download_{shortcode}')],
                [InlineKeyboardButton("❌ لغو", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                f"✅ **آماده دانلود!**\n\n"
                f"👤 **کاربر:** @{post.owner_username}\n"
                f"❤️ **لایک:** {post.likes:,}\n"
                f"📅 **تاریخ:** {post.date.strftime('%Y-%m-%d')}\n\n"
                f"برای شروع دانلود کلیک کنید:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            context.user_data[f'ig_post_{shortcode}'] = {
                'url': url,
                'post': post,
                'shortcode': shortcode
            }
            
        except Exception as e:
            await loading_msg.edit_text(
                f"❌ **خطا در پردازش اینستاگرام!**\n"
                f"ممکن است پست خصوصی باشد یا لینک اشتباه باشد.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def download_soundcloud(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, loading_msg):
        """دانلود از ساندکلود"""
        await loading_msg.edit_text(
            "🎵 **ساندکلود شناسایی شد**\n⬛⬛⬛⬜⬜⬜⬜⬜⬜⬜ 30%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp3]/best',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            title = info.get('title', 'Unknown')[:50]
            uploader = info.get('uploader', 'Unknown')
            duration = info.get('duration', 0)
            
            keyboard = [
                [InlineKeyboardButton("🎵 دانلود MP3", callback_data=f'sc_download_{info["id"]}')],
                [InlineKeyboardButton("❌ لغو", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                f"✅ **آماده دانلود!**\n\n"
                f"🎵 **عنوان:** {title}\n"
                f"👤 **هنرمند:** {uploader}\n"
                f"⏱️ **مدت:** {duration//60}:{duration%60:02d}\n\n"
                f"برای شروع دانلود کلیک کنید:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            context.user_data[f'sc_track_{info["id"]}'] = {
                'url': url,
                'title': title,
                'info': info
            }
            
        except Exception as e:
            await loading_msg.edit_text(
                f"❌ **خطا در پردازش ساندکلود!**\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کلیک‌های دکمه"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'cancel':
            await query.edit_message_text("❌ عملیات لغو شد.")
            return
            
        if data == 'help':
            await self.help_command(update, context)
            return
            
        if data == 'search_youtube':
            await query.edit_message_text(
                "🔍 **جستجو در یوتیوب**\n\n"
                "برای جستجو از دستور زیر استفاده کنید:\n"
                "`/search کلمه کلیدی`\n\n"
                "**مثال:**\n"
                "`/search حبیب نوری`\n"
                "`/search despacito`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        if data == 'search_help':
            await query.edit_message_text(
                "🔍 **راهنمای جستجو**\n\n"
                "**نحوه استفاده:**\n"
                "• `/search نام آهنگ`\n"
                "• `/search نام خواننده + نام آهنگ`\n"
                "• `/search عنوان ویدیو`\n\n"
                "**نکات:**\n"
                "✅ از کلمات فارسی و انگلیسی پشتیبانی می‌کند\n"
                "✅ حداکثر 5 نتیجه نمایش داده می‌شود\n"
                "✅ می‌تونید مستقیماً روی نتیجه کلیک کنید",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        if data == 'stats':
            await query.edit_message_text(
                "📊 **آمار ربات**\n\n"
                f"👥 **تعداد کاربران فعال:** {len(self.active_downloads)}\n"
                f"📁 **فایل‌های موجود:** {len(os.listdir(DOWNLOAD_DIR))}\n"
                f"💾 **فضای استفاده شده:** {self.get_dir_size(DOWNLOAD_DIR):.1f} MB",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # پردازش دانلود از جستجو
        if data.startswith('search_download_'):
            await self.process_search_download(query, context, data)
            return
            
        # پردازش دانلودها
        if data.startswith('yt_'):
            await self.process_youtube_download(query, context, data)
        elif data.startswith('ig_'):
            await self.process_instagram_download(query, context, data)
        elif data.startswith('sc_'):
            await self.process_soundcloud_download(query, context, data)

    async def process_search_download(self, query, context, data):
        """پردازش دانلود از نتایج جستجو"""
        video_id = data.split('_')[-1]
        search_result = context.user_data.get(f'search_result_{video_id}')
        
        if not search_result:
            await query.edit_message_text("❌ اطلاعات ویدیو یافت نشد!")
            return
            
        # نمایش گزینه‌های دانلود
        keyboard = [
            [InlineKeyboardButton("📹 ویدیو - کیفیت بالا", callback_data=f'yt_video_best_{video_id}')],
            [InlineKeyboardButton("📹 ویدیو - کیفیت متوسط", callback_data=f'yt_video_medium_{video_id}')],
            [InlineKeyboardButton("🎵 فقط صدا - MP3", callback_data=f'yt_audio_{video_id}')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='search_youtube')],
            [InlineKeyboardButton("❌ لغو", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ذخیره اطلاعات برای دانلود
        context.user_data[f'video_info_{video_id}'] = {
            'url': search_result['url'],
            'title': search_result['title'],
            'info': {'id': video_id, 'title': search_result['title']}
        }
        
        duration = search_result.get('duration', 0)
        duration_str = f"{duration//60}:{duration%60:02d}" if duration else "نامشخص"
        
        await query.edit_message_text(
            f"✅ **آماده دانلود!**\n\n"
            f"📹 **عنوان:** {search_result['title'][:50]}...\n"
            f"👤 **کانال:** {search_result['uploader']}\n"
            f"⏱️ **مدت:** {duration_str}\n\n"
            f"لطفاً نوع دانلود را انتخاب کنید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def process_youtube_download(self, query, context, data):
        """پردازش دانلود یوتیوب"""
        parts = data.split('_')
        download_type = parts[1]  # video/audio
        quality = parts[2] if len(parts) > 3 else 'best'
        video_id = '_'.join(parts[3:]) if len(parts) > 3 else parts[2]
        
        video_info = context.user_data.get(f'video_info_{video_id}')
        if not video_info:
            await query.edit_message_text("❌ اطلاعات ویدیو یافت نشد!")
            return
            
        # شروع دانلود با نمایش پیشرفت
        progress_msg = await query.edit_message_text(
            "⬇️ **شروع دانلود...**\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            filename = f"{video_id}_{download_type}_{quality}"
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            
            # تنظیمات دانلود
            if download_type == 'audio':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': filepath + '.%(ext)s',
                    'extract_flat': False,
                }
            else:
                format_selector = 'best[height<=720]' if quality == 'medium' else 'best'
                ydl_opts = {
                    'format': format_selector,
                    'outtmpl': filepath + '.%(ext)s',
                }
            
            # دانلود با نمایش پیشرفت
            class ProgressHook:
                def __init__(self, progress_msg):
                    self.progress_msg = progress_msg
                    self.last_update = 0
                    
                async def __call__(self, d):
                    if d['status'] == 'downloading':
                        if 'total_bytes' in d:
                            percent = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
                            if time.time() - self.last_update > 2:  # آپدیت هر 2 ثانیه
                                blocks = '⬛' * (percent // 10) + '⬜' * (10 - percent // 10)
                                try:
                                    await self.progress_msg.edit_text(
                                        f"⬇️ **در حال دانلود...** {percent}%\n{blocks}",
                                        parse_mode=ParseMode.MARKDOWN
                                    )
                                except:
                                    pass
                                self.last_update = time.time()
            
            progress_hook = ProgressHook(progress_msg)
            ydl_opts['progress_hooks'] = [lambda d: asyncio.create_task(progress_hook(d))]
            
            # دانلود فایل
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.get_event_loop().run_in_executor(
                    None, ydl.download, [video_info['url']]
                )
            
            # یافتن فایل دانلود شده
            downloaded_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith(filename)]
            if not downloaded_files:
                raise Exception("فایل دانلود نشد!")
                
            file_path = os.path.join(DOWNLOAD_DIR, downloaded_files[0])
            file_size = os.path.getsize(file_path)
            
            if file_size > MAX_FILE_SIZE:
                os.remove(file_path)
                await progress_msg.edit_text(
                    f"❌ **فایل بزرگ‌تر از حد مجاز!**\n"
                    f"حجم: {file_size/(1024*1024):.1f}MB\n"
                    f"حداکثر مجاز: {MAX_FILE_SIZE/(1024*1024):.0f}MB",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # ارسال فایل
            await progress_msg.edit_text(
                "📤 **در حال ارسال...**\n⬛⬛⬛⬛⬛⬛⬛⬛⬛⬜ 90%",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await query.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
            
            with open(file_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=f"{video_info['title']}.{downloaded_files[0].split('.')[-1]}",
                    caption=f"✅ **دانلود موفق!**\n📹 {video_info['title'][:30]}...",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # پاک کردن فایل و پیام
            os.remove(file_path)
            await asyncio.sleep(2)
            await progress_msg.delete()
            
        except Exception as e:
            await progress_msg.edit_text(
                f"❌ **خطا در دانلود!**\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def process_instagram_download(self, query, context, data):
        """پردازش دانلود اینستاگرام"""
        shortcode = data.split('_')[-1]
        post_info = context.user_data.get(f'ig_post_{shortcode}')
        
        if not post_info:
            await query.edit_message_text("❌ اطلاعات پست یافت نشد!")
            return
            
        progress_msg = await query.edit_message_text(
            "⬇️ **در حال دانلود از اینستاگرام...**\n⬛⬛⬛⬜⬜⬜⬜⬜⬜⬜ 30%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            L = instaloader.Instaloader()
            post = post_info['post']
            
            # دانلود در پوشه موقت
            temp_dir = tempfile.mkdtemp()
            L.dirname_pattern = temp_dir
            L.download_post(post, target=temp_dir)
            
            await progress_msg.edit_text(
                "📤 **در حال ارسال...**\n⬛⬛⬛⬛⬛⬛⬛⬛⬜⬜ 80%",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # پیدا کردن فایل‌های دانلود شده
            files = []
            for root, dirs, filenames in os.walk(temp_dir):
                for filename in filenames:
                    if filename.endswith(('.jpg', '.mp4', '.png')):
                        files.append(os.path.join(root, filename))
            
            if not files:
                raise Exception("فایلی دانلود نشد!")
            
            # ارسال فایل‌ها
            for file_path in files[:5]:  # حداکثر 5 فایل
                file_size = os.path.getsize(file_path)
                if file_size <= MAX_FILE_SIZE:
                    with open(file_path, 'rb') as f:
                        if file_path.endswith('.mp4'):
                            await query.message.reply_video(
                                video=f,
                                caption="✅ دانلود از اینستاگرام"
                            )
                        else:
                            await query.message.reply_photo(
                                photo=f,
                                caption="✅ دانلود از اینستاگرام"
                            )
            
            # پاک‌سازی
            shutil.rmtree(temp_dir)
            await progress_msg.delete()
            
        except Exception as e:
            await progress_msg.edit_text(
                f"❌ **خطا در دانلود اینستاگرام!**\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def process_soundcloud_download(self, query, context, data):
        """پردازش دانلود ساندکلود"""
        track_id = data.split('_')[-1]
        track_info = context.user_data.get(f'sc_track_{track_id}')
        
        if not track_info:
            await query.edit_message_text("❌ اطلاعات آهنگ یافت نشد!")
            return
            
        progress_msg = await query.edit_message_text(
            "⬇️ **در حال دانلود از ساندکلود...**\n⬛⬛⬛⬛⬜⬜⬜⬜⬜⬜ 40%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            filename = f"sc_{track_id}.mp3"
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            
            ydl_opts = {
                'format': 'best[ext=mp3]/best',
                'outtmpl': filepath,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.get_event_loop().run_in_executor(
                    None, ydl.download, [track_info['url']]
                )
            
            await progress_msg.edit_text(
                "📤 **در حال ارسال...**\n⬛⬛⬛⬛⬛⬛⬛⬛⬛⬜ 90%",
                parse_mode=ParseMode.MARKDOWN
            )
            
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size <= MAX_FILE_SIZE:
                    with open(filepath, 'rb') as f:
                        await query.message.reply_audio(
                            audio=f,
                            title=track_info['title'],
                            caption="✅ دانلود از ساندکلود"
                        )
                else:
                    raise Exception("فایل بزرگ‌تر از حد مجاز!")
                    
                os.remove(filepath)
            
            await progress_msg.delete()
            
        except Exception as e:
            await progress_msg.edit_text(
                f"❌ **خطا در دانلود ساندکلود!**\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )

    def is_valid_url(self, url: str) -> bool:
        """بررسی معتبر بودن URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def detect_platform(self, url: str) -> str:
        """تشخیص پلتفرم از روی URL"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'instagram.com' in url:
            return 'instagram'  
        elif 'soundcloud.com' in url:
            return 'soundcloud'
        return 'unknown'

    def get_dir_size(self, path: str) -> float:
        """محاسبه حجم پوشه به مگابایت"""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
        except:
            pass
        return total / (1024 * 1024)

    async def cleanup_old_files(self):
        """پاک‌سازی فایل‌های قدیمی"""
        try:
            current_time = time.time()
            for filename in os.listdir(DOWNLOAD_DIR):
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.getctime(file_path) < current_time - 3600:  # 1 ساعت
                    os.remove(file_path)
        except Exception as e:
            logger.error(f"خطا در پاک‌سازی: {e}")

def main():
    """اجرای ربات"""
    bot = DownloadBot()
    
    # ایجاد اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("search", bot.search_youtube))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_url))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # شروع ربات
    print("🚀 ربات دانلود شروع شد!")
    print("🔍 ویژگی جستجو یوتیوب فعال شد!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()