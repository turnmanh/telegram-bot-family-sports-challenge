from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, Application, CommandHandler, ContextTypes, MessageHandler, filters
from core.config import settings
from stravalib.client import Client
from db.supabase import supabase
from app.sync import sync_for_user, sync_all_users


async def check_phone_allowed(phone_number: str) -> bool:
    """
    Checks if a phone number is in the allowed_numbers table.
    Performs cleanup and fuzzy matching.
    """
    # Normalize: remove '+' and spaces
    clean_phone = phone_number.replace('+', '').replace(' ', '')
    
    try:
        # Check allowed_numbers
        # We try strict match or match without leading + if DB has it stored differently
        res = supabase.table("allowed_numbers").select("*").or_(f"phone_number.eq.{phone_number},phone_number.eq.+{phone_number}").execute()
        
        if res.data:
            return True
        else:
            # Fuzzy check
            all_res = supabase.table("allowed_numbers").select("phone_number").execute()
            for row in all_res.data:
                db_num = row['phone_number'].replace('+', '').replace(' ', '')
                if db_num == clean_phone:
                    return True
        return False
    except Exception as e:
        print(f"Error checking allowed numbers: {e}")
        return False

async def is_user_verified(update: Update) -> bool:
    """Check if user is verified in the DB and sync their telegram info."""
    user = update.effective_user
    if not user:
        return False
        
    try:
        response = supabase.table("users").select("is_verified, phone_number, telegram_username").eq("telegram_id", user.id).execute()
        if response.data:
            user_data = response.data[0]
            
            # Sync username if it changed or is missing
            if user.username and user_data.get("telegram_username") != user.username:
                supabase.table("users").update({"telegram_username": user.username}).eq("telegram_id", user.id).execute()
            
            if user_data.get("is_verified", False):
                return True
            
            # Check if there is a saved phone number in the profile that is valid
            saved_phone = user_data.get("phone_number")
            if saved_phone:
                print(f"Checking saved phone number for user {user.id}...")
                if await check_phone_allowed(saved_phone):
                    # Auto-verify
                    supabase.table("users").update({"is_verified": True}).eq("telegram_id", user.id).execute()
                    return True
                    
        return False
    except Exception as e:
        print(f"Auth check failed: {e}")
        return False

async def request_verification(update: Update):
    """Prompts the user to share their phone number."""
    contact_keyboard = KeyboardButton(text="📱 Share Phone Number", request_contact=True)
    custom_keyboard = ReplyKeyboardMarkup([[contact_keyboard]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "⛔ You are not authorized yet.\n"
        "Please share your phone number to verify access.",
        reply_markup=custom_keyboard
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles received phone numbers and verifies them against the allowed list.
    """
    contact = update.message.contact
    user_id = update.effective_user.id
    if contact.user_id != user_id:
        await update.message.reply_text("Please share YOUR own contact.")
        return

    phone_number = contact.phone_number
    
    if await check_phone_allowed(phone_number):
        user_data = {
            "telegram_id": user_id,
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name,
            "telegram_username": update.effective_user.username,
            "phone_number": phone_number,
            "is_verified": True
        }
        supabase.table("users").upsert(user_data).execute()
        
        await update.message.reply_text(
            "✅ Verification successful! Welcome to the Family Sport Challenge Bot.\n\n"
            "Use /join to connect your Strava account.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "❌ This phone number is not in the allowed list.\n"
            "Please contact the administrator.",
            reply_markup=ReplyKeyboardRemove()
        )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_verified(update):
        await request_verification(update)
        return

    await update.message.reply_text(
        "Welcome to the Family Sport Challenge Bot! 👏\n\n"
        "Use /join to connect your Strava account.\n"
        "Use /name [First] [Last] to set your display name.\n"
        "Use /stats to see your total weighted distance.\n"
        "Use /activities to list your recent activities.\n"
        "Use /top to see the leaderboard, i.e. the top 3 performers.\n"
        "Use /weights to see current conversion factors."
    )

async def name_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_verified(update):
        await request_verification(update)
        return

    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /name [First Name] [Last Name]\nExample: /name John Doe")
        return

    first_name = args[0]
    last_name = " ".join(args[1:]) if len(args) > 1 else ""

    try:
        supabase.table("users").update({
            "first_name": first_name,
            "last_name": last_name
        }).eq("telegram_id", user_id).execute()
        
        await update.message.reply_text(f"✅ Name updated to: {first_name} {last_name}".strip())
    except Exception as e:
        await update.message.reply_text(f"Error updating name: {e}")

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_verified(update):
        await request_verification(update)
        return

    print(f"Received /join command from {update.effective_user.id}")
    client = Client()
    state = str(update.effective_user.id)
    authorize_url = client.authorization_url(
        client_id=settings.STRAVA_CLIENT_ID,
        redirect_uri=settings.STRAVA_REDIRECT_URI,
        state=state,
        scope=["activity:read_all"]
    )
    await update.message.reply_text(
        f"Please authorize Strava access by clicking the link below:\n\n{authorize_url}"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_verified(update):
        await request_verification(update)
        return

    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await sync_for_user(user_id)
    try:
        response = supabase.table("activities").select("weighted_distance").eq("user_id", user_id).execute()
        total = sum(item["weighted_distance"] for item in response.data)
        await update.message.reply_text(f"📊 Your Total Weighted Distance: {total:.2f} km")
    except Exception as e:
        await update.message.reply_text(f"Error fetching stats: {e}")

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_verified(update):
        await request_verification(update)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await sync_all_users()

    try:
        response = supabase.table("activities").select("user_id, weighted_distance").execute()
        totals = {}
        for item in response.data:
            uid = item["user_id"]
            totals[uid] = totals.get(uid, 0) + item["weighted_distance"]
        
        sorted_users = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:3]
        
        names_map = {}
        if sorted_users:
            top_ids = [u[0] for u in sorted_users]
            try:
                user_res = supabase.table("users").select("telegram_id, first_name, last_name, telegram_username").in_("telegram_id", top_ids).execute()
                for u in user_res.data:
                    # Logic: first + last > telegram_username > ID
                    display_name = f"{u.get('first_name') or ''} {u.get('last_name') or ''}".strip()
                    if not display_name:
                        if u.get('telegram_username'):
                            display_name = f"@{u['telegram_username']}"
                        else:
                            display_name = f"User {u['telegram_id']}"
                    names_map[u['telegram_id']] = display_name
            except Exception as e:
                print(f"Error fetching names: {e}")

        msg = "🏆 Leaderboard:\n"
        for i, (uid, dist) in enumerate(sorted_users, 1):
            name = names_map.get(uid, f"User {uid}")
            msg += f"{i}. {name}: {dist:.2f} km\n"
            
        if not sorted_users:
            msg += "No activities yet!"
            
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error fetching leaderboard: {e}")

async def activities_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_verified(update):
        await request_verification(update)
        return

    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await sync_for_user(user_id)
    try:
        count_response = supabase.table("activities").select("activity_id", count="exact").eq("user_id", user_id).execute()
        total_count = count_response.count

        response = supabase.table("activities")\
            .select("type, distance, weighted_distance, name, start_date")\
            .eq("user_id", user_id)\
            .order("start_date", desc=True)\
            .limit(20)\
            .execute()
            
        activities = response.data
        if not activities:
            await update.message.reply_text("No activities found.")
            return

        msg = f"📅 Your Activities (Total: {total_count})\nshowing last 20:\n\n"
        for act in activities:
            date_str = act['start_date'].split('T')[0]
            msg += (
                f"• {date_str} - {act['name']}\n"
                f"  Type: {act['type']} | Dist: {act['distance']:.2f}km | Score: {act['weighted_distance']:.2f}km\n\n"
            )
        await update.message.reply_text(msg)
        
    except Exception as e:
        await update.message.reply_text(f"Error fetching activities: {e}")

async def weights_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the current activity weights/conversion factors."""
    from core.scoring import refresh_activity_weights
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    weights = await refresh_activity_weights()
    
    msg = "⚖️ Activity Conversion Factors:\n(Distance * Weight = Score)\n\n"
    # Filter out 0.0 weights
    active_weights = {k: v for k, v in weights.items() if v > 0}
    
    for sport, weight in sorted(active_weights.items()):
        msg += f"• {sport}: {weight:.2f}x\n"
    
    await update.message.reply_text(msg)

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
            
        await update.message.reply_text(
            f"Welcome {member.first_name} to the Family Sport Challenge! 🏃‍♂️🚴‍♀️\n\n"
            "I can track your sports activities and show you the leaderboard.\n"
            "Please start a private chat with me and send /start to connect your Strava account!"
        )

def create_bot_application() -> Application:
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("join", join_command))
    app.add_handler(CommandHandler("name", name_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("activities", activities_command))
    app.add_handler(CommandHandler("weights", weights_command))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    return app
