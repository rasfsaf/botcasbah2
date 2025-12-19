# Telegram Casino Bot - Рулетка и Блек Джек
# Автор: Casino Bot Creator
# Версия: 2.2 - Казино Бабахи (Групповая рулетка)
# Валюта: Хэш-Фугасы

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# =============== КОНФИГУРАЦИЯ ===============
# Вставьте ваш токен прямо сюда (в КАВЫЧКАХ!):
TOKEN = "8534556244:AAHY2I4IQn0ltUqcATx_SIM4ut_9n_nyTNg"

# Инициализация
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =============== СКЛОНЕНИЯ ===============
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

# =============== СОСТОЯНИЯ ===============
class GameStates(StatesGroup):
    main_menu = State()
    roulette_betting = State()
    roulette_spinning = State()
    blackjack_betting = State()
    blackjack_playing = State()
    multiplayer_menu = State()
    waiting_players = State()
    multiplayer_game = State()
    group_roulette_waiting = State()

# =============== БАЗА ДАННЫХ (в памяти) ===============
users_data: Dict[int, dict] = {}
group_roulette_games: Dict[int, dict] = {}  # Игры в группе по chat_id

def get_user(user_id: int) -> dict:
    """Получить данные пользователя или создать новые"""
    if user_id not in users_data:
        users_data[user_id] = {
            'hash_fugasy': 1000,  # Стартовые Хэш-Фугасы
            'total_won': 0,
            'total_lost': 0,
            'games_played': 0,
            'username': 'Unknown'
        }
    return users_data[user_id]

def save_user(user_id: int, data: dict):
    """Сохранить данные пользователя"""
    users_data[user_id] = data

def get_user_name(user: types.User) -> str:
    """Получить имя пользователя (правильное)"""
    return user.first_name or user.username or "Игрок"

def create_main_menu(user: dict, player_name: str) -> str:
    """Создать текст главного меню с актуальным балансом"""
    welcome_text = f"""
🎰 **ДОБРО ПОЖАЛОВАТЬ В КАЗИНО БАБАХИ!** 🎰

Привет, {player_name}! 👋

Ваш баланс: {format_currency(user['hash_fugasy'])}

**Доступные игры:**
1️⃣ **Рулетка** - классическая игра везения
2️⃣ **Блек Джек** - игра против дилера
3️⃣ **Рулетка в группе** - играй с друзьями

Выберите игру или посмотрите статистику!
    """
    return welcome_text

# =============== ГЛАВНОЕ МЕНЮ ===============
@dp.message(Command("babaha"))
async def start_command(message: types.Message, state: FSMContext):
    """Начало работы бота"""
    user_id = message.from_user.id
    user = get_user(user_id)
    player_name = get_user_name(message.from_user)
    user['username'] = player_name
    save_user(user_id, user)
    
    await state.set_state(GameStates.main_menu)
    
    welcome_text = create_main_menu(user, player_name)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
            InlineKeyboardButton(text="♠️ Блек Джек", callback_data="game_blackjack")
        ],
        [
            InlineKeyboardButton(text="🎡 Рулетка в группе", callback_data="group_roulette_menu")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance")
        ]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

# =============== РУЛЕТКА (личная) ===============
@dp.callback_query(lambda c: c.data == "game_roulette")
async def roulette_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню рулетки"""
    await state.set_state(GameStates.roulette_betting)
    
    text = """
🎡 **РУЛЕТКА** 🎡

**Правила:**
- Выберите ставку (от 10 до 500 Хэш-Фугас)
- Угадайте: Красное или Чёрное
- Вероятность выигрыша: 48.6%
- При выигрыше удвоите ставку

Сколько ставите?
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
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['hash_fugasy'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    await state.update_data(roulette_bet=bet)
    
    text = f"""
🎡 **ВЫБЕРИТЕ ЦВЕТ** 🎡

Ставка: {format_currency(bet)}

Выберите:
🔴 **Красное** - удвоите ставку
⬛ **Чёрное** - удвоите ставку
    """
    
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
    
    # Вращение рулетки (48.6% вероятность выигрыша)
    result_color = random.choices(["Красное", "Чёрное"], weights=[48.6, 51.4])[0]
    is_win = result_color == chosen_color
    
    # Обновляем баланс
    if is_win:
        user['hash_fugasy'] += bet
        user['total_won'] += bet
        result_text = f"""
🎉 **ВЫИГРЫШ!** 🎉

Результат рулетки: **{result_color}** ✅
Ваш выбор: **{chosen_color}** ✅
Выигрыш: **+{bet}** 🪙

Новый баланс: {format_currency(user['hash_fugasy'])}
        """
    else:
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        result_text = f"""
😢 **ПРОИГРЫШ** 😢

Результат рулетки: **{result_color}** ❌
Ваш выбор: **{chosen_color}** ❌
Потеря: **-{bet}** 🪙

Новый баланс: {format_currency(user['hash_fugasy'])}
        """
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Ещё раз", callback_data="game_roulette"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== РУЛЕТКА В ГРУППЕ ===============
@dp.callback_query(lambda c: c.data == "group_roulette_menu")
async def group_roulette_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню групповой рулетки"""
    text = """
🎡 **ГРУППОВАЯ РУЛЕТКА** 🎡

**Как это работает:**
- Любой может присоединиться к игре
- Все ставят одновременно
- Один результат рулетки для всех
- У каждого свой баланс и счет

Напишите ставку числом (10-500)
или нажмите одну из кнопок:
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10 🪙", callback_data="group_bet_10"),
            InlineKeyboardButton(text="50 🪙", callback_data="group_bet_50"),
            InlineKeyboardButton(text="100 🪙", callback_data="group_bet_100")
        ],
        [
            InlineKeyboardButton(text="250 🪙", callback_data="group_bet_250"),
            InlineKeyboardButton(text="500 🪙", callback_data="group_bet_500")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("group_bet_"))
async def group_roulette_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало групповой рулетки"""
    if not callback.message.chat.type in ['group', 'supergroup', 'private']:
        await callback.answer("❌ Эта команда работает только в группах или ЛС", show_alert=True)
        return
    
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    player_name = get_user_name(callback.from_user)
    user = get_user(user_id)
    
    if user['hash_fugasy'] < bet:
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['hash_fugasy'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    chat_id = callback.message.chat.id
    
    # Создаём игру если её нет
    if chat_id not in group_roulette_games:
        group_roulette_games[chat_id] = {
            'players': {},
            'bet': bet,
            'message_id': callback.message.message_id
        }
    
    # Добавляем игрока
    game = group_roulette_games[chat_id]
    game['players'][user_id] = {
        'name': player_name,
        'bet': bet,
        'color': None
    }
    
    # Обновляем сообщение
    players_text = "\n".join([f"👤 {p['name']} - {format_currency(p['bet'])}" 
                              for p in game['players'].values()])
    
    text = f"""
🎡 **ГРУППОВАЯ РУЛЕТКА** 🎡

**Ставка:** {format_currency(bet)}
**Игроков:** {len(game['players'])}

**Участники:**
{players_text}

Выберите цвет:
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 Красное", callback_data=f"group_color_red_{user_id}"),
            InlineKeyboardButton(text="⬛ Чёрное", callback_data=f"group_color_black_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🎡 Запустить рулетку!", callback_data="group_roulette_spin")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("✅ Вы присоединились к игре!")

@dp.callback_query(lambda c: c.data.startswith("group_color_"))
async def group_roulette_color(callback: types.CallbackQuery):
    """Выбор цвета в групповой рулетке"""
    parts = callback.data.split("_")
    color = parts[2]  # red или black
    user_id = int(parts[3])
    chat_id = callback.message.chat.id
    
    if chat_id not in group_roulette_games:
        await callback.answer("❌ Игра не начиналась", show_alert=True)
        return
    
    game = group_roulette_games[chat_id]
    if user_id not in game['players']:
        await callback.answer("❌ Вы не в этой игре", show_alert=True)
        return
    
    color_name = "Красное" if color == "red" else "Чёрное"
    game['players'][user_id]['color'] = color
    
    await callback.answer(f"✅ Вы выбрали: {color_name}")

@dp.callback_query(lambda c: c.data == "group_roulette_spin")
async def group_roulette_spin(callback: types.CallbackQuery):
    """Вращение групповой рулетки"""
    chat_id = callback.message.chat.id
    
    if chat_id not in group_roulette_games:
        await callback.answer("❌ Нет активной игры", show_alert=True)
        return
    
    game = group_roulette_games[chat_id]
    
    # Проверяем, что все выбрали цвет
    players_without_color = [p for p in game['players'].values() if p['color'] is None]
    if players_without_color:
        await callback.answer(f"❌ Не все выбрали цвет! {len(players_without_color)} игроков ждут...", show_alert=True)
        return
    
    # Вращение рулетки
    result_color = random.choices(["Красное", "Чёрное"], weights=[48.6, 51.4])[0]
    
    # Обрабатываем результаты
    results = []
    for user_id, player in game['players'].items():
        user = get_user(user_id)
        player_color = "Красное" if player['color'] == "red" else "Чёрное"
        is_win = result_color == player_color
        
        if is_win:
            user['hash_fugasy'] += player['bet']
            user['total_won'] += player['bet']
            results.append(f"✅ {player['name']} выиграл {format_currency(player['bet'])}")
        else:
            user['hash_fugasy'] -= player['bet']
            user['total_lost'] += player['bet']
            results.append(f"❌ {player['name']} проиграл {format_currency(player['bet'])}")
        
        user['games_played'] += 1
        save_user(user_id, user)
    
    results_text = "\n".join(results)
    
    text = f"""
🎰 **РЕЗУЛЬТАТ РУЛЕТКИ** 🎰

**Выпало:** {result_color}

**Результаты:**
{results_text}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎡 Новая игра", callback_data="group_roulette_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    # Удаляем игру
    if chat_id in group_roulette_games:
        del group_roulette_games[chat_id]
    
    await callback.answer("🎉 Игра завершена!")

# =============== БЛЕК ДЖЕК ===============
@dp.callback_query(lambda c: c.data == "game_blackjack")
async def blackjack_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню Блек Джека"""
    await state.set_state(GameStates.blackjack_betting)
    
    text = """
♠️ **БЛЕ К ДЖЕК** ♠️

**Правила:**
- Цель: набрать 21 очко или близко к нему
- Дилер играет против вас
- Если перебрали (>21) - проигрыш
- При выигрыше - получаете 1.5x от ставки

Сколько ставите?
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

def card_value(card: str) -> int:
    """Получить значение карты"""
    if card in ['J', 'Q', 'K']:
        return 10
    elif card == 'A':
        return 11
    else:
        return int(card)

def calculate_hand(cards: List[str]) -> tuple:
    """Рассчитать значение руки (возвращает значение и количество aces)"""
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

def get_deck() -> List[str]:
    """Создать колоду карт"""
    deck = []
    cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    for _ in range(4):  # 4 колоды
        deck.extend(cards)
    random.shuffle(deck)
    return deck

@dp.callback_query(lambda c: c.data.startswith("bj_bet_"))
async def blackjack_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало игры Блек Джека"""
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['hash_fugasy'] < bet:
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['hash_fugasy'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    # Инициализируем игру
    deck = get_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
    
    await state.update_data(
        bj_bet=bet,
        bj_deck=deck,
        bj_player_cards=player_cards,
        bj_dealer_cards=dealer_cards
    )
    await state.set_state(GameStates.blackjack_playing)
    
    player_value, _ = calculate_hand(player_cards)
    
    text = f"""
♠️ **БЛЕ К ДЖЕК - ИГРА** ♠️

**Ваши карты:** {' '.join(player_cards)}
Сумма: **{player_value}**

**Карта дилера:** {dealer_cards[0]} ?

**Ставка:** {format_currency(bet)}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Ещё карту", callback_data="bj_hit"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "bj_hit")
async def blackjack_hit(callback: types.CallbackQuery, state: FSMContext):
    """Взять ещё карту"""
    data = await state.get_data()
    deck = data['bj_deck']
    player_cards = data['bj_player_cards']
    dealer_cards = data['bj_dealer_cards']
    bet = data['bj_bet']
    
    if not deck:
        deck = get_deck()
    
    player_cards.append(deck.pop())
    player_value, _ = calculate_hand(player_cards)
    
    if player_value > 21:
        # Проигрыш
        user_id = callback.from_user.id
        user = get_user(user_id)
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        user['games_played'] += 1
        save_user(user_id, user)
        
        text = f"""
😢 **ПЕРЕБОР!** 😢

**Ваши карты:** {' '.join(player_cards)}
**Сумма:** {player_value} ❌

Проигрыш: **-{bet}** 🪙
Новый баланс: {format_currency(user['hash_fugasy'])}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="♠️ Ещё партию", callback_data="game_blackjack"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
            ]
        ])
        
        await state.clear()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return
    
    await state.update_data(bj_deck=deck, bj_player_cards=player_cards)
    
    text = f"""
♠️ **БЛЕ К ДЖЕК - ИГРА** ♠️

**Ваши карты:** {' '.join(player_cards)}
Сумма: **{player_value}**

**Карта дилера:** {dealer_cards[0]} ?

**Ставка:** {format_currency(bet)}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Ещё карту", callback_data="bj_hit"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "bj_stand")
async def blackjack_stand(callback: types.CallbackQuery, state: FSMContext):
    """Остановиться и завершить игру"""
    data = await state.get_data()
    deck = data['bj_deck']
    player_cards = data['bj_player_cards']
    dealer_cards = data['bj_dealer_cards']
    bet = data['bj_bet']
    
    # Дилер играет
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
    
    # Определяем результат
    if dealer_value > 21:
        winnings = int(bet * 1.5)
        user['hash_fugasy'] += winnings
        user['total_won'] += winnings
        result = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}** ❌

Дилер перебрал!
Выигрыш: **+{winnings}** 🪙
Новый баланс: {format_currency(user['hash_fugasy'])}
        """
    elif player_value > dealer_value:
        winnings = int(bet * 1.5)
        user['hash_fugasy'] += winnings
        user['total_won'] += winnings
        result = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}** ✅
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

Выигрыш: **+{winnings}** 🪙
Новый баланс: {format_currency(user['hash_fugasy'])}
        """
    elif player_value == dealer_value:
        result = f"""
🤝 **НИЧЬЯ** 🤝

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

Ставка возвращена: **+{bet}** 🪙
Баланс: {format_currency(user['hash_fugasy'])}
        """
        user['hash_fugasy'] += bet
    else:
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        result = f"""
😢 **ПРОИГРЫШ** 😢

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}** ✅

Проигрыш: **-{bet}** 🪙
Новый баланс: {format_currency(user['hash_fugasy'])}
        """
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="♠️ Ещё партию", callback_data="game_blackjack"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await state.clear()
    await callback.message.edit_text(result, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== СТАТИСТИКА ===============
@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    """Показать статистику"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    profit = user['total_won'] - user['total_lost']
    profit_emoji = "📈" if profit >= 0 else "📉"
    profit_word = declension(abs(profit), "Хэш-Фугас", "Хэш-Фугаса", "Хэш-Фугас")
    
    text = f"""
📊 **ВАША СТАТИСТИКА** 📊

**Баланс:** {format_currency(user['hash_fugasy'])}

**Всего игр:** {user['games_played']}
**Выигрыш:** +{user['total_won']} 🪙
**Проигрыш:** -{user['total_lost']} 🪙
**Прибыль/Убыток:** {profit_emoji} {profit:+d} {profit_word}
    """
    
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
    """Вернуться в главное меню с актуальным балансом"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    player_name = get_user_name(callback.from_user)
    
    await state.set_state(GameStates.main_menu)
    
    welcome_text = create_main_menu(user, player_name)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
            InlineKeyboardButton(text="♠️ Блек Джек", callback_data="game_blackjack")
        ],
        [
            InlineKeyboardButton(text="🎡 Рулетка в группе", callback_data="group_roulette_menu")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance")
        ]
    ])
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== ЗАПУСК БОТА ===============
async def main():
    """Запуск бота"""
    print("🎰 Казино БАБАХИ запущено! (Версия 2.2 - Групповая рулетка)")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
