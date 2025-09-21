import telebot
import sqlite3
from datetime import datetime
import os
import sys
import subprocess
import json
import random
import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = telebot.TeleBot("7734129868:AAFCFB9sqr9clM3nk49vkKjWfu8I9-6Cnkg")  # توكن البوت


# قاعدة بيانات
conn = sqlite3.connect('clash_bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS players 
             (id INTEGER PRIMARY KEY, level INT DEFAULT 1, gold INT DEFAULT 1000, elixir INT DEFAULT 1000, 
              troops TEXT DEFAULT '{}', trophies INT DEFAULT 0, last_collect TEXT, clan_name TEXT DEFAULT NULL)''')
c.execute('''CREATE TABLE IF NOT EXISTS clans 
             (name TEXT PRIMARY KEY, level INT DEFAULT 1, resources TEXT DEFAULT '{}', members TEXT DEFAULT '[]', 
              troop_storage TEXT DEFAULT '{}')''')
c.execute('''CREATE TABLE IF NOT EXISTS banned (id INTEGER PRIMARY KEY)''')

# إضافة عمود username إذا لم يكن موجودًا
try:
    c.execute("ALTER TABLE players ADD COLUMN username TEXT")
except sqlite3.OperationalError:
    pass  # العمود موجود بالفعل

# إضافة عمود last_activity إذا لم يكن موجودًا
try:
    c.execute("ALTER TABLE players ADD COLUMN last_activity TEXT")
except sqlite3.OperationalError:
    pass  # العمود موجود بالفعل
try:
    c.execute("ALTER TABLE players ADD COLUMN last_attack_id TEXT")
except sqlite3.OperationalError:
    pass  # العمود موجود بالفعل    
    

conn.commit()

OWNER_ID = 6789179634  # غير إلى ID تليجرام الخاص بك
CHANNEL_ID = -1002012804950  # غير إلى ID القناة
CHANNEL_USERNAME = '@SYR_SB'  # غير إلى username القناة

# دالة للتحقق من الاشتراك
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# دالة للتحقق إذا محظور
def is_banned(user_id):
    c.execute("SELECT * FROM banned WHERE id=?", (user_id,))
    return c.fetchone() is not None

# إحصائيات الجنود
TROOP_STATS = {
    'بربري': {'dps': 8, 'hp': 45, 'space': 1, 'cost': 25},
    'آرشر': {'dps': 7, 'hp': 20, 'space': 1, 'cost': 50},
    'عملاق': {'dps': 11, 'hp': 100, 'space': 5, 'cost': 250},
    'ساحر': {'dps': 50, 'hp': 75, 'space': 4, 'cost': 120}
}

def get_army_capacity(level):
    if level <= 5:
        return level * 100
    else:
        return 500 + (level - 5) * 40
        
        

def calculate_army_power(troops_str, level):
    troops = json.loads(troops_str)
    total_dps = 0
    for troop, count in troops.items():
        if troop in TROOP_STATS:
            dps = TROOP_STATS[troop]['dps'] * (1 + 0.1 * (level - 1))
            total_dps += dps * count
    return total_dps

def calculate_village_hp(troops_str, level):
    troops = json.loads(troops_str)
    total_hp = level * 1000
    for troop, count in troops.items():
        if troop in TROOP_STATS:
            total_hp += TROOP_STATS[troop]['hp'] * count * (1 + 0.1 * (level - 1))
    return total_hp

def lose_troops(troops_str, loss_percent):
    troops = json.loads(troops_str)
    for troop in troops:
        troops[troop] = max(0, int(troops[troop] * (1 - loss_percent)))
    return json.dumps(troops)

def show_opponent_info(chat_id, opp_id, opp_username, opp_level, opp_troops, opp_gold, opp_elixir, user_id, is_revenge=False):
    troops = json.loads(opp_troops)
    markup = InlineKeyboardMarkup()
    callback_data = f"revenge:{opp_id}:{user_id}" if is_revenge else f"attack:{opp_id}:{user_id}"
    markup.add(InlineKeyboardButton("هجوم ⚔️" if not is_revenge else "انتقام ⚔️", callback_data=callback_data))
    markup.add(InlineKeyboardButton("التالي ⏭️", callback_data=f"next_opponent:{user_id}"))
    bot.send_message(
        chat_id,
        f"🚨 <b>خصم محتمل:</b> <a href='tg://user?id={opp_id}'>{opp_username}</a>\n"
        f"📊 <b>مستوى:</b> {opp_level}\n"
        f"💂 <b>جنود:</b> {troops}\n"
        f"💰 <b>موارد متاحة للسرقة:</b> {opp_gold // 10} ذهب، {opp_elixir // 10} إكسير",
        parse_mode='HTML',
        reply_markup=markup
    )


# خيط للإشعارات الدورية
def send_notifications():
    while True:
        now = datetime.now()
        try:
            c.execute("SELECT id, last_collect, last_activity FROM players")
            players = c.fetchall()
            for user_id, last_collect_str, last_activity_str in players:
                if is_banned(user_id):
                    continue
                try:
                    last_collect = datetime.fromisoformat(last_collect_str)
                    last_activity = datetime.fromisoformat(last_activity_str) if last_activity_str else now
                    if (now - last_collect).total_seconds() >= 3600:
                        bot.send_message(user_id, "🔔 **مواردك جاهزة للجمع!** ⛏️ أعد اللعب الآن.", parse_mode='Markdown')
                    if (now - last_activity).total_seconds() >= 86400:
                        bot.send_message(user_id, "🛡️ **أيها الزعيم، قريتك تنتظرك!** أين أنت؟ نفتقدك أيها القائد. 🌟", parse_mode='Markdown')
                except telebot.apihelper.ApiTelegramException as e:
                    if e.error_code == 403:
                        c.execute("DELETE FROM players WHERE id=?", (user_id,))
                        conn.commit()
                        bot.send_message(OWNER_ID, f"حذفت قرية ID {user_id} لأنه حظر البوت.", parse_mode='Markdown')
                except Exception as e:
                    pass
                time.sleep(0.05)
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                # إعادة إنشاء الأعمدة إذا لزم
                try:
                    if "last_activity" in str(e):
                        c.execute("ALTER TABLE players ADD COLUMN last_activity TEXT")
                    if "username" in str(e):
                        c.execute("ALTER TABLE players ADD COLUMN username TEXT")
                    conn.commit()
                except:
                    pass
        time.sleep(3600)

threading.Thread(target=send_notifications, daemon=True).start()

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("قناة المطور", url="https://t.me/" + CHANNEL_USERNAME[1:]))

    if not is_subscribed(user_id):
        sub_markup = InlineKeyboardMarkup()
        sub_markup.add(InlineKeyboardButton("اشترك في القناة", url="https://t.me/" + CHANNEL_USERNAME[1:]))
        bot.reply_to(message, "مرحباً! للعب، يجب الاشتراك في قناة البوت أولاً. اشترك ثم أعد كتابة /start.", reply_markup=sub_markup, parse_mode='Markdown')
        time.sleep(0.1)
        return

    # إرسال الـ GIF مع النص كـ caption
    caption = "أهلاً بك في بوت **كلاش أوف كلانس** التليجرامي! 🎮\n" \
              "هنا تبني قريتك المصغرة، تدرب جيشك، وتحارب أصدقاءك أو أعداء عشوائيين.\n" \
              "ابدأ بكتابة 'إنشاء قرية' لإنشاء قريتك.\n" \
              "للمزيد وفهم اللعبة، اكتب 'التعليمات' واقرأ قواعد اللعبة."
    bot.send_animation(
        chat_id=message.chat.id,
        animation="https://freight.cargo.site/w/533/i/cb4cc454dace15a49702671ac0ed7ca0f6887feb0e5bf525cbba6d5251b60441/COC-.gif",
        caption=caption,
        parse_mode='Markdown',
        reply_markup=markup
    )
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("إنشاء قرية"))
def create_village(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT * FROM players WHERE id=?", (user_id,))
    if c.fetchone():
        bot.reply_to(message, "لديك قرية بالفعل! اكتب '**معلوماتي**' لرؤيتها.", parse_mode='Markdown')
    else:
        now = datetime.now().isoformat()
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip() or f"User{user_id}"
        c.execute("INSERT INTO players (id, username, last_collect, last_activity, troops) VALUES (?, ?, ?, ?, '{}')", 
                  (user_id, full_name, now, now))
        conn.commit()
        bot.reply_to(message, "تم إنشاء قريتك المستوى **1**! 🎉\nلديك **1000** ذهب و**1000** إكسير. ابدأ بتجميع الموارد. 🌟", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "معلوماتي")
def my_info(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT level, gold, elixir, trophies, troops, clan_name FROM players WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        level, gold, elixir, trophies, troops_str, clan_name = row
        troops = json.loads(troops_str)
        info = f"📊 **معلومات قريتك**:\n**مستوى**: {level} 🏰\n**ذهب**: {gold} 💰\n**إكسير**: {elixir} 🧪\n**كؤوس**: {trophies} 🏆\n**تحالف**: {clan_name or 'لا يوجد'} 👥\n**جنود**: {troops} 💂"
        bot.reply_to(message, info, parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً بكتابة '**إنشاء قرية**'.", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "تجميع موارد")
def collect_resources(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT level, last_collect FROM players WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        level, last_collect = row
        now = datetime.now()
        last = datetime.fromisoformat(last_collect)
        hours = (now - last).total_seconds() / 3600
        production = int(100 * level * hours)
        c.execute("UPDATE players SET gold = gold + ?, elixir = elixir + ?, last_collect = ? WHERE id=?",
                  (production, production, now.isoformat(), user_id))
        conn.commit()
        bot.reply_to(message, f"جمعت **{production}** ذهب و **{production}** إكسير! ⛏️✨", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً!", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("ترقية قرية"))
def upgrade_village(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT level, gold FROM players WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        level, gold = row
        cost = 1000 * level
        if gold >= cost:
            c.execute("UPDATE players SET level = level + 1, gold = gold - ? WHERE id=?", (cost, user_id))
            conn.commit()
            bot.reply_to(message, f"تم ترقية قريتك إلى مستوى **{level + 1}**! 🏰🎊\nتكلفة: **{cost}** ذهب.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"ليس لديك ذهب كافٍ! مطلوب: **{cost}** 💸", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً!", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("تدريب جنود "))
def train_troops(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    parts = message.text.split()[2:]
    if len(parts) != 2:
        bot.reply_to(message, "الصيغة: **تدريب جنود [نوع] [عدد]**، مثل 'بربري 10' 💡", parse_mode='Markdown')
        time.sleep(0.1)
        return
    troop_type, count_str = parts
    if troop_type not in TROOP_STATS:
        bot.reply_to(message, "نوع غير موجود! المتاح: **بربري**، **آرشر**، **عملاق**، **ساحر** ⚠️", parse_mode='Markdown')
        time.sleep(0.1)
        return
    try:
        count = int(count_str)
    except:
        bot.reply_to(message, "عدد غير صالح! ❌", parse_mode='Markdown')
        time.sleep(0.1)
        return

    c.execute("SELECT level, elixir, troops FROM players WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        level, elixir, troops_str = row
        troops = json.loads(troops_str)
        cost = TROOP_STATS[troop_type]['cost'] * count
        space = TROOP_STATS[troop_type]['space'] * count
        current_space = sum(TROOP_STATS[t]['space'] * c for t, c in troops.items())
        max_space = get_army_capacity(level)
        if current_space + space > max_space:
            bot.reply_to(message, f"مساحة الجيش غير كافية! الحالي: **{current_space}/{max_space}** 📏", parse_mode='Markdown')
            time.sleep(0.1)
            return
        if elixir < cost:
            bot.reply_to(message, f"إكسير غير كافٍ! تكلفة: **{cost}** 🧪", parse_mode='Markdown')
            time.sleep(0.1)
            return
        troops[troop_type] = troops.get(troop_type, 0) + count
        c.execute("UPDATE players SET elixir = elixir - ?, troops = ? WHERE id=?", (cost, json.dumps(troops), user_id))
        conn.commit()
        bot.reply_to(message, f"تم تدريب **{count} {troop_type}**! 💂🔥", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً! 🏘️", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "جنودي")
def my_troops(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT troops FROM players WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        troops = json.loads(row[0])
        bot.reply_to(message, f"**جنودك**: {troops} 💪", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً! 🏘️", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "هجوم كلانس")
def start_battle(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT id, username, level, troops, gold, elixir FROM players WHERE id != ? AND id NOT IN (SELECT id FROM banned) ORDER BY RANDOM() LIMIT 1", (user_id,))
    opponent_row = c.fetchone()
    if not opponent_row:
        bot.reply_to(message, "لا يوجد خصوم متاحين حالياً! 🔍", parse_mode='Markdown')
        time.sleep(0.1)
        return
    opp_id, opp_username, opp_level, opp_troops, opp_gold, opp_elixir = opponent_row
    c.execute("SELECT level, troops, clan_name FROM players WHERE id=?", (user_id,))
    player_row = c.fetchone()
    if not player_row:
        bot.reply_to(message, "أنشئ قرية أولاً! 🏘️", parse_mode='Markdown')
        time.sleep(0.1)
        return
    level, troops_str, clan_name = player_row
    if abs(level - opp_level) > 1:
        bot.reply_to(message, "لا يوجد خصم بنفس المستوى! جرب لاحقاً. ⏳", parse_mode='Markdown')
        time.sleep(0.1)
        return
    show_opponent_info(message.chat.id, opp_id, opp_username, opp_level, opp_troops, opp_gold, opp_elixir, user_id)
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("إنشاء تحالف "))
def create_clan(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    if message.chat.type != 'group':
        bot.reply_to(message, "استخدم هذا في مجموعة! 👥", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    clan_name = ' '.join(message.text.split()[2:])
    if not clan_name:
        bot.reply_to(message, "الصيغة: **إنشاء تحالف [اسم]** 📝", parse_mode='Markdown')
        time.sleep(0.1)
        return
    c.execute("SELECT * FROM clans WHERE name=?", (clan_name,))
    if c.fetchone():
        bot.reply_to(message, "التحالف موجود بالفعل! ⚠️", parse_mode='Markdown')
        time.sleep(0.1)
        return
    cost_gold, cost_elixir = 50000, 50000
    c.execute("SELECT gold, elixir FROM players WHERE id=?", (user_id,))
    row = c.fetchone()
    if row and row[0] >= cost_gold and row[1] >= cost_elixir:
        c.execute("UPDATE players SET gold = gold - ?, elixir = elixir - ?, clan_name = ? WHERE id=?", (cost_gold, cost_elixir, clan_name, user_id))
        members = [user_id]
        c.execute("INSERT INTO clans (name, resources, members) VALUES (?, ?, ?)", (clan_name, json.dumps({'gold':0, 'elixir':0}), json.dumps(members)))
        conn.commit()
        bot.reply_to(message, f"تم إنشاء تحالف **{clan_name}**! 🛡️🎉", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"موارد غير كافية! مطلوب: **50000** ذهب/إكسير. يمكن للأعضاء الدعم. 🤝", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("انضم تحالف "))
def join_clan(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    clan_name = ' '.join(message.text.split()[2:])
    if not clan_name:
        bot.reply_to(message, "الصيغة: **انضم تحالف [اسم]** 📝", parse_mode='Markdown')
        time.sleep(0.1)
        return
    c.execute("SELECT members FROM clans WHERE name=?", (clan_name,))
    row = c.fetchone()
    if row:
        members = json.loads(row[0])
        if user_id in members:
            bot.reply_to(message, "أنت عضو بالفعل! 👤", parse_mode='Markdown')
            time.sleep(0.1)
            return
        members.append(user_id)
        c.execute("UPDATE clans SET members = ? WHERE name=?", (json.dumps(members), clan_name))
        c.execute("UPDATE players SET clan_name = ? WHERE id=?", (clan_name, user_id))
        conn.commit()
        bot.reply_to(message, f"انضممت إلى **{clan_name}**! 👥🎊", parse_mode='Markdown')
    else:
        bot.reply_to(message, "التحالف غير موجود! ⚠️", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("دعم تحالف "))
def support_clan(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    parts = message.text.split()[2:]
    if len(parts) != 2:
        bot.reply_to(message, "الصيغة: **دعم تحالف [نوع: ذهب/إكسير] [كمية]** 📝", parse_mode='Markdown')
        time.sleep(0.1)
        return
    resource_type, amount_str = parts
    if resource_type not in ['ذهب', 'إكسير']:
        bot.reply_to(message, "نوع: **ذهب** أو **إكسير** ⚠️", parse_mode='Markdown')
        time.sleep(0.1)
        return
    try:
        amount = int(amount_str)
    except:
        bot.reply_to(message, "كمية غير صالحة! ❌", parse_mode='Markdown')
        time.sleep(0.1)
        return

    user_id = message.from_user.id
    c.execute("SELECT clan_name FROM players WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        clan_name = row[0]
    else:
        clan_name = None
    if not clan_name:
        bot.reply_to(message, "انضم إلى تحالف أولاً! 👥", parse_mode='Markdown')
        time.sleep(0.1)
        return

    field = 'gold' if resource_type == 'ذهب' else 'elixir'
    c.execute(f"SELECT {field} FROM players WHERE id=?", (user_id,))
    if c.fetchone()[0] < amount:
        bot.reply_to(message, "موارد غير كافية! 💸", parse_mode='Markdown')
        time.sleep(0.1)
        return

    c.execute(f"UPDATE players SET {field} = {field} - ? WHERE id=?", (amount, user_id))
    c.execute("SELECT resources, level FROM clans WHERE name=?", (clan_name,))
    res_str, level = c.fetchone()
    resources = json.loads(res_str)
    resources[field] += amount
    next_cost = 10000 * level
    if resources['gold'] >= next_cost and resources['elixir'] >= next_cost and level < 10:
        c.execute("UPDATE clans SET level = level + 1, resources = ? WHERE name=?", (json.dumps({'gold':0, 'elixir':0}), clan_name))
        bot.reply_to(message, f"تم ترقية التحالف إلى مستوى **{level + 1}**! 📈🎉", parse_mode='Markdown')
    else:
        c.execute("UPDATE clans SET resources = ? WHERE name=?", (json.dumps(resources), clan_name))
    conn.commit()
    bot.reply_to(message, f"تم دعم **{amount} {resource_type}**! 🤝✨", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("تحويل "))
def transfer(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    parts = message.text.split()[1:]
    if len(parts) != 3:
        bot.reply_to(message, "الصيغة: **تحويل [ID] [نوع: ذهب/إكسير] [كمية]** 📝", parse_mode='Markdown')
        time.sleep(0.1)
        return
    try:
        target_id = int(parts[0])
        resource_type = parts[1]
        amount = int(parts[2])
    except:
        bot.reply_to(message, "بيانات غير صالحة! ❌", parse_mode='Markdown')
        time.sleep(0.1)
        return
    if resource_type not in ['ذهب', 'إكسير']:
        bot.reply_to(message, "نوع: **ذهب** أو **إكسير** ⚠️", parse_mode='Markdown')
        time.sleep(0.1)
        return

    user_id = message.from_user.id
    c.execute("SELECT clan_name FROM players WHERE id=?", (user_id,))
    clan_name = c.fetchone()[0]
    c.execute("SELECT clan_name FROM players WHERE id=?", (target_id,))
    target_clan = c.fetchone()
    if not target_clan or target_clan[0] != clan_name:
        bot.reply_to(message, "المتلقي ليس في نفس التحالف أو غير موجود! 👥", parse_mode='Markdown')
        time.sleep(0.1)
        return

    field = 'gold' if resource_type == 'ذهب' else 'elixir'
    c.execute(f"SELECT {field} FROM players WHERE id=?", (user_id,))
    if c.fetchone()[0] < amount:
        bot.reply_to(message, "موارد غير كافية! 💸", parse_mode='Markdown')
        time.sleep(0.1)
        return

    c.execute("SELECT level FROM clans WHERE name=?", (clan_name,))
    clan_level = c.fetchone()[0]
    bonus = amount * (0.02 * clan_level)
    total = amount + int(bonus)

    c.execute(f"UPDATE players SET {field} = {field} - ? WHERE id=?", (amount, user_id))
    c.execute(f"UPDATE players SET {field} = {field} + ? WHERE id=?", (total, target_id))
    conn.commit()
    bot.reply_to(message, f"تم تحويل **{amount} {resource_type}** (مع مكافأة **{int(bonus)}**) إلى ID **{target_id}**! 💸🎁", parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "توب لاعبين")
def top_players(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT username, id, trophies FROM players WHERE id NOT IN (SELECT id FROM banned) ORDER BY trophies DESC LIMIT 10")
    tops = c.fetchall()
    text = "**🏆 توب 10 لاعبين**:\n"
    for i, (username, uid, trophies) in enumerate(tops, 1):
        if user_id == OWNER_ID:
            text += f"{i}. **{username}** (ID: {uid}): **{trophies}** كؤوس\n"
        else:
            text += f"{i}. **{username}**: **{trophies}** كؤوس\n"
    text += "\n*أي إساءة مخالفة وغير لائقة سوف يحظر من التوب.* ⚠️"
    bot.reply_to(message, text, parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "توب تحالفات")
def top_clans(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    c.execute("SELECT name, level FROM clans ORDER BY level DESC LIMIT 10")
    tops = c.fetchall()
    text = "**🏆 توب 10 تحالفات**:\n"
    for i, (name, level) in enumerate(tops, 1):
        text += f"{i}. **{name}**: مستوى **{level}**\n"
    text += "\n*أي إساءة مخالفة وغير لائقة سوف يحظر من التوب.* ⚠️"
    bot.reply_to(message, text, parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), message.from_user.id))
    conn.commit()
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "التعليمات")
def instructions(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    instructions_text = """
📜 **تعليمات اللعبة الكاملة: كلاش أوف كلانس التليجرامي** 🎮

هذه اللعبة مصغرة مستوحاة من Clash of Clans، حيث تبني قريتك، تدرب جيشك، وتحارب الآخرين عبر تليجرام. اللعبة متعددة اللاعبين، مع قاعدة بيانات مشتركة لجميع المجموعات. كل الأوامر بالعربية!

**1. البداية والقرية**
- انقر **إنشاء قرية** لإنشاء قريتك المستوى 1 (تبدأ بـ**1000** ذهب وإكسير).
- **معلوماتي**: يعرض مستوى قريتك، الموارد، الكؤوس، والجنود.
- **ترقية قرية**: يرقي مستوى قريتك (تكلف ذهب متزايد، مثل **1000** للمستوى 2). المستويات تزيد سعة الجيش (مثل **100** في L1، حتى **1000** في L10).

**2. الموارد**
- الموارد: **ذهب** (للترقيات) و**إكسير** (لتدريب الجنود).
- تنتج تلقائياً كل ساعة (**100** لكل مستوى قرية).
- **تجميع موارد**: يجمع ما تراكم منذ آخر جمع.

**3. الجنود**
- أنواع: **بربري** (قوي في العدد)، **آرشر** (هجوم عن بعد)، **عملاق** (صحة عالية، يستهدف الدفاعات)، **ساحر** (دمج قوي للمجموعات).
- **تدريب جنود**: انقر لتدريب جنود مثل "بربري 10". يكلف إكسير.
- قوتهم تتضاعف بنسبة **10%** لكل مستوى قرية.
- **جنودي**: يعرض جنودك الحاليين.

**4. المعارك**
- **هجوم كلانس**: يبحث عن خصم عشوائي بنفس المستوى (±1).
- مدة: **5** دقائق (يرسل تحديثات كل دقيقة).
- الفوز يعتمد على قوة الجيش مع عامل عشوائي.
- **نجوم**: **1** لـ**50%** تدمير، **2** لـ**75%**، **3** لـ**100%**. تحصل على كؤوس وغنائم.

**5. التحالفات (الكلانس)**
- **إنشاء تحالف**: في مجموعة تليجرام، تكلف **50,000** ذهب/إكسير.
- **انضم تحالف**: للانضمام إلى تحالف موجود.
- **دعم تحالف**: يجمع موارد لترقية التحالف (حتى L**10**).
- فوائد: زيادة موارد بنسبة **2%** لكل مستوى، +**1** مستوى للجنود بعد L**5**.
- **تحويل**: لتبادل موارد مع أعضاء التحالف.

**6. التوب**
- **توب لاعبين**: أعلى **10** كؤوس.
- **توب تحالفات**: أعلى **10** مستويات.

**نصائح عامة**:
- اللعبة حية: تغييراتك تحفظ فوراً.
- استمتع باللعب! ⚔️🏰
    """
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("إنشاء قرية", callback_data=f"cmd:إنشاء قرية:{user_id}"),
        InlineKeyboardButton("معلوماتي", callback_data=f"cmd:معلوماتي:{user_id}"),
        InlineKeyboardButton("تجميع موارد", callback_data=f"cmd:تجميع موارد:{user_id}"),
        InlineKeyboardButton("ترقية قرية", callback_data=f"cmd:ترقية قرية:{user_id}"),
        InlineKeyboardButton("تدريب جنود", callback_data=f"cmd:تدريب جنود:{user_id}"),
        InlineKeyboardButton("جنودي", callback_data=f"cmd:جنودي:{user_id}"),
        InlineKeyboardButton("هجوم كلانس", callback_data=f"cmd:هجوم كلانس:{user_id}"),
        InlineKeyboardButton("إنشاء تحالف", callback_data=f"cmd:إنشاء تحالف:{user_id}"),
        InlineKeyboardButton("انضم تحالف", callback_data=f"cmd:انضم تحالف:{user_id}"),
        InlineKeyboardButton("دعم تحالف", callback_data=f"cmd:دعم تحالف:{user_id}"),
        InlineKeyboardButton("تحويل", callback_data=f"cmd:تحويل:{user_id}"),
        InlineKeyboardButton("توب لاعبين", callback_data=f"cmd:توب لاعبين:{user_id}"),
        InlineKeyboardButton("توب تحالفات", callback_data=f"cmd:توب تحالفات:{user_id}")
    ]
    markup.add(*buttons)
    bot.reply_to(message, instructions_text, parse_mode='Markdown', reply_markup=markup)
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    time.sleep(0.1)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cmd:"))
def command_callback(call):
    parts = call.data.split(":")
    command = parts[1]
    target_user_id = int(parts[2])
    user_id = call.from_user.id

    # التحقق من هوية المستخدم
    if user_id != target_user_id:
        bot.answer_callback_query(call.id, "هذه القائمة ليست لك! استخدم /التعليمات بنفسك. 🚫", show_alert=True)
        return

    # تنفيذ الأوامر
    if command == "إنشاء قرية":
        c.execute("SELECT * FROM players WHERE id=?", (user_id,))
        if c.fetchone():
            bot.answer_callback_query(call.id, "لديك قرية بالفعل! اكتب 'معلوماتي' لرؤيتها.", show_alert=True)
        else:
            now = datetime.now().isoformat()
            username = call.from_user.first_name or f"User{user_id}"
            c.execute("INSERT INTO players (id, username, last_collect, last_activity, troops) VALUES (?, ?, ?, ?, '{}')", 
                      (user_id, username, now, now))
            conn.commit()
            bot.send_message(call.message.chat.id, "تم إنشاء قريتك المستوى **1**! 🎉\nلديك **1000** ذهب و**1000** إكسير. ابدأ بتجميع الموارد. 🌟", parse_mode='Markdown')
    elif command == "معلوماتي":
        c.execute("SELECT level, gold, elixir, trophies, troops, clan_name FROM players WHERE id=?", (user_id,))
        row = c.fetchone()
        if row:
            level, gold, elixir, trophies, troops_str, clan_name = row
            troops = json.loads(troops_str)
            info = f"📊 **معلومات قريتك**:\n**مستوى**: {level} 🏰\n**ذهب**: {gold} 💰\n**إكسير**: {elixir} 🧪\n**كؤوس**: {trophies} 🏆\n**تحالف**: {clan_name or 'لا يوجد'} 👥\n**جنود**: {troops} 💂"
            bot.send_message(call.message.chat.id, info, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "أنشئ قرية أولاً باستخدام زر 'إنشاء قرية'!", show_alert=True)
    elif command == "تجميع موارد":
        c.execute("SELECT level, last_collect FROM players WHERE id=?", (user_id,))
        row = c.fetchone()
        if row:
            level, last_collect = row
            now = datetime.now()
            last = datetime.fromisoformat(last_collect)
            hours = (now - last).total_seconds() / 3600
            production = int(100 * level * hours)
            c.execute("UPDATE players SET gold = gold + ?, elixir = elixir + ?, last_collect = ? WHERE id=?", 
                      (production, production, now.isoformat(), user_id))
            conn.commit()
            bot.send_message(call.message.chat.id, f"جمعت **{production}** ذهب و **{production}** إكسير! ⛏️✨", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "أنشئ قرية أولاً!", show_alert=True)
    elif command == "ترقية قرية":
        c.execute("SELECT level, gold FROM players WHERE id=?", (user_id,))
        row = c.fetchone()
        if row:
            level, gold = row
            cost = 1000 * level
            if gold >= cost:
                c.execute("UPDATE players SET level = level + 1, gold = gold - ? WHERE id=?", (cost, user_id))
                conn.commit()
                bot.send_message(call.message.chat.id, f"تم ترقية قريتك إلى مستوى **{level + 1}**! 🏰🎊\nتكلفة: **{cost}** ذهب.", parse_mode='Markdown')
            else:
                bot.answer_callback_query(call.id, f"ليس لديك ذهب كافٍ! مطلوب: **{cost}** 💸", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "أنشئ قرية أولاً!", show_alert=True)
    elif command == "تدريب جنود":
        bot.send_message(call.message.chat.id, "أدخل الأمر بالصيغة: **تدريب جنود [نوع] [عدد]**، مثل 'تدريب جنود بربري 10' 💂", parse_mode='Markdown')
    elif command == "جنودي":
        c.execute("SELECT troops FROM players WHERE id=?", (user_id,))
        row = c.fetchone()
        if row:
            troops = json.loads(row[0])
            bot.send_message(call.message.chat.id, f"**جنودك**: {troops} 💪", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "أنشئ قرية أولاً!", show_alert=True)
    if command == "هجوم كلانس":
        c.execute("SELECT id, username, level, troops, gold, elixir FROM players WHERE id != ? AND id NOT IN (SELECT id FROM banned) ORDER BY RANDOM() LIMIT 1", (user_id,))
        opponent_row = c.fetchone()
        if not opponent_row:
            bot.answer_callback_query(call.id, "لا يوجد خصوم متاحين حالياً! 🔍", show_alert=True)
            return
        opp_id, opp_username, opp_level, opp_troops, opp_gold, opp_elixir = opponent_row
        c.execute("SELECT level, troops, clan_name FROM players WHERE id=?", (user_id,))
        player_row = c.fetchone()
        if not player_row:
            bot.answer_callback_query(call.id, "أنشئ قرية أولاً! 🏘️", show_alert=True)
            return
        level, troops_str, clan_name = player_row
        if abs(level - opp_level) > 1:
            bot.answer_callback_query(call.id, "لا يوجد خصم بنفس المستوى! جرب لاحقاً. ⏳", show_alert=True)
            return
        show_opponent_info(call.message.chat.id, opp_id, opp_username, opp_level, opp_troops, opp_gold, opp_elixir, user_id)
    elif command == "إنشاء تحالف":
        bot.send_message(call.message.chat.id, "أدخل الأمر بالصيغة: **إنشاء تحالف [اسم]** في مجموعة تليجرام 📝", parse_mode='Markdown')
    elif command == "انضم تحالف":
        bot.send_message(call.message.chat.id, "أدخل الأمر بالصيغة: **انضم تحالف [اسم]** 📝", parse_mode='Markdown')
    elif command == "دعم تحالف":
        bot.send_message(call.message.chat.id, "أدخل الأمر بالصيغة: **دعم تحالف [نوع: ذهب/إكسير] [كمية]** 📝", parse_mode='Markdown')
    elif command == "تحويل":
        bot.send_message(call.message.chat.id, "أدخل الأمر بالصيغة: **تحويل [ID] [نوع: ذهب/إكسير] [كمية]** 📝", parse_mode='Markdown')
    elif command == "توب لاعبين":
        c.execute("SELECT id, username, trophies FROM players WHERE id NOT IN (SELECT id FROM banned) ORDER BY trophies DESC LIMIT 10")
        tops = c.fetchall()
        text = "**🏆 توب 10 لاعبين**:\n"
        for i, (uid, username, trophies) in enumerate(tops, 1):
            if user_id == OWNER_ID:
                text += f"{i}. <a href='tg://user?id={uid}'>{username or f'User{uid}'}</a> (ID: {uid}): **{trophies}** كؤوس\n"
            else:
                text += f"{i}. <a href='tg://user?id={uid}'>{username or f'User{uid}'}</a>: **{trophies}** كؤوس\n"
        text += "\n*أي إساءة مخالفة وغير لائقة سوف يحظر من التوب.* ⚠️"
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    elif command == "توب تحالفات":
        c.execute("SELECT name, level FROM clans ORDER BY level DESC LIMIT 10")
        tops = c.fetchall()
        text = "**🏆 توب 10 تحالفات**:\n"
        for i, (name, level) in enumerate(tops, 1):
            text += f"{i}. **{name}**: مستوى **{level}**\n"
        text += "\n*أي إساءة مخالفة وغير لائقة سوف يحظر من التوب.* ⚠️"
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    c.execute("UPDATE players SET last_activity = ? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    bot.answer_callback_query(call.id)
    time.sleep(0.1)

@bot.callback_query_handler(func=lambda call: call.data.startswith("attack:") or call.data.startswith("revenge:"))
def start_attack(call):
    parts = call.data.split(":")
    action = parts[0]
    opp_id = int(parts[1])
    user_id = int(parts[2])
    if user_id != call.from_user.id:
        bot.answer_callback_query(call.id, "هذا الهجوم ليس لك! 🚫", show_alert=True)
        return
    c.execute("SELECT username, level, troops, gold, elixir, clan_name FROM players WHERE id=?", (opp_id,))
    opponent_row = c.fetchone()
    if not opponent_row:
        bot.answer_callback_query(call.id, "الخصم غير متاح! 🔍", show_alert=True)
        return
    opp_username, opp_level, opp_troops, opp_gold, opp_elixir, opp_clan = opponent_row
    c.execute("SELECT level, troops, clan_name FROM players WHERE id=?", (user_id,))
    player_row = c.fetchone()
    if not player_row:
        bot.answer_callback_query(call.id, "أنشئ قرية أولاً! 🏘️", show_alert=True)
        return
    level, troops_str, clan_name = player_row
    bot.send_message(
        call.message.chat.id,
        f"🚀 <b>بدأت معركة ضد:</b> <a href='tg://user?id={opp_id}'>{opp_username}</a> مستوى **{opp_level}**! ⚔️💥\nمدة: 5 دقائق. انتظر التحديثات.",
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

    support_troops = {}
    if clan_name:
        c.execute("SELECT troop_storage, level FROM clans WHERE name=?", (clan_name,))
        clan_row = c.fetchone()
        if clan_row:
            support_troops = json.loads(clan_row[0])

    def battle_thread():
        attacker_power = calculate_army_power(troops_str, level)
        defender_hp = calculate_village_hp(opp_troops, opp_level)
        destruction = 0
        for minute in range(5):
            damage = attacker_power * random.uniform(0.8, 1.2)
            if support_troops:
                support_power = calculate_army_power(json.dumps(support_troops), level)
                damage += support_power
            defender_hp -= damage
            destruction = min(100, destruction + random.randint(10, 30))
            markup = InlineKeyboardMarkup()
            if destruction < 50:
                markup.add(InlineKeyboardButton("انسحاب 🏃", callback_data=f"withdraw:{user_id}:{opp_id}:{destruction}"))
            bot.send_message(
                call.message.chat.id,
                f"🕒 <b>دقيقة {minute+1}:</b> دمرت **{destruction}%** من الخصم! 🔥💥",
                reply_markup=markup,
                parse_mode='Markdown'
            )
            if destruction >= 100:
                bot.send_message(call.message.chat.id, "🏆 <b>انتصرت! تدمير كامل 100%!</b> 🎉", parse_mode='Markdown')
                break
            time.sleep(60)  # أو 1 للاختبار

        stars = 0
        if destruction >= 50: stars = 1
        if destruction >= 75: stars = 2
        if destruction == 100: stars = 3
        trophy_offer = 30
        trophies_won = stars * (trophy_offer // 3)
        loot_percent = 0.1 + 0.05 * (stars - 1)
        loot = int(loot_percent * 1000 * level)
        loss_percent = 1 if stars == 0 else (0.5 if stars < 3 else 0.2)
        new_troops = lose_troops(troops_str, loss_percent)
        c.execute("UPDATE players SET trophies = trophies + ?, gold = gold + ?, elixir = elixir + ?, troops = ?, last_attack_id = ? WHERE id=?", 
                  (trophies_won, loot, loot, new_troops, opp_id, user_id))
        c.execute("UPDATE players SET trophies = trophies - ?, gold = gold - ?, elixir = elixir - ?, last_attack_id = ? WHERE id=?", 
                  (trophies_won, loot, loot, user_id, opp_id))
        conn.commit()
        bot.send_message(
            call.message.chat.id,
            f"📜 <b>انتهت المعركة!</b>\nنجوم: **{stars}** ⭐✨\nكؤوس مكتسبة: **{trophies_won}** 🏆\nغنائم: **{loot}** ذهب/إكسير\nخسرت **{int(loss_percent*100)}%** من جنودك. 💂",
            parse_mode='Markdown'
        )
        try:
            revenge_markup = InlineKeyboardMarkup()
            revenge_markup.add(InlineKeyboardButton("انتقام ⚔️", callback_data=f"revenge:{user_id}:{opp_id}"))
            bot.send_message(
                opp_id,
                f"🛑 <b>تعرضت للهجوم من:</b> <a href='tg://user?id={user_id}'>{call.from_user.first_name}</a>!\n"
                f"خسرت <b>{trophies_won}</b> كؤوس و<b>{loot}</b> موارد.\n"
                f"📢 <b>هل ترغب بالانتقام؟</b>",
                parse_mode='HTML',
                reply_markup=revenge_markup
            )
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 403:
                c.execute("DELETE FROM players WHERE id=?", (opp_id,))
                conn.commit()
                bot.send_message(OWNER_ID, f"حذفت قرية ID {opp_id} لأنه حظر البوت.", parse_mode='Markdown')
    threading.Thread(target=battle_thread).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw:") or call.data.startswith("next_opponent:"))
def battle_actions(call):
    parts = call.data.split(":")
    action = parts[0]
    user_id = int(parts[1])
    if user_id != call.from_user.id:
        bot.answer_callback_query(call.id, "هذا الإجراء ليس لك! 🚫", show_alert=True)
        return
    if action == "withdraw":
        opp_id = int(parts[2])
        destruction = int(parts[3])  # احصل على destruction الحالي
        stars = 0
        if destruction >= 50: stars = 1
        if destruction >= 75: stars = 2
        if destruction == 100: stars = 3
        trophy_offer = 30
        trophies_won = (stars * (trophy_offer // 3)) // 2  # نسبة قليلة عند الانسحاب
        loot_percent = 0.1 + 0.05 * (stars - 1)
        loot = int(loot_percent * 1000 * (stars / 3))  # نسبة بناءً على النجوم
        loss_percent = 0.5 if stars < 2 else 0.3  # خسارة جزئية
        new_troops = lose_troops(troops_str, loss_percent)
        c.execute("UPDATE players SET trophies = trophies + ?, gold = gold + ?, elixir = elixir + ?, troops = ? WHERE id=?", 
                  (trophies_won, loot, loot, new_troops, user_id))
        c.execute("UPDATE players SET trophies = trophies - ? WHERE id=?", (trophies_won, opp_id))
        conn.commit()
        bot.send_message(call.message.chat.id, f"انسحبت من المعركة! خسرت **10** كؤوس، لكن حصلت على **{loot}** موارد بناءً على {stars} نجوم. 🏃", parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    elif action == "next_opponent":
        c.execute("SELECT id, username, level, troops, gold, elixir FROM players WHERE id != ? AND id NOT IN (SELECT id FROM banned) ORDER BY RANDOM() LIMIT 1", (user_id,))
        opponent_row = c.fetchone()
        if not opponent_row:
            bot.answer_callback_query(call.id, "لا يوجد خصوم متاحين حالياً! 🔍", show_alert=True)
            return
        opp_id, opp_username, opp_level, opp_troops, opp_gold, opp_elixir = opponent_row
        show_opponent_info(call.message.chat.id, opp_id, opp_username, opp_level, opp_troops, opp_gold, opp_elixir, user_id)
        bot.answer_callback_query(call.id)

@bot.message_handler(commands=['ban'])
def ban_user(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "عذراً، هذا الأمر متاح فقط للمالك! 🚫", parse_mode='Markdown')
        time.sleep(0.1)
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "الصيغة: /ban [ID]", parse_mode='Markdown')
        time.sleep(0.1)
        return
    try:
        ban_id = int(parts[1])
    except:
        bot.reply_to(message, "ID غير صالح! ❌", parse_mode='Markdown')
        time.sleep(0.1)
        return
    c.execute("INSERT OR IGNORE INTO banned (id) VALUES (?)", (ban_id,))
    c.execute("DELETE FROM players WHERE id=?", (ban_id,))
    conn.commit()
    bot.reply_to(message, f"تم حظر ID **{ban_id}** من التوب واللعبة! 🔒", parse_mode='Markdown')
    time.sleep(0.1)

@bot.message_handler(commands=['rest'])
def restart_bot(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "عذراً، هذا الأمر متاح فقط للمالك! 🚫", parse_mode='Markdown')
        time.sleep(0.1)
        return

    try:
        bot.reply_to(message, "جاري جلب التحديثات من GitHub... 🔄", parse_mode='Markdown')
        subprocess.run(['git', 'pull'], check=True, capture_output=True, text=True)
        bot.reply_to(message, "تم جلب التحديثات! إعادة تشغيل... 🔄", parse_mode='Markdown')
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        bot.reply_to(message, f"خطأ: {str(e)} ❌", parse_mode='Markdown')
    time.sleep(0.1)

# تشغيل البوت
bot.polling()