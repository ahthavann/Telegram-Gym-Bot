import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os

# Sample exercise templates
TEMPLATES = {
    "day1": [
        ("Standing Calf Raises", 2),
        ("Hip Adductors", 2),
        ("Pendulum Squat", 2),
        ("Leg Extensions", 2),
        ("Laying Hamstring Curls", 2),
        ("Ab Crunches", 3),
        ("Wrist Curl", 2),
    ],
    "day2": [
        ("Powerlifting Incline Bench", 3),
        ("Pec Deck", 1),
        ("Incline Skullcrushers", 2),
        ("Dumbbell Shoulder Press", 2),
        ("Dumbbell Lateral Raise", 2),
        ("Weighted Pull-ups", 1),
        ("Cable Row", 1),
        ("Kelso Shrug", 1),
        ("Machine Preacher Curl", 1),
        ("Rope Hammer Curl", 1),
        ("Rear Delt Crossover", 1),
    ],
    "day3": [
        ("Powerlifting Incline Bench", 3),
        ("Laying Hamstring Curls", 2),
        ("Hack Squat", 2),
        ("Back Extensions", 2),
        ("Hip Adductors", 1),
        ("Standing Calf Raises", 2),
        ("Leg Raises", 2),
        ("Reverse Grip Curl", 2),
    ],
    "day4": [
        ("Powerlifting Incline Bench", 3),
        ("Tricep Pushdown", 2),
        ("Incline Skullcrushers", 1),
        ("Extreme Row", 2),
        ("Cable Row", 2),
        ("Bayesian Curl", 2),
        ("Rope Hammer Curl", 1),
        ("Dumbbell Shoulder Press", 1),
        ("Dumbbell Lateral Raise", 1),
        ("Rear Delt Crossover", 2),
    ],
    "day5": [
        ("Powerlifting Incline Bench", 3),
        ("Weighted Pull-ups", 2),
        ("Weighted Dips", 2),
        ("Kelso Shrug", 2),
        ("Standing Calf Raises", 2),
        ("Ab Crunches", 2),
        ("Leg Raises", 2),
    ]
}

# Store in-memory session data (could be persisted)
user_sessions = {}

# Inline keyboard helper
def build_buttons(options, prefix=""):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=f"{prefix}:{text}")]
        for text in options
    ])

# Start workout
async def start_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = {
        "Day I (Lower I)": "day1",
        "Day II (Upper I)": "day2",
        "Day III (Lower II)": "day3",
        "Day IV (Upper II)": "day4",
        "Day V (Aesthetic)": "day5",
    }
    keyboard = [[InlineKeyboardButton(k, callback_data=f"day:{v}")] for k, v in days.items()]
    await update.message.reply_text("Choose workout day:", reply_markup=InlineKeyboardMarkup(keyboard))

# Handle workout day selection
async def handle_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    day_code = query.data.split(":")[1]
    user_id = query.from_user.id
    user_sessions[user_id] = {
        "day": day_code,
        "template": TEMPLATES[day_code],
        "index": 0,
        "sets_done": [],
        "messages_to_delete": [query.message.message_id],
    }
    await send_next_set(query.message.chat_id, user_id, context)

# Send next set
async def send_next_set(chat_id, user_id, context):
    session = user_sessions[user_id]
    if session["index"] >= len(session["template"]):
        keyboard = build_buttons(["Yes", "No"], "done")
        msg = await context.bot.send_message(chat_id, "Workout complete. Mark it as finished?", reply_markup=keyboard)
        session["messages_to_delete"].append(msg.message_id)
        return

    exercise, total_sets = session["template"][session["index"]]
    current_set = len([s for s in session["sets_done"] if s[0] == exercise])

    if current_set >= total_sets:
        session["index"] += 1
        await send_next_set(chat_id, user_id, context)
        return

    keyboard = build_buttons(["+1 Rep", "+2.5kg", "Done", "Skip", "Come Back"], f"set:{exercise}")
    msg = await context.bot.send_message(chat_id, f"{exercise} – Set {current_set+1}/{total_sets}", reply_markup=keyboard)
    session["messages_to_delete"].append(msg.message_id)

# Handle set updates
async def handle_set_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = user_sessions[user_id]
    action = query.data.split(":")[1]

    if action in ["+1 Rep", "+2.5kg", "Done"]:
        exercise = session["template"][session["index"]][0]
        session["sets_done"].append((exercise, action))
        session["messages_to_delete"].append(query.message.message_id)
        await send_next_set(query.message.chat_id, user_id, context)

    elif action == "Skip":
        session["sets_done"].append(("Skipped", session["template"][session["index"]][0]))
        session["index"] += 1
        await send_next_set(query.message.chat_id, user_id, context)

    elif action == "Come Back":
        session["template"].append(session["template"][session["index"]])
        session["index"] += 1
        await send_next_set(query.message.chat_id, user_id, context)

# Handle workout end confirmation
async def handle_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = user_sessions.get(user_id)

    if query.data.endswith("Yes") and session:
        for mid in session["messages_to_delete"]:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=mid)
            except:
                pass
        log = "\n".join([f"{e} – {a}" for e, a in session["sets_done"]])
        await context.bot.send_message(query.message.chat_id, f"Workout Summary:\n{log}")
        del user_sessions[user_id]
    elif query.data.endswith("No"):
        await query.edit_message_text("Okay. You can continue the workout.")

# Main
def main():
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    app.add_handler(CommandHandler("start_workout", start_workout))
    app.add_handler(CallbackQueryHandler(handle_day, pattern="^day:"))
    app.add_handler(CallbackQueryHandler(handle_set_action, pattern="^set:"))
    app.add_handler(CallbackQueryHandler(handle_done, pattern="^done:"))
    app.run_polling()

if __name__ == "__main__":
    main()
