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
              troop_storage TEXT DEFAULT '{}')''')  # resources: {'gold':0, 'elixir':0}, troop_storage: JSON جنود
conn.commit()

OWNER_ID = 6789179634  # غير إلى ID تليجرام الخاص بك
CHANNEL_ID = -1002012804950  # غير إلى ID القناة (مثل -100xxxxxxxxxx)
CHANNEL_USERNAME = '@SYR_SB'  # غير إلى username القناة بدون @

# دالة للتحقق من الاشتراك
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

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

    bot.reply_to(message, "أهلاً بك في بوت **كلاش أوف كلانس** التليجرامي! 🎮\n"
                          "هنا تبني قريتك المصغرة، تدرب جيشك، وتحارب أصدقاءك أو أعداء عشوائيين.\n"
                          "ابدأ بكتابة 'إنشاء قرية' لإنشاء قريتك.\n"
                          "للمزيد وفهم اللعبة، اكتب 'التعليمات' واقرأ قواعد اللعبة.", reply_markup=markup, parse_mode='Markdown')
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
        c.execute("INSERT INTO players (id, last_collect, troops) VALUES (?, ?, '{}')", (user_id, now))
        conn.commit()
        bot.reply_to(message, "تم إنشاء قريتك المستوى **1**! 🎉\nلديك **1000** ذهب و**1000** إكسير. ابدأ بتجميع الموارد.", parse_mode='Markdown')
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
        info = f"📊 **معلومات قريتك**:\n**مستوى**: {level}\n**ذهب**: {gold}\n**إكسير**: {elixir}\n**كؤوس**: {trophies}\n**تحالف**: {clan_name or 'لا يوجد'}\n**جنود**: {troops}"
        bot.reply_to(message, info, parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً بكتابة '**إنشاء قرية**'.", parse_mode='Markdown')
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
        bot.reply_to(message, f"جمعت **{production}** ذهب و **{production}** إكسير! ⛏️", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً!", parse_mode='Markdown')
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
            bot.reply_to(message, f"تم ترقية قريتك إلى مستوى **{level + 1}**! 🏰\nتكلفة: **{cost}** ذهب.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"ليس لديك ذهب كافٍ! مطلوب: **{cost}**", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً!", parse_mode='Markdown')
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
        bot.reply_to(message, "الصيغة: **تدريب جنود [نوع] [عدد]**، مثل 'بربري 10'", parse_mode='Markdown')
        time.sleep(0.1)
        return
    troop_type, count_str = parts
    if troop_type not in TROOP_STATS:
        bot.reply_to(message, "نوع غير موجود! المتاح: **بربري**، **آرشر**، **عملاق**، **ساحر**", parse_mode='Markdown')
        time.sleep(0.1)
        return
    try:
        count = int(count_str)
    except:
        bot.reply_to(message, "عدد غير صالح!", parse_mode='Markdown')
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
            bot.reply_to(message, f"مساحة الجيش غير كافية! الحالي: **{current_space}/{max_space}**", parse_mode='Markdown')
            time.sleep(0.1)
            return
        if elixir < cost:
            bot.reply_to(message, f"إكسير غير كافٍ! تكلفة: **{cost}**", parse_mode='Markdown')
            time.sleep(0.1)
            return
        troops[troop_type] = troops.get(troop_type, 0) + count
        c.execute("UPDATE players SET elixir = elixir - ?, troops = ? WHERE id=?", (cost, json.dumps(troops), user_id))
        conn.commit()
        bot.reply_to(message, f"تم تدريب **{count} {troop_type}**! 💂", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً!", parse_mode='Markdown')
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
        bot.reply_to(message, f"**جنودك**: {troops}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "أنشئ قرية أولاً!", parse_mode='Markdown')
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "هجوم كلانس")
def start_battle(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    c.execute("SELECT id, level, troops, trophies, clan_name FROM players WHERE id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
    opponent_row = c.fetchone()
    if not opponent_row:
        bot.reply_to(message, "لا يوجد خصوم متاحين متاحين حالياً!", parse_mode='Markdown')
        time.sleep(0.1)
        return
    opp_id, opp_level, opp_troops, opp_trophies, opp_clan = opponent_row

    c.execute("SELECT level, troops, clan_name FROM players WHERE id=?", (user_id,))
    player_row = c.fetchone()
    if not player_row:
        bot.reply_to(message, "أنشئ قرية أولاً!", parse_mode='Markdown')
        time.sleep(0.1)
        return
    level, troops_str, clan_name = player_row

    if abs(level - opp_level) > 1:
        bot.reply_to(message, "لا يوجد خصم بنفس المستوى! جرب لاحقاً.", parse_mode='Markdown')
        time.sleep(0.1)
        return

    bot.reply_to(message, f"بدأت معركة ضد خصم مستوى **{opp_level}**! ⚔️\nمدة: 5 دقائق. انتظر التحديثات.", parse_mode='Markdown')
    time.sleep(0.1)

    support_troops = {}
    if clan_name:
        c.execute("SELECT troop_storage FROM clans WHERE name=?", (clan_name,))
        clan_row = c.fetchone()
        if clan_row:
            support_troops = json.loads(clan_row[0])

    def battle_thread():
        attacker_power = calculate_army_power(troops_str, level)
        defender_hp = calculate_village_hp(opp_troops, opp_level)
        destruction = 0
        for minute in range(5):
            time.sleep(60)  # أو 1 للاختبار
            damage = attacker_power * random.uniform(0.8, 1.2)
            if support_troops:
                support_power = calculate_army_power(json.dumps(support_troops), level)
                damage += support_power
            defender_hp -= damage
            destruction = min(100, destruction + 20)
            bot.send_message(message.chat.id, f"دقيقة **{minute+1}**: دمرت **{destruction}%** من الخصم! 🔥", parse_mode='Markdown')
            time.sleep(0.1)

        stars = 0
        if destruction >= 50: stars = 1
        if destruction >= 75: stars = 2
        if destruction == 100: stars = 3
        trophy_offer = 30
        trophies_won = stars * (trophy_offer // 3)
        loot = int(0.1 * stars * 1000)

        c.execute("UPDATE players SET trophies = trophies + ? WHERE id=?", (trophies_won, user_id))
        c.execute("UPDATE players SET trophies = trophies - ? WHERE id=?", (trophies_won, opp_id))
        c.execute("UPDATE players SET gold = gold + ?, elixir = elixir + ? WHERE id=?", (loot, loot, user_id))
        conn.commit()

        bot.send_message(message.chat.id, f"انتهت المعركة! نجوم: **{stars}** ⭐\nكؤوس مكتسبة: **{trophies_won}**\nغنائم: **{loot}** ذهب/إكسير.", parse_mode='Markdown')
        time.sleep(0.1)

    threading.Thread(target=battle_thread).start()

@bot.message_handler(func=lambda m: m.text.lower().startswith("إنشاء تحالف "))
def create_clan(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    if message.chat.type != 'group':
        bot.reply_to(message, "استخدم هذا في مجموعة!", parse_mode='Markdown')
        time.sleep(0.1)
        return
    user_id = message.from_user.id
    clan_name = ' '.join(message.text.split()[2:])
    if not clan_name:
        bot.reply_to(message, "الصيغة: **إنشاء تحالف [اسم]**", parse_mode='Markdown')
        time.sleep(0.1)
        return
    c.execute("SELECT * FROM clans WHERE name=?", (clan_name,))
    if c.fetchone():
        bot.reply_to(message, "التحالف موجود بالفعل!", parse_mode='Markdown')
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
        bot.reply_to(message, f"تم إنشاء تحالف **{clan_name}**! 🛡️", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"موارد غير كافية! مطلوب: **50000** ذهب/إكسير. يمكن للأعضاء الدعم.", parse_mode='Markdown')
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
        bot.reply_to(message, "الصيغة: **انضم تحالف [اسم]**", parse_mode='Markdown')
        time.sleep(0.1)
        return
    c.execute("SELECT members FROM clans WHERE name=?", (clan_name,))
    row = c.fetchone()
    if row:
        members = json.loads(row[0])
        if user_id in members:
            bot.reply_to(message, "أنت عضو بالفعل!", parse_mode='Markdown')
            time.sleep(0.1)
            return
        members.append(user_id)
        c.execute("UPDATE clans SET members = ? WHERE name=?", (json.dumps(members), clan_name))
        c.execute("UPDATE players SET clan_name = ? WHERE id=?", (clan_name, user_id))
        conn.commit()
        bot.reply_to(message, f"انضممت إلى **{clan_name}**! 👥", parse_mode='Markdown')
    else:
        bot.reply_to(message, "التحالف غير موجود!", parse_mode='Markdown')
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("دعم تحالف "))
def support_clan(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    parts = message.text.split()[2:]
    if len(parts) != 2:
        bot.reply_to(message, "الصيغة: **دعم تحالف [نوع: ذهب/إكسير] [كمية]**", parse_mode='Markdown')
        time.sleep(0.1)
        return
    resource_type, amount_str = parts
    if resource_type not in ['ذهب', 'إكسير']:
        bot.reply_to(message, "نوع: **ذهب** أو **إكسير**", parse_mode='Markdown')
        time.sleep(0.1)
        return
    try:
        amount = int(amount_str)
    except:
        bot.reply_to(message, "كمية غير صالحة!", parse_mode='Markdown')
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
        bot.reply_to(message, "انضم إلى تحالف أولاً!", parse_mode='Markdown')
        time.sleep(0.1)
        return

    field = 'gold' if resource_type == 'ذهب' else 'elixir'
    c.execute(f"SELECT {field} FROM players WHERE id=?", (user_id,))
    if c.fetchone()[0] < amount:
        bot.reply_to(message, "موارد غير كافية!", parse_mode='Markdown')
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
        bot.reply_to(message, f"تم ترقية التحالف إلى مستوى **{level + 1}**! 📈", parse_mode='Markdown')
    else:
        c.execute("UPDATE clans SET resources = ? WHERE name=?", (json.dumps(resources), clan_name))
    conn.commit()
    bot.reply_to(message, f"تم دعم **{amount} {resource_type}**! 🤝", parse_mode='Markdown')
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower().startswith("تحويل "))
def transfer(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    parts = message.text.split()[1:]
    if len(parts) != 3:
        bot.reply_to(message, "الصيغة: **تحويل [ID] [نوع: ذهب/إكسير] [كمية]**", parse_mode='Markdown')
        time.sleep(0.1)
        return
    try:
        target_id = int(parts[0])
        resource_type = parts[1]
        amount = int(parts[2])
    except:
        bot.reply_to(message, "بيانات غير صالحة!", parse_mode='Markdown')
        time.sleep(0.1)
        return
    if resource_type not in ['ذهب', 'إكسير']:
        bot.reply_to(message, "نوع: **ذهب** أو **إكسير**", parse_mode='Markdown')
        time.sleep(0.1)
        return

    user_id = message.from_user.id
    c.execute("SELECT clan_name FROM players WHERE id=?", (user_id,))
    clan_name = c.fetchone()[0]
    c.execute("SELECT clan_name FROM players WHERE id=?", (target_id,))
    target_clan = c.fetchone()
    if not target_clan or target_clan[0] != clan_name:
        bot.reply_to(message, "المتلقي ليس في نفس التحالف أو غير موجود!", parse_mode='Markdown')
        time.sleep(0.1)
        return

    field = 'gold' if resource_type == 'ذهب' else 'elixir'
    c.execute(f"SELECT {field} FROM players WHERE id=?", (user_id,))
    if c.fetchone()[0] < amount:
        bot.reply_to(message, "موارد غير كافية!", parse_mode='Markdown')
        time.sleep(0.1)
        return

    # إضافة perk: زيادة بنسبة 2% لكل مستوى تحالف
    c.execute("SELECT level FROM clans WHERE name=?", (clan_name,))
    clan_level = c.fetchone()[0]
    bonus = amount * (0.02 * clan_level)
    total = amount + int(bonus)

    c.execute(f"UPDATE players SET {field} = {field} - ? WHERE id=?", (amount, user_id))
    c.execute(f"UPDATE players SET {field} = {field} + ? WHERE id=?", (total, target_id))
    conn.commit()
    bot.reply_to(message, f"تم تحويل **{amount} {resource_type}** (مع مكافأة **{int(bonus)}**) إلى ID **{target_id}**! 💸", parse_mode='Markdown')
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "توب لاعبين")
def top_players(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    c.execute("SELECT id, trophies FROM players ORDER BY trophies DESC LIMIT 10")
    tops = c.fetchall()
    text = "**🏆 توب 10 لاعبين**:\n"
    for i, (uid, trophies) in enumerate(tops, 1):
        text += f"{i}. ID **{uid}**: **{trophies}** كؤوس\n"
    bot.reply_to(message, text, parse_mode='Markdown')
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
    bot.reply_to(message, text, parse_mode='Markdown')
    time.sleep(0.1)

@bot.message_handler(func=lambda m: m.text.lower() == "التعليمات")
def instructions(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك في القناة أولاً! /start", parse_mode='Markdown')
        time.sleep(0.1)
        return
    instructions_text = """
📜 **تعليمات اللعبة الكاملة: كلاش أوف كلانس التليجرامي** 🎮

هذه اللعبة مصغرة مستوحاة من Clash of Clans، حيث تبني قريتك، تدرب جيشك، وتحارب الآخرين عبر تليجرام. اللعبة متعددة اللاعبين، مع قاعدة بيانات مشتركة لجميع المجموعات. كل الأوامر بالعربية!

**1. البداية والقرية**
- ابدأ بكتابة **إنشاء قرية** لإنشاء قريتك المستوى 1 (تبدأ بـ**1000** ذهب وإكسير).
- **معلوماتي**: يعرض مستوى قريتك، الموارد، الكؤوس، والجنود.
- **ترقية قرية**: يرقي مستوى قريتك (تكلف ذهب متزايد، مثل **1000** للمستوى 2). المستويات تزيد سعة الجيش (مثل **100** في L1، حتى **1000** في L10).

**2. الموارد**
- الموارد: **ذهب** (للترقيات) و**إكسير** (لتدريب الجنود).
- تنتج تلقائياً كل ساعة (**100** لكل مستوى قرية).
- **تجميع موارد**: يجمع ما تراكم منذ آخر جمع.

**3. الجنود**
- أنواع: **بربري** (قوي في العدد)، **آرشر** (هجوم عن بعد)، **عملاق** (صحة عالية، يستهدف الدفاعات)، **ساحر** (دمج قوي للمجموعات).
- **تدريب جنود [نوع] [عدد]**: مثل "تدريب جنود بربري 10". يكلف إكسير، وتحدد المساحة بناءً على مستوى القرية.
- قوتهم تتضاعف بنسبة **10%** لكل مستوى قرية.
- **جنودي**: يعرض جنودك الحاليين.

**4. المعارك**
- **هجوم كلانس**: يبحث عن خصم عشوائي بنفس المستوى (±1).
- مدة: **5** دقائق (يرسل تحديثات كل دقيقة).
- الفوز يعتمد على قوة الجيش (DPS vs HP) مع عامل عشوائي للاستراتيجية (مثل تفوق البرابرة في العدد أو السحرة في الدمج).
- **نجوم**: **1** لـ**50%** تدمير، **2** لـ**75%**، **3** لـ**100%**. تحصل على كؤوس (مثل **10-30**) وغنائم (**10-20%** من موارد الخصم).
- إذا كان لديك تحالف، يمكن إضافة جنود دعم.

**5. التحالفات (الكلانس)**
- **إنشاء تحالف [اسم]**: في مجموعة تليجرام، تكلف **50,000** ذهب/إكسير (أو دعم من الأعضاء).
- **انضم تحالف [اسم]**: للانضمام إلى تحالف موجود.
- **دعم تحالف [نوع] [كمية]**: مثل "دعم تحالف ذهب 1000". يجمع موارد لترقية التحالف (حتى L**10**).
- فوائد: زيادة موارد مرسلة بنسبة **2%** لكل مستوى، +**1** مستوى للجنود بعد L**5**، سعة تخزين جنود متزايدة.
- **تحويل [ID] [نوع] [كمية]**: لتبادل موارد مع أعضاء التحالف (مع مكافآت التحالف).
- الجنود المرسلة تضاف إلى الهجمات كدعم.

**6. التوب**
- **توب لاعبين**: أعلى **10** كؤوس.
- **توب تحالفات**: أعلى **10** مستويات.

**نصائح عامة**:
- اللعبة حية: تغييراتك تحفظ فوراً، ويمكن اللعب عبر مجموعات متعددة.
- للتوازن: حد مساحة الجيش، عشوائية في المعارك لتشجيع الاستراتيجيات.
- استمتع باللعب! ⚔️🏰
    """
    bot.reply_to(message, instructions_text, parse_mode='Markdown')
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

# تشغيل البوت مع polling
bot.polling()