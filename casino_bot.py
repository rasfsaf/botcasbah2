import asyncio
import json
import os
import random
from typing import Dict, List

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# =============== КОНФИГУРАЦИЯ ===============

TOKEN = "8534556244:AAHY2I4IQn0ltUqcATx_SIM4ut_9n_nyTNg"
USERS_DATA_FILE = "users_data.json"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =============== СКЛОНЕНИЯ И ВАЛЮТА ===============


def declension(num: int, word1: str, word2: str, word5: str) -> str:
    if num % 10 == 1 and num % 100 != 11:
        return word1
    elif num % 10 in [2, 3, 4] and num % 100 not in [12, 13, 14]:
        return word2
    else:
        return word5


def format_currency(num: int) -> str:
    word = declension(num, "Хэш-Фугас", "Хэш-Фугаса", "Хэш-Фугас")
    return f"**{num}** 🪙 {word}"


# =============== СОСТОЯНИЯ ===============

class GameStates(StatesGroup):
    main_menu = State()

    roulette_betting = State()
    roulette_spinning = State()

    blackjack_betting = State()
    blackjack_playing = State()

    group_roulette_waiting = State()
    group_blackjack_betting = State()
    group_blackjack_playing = State()


# =============== БАЗА ДАННЫХ В ПАМЯТИ ===============

users_data: Dict[str, dict] = {}
group_roulette_games: Dict[int, dict] = {}
group_blackjack_games: Dict[int, dict] = {}


# =============== РАБОТА С ФАЙЛОМ ПОЛЬЗОВАТЕЛЕЙ ===============

def load_users_data():
    global users_data
    if os.path.exists(USERS_DATA_FILE):
        try:
            with open(USERS_DATA_FILE, "r", encoding="utf-8") as f:
                users_data = json.load(f)
            print(f"✅ Загружено {len(users_data)} пользователей из файла")
        except Exception as e:
            print(f"❌ Ошибка при загрузке данных: {e}")
            users_data = {}
    else:
        print("📝 Файл данных не найден, создаём новый")
        users_data = {}


def save_users_data():
    try:
        with open(USERS_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Ошибка при сохранении данных: {e}")


def get_user(user_id: int) -> dict:
    user_id_str = str(user_id)
    if user_id_str not in users_data:
        users_data[user_id_str] = {
            "hash_fugasy": 1000,
            "total_won": 0,
            "total_lost": 0,
            "games_played": 0,
            "username": "Unknown",
        }
        save_users_data()
    return users_data[user_id_str]


def save_user(user_id: int, data: dict):
    users_data[str(user_id)] = data
    save_users_data()


def get_user_name(user: types.User) -> str:
    return user.first_name or user.username or "Игрок"


# =============== ТЕКСТЫ И КЛАВИАТУРЫ ===============

def create_main_menu(user: dict, player_name: str) -> str:
    return f"""
🎰 **ДОБРО ПОЖАЛОВАТЬ В КАЗИНО БАБАХИ!** 🎰

Привет, {player_name}! 👋

Ваш баланс: {format_currency(user['hash_fugasy'])}

**Доступные игры:**

1️⃣ **Рулетка** - классическая игра везения  
2️⃣ **Black Jack** - игра против дилера  
3️⃣ **Рулетка в группе** - играй с друзьями  
4️⃣ **Black Jack в группе** - групповая игра  

Выберите игру или посмотрите статистику!
"""


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
                InlineKeyboardButton(text="♠️ Black Jack", callback_data="game_blackjack"),
            ],
            [
                InlineKeyboardButton(
                    text="🎡 Рулетка в группе", callback_data="group_roulette_menu"
                ),
                InlineKeyboardButton(
                    text="♠️ Black Jack в группе",
                    callback_data="group_blackjack_menu",
                ),
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
            ],
        ]
    )


def roulette_bet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="roulette_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="roulette_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="roulette_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="roulette_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="roulette_bet_500"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )


def blackjack_bet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="bj_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="bj_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="bj_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="bj_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="bj_bet_500"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )


# =============== /start ===============

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    player_name = get_user_name(message.from_user)
    user["username"] = player_name
    save_user(user_id, user)

    await state.set_state(GameStates.main_menu)
    welcome_text = create_main_menu(user, player_name)
    await message.answer(
        welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
    )


# =============== РУЛЕТКА ОДИНОЧНАЯ ===============

@dp.callback_query(F.data == "game_roulette")
async def roulette_menu(callback: types.CallbackQuery, state: FSMContext):
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
    await callback.message.edit_text(
        text, reply_markup=roulette_bet_keyboard(), parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("roulette_bet_"))
async def roulette_choose_color(callback: types.CallbackQuery, state: FSMContext):
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)

    if user["hash_fugasy"] < bet:
        await callback.answer(
            f"❌ Недостаточно! У вас {format_currency(user['hash_fugasy'])}, "
            f"нужно {format_currency(bet)}",
            show_alert=True,
        )
        return

    await state.update_data(roulette_bet=bet)

    text = f"""
🎡 **ВЫБЕРИТЕ ЦВЕТ** 🎡

Ставка: {format_currency(bet)}

Выберите:

🔴 **Красное**  
⬛ **Чёрное**
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Красное", callback_data="roulette_red"),
                InlineKeyboardButton(text="⬛ Чёрное", callback_data="roulette_black"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )
    await callback.message.edit_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.in_(["roulette_red", "roulette_black"]))
async def roulette_spin(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get("roulette_bet", 10)
    chosen_color = "Красное" if callback.data == "roulette_red" else "Чёрное"

    user_id = callback.from_user.id
    user = get_user(user_id)

    result_color = random.choices(["Красное", "Чёрное"], weights=[48.6, 51.4])[0]
    is_win = result_color == chosen_color

    if is_win:
        user["hash_fugasy"] += bet
        user["total_won"] += bet
        text = f"""
🎉 **ВЫИГРЫШ!** 🎉

Результат рулетки: **{result_color}** ✅  
Ваш выбор: **{chosen_color}** ✅  

Выигрыш: **+{bet}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""
    else:
        user["hash_fugasy"] -= bet
        user["total_lost"] += bet
        text = f"""
😢 **ПРОИГРЫШ** 😢

Результат рулетки: **{result_color}** ❌  
Ваш выбор: **{chosen_color}** ❌  

Потеря: **-{bet}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""

    user["games_played"] += 1
    save_user(user_id, user)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎡 Ещё раз", callback_data="game_roulette"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu"),
            ]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# =============== BLACK JACK ОДИНОЧНЫЙ ===============

def calculate_hand(cards: List[str]) -> tuple[int, int]:
    total = 0
    aces = 0
    for card in cards:
        if card == "A":
            aces += 1
            total += 11
        elif card in ["J", "Q", "K"]:
            total += 10
        else:
            total += int(card)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total, aces


def is_blackjack(cards: List[str]) -> bool:
    if len(cards) != 2:
        return False
    value, _ = calculate_hand(cards)
    return value == 21


def get_deck() -> List[str]:
    deck: List[str] = []
    cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    for _ in range(4):
        deck.extend(cards)
    random.shuffle(deck)
    return deck


@dp.callback_query(F.data == "game_blackjack")
async def blackjack_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.blackjack_betting)
    text = """
♠️ **BLACK JACK** ♠️

**Правила:**
- Цель: набрать 21 очко или близко к нему
- Дилер играет против вас
- Если перебрали (>21) - ПЕРЕБОР
- **BLACK JACK!** (21 с первых двух карт) = **5x ставка**
- При обычном выигрыше - 1.5x от ставки

Сколько ставите?
"""
    await callback.message.edit_text(
        text, reply_markup=blackjack_bet_keyboard(), parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("bj_bet_"))
async def blackjack_start(callback: types.CallbackQuery, state: FSMContext):
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)

    if user["hash_fugasy"] < bet:
        await callback.answer(
            f"❌ Недостаточно! У вас {format_currency(user['hash_fugasy'])}, "
            f"нужно {format_currency(bet)}",
            show_alert=True,
        )
        return

    deck = get_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]

    player_value, _ = calculate_hand(player_cards)
    dealer_value, _ = calculate_hand(dealer_cards)

    if is_blackjack(player_cards):
        if is_blackjack(dealer_cards):
            user["hash_fugasy"] += bet
            user["total_won"] += bet
            text = f"""
🤝 **ОБА ИМЕЮТ BLACK JACK!** 🤝

**Ваши карты:** {' '.join(player_cards)} = **21**  
**Карты дилера:** {' '.join(dealer_cards)} = **21**  

Ставка возвращена: **+{bet}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""
        else:
            winnings = bet * 5
            user["hash_fugasy"] += winnings
            user["total_won"] += winnings
            text = f"""
🌟 **BLACK JACK!!!** 🌟

**Ваши карты:** {' '.join(player_cards)} = **21**  
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**  

Выигрыш: **+{winnings}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""
        user["games_played"] += 1
        save_user(user_id, user)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="♠️ Ещё партию", callback_data="game_blackjack"
                    ),
                    InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu"),
                ]
            ]
        )
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return

    await state.update_data(
        bj_bet=bet,
        bj_deck=deck,
        bj_player_cards=player_cards,
        bj_dealer_cards=dealer_cards,
    )
    await state.set_state(GameStates.blackjack_playing)

    text = f"""
♠️ **BLACK JACK - ИГРА** ♠️

**Ваши карты:** {' '.join(player_cards)}  
Сумма: **{player_value}**

**Карта дилера:** {dealer_cards[0]} ?  

**Ставка:** {format_currency(bet)}
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎴 Ещё карту", callback_data="bj_hit"),
                InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand"),
            ]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "bj_hit")
async def blackjack_hit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    deck: List[str] = data["bj_deck"]
    player_cards: List[str] = data["bj_player_cards"]
    dealer_cards: List[str] = data["bj_dealer_cards"]
    bet: int = data["bj_bet"]

    if not deck:
        deck = get_deck()
    player_cards.append(deck.pop())
    player_value, _ = calculate_hand(player_cards)

    if player_value > 21:
        user_id = callback.from_user.id
        user = get_user(user_id)
        user["hash_fugasy"] -= bet
        user["total_lost"] += bet
        user["games_played"] += 1
        save_user(user_id, user)

        text = f"""
💥 **ПЕРЕБОР!** 💥

**Ваши карты:** {' '.join(player_cards)}  
**Сумма:** {player_value} ❌  

Проигрыш: **-{bet}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="♠️ Ещё партию", callback_data="game_blackjack"
                    ),
                    InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu"),
                ]
            ]
        )
        await state.clear()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return

    await state.update_data(bj_deck=deck, bj_player_cards=player_cards)

    text = f"""
♠️ **BLACK JACK - ИГРА** ♠️

**Ваши карты:** {' '.join(player_cards)}  
Сумма: **{player_value}**

**Карта дилера:** {dealer_cards[0]} ?  

**Ставка:** {format_currency(bet)}
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎴 Ещё карту", callback_data="bj_hit"),
                InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand"),
            ]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "bj_stand")
async def blackjack_stand(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    deck: List[str] = data["bj_deck"]
    player_cards: List[str] = data["bj_player_cards"]
    dealer_cards: List[str] = data["bj_dealer_cards"]
    bet: int = data["bj_bet"]

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

    if is_blackjack(dealer_cards):
        user["hash_fugasy"] -= bet
        user["total_lost"] += bet
        text = f"""
🌟 **ДИЛЕР ИМЕЕТ BLACK JACK!** 🌟

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**  
**Карты дилера:** {' '.join(dealer_cards)} = **21**  

Проигрыш: **-{bet}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""
    elif dealer_value > 21:
        winnings = int(bet * 1.5)
        user["hash_fugasy"] += winnings
        user["total_won"] += winnings
        text = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**  
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}** (перебор)  

Выигрыш: **+{winnings}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""
    elif player_value > dealer_value:
        winnings = int(bet * 1.5)
        user["hash_fugasy"] += winnings
        user["total_won"] += winnings
        text = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**  
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**  

Выигрыш: **+{winnings}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""
    elif player_value == dealer_value:
        user["hash_fugasy"] += bet
        text = f"""
🤝 **НИЧЬЯ** 🤝

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**  
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**  

Ставка возвращена: **+{bet}** 🪙  
Баланс: {format_currency(user['hash_fugasy'])}
"""
    else:
        user["hash_fugasy"] -= bet
        user["total_lost"] += bet
        text = f"""
😢 **ПРОИГРЫШ** 😢

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**  
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**  

Проигрыш: **-{bet}** 🪙  
Новый баланс: {format_currency(user['hash_fugasy'])}
"""

    user["games_played"] += 1
    save_user(user_id, user)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="♠️ Ещё партию", callback_data="game_blackjack"
                ),
                InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu"),
            ]
        ]
    )
    await state.clear()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# =============== ГРУППОВАЯ РУЛЕТКА ===============

@dp.callback_query(F.data == "group_roulette_menu")
async def group_roulette_menu(callback: types.CallbackQuery, state: FSMContext):
    text = """
🎡 **ГРУППОВАЯ РУЛЕТКА** 🎡

- Любой может присоединиться
- Все ставят одну сумму
- Один результат рулетки для всех

Выберите ставку:
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="group_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="group_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="group_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="group_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="group_bet_500"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("group_bet_"))
async def group_roulette_start(callback: types.CallbackQuery, state: FSMContext):
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    player_name = get_user_name(callback.from_user)
    user = get_user(user_id)

    if user["hash_fugasy"] < bet:
        await callback.answer(
            f"❌ Недостаточно! У вас {format_currency(user['hash_fugasy'])}, "
            f"нужно {format_currency(bet)}",
            show_alert=True,
        )
        return

    chat_id = callback.message.chat.id
    if chat_id not in group_roulette_games:
        group_roulette_games[chat_id] = {
            "players": {},
            "bet": bet,
        }

    game = group_roulette_games[chat_id]
    game["bet"] = bet
    game["players"][user_id] = {
        "name": player_name,
        "bet": bet,
        "color": None,
    }

    players_text = "\n".join(
        [
            f"👤 {p['name']} - {format_currency(p['bet'])}"
            for p in game["players"].values()
        ]
    )

    text = f"""
🎡 **ГРУППОВАЯ РУЛЕТКА** 🎡

Ставка: {format_currency(bet)}  
Игроков: {len(game['players'])}

Участники:
{players_text}

Выберите цвет:
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔴 Красное", callback_data=f"group_color_red"
                ),
                InlineKeyboardButton(
                    text="⬛ Чёрное", callback_data=f"group_color_black"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎡 Запустить рулетку!", callback_data="group_roulette_spin"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("✅ Вы присоединились к игре!")


@dp.callback_query(F.data.in_(["group_color_red", "group_color_black"]))
async def group_roulette_color(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in group_roulette_games:
        await callback.answer("❌ Игра не начиналась", show_alert=True)
        return

    game = group_roulette_games[chat_id]
    user_id = callback.from_user.id

    if user_id not in game["players"]:
        await callback.answer("❌ Вы не в этой игре", show_alert=True)
        return

    color = "red" if callback.data == "group_color_red" else "black"
    color_name = "Красное" if color == "red" else "Чёрное"
    game["players"][user_id]["color"] = color

    await callback.answer(f"✅ Вы выбрали: {color_name}")


@dp.callback_query(F.data == "group_roulette_spin")
async def group_roulette_spin(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in group_roulette_games:
        await callback.answer("❌ Нет активной игры", show_alert=True)
        return

    game = group_roulette_games[chat_id]
    players_without_color = [
        p for p in game["players"].values() if p["color"] is None
    ]
    if players_without_color:
        await callback.answer(
            f"❌ Не все выбрали цвет! {len(players_without_color)} игроков ждут...",
            show_alert=True,
        )
        return

    result_color = random.choices(["Красное", "Чёрное"], weights=[48.6, 51.4])[0]
    results = []

    for uid, player in game["players"].items():
        user = get_user(uid)
        player_color = "Красное" if player["color"] == "red" else "Чёрное"
        is_win = result_color == player_color

        if is_win:
            user["hash_fugasy"] += player["bet"]
            user["total_won"] += player["bet"]
            results.append(
                f"✅ {player['name']} выиграл {format_currency(player['bet'])}"
            )
        else:
            user["hash_fugasy"] -= player["bet"]
            user["total_lost"] += player["bet"]
            results.append(
                f"❌ {player['name']} проиграл {format_currency(player['bet'])}"
            )

        user["games_played"] += 1
        save_user(uid, user)

    results_text = "\n".join(results)
    text = f"""
🎰 **РЕЗУЛЬТАТ РУЛЕТКИ** 🎰

Выпало: **{result_color}**

Результаты:
{results_text}
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎡 Новая игра", callback_data="group_roulette_menu"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    if chat_id in group_roulette_games:
        del group_roulette_games[chat_id]
    await callback.answer("🎉 Игра завершена!")


# =============== ГРУППОВОЙ BLACK JACK ===============

@dp.callback_query(F.data == "group_blackjack_menu")
async def group_blackjack_menu(callback: types.CallbackQuery, state: FSMContext):
    text = """
♠️ **ГРУППОВОЙ BLACK JACK** ♠️

- Все играют против одного дилера
- У каждого свой bet и свои решения
- Итог дилера один для всех

Выберите ставку:
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="group_bj_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="group_bj_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="group_bj_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="group_bj_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="group_bj_bet_500"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("group_bj_bet_"))
async def group_blackjack_start(callback: types.CallbackQuery, state: FSMContext):
    bet = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    player_name = get_user_name(callback.from_user)
    user = get_user(user_id)

    if user["hash_fugasy"] < bet:
        await callback.answer(
            f"❌ Недостаточно! У вас {format_currency(user['hash_fugasy'])}, "
            f"нужно {format_currency(bet)}",
            show_alert=True,
        )
        return

    chat_id = callback.message.chat.id

    if chat_id not in group_blackjack_games:
        deck = get_deck()
        group_blackjack_games[chat_id] = {
            "players": {},
            "dealer_cards": [deck.pop(), deck.pop()],
            "deck": deck,
        }

    game = group_blackjack_games[chat_id]
    deck = game["deck"]

    game["players"][user_id] = {
        "name": player_name,
        "bet": bet,
        "cards": [deck.pop(), deck.pop()],
        "status": "playing",
        "finished": False,
    }

    players_display = []
    for uid, player in game["players"].items():
        value, _ = calculate_hand(player["cards"])
        cards_str = " ".join(player["cards"])
        players_display.append(f"👤 {player['name']}: {cards_str} = **{value}**")

    players_text = "\n".join(players_display)
    text = f"""
♠️ **ГРУППОВОЙ BLACK JACK** ♠️

Карта дилера: {game['dealer_cards'][0]} ?  

Игроки ({len(game['players'])}):
{players_text}

Делайте ходы:
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎴 Ещё карту", callback_data=f"group_bj_hit"
                ),
                InlineKeyboardButton(
                    text="⏹️ Стоп", callback_data=f"group_bj_stand"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Начать игру дилера", callback_data="group_bj_dealer"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("✅ Вы присоединились!")


@dp.callback_query(F.data == "group_bj_hit")
async def group_blackjack_hit(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if chat_id not in group_blackjack_games:
        await callback.answer("❌ Игра не начиналась", show_alert=True)
        return

    game = group_blackjack_games[chat_id]

    if user_id not in game["players"]:
        await callback.answer("❌ Вы не в этой игре", show_alert=True)
        return

    player = game["players"][user_id]
    if player["finished"]:
        await callback.answer("❌ Ваша игра уже завершена", show_alert=True)
        return

    deck = game["deck"]
    if not deck:
        deck = get_deck()
        game["deck"] = deck

    player["cards"].append(deck.pop())
    value, _ = calculate_hand(player["cards"])

    if value > 21:
        player["status"] = "bust"
        player["finished"] = True
        await callback.answer(f"💥 ПЕРЕБОР! {value} очков - ваша игра закончена")
    else:
        await callback.answer(f"🎴 Взяли карту. Сумма: {value}")


@dp.callback_query(F.data == "group_bj_stand")
async def group_blackjack_stand(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if chat_id not in group_blackjack_games:
        await callback.answer("❌ Игра не начиналась", show_alert=True)
        return

    game = group_blackjack_games[chat_id]

    if user_id not in game["players"]:
        await callback.answer("❌ Вы не в этой игре", show_alert=True)
        return

    player = game["players"][user_id]
    value, _ = calculate_hand(player["cards"])
    player["status"] = "stand"
    player["finished"] = True
    await callback.answer(f"⏹️ Вы остановились с {value} очками")


@dp.callback_query(F.data == "group_bj_dealer")
async def group_blackjack_dealer(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in group_blackjack_games:
        await callback.answer("❌ Нет активной игры", show_alert=True)
        return

    game = group_blackjack_games[chat_id]
    deck = game["deck"]
    dealer_cards = game["dealer_cards"]

    while True:
        dealer_value, _ = calculate_hand(dealer_cards)
        if dealer_value >= 17:
            break
        if not deck:
            deck = get_deck()
            game["deck"] = deck
        dealer_cards.append(deck.pop())

    dealer_value, _ = calculate_hand(dealer_cards)
    dealer_has_blackjack = is_blackjack(dealer_cards)

    results = []
    for uid, player in game["players"].items():
        user = get_user(uid)
        player_value, _ = calculate_hand(player["cards"])
        player_has_blackjack = is_blackjack(player["cards"])

        if player["status"] == "bust":
            user["hash_fugasy"] -= player["bet"]
            user["total_lost"] += player["bet"]
            results.append(f"💥 {player['name']} - ПЕРЕБОР ({player_value})")
        elif player_has_blackjack and dealer_has_blackjack:
            user["hash_fugasy"] += player["bet"]
            results.append(f"🤝 {player['name']} - BLACK JACK НИЧЬЯ")
        elif player_has_blackjack:
            winnings = player["bet"] * 5
            user["hash_fugasy"] += winnings
            user["total_won"] += winnings
            results.append(f"🌟 {player['name']} - BLACK JACK! +{winnings}")
        elif dealer_has_blackjack:
            user["hash_fugasy"] -= player["bet"]
            user["total_lost"] += player["bet"]
            results.append(
                f"🌟 {player['name']} - Дилер BLACK JACK, -{player['bet']}"
            )
        elif dealer_value > 21:
            win = int(player["bet"] * 1.5)
            user["hash_fugasy"] += win
            user["total_won"] += win
            results.append(f"✅ {player['name']} - ВЫИГРЫШ! Дилер перебрал")
        elif player_value > dealer_value:
            win = int(player["bet"] * 1.5)
            user["hash_fugasy"] += win
            user["total_won"] += win
            results.append(
                f"✅ {player['name']} - ВЫИГРЫШ! ({player_value} vs {dealer_value})"
            )
        elif player_value == dealer_value:
            user["hash_fugasy"] += player["bet"]
            results.append(f"🤝 {player['name']} - НИЧЬЯ ({player_value})")
        else:
            user["hash_fugasy"] -= player["bet"]
            user["total_lost"] += player["bet"]
            results.append(
                f"❌ {player['name']} - ПРОИГРЫШ ({player_value} vs {dealer_value})"
            )

        user["games_played"] += 1
        save_user(uid, user)

    results_text = "\n".join(results)
    text = f"""
🎰 **РЕЗУЛЬТАТЫ BLACK JACK** 🎰

Карты дилера: {' '.join(dealer_cards)} = **{dealer_value}**

Результаты:
{results_text}
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="♠️ Новая игра", callback_data="group_blackjack_menu"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    if chat_id in group_blackjack_games:
        del group_blackjack_games[chat_id]

    await callback.answer("🎉 Игра завершена!")


# =============== СТАТИСТИКА И БАЛАНС ===============

@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    profit = user["total_won"] - user["total_lost"]
    profit_emoji = "📈" if profit >= 0 else "📉"
    profit_word = declension(abs(profit), "Хэш-Фугас", "Хэш-Фугаса", "Хэш-Фугас")

    text = f"""
📊 **ВАША СТАТИСТИКА** 📊

Баланс: {format_currency(user['hash_fugasy'])}  

Всего игр: {user['games_played']}  
Выигрыш: +{user['total_won']} 🪙  
Проигрыш: -{user['total_lost']} 🪙  

Прибыль/Убыток: {profit_emoji} {profit:+d} {profit_word}
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "balance")
async def show_balance(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)

    text = f"""
💰 **ВАШ БАЛАНС** 💰

{format_currency(user['hash_fugasy'])}

Начинайте игру и выигрывайте! 🎰
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# =============== НАВИГАЦИЯ В МЕНЮ ===============

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    player_name = get_user_name(callback.from_user)

    await state.set_state(GameStates.main_menu)
    welcome_text = create_main_menu(user, player_name)

    await callback.message.edit_text(
        welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
    )
    await callback.answer()


# =============== ЗАПУСК ===============

async def main():
    print("🎰 Казино БАБАХИ запущено (полная версия с одиночными и групповыми играми)")
    load_users_data()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())

