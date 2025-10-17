# bot.py
import logging
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext

# Enable logging (more verbose for debugging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# Global variables
all_names = ["احمد", "اصيل", "علي", "سجاد", "كرار", "مرتضى", "حسين"]
fixed_schedule = {
    "الأحد": ["حسين", "اصيل"],
    "الاثنين": ["سجاد", "علي"],
    "الخميس": ["احمد", "مرتضى"]
}

# Store dynamic pairs and completion status
tuesday_pairs = {}  # Format: {week_number: {"pair": [name1, name2], "completed": False}}
wednesday_pairs = {}  # Format: {week_number: {"pair": [name1, name2], "completed": False}}
used_names = {}  # Track used names per week

def get_week_number():
    return datetime.now().isocalendar()[1]

def get_random_pair(exclude_names=None):
    week_num = get_week_number()
    if week_num not in used_names:
        used_names[week_num] = set()
    
    if exclude_names is None:
        exclude_names = set()
    
    # Get available names (excluding used names and names to exclude)
    available_names = [name for name in all_names 
                      if name not in used_names[week_num] and 
                      name not in exclude_names]
    
    # If not enough available names, reset the used names
    if len(available_names) < 2:
        used_names[week_num].clear()
        available_names = [name for name in all_names if name not in exclude_names]
    
    # Select two random names
    name1 = random.choice(available_names)
    available_names.remove(name1)
    name2 = random.choice(available_names)
    
    # Add both names to used names
    used_names[week_num].add(name1)
    used_names[week_num].add(name2)
    
    return [name1, name2]

def get_random_partner(main_person):
    week_num = get_week_number()
    if week_num not in used_names:
        used_names[week_num] = set()
    
    available_partners = [name for name in all_names 
                         if name != main_person and 
                         name not in used_names[week_num]]
    
    if not available_partners:
        used_names[week_num].clear()
        available_partners = [name for name in all_names if name != main_person]
    
    partner = random.choice(available_partners)
    used_names[week_num].add(partner)
    return partner

def mark_day_completed(day, week_num):
    if day == "الثلاثاء" and week_num in tuesday_pairs:
        tuesday_pairs[week_num]["completed"] = True
    elif day == "الاربعاء" and week_num in wednesday_pairs:
        wednesday_pairs[week_num]["completed"] = True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f"/start called by user: {update.effective_user.id if update.effective_user else 'unknown'}")
        keyboard = [
            ["الأحد", "الاثنين", "الثلاثاء"],
            ["الاربعاء", "الخميس"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "أهلاً بك في بوت جدول الطبخ الأسبوعي! 👨‍🍳\n"
            "اختر اليوم لمعرفة من مسؤول عن الطبخ:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("حدث خطأ، الرجاء المحاولة مرة أخرى باستخدام /start")

async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text if update.message and update.message.text else ''
    logger.debug(f"handle_day_selection received text: {text} from user: {update.effective_user.id if update.effective_user else 'unknown'}")
    week_num = get_week_number()
    
    # Handle "تم" command
    if text.strip() == "تم":
        if 'last_day' not in context.user_data:
            await update.message.reply_text("الرجاء اختيار يوم أولاً")
            return
        last_day = context.user_data['last_day']
        if last_day in ["الثلاثاء", "الاربعاء"]:
            mark_day_completed(last_day, week_num)
            await update.message.reply_text(f"تم تسجيل اكتمال الطبخ ليوم {last_day}! ستتغير الأسماء في المرة القادمة.")
        return
    
    # Handle day selection
    day = text
    if day in fixed_schedule:
        names = fixed_schedule[day]
        await update.message.reply_text(f"اليوم {day}:\n👨‍🍳 {names[0]} و {names[1]}")
    
    elif day == "الثلاثاء":
        logger.debug(f"Processing Tuesday for week {week_num}. Existing pair: {tuesday_pairs.get(week_num)}")
        if week_num not in tuesday_pairs or tuesday_pairs[week_num].get("completed", False):
            partner = get_random_partner("كرار")
            tuesday_pairs[week_num] = {"pair": ["كرار", partner], "completed": False}
            logger.debug(f"Assigned Tuesday pair for week {week_num}: {tuesday_pairs[week_num]}")
        pair_info = tuesday_pairs[week_num]["pair"]
        context.user_data['last_day'] = day
        try:
            await update.message.reply_text(
                f"اليوم {day}:\n👨‍🍳 {pair_info[0]} و {pair_info[1]}\n\n"
                "بعد الانتهاء من الطبخ، الرجاء كتابة كلمة (تم) لتغيير الأسماء في المرة القادمة"
            )
        except Exception as e:
            logger.exception("Failed to send Tuesday reply")
            await update.message.reply_text("حدث خطأ عند عرض أسماء يوم الثلاثاء، الرجاء المحاولة مرة أخرى.")

    elif day == "الاربعاء":
        if week_num not in wednesday_pairs or wednesday_pairs[week_num].get("completed", False):
            # Get Tuesday's names to exclude
            tuesday_names = set()
            if week_num in tuesday_pairs:
                tuesday_names = set(tuesday_pairs[week_num]["pair"])

            # Get random pair excluding Tuesday's names
            selected_pair = get_random_pair(exclude_names=tuesday_names)
            wednesday_pairs[week_num] = {"pair": selected_pair, "completed": False}

        pair_info = wednesday_pairs[week_num]["pair"]
        context.user_data['last_day'] = day
        await update.message.reply_text(
            f"اليوم {day}:\n👨‍🍳 {pair_info[0]} و {pair_info[1]}\n\n"
            "بعد الانتهاء من الطبخ، الرجاء كتابة كلمة (تم) لتغيير الأسماء في المرة القادمة"
        )


async def force_tuesday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to force/show Tuesday pair for testing."""
    week_num = get_week_number()
    logger.debug(f"/tuesday called by user: {update.effective_user.id if update.effective_user else 'unknown'}")
    if week_num not in tuesday_pairs or tuesday_pairs[week_num].get("completed", False):
        partner = get_random_partner("كرار")
        tuesday_pairs[week_num] = {"pair": ["كرار", partner], "completed": False}
        logger.debug(f"Assigned Tuesday pair via /tuesday for week {week_num}: {tuesday_pairs[week_num]}")
    pair_info = tuesday_pairs[week_num]["pair"]
    context.user_data['last_day'] = "الثلاثاء"
    await update.message.reply_text(f"[اختبار] اليوم الثلاثاء: {pair_info[0]} و {pair_info[1]}")

async def debug_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    week_num = get_week_number()
    text = (
        f"current_week={week_num}\n"
        f"tuesday_pairs={tuesday_pairs.get(week_num)}\n"
        f"wednesday_pairs={wednesday_pairs.get(week_num)}\n"
        f"used_names={used_names.get(week_num)}\n"
    )
    await update.message.reply_text(f"Debug state:\n{text}")


def main() -> None:
    try:
        # Create the Application
        application = Application.builder().token("8233993858:AAG0cc4B8rJcW4_PmdF4_GKOLPPu1IZQu-I").build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("debug", debug_state))
        application.add_handler(CommandHandler("tuesday", force_tuesday))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_day_selection))

        # Start the bot
        print("Telegram bot is running... Ctrl+C للإيقاف")
        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.exception("Exception during run_polling")
        finally:
            print("run_polling has exited")
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        print(f"حدث خطأ عند تشغيل البوت: {str(e)}")

if __name__ == '__main__':
    main()