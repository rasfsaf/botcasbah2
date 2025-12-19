# Telegram Casino Bot - С SQLite БД
# Версия: 4.1 - ПРОФЕССИОНАЛЬНАЯ БД ДЛЯ ИГРОКОВ
# Бонус за реферала: 50000 Хэш-Фугас

import asyncio
import sqlite3
import os
import random
import string
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage

# =============== КОНФИГУРАЦИЯ ===============
TOKEN = "8534556244:AAHY2I4IQn0ltUqcATx_SIM4ut_9n_nyTNg"

DATA_DIR = "casino_data"
DB_FILE = os.path.join(DATA_DIR, "casino_players.db")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =============== СОСТОЯНИЯ ===============
class GameStates(StatesGroup):
    main_menu = State()
    roulette_betting = State()
    blackjack_betting = State()
    blackjack_playing = State()
    group_roulette_waiting = State()
    group_blackjack_betting = State()
    group_blackjack_playing = State()

# =============== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===============
group_roulette_games: Dict[int, dict] = {}
group_blackjack_games: Dict[int, dict] = {}

# =============== ИНИЦИАЛИЗАЦИЯ БД ===============
def init_database():
    """Инициализировать базу данных SQLite"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Таблица игроков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            balance INTEGER DEFAULT 1000,
            total_won INTEGER DEFAULT 0,
            total_lost INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            ref_code TEXT UNIQUE NOT NULL,
            invited_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            referral_earnings INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица истории транзакций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            result TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES players(user_id)
        )
    ''')
    
    # Таблица рефералов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL,
            bonus_amount INTEGER DEFAULT 50000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES players(user_id),
            FOREIGN KEY (referred_user_id) REFERENCES players(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ БД инициализирована: {DB_FILE}")

# =============== ФУНКЦИИ РАБОТЫ С БД ===============
def generate_ref_code() -> str:
    """Генерировать уникальный реферальный код"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT ref_code FROM players WHERE ref_code = ?', (code,))
        result = cursor.fetchone()
        conn.close()
        
        if result is None:
            return code

def find_user_by_ref_code(ref_code: str) -> Optional[int]:
    """Найти user_id по реферальному коду"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM players WHERE ref_code = ?', (ref_code,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def get_user(user_id: int) -> dict:
    """Получить данные пользователя или создать новые"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return {
            'user_id': result[0],
            'username': result[1],
            'hash_fugasy': result[2],
            'total_won': result[3],
            'total_lost': result[4],
            'games_played': result[5],
            'ref_code': result[6],
            'invited_by': result[7],
            'referrals_count': result[8],
            'referral_earnings': result[9],
            'created_at': result[10],
            'last_activity': result[11]
        }
    else:
        # Создаём нового игрока
        ref_code = generate_ref_code()
        cursor.execute('''
            INSERT INTO players 
            (user_id, username, balance, ref_code) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'Unknown', 1000, ref_code))
        
        conn.commit()
        conn.close()
        
        return {
            'user_id': user_id,
            'username': 'Unknown',
            'hash_fugasy': 1000,
            'total_won': 0,
            'total_lost': 0,
            'games_played': 0,
            'ref_code': ref_code,
            'invited_by': None,
            'referrals_count': 0,
            'referral_earnings': 0,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }

def save_user(user_id: int, data: dict):
    """Сохранить данные пользователя в БД"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE players SET
        username = ?,
        balance = ?,
        total_won = ?,
        total_lost = ?,
        games_played = ?,
        invited_by = ?,
        referrals_count = ?,
        referral_earnings = ?,
        last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', (
        data['username'],
        data['hash_fugasy'],
        data['total_won'],
        data['total_lost'],
        data['games_played'],
        data['invited_by'],
        data['referrals_count'],
        data['referral_earnings'],
        user_id
    ))
    
    conn.commit()
    conn.close()

def add_transaction(user_id: int, game_type: str, amount: int, result: str):
    """Добавить запись о транзакции"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (user_id, game_type, amount, result)
        VALUES (?, ?, ?, ?)
    ''', (user_id, game_type, amount, result))
    conn.commit()
    conn.close()

def add_referral(referrer_id: int, referred_user_id: int):
    """Добавить запись о реферале"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO referrals (referrer_id, referred_user_id)
        VALUES (?, ?)
    ''', (referrer_id, referred_user_id))
    conn.commit()
    conn.close()

def get_player_stats(user_id: int) -> dict:
    """Получить полную статистику игрока"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    player = cursor.fetchone()
    
    cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user_id,))
    total_transactions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    referral_count = cursor.fetchone()[0]
    
    conn.close()
    
    if player:
        return {
            'username': player[1],
            'balance': player[2],
            'total_won': player[3],
            'total_lost': player[4],
            'games_played': player[5],
            'ref_code': player[6],
            'referrals_count': player[8],
            'referral_earnings': player[9],
            'transactions': total_transactions,
            'created_at': player[10]
        }
    return None

# =============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===============
def declension(num: int, word1: str, word2: str, word5: str) -> str:
    """Правильное склонение слова по числу"""
    if num % 10 == 1 and num % 100 != 11:
        return word1
    elif num % 10 in [2, 3, 4] and num % 100 not in [12, 13, 14]:
        return word2
    else:
        return word5

def format_currency(num: int) -> str:
    """Форматировать число с правильным названием валюты"""
    word = declension(num, "Хэш-Фугас", "Хэш-Фугаса", "Хэш-Фугас")
    return f"**{num}** 🪙 {word}"

def get_user_name(user: types.User) -> str:
    """Получить имя пользователя"""
    return user.first_name or user.username or "Игрок"

def create_main_menu(user: dict, player_name: str) -> str:
    """Создать текст главного меню"""
    ref_info = ""
    if user.get('referrals_count', 0) > 0:
        ref_info = f"\n\n👥 **Рефералов:** {user['referrals_count']}\n💰 **Заработок:** {format_currency(user.get('referral_earnings', 0))}"
    
    welcome_text = f"""
🎰 **ДОБРО ПОЖАЛОВАТЬ В КАЗИНО БАБАХИ!** 🎰

Привет, {player_name}! 👋

Ваш баланс: {format_currency(user['hash_fugasy'])}

**Доступные игры:**
1️⃣ **Рулетка** - классическая игра везения
2️⃣ **Black Jack** - игра против дилера

**Реферальная программа:**
3️⃣ **Мой реф.код** - пригласи друзей и получай 50000 🪙
{ref_info}

Выберите игру или посмотрите статистику!
    """
    return welcome_text

# =============== ГЛАВНОЕ МЕНЮ ===============
@dp.message(Command("babaha"))
async def start_command(message: types.Message, state: FSMContext):
    """Начало работы бота"""
    user_id = message.from_user.id
    player_name = get_user_name(message.from_user)
    
    # Проверяем есть ли реф.код в сообщении
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1].upper()
        referrer_id = find_user_by_ref_code(ref_code)
        
        if referrer_id and referrer_id != user_id:
            user = get_user(user_id)
            
            if user.get('invited_by') is None:
                # Даём 50000 новому игроку
                user['hash_fugasy'] += 50000
                user['invited_by'] = referrer_id
                user['username'] = player_name
                save_user(user_id, user)
                add_transaction(user_id, 'REFERRAL_BONUS', 50000, 'RECEIVED')
                
                # Даём 50000 тому кто пригласил
                referrer = get_user(referrer_id)
                referrer['hash_fugasy'] += 50000
                referrer['referrals_count'] += 1
                referrer['referral_earnings'] += 50000
                save_user(referrer_id, referrer)
                add_transaction(referrer_id, 'REFERRAL_BONUS', 50000, 'EARNED')
                
                # Записываем реферала
                add_referral(referrer_id, user_id)
                
                await message.answer(
                    f"🎉 **БОНУС ЗА РЕФЕРАЛА!** 🎉\n\n"
                    f"✅ Вы получили **50000** 🪙!\n"
                    f"✅ Приглашивший получил **50000** 🪙!\n\n"
                    f"Баланс: {format_currency(user['hash_fugasy'])}"
                )
            else:
                await message.answer(f"⚠️ Вы уже приглашены другим игроком!")
    
    user = get_user(user_id)
    user['username'] = player_name
    save_user(user_id, user)
    
    await state.set_state(GameStates.main_menu)
    welcome_text = create_main_menu(user, player_name)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
            InlineKeyboardButton(text="♠️ Black Jack", callback_data="game_blackjack")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance")
        ],
        [
            InlineKeyboardButton(text="👥 Мой реф.код", callback_data="my_referral")
        ]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

# =============== РЕФЕРАЛЬНЫЙ КОД ===============
@dp.callback_query(lambda c: c.data == "my_referral")
async def show_referral(callback: types.CallbackQuery):
    """Показать реферальный код"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    ref_code = user.get('ref_code', 'ERROR')
    
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"
    
    text = f"""
👥 **РЕФЕРАЛЬНАЯ ПРОГРАММА** 👥

**Ваш код:** `{ref_code}`
**Ссылка:** `{ref_link}`

✅ Друг получит **50000** 🪙
✅ Вы получите **50000** 🪙

**Статистика:**
👥 Рефералов: **{user.get('referrals_count', 0)}**
💰 Заработок: {format_currency(user.get('referral_earnings', 0))}

Скопируй ссылку и отправь друзьям! 🚀
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== РУЛЕТКА ===============
@dp.callback_query(lambda c: c.data == "game_roulette")
async def roulette_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню рулетки"""
    await state.set_state(GameStates.roulette_betting)
    
    text = """
🎡 **РУЛЕТКА** 🎡

Выберите ставку (10-500):
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10 🪙", callback_data="roulette_bet_10"),
            InlineKeyboardButton(text="50 🪙", callback_data="roulette_bet_50"),
            InlineKeyboardButton(text="100 🪙", callback_data="roulette_bet_100")
        ],
        [
            InlineKeyboardButton(text="250 🪙", callback_data="roulette_bet_250"),
            InlineKeyboardButton(text="500 🪙", callback_data="roulette_bet_500")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("roulette_bet_"))
async def roulette_choose_color(callback: types.CallbackQuery, state: FSMContext):
    """Выбор цвета в рулетке"""
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['hash_fugasy'] < bet:
        await callback.answer(f"❌ Недостаточно!", show_alert=True)
        return
    
    await state.update_data(roulette_bet=bet)
    
    text = f"Выберите цвет (ставка: {bet}):"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 Красное", callback_data="roulette_red"),
            InlineKeyboardButton(text="⬛ Чёрное", callback_data="roulette_black")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["roulette_red", "roulette_black"])
async def roulette_spin(callback: types.CallbackQuery, state: FSMContext):
    """Вращение рулетки"""
    data = await state.get_data()
    bet = data.get('roulette_bet', 10)
    chosen_color = "Красное" if callback.data == "roulette_red" else "Чёрное"
    
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    result_color = random.choices(["Красное", "Чёрное"], weights=[48.6, 51.4])[0]
    is_win = result_color == chosen_color
    
    if is_win:
        user['hash_fugasy'] += bet
        user['total_won'] += bet
        result_text = f"🎉 **ВЫИГРЫШ!** +{bet} 🪙"
        add_transaction(user_id, 'ROULETTE', bet, f'WON_{chosen_color}')
    else:
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        result_text = f"😢 **ПРОИГРЫШ!** -{bet} 🪙"
        add_transaction(user_id, 'ROULETTE', bet, f'LOST_{chosen_color}')
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    text = f"{result_text}\n\nБаланс: {format_currency(user['hash_fugasy'])}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Ещё", callback_data="game_roulette"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== BLACK JACK ===============
def calculate_hand(cards: List[str]) -> tuple:
    """Рассчитать значение руки"""
    total = 0
    aces = 0
    for card in cards:
        if card == 'A':
            aces += 1
            total += 11
        elif card in ['J', 'Q', 'K']:
            total += 10
        else:
            total += int(card)
    
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    
    return total, aces

def is_blackjack(cards: List[str]) -> bool:
    """Проверить Black Jack"""
    if len(cards) != 2:
        return False
    value, _ = calculate_hand(cards)
    return value == 21

def get_deck() -> List[str]:
    """Создать колоду карт"""
    deck = []
    cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    for _ in range(4):
        deck.extend(cards)
    random.shuffle(deck)
    return deck

@dp.callback_query(lambda c: c.data == "game_blackjack")
async def blackjack_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню Black Jack"""
    await state.set_state(GameStates.blackjack_betting)
    
    text = """
♠️ **BLACK JACK** ♠️

BLACK JACK (21) = 5x выигрыш!

Выберите ставку:
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10 🪙", callback_data="bj_bet_10"),
            InlineKeyboardButton(text="50 🪙", callback_data="bj_bet_50"),
            InlineKeyboardButton(text="100 🪙", callback_data="bj_bet_100")
        ],
        [
            InlineKeyboardButton(text="250 🪙", callback_data="bj_bet_250"),
            InlineKeyboardButton(text="500 🪙", callback_data="bj_bet_500")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("bj_bet_"))
async def blackjack_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало Black Jack"""
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['hash_fugasy'] < bet:
        await callback.answer(f"❌ Недостаточно!", show_alert=True)
        return
    
    deck = get_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
    
    if is_blackjack(player_cards):
        if is_blackjack(dealer_cards):
            user['hash_fugasy'] += bet
            winnings = bet
        else:
            winnings = bet * 5
            user['hash_fugasy'] += winnings
            user['total_won'] += winnings
        
        user['games_played'] += 1
        save_user(user_id, user)
        add_transaction(user_id, 'BLACKJACK', winnings, 'BLACKJACK')
        
        result = f"🌟 **BLACK JACK!!!** 🌟\n\n+{winnings} 🪙\n\nБаланс: {format_currency(user['hash_fugasy'])}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="♠️ Ещё", callback_data="game_blackjack"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
            ]
        ])
        
        await callback.message.edit_text(result, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return
    
    await state.update_data(bj_bet=bet, bj_deck=deck, bj_player_cards=player_cards, bj_dealer_cards=dealer_cards)
    await state.set_state(GameStates.blackjack_playing)
    
    player_value, _ = calculate_hand(player_cards)
    text = f"Ваши карты: {' '.join(player_cards)} = **{player_value}**\nКарта дилера: {dealer_cards[0]} ?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Ещё", callback_data="bj_hit"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "bj_hit")
async def blackjack_hit(callback: types.CallbackQuery, state: FSMContext):
    """Взять карту"""
    data = await state.get_data()
    deck = data['bj_deck']
    player_cards = data['bj_player_cards']
    bet = data['bj_bet']
    
    if not deck:
        deck = get_deck()
    
    player_cards.append(deck.pop())
    player_value, _ = calculate_hand(player_cards)
    
    if player_value > 21:
        user_id = callback.from_user.id
        user = get_user(user_id)
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        user['games_played'] += 1
        save_user(user_id, user)
        add_transaction(user_id, 'BLACKJACK', bet, 'BUST')
        
        text = f"💥 **ПЕРЕБОР!** -{bet} 🪙\n\nБаланс: {format_currency(user['hash_fugasy'])}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="♠️ Ещё", callback_data="game_blackjack"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
            ]
        ])
        
        await state.clear()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return
    
    await state.update_data(bj_deck=deck, bj_player_cards=player_cards)
    
    text = f"Ваши карты: {' '.join(player_cards)} = **{player_value}**"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Ещё", callback_data="bj_hit"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "bj_stand")
async def blackjack_stand(callback: types.CallbackQuery, state: FSMContext):
    """Остановиться"""
    data = await state.get_data()
    deck = data['bj_deck']
    player_cards = data['bj_player_cards']
    dealer_cards = data['bj_dealer_cards']
    bet = data['bj_bet']
    
    while True:
        dealer_value, _ = calculate_hand(dealer_cards)
        if dealer_value >= 17:
            break
        if not deck:
            deck = get_deck()
        dealer_cards.append(deck.pop())
    
    player_value, _ = calculate_hand(player_cards)
    dealer_value, _ = calculate_hand(dealer_cards)
    
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if dealer_value > 21:
        winnings = int(bet * 1.5)
        user['hash_fugasy'] += winnings
        user['total_won'] += winnings
        result = f"🎉 **ВЫИГРЫШ!** +{winnings} 🪙"
        transaction_result = 'DEALER_BUST'
    elif player_value > dealer_value:
        winnings = int(bet * 1.5)
        user['hash_fugasy'] += winnings
        user['total_won'] += winnings
        result = f"🎉 **ВЫИГРЫШ!** +{winnings} 🪙"
        transaction_result = 'WIN'
    elif player_value == dealer_value:
        user['hash_fugasy'] += bet
        result = f"🤝 **НИЧЬЯ** +{bet} 🪙"
        transaction_result = 'DRAW'
        winnings = bet
    else:
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        result = f"😢 **ПРОИГРЫШ** -{bet} 🪙"
        transaction_result = 'LOSE'
        winnings = bet
    
    user['games_played'] += 1
    save_user(user_id, user)
    add_transaction(user_id, 'BLACKJACK', winnings, transaction_result)
    
    text = f"{result}\n\nБаланс: {format_currency(user['hash_fugasy'])}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="♠️ Ещё", callback_data="game_blackjack"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await state.clear()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== СТАТИСТИКА ===============
@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    """Показать статистику"""
    user_id = callback.from_user.id
    stats = get_player_stats(user_id)
    
    if stats:
        profit = stats['total_won'] - stats['total_lost']
        profit_emoji = "📈" if profit >= 0 else "📉"
        
        text = f"""
📊 **СТАТИСТИКА** 📊

**Баланс:** {format_currency(stats['balance'])}

**Игровые показатели:**
🎮 Всего игр: {stats['games_played']}
✅ Выигрыш: +{stats['total_won']} 🪙
❌ Проигрыш: -{stats['total_lost']} 🪙
{profit_emoji} **Баланс:** {profit:+d} 🪙

**Реферальная программа:**
👥 Рефералов: {stats['referrals_count']}
💰 Заработок: {format_currency(stats['referral_earnings'])}

**Аккаунт:**
🆔 Код: `{stats['ref_code']}`
📱 Транзакций: {stats['transactions']}
        """
    else:
        text = "❌ Ошибка загрузки статистики"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "balance")
async def show_balance(callback: types.CallbackQuery):
    """Показать баланс"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    text = f"""
💰 **ВАШ БАЛАНС** 💰

{format_currency(user['hash_fugasy'])}

Начинайте игру и выигрывайте! 🎰
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== НАВИГАЦИЯ ===============
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в меню"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    player_name = get_user_name(callback.from_user)
    
    await state.set_state(GameStates.main_menu)
    welcome_text = create_main_menu(user, player_name)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
            InlineKeyboardButton(text="♠️ Black Jack", callback_data="game_blackjack")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance")
        ],
        [
            InlineKeyboardButton(text="👥 Мой реф.код", callback_data="my_referral")
        ]
    ])
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== ЗАПУСК БОТА ===============
async def main():
    """Запуск бота"""
    print("🎰 Казино БАБАХИ запущено! (Версия 4.1 - С SQLite БД)")
    print(f"📁 Папка данных: {os.path.abspath(DATA_DIR)}")
    print(f"📄 БД: {os.path.abspath(DB_FILE)}")
    print("💾 База данных: SQLite (надёжная и профессиональная)")
    init_database()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
