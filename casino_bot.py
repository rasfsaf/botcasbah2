# Telegram Casino Bot - Рулетка и Блек Джек
# Автор: Casino Bot Creator
# Версия: 1.0
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

# Инициализация
TOKEN = 8534556244:AAHY2I4IQn0ltUqcATx_SIM4ut_9n_nyTNg  # Будет установлен из переменной окружения
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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

# =============== БАЗА ДАННЫХ (в памяти) ===============
users_data: Dict[int, dict] = {}

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

# =============== ГЛАВНОЕ МЕНЮ ===============
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """Начало работы бота"""
    user_id = message.from_user.id
    user = get_user(user_id)
    user['username'] = message.from_user.username or message.from_user.first_name
    save_user(user_id, user)
    
    await state.set_state(GameStates.main_menu)
    
    welcome_text = f"""
🎰 **ДОБРО ПОЖАЛОВАТЬ В КАЗИНО ХЭША!** 🎰

Привет, {message.from_user.first_name}! 👋

Ваш баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас

**Доступные игры:**
1️⃣ **Рулетка** - классическая игра везения
2️⃣ **Блек Джек** - игра против дилера
3️⃣ **Мультиплеер** - играй с друзьями онлайн

Выберите игру или посмотрите статистику!
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
            InlineKeyboardButton(text="♠️ Блек Джек", callback_data="game_blackjack")
        ],
        [
            InlineKeyboardButton(text="👥 Мультиплеер", callback_data="game_multiplayer")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance")
        ]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

# =============== РУЛЕТКА ===============
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

Сколько Хэш-Фугас ставите?
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
        await callback.answer(f"❌ Недостаточно Хэш-Фугас! У вас {user['hash_fugasy']}, нужно {bet}", show_alert=True)
        return
    
    await state.update_data(roulette_bet=bet)
    
    text = f"""
🎡 **ВЫБЕРИТЕ ЦВЕТ** 🎡

Ставка: **{bet}** 🪙 Хэш-Фугас

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

Новый баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас
        """
    else:
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        result_text = f"""
😢 **ПРОИГРЫШ** 😢

Результат рулетки: **{result_color}** ❌
Ваш выбор: **{chosen_color}** ❌
Потеря: **-{bet}** 🪙

Новый баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас
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
- Блекджек (21 с 2 карт) - выигрыш в 2.5x

Сколько Хэш-Фугас ставите?
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
        await callback.answer(f"❌ Недостаточно Хэш-Фугас! У вас {user['hash_fugasy']}, нужно {bet}", show_alert=True)
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

**Ставка:** {bet} 🪙 Хэш-Фугас
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

**Карты дилера:** {' '.join(dealer_cards)}

Проигрыш: **-{bet}** 🪙
Новый баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас
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

**Ставка:** {bet} 🪙 Хэш-Фугас
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
        # Выигрыш (дилер перебрал)
        winnings = int(bet * 1.5)
        user['hash_fugasy'] += winnings
        user['total_won'] += winnings
        result = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}** ❌

Дилер перебрал!
Выигрыш: **+{winnings}** 🪙
Новый баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас
        """
    elif player_value > dealer_value:
        # Выигрыш
        winnings = int(bet * 1.5)
        user['hash_fugasy'] += winnings
        user['total_won'] += winnings
        result = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}** ✅
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

Выигрыш: **+{winnings}** 🪙
Новый баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас
        """
    elif player_value == dealer_value:
        # Ничья
        result = f"""
🤝 **НИЧЬЯ** 🤝

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

Ставка возвращена: **+{bet}** 🪙
Баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас
        """
        user['hash_fugasy'] += bet
    else:
        # Проигрыш
        user['hash_fugasy'] -= bet
        user['total_lost'] += bet
        result = f"""
😢 **ПРОИГРЫШ** 😢

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}** ✅

Проигрыш: **-{bet}** 🪙
Новый баланс: **{user['hash_fugasy']}** 🪙 Хэш-Фугас
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
    
    text = f"""
📊 **ВАША СТАТИСТИКА** 📊

**Баланс:** {user['hash_fugasy']} 🪙 Хэш-Фугас

**Всего игр:** {user['games_played']}
**Выигрыш:** +{user['total_won']} 🪙
**Проигрыш:** -{user['total_lost']} 🪙
**Прибыль/Убыток:** {profit_emoji} {profit:+d} 🪙
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

**{user['hash_fugasy']}** 🪙 Хэш-Фугас

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
    """Вернуться в главное меню"""
    await start_command(callback.message, state)

@dp.callback_query(lambda c: c.data == "game_multiplayer")
async def multiplayer_soon(callback: types.CallbackQuery):
    """Заглушка для мультиплеера"""
    text = """
👥 **МУЛЬТИПЛЕЕР** 👥

Эта функция находится в разработке! 🚀

На данный момент доступны:
- 🎡 Рулетка
- ♠️ Блек Джек

Следите за обновлениями! 📢
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== ЗАПУСК БОТА ===============
async def main():
    """Запуск бота"""
    print("🎰 Казино бот с Хэш-Фугасами запущен!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
