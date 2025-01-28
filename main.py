import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
import requests

class SetProfileState(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    calorie_goal = State()


class LogFoodState(StatesGroup):
    food = State()


def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:  # Проверяем, есть ли найденные продукты
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
        return None
    print(f"Ошибка: {response.status_code}")
    return None



bd = {}
token = ""

bot = Bot(token=token)
dp = Dispatcher()


@dp.message(Command('set_profile'))
async def cmd_set_profile(message: types.Message, state: FSMContext):
    await message.reply("Пожалуйста,введите ваш вес (в кг):")
    await state.set_state(SetProfileState.weight)


@dp.message(SetProfileState.weight)
async def weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(weight=weight)
        await message.reply("Укажите ваш рост (в см):")
        await state.set_state(SetProfileState.height)
    except ValueError:
        await message.reply("Пожалуйста, введите число. Введите ваш вес :")


@dp.message(SetProfileState.height)
async def height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text)
        await state.update_data(height=height)
        await message.reply("Укажите ваш возраст :")
        await state.set_state(SetProfileState.age)
    except ValueError:
        await message.reply("Пожалуйста, введите число. Введите ваш рост :")


@dp.message(SetProfileState.age)
async def age(message: types.Message, state: FSMContext):
    try:
        age = float(message.text)
        await state.update_data(age=age)
        await message.reply("Укажите,сколько минут активности у вас в день? :")
        await state.set_state(SetProfileState.activity)
    except ValueError:
        await message.reply("Пожалуйста, введите число. Введите ваш возраст :")


@dp.message(SetProfileState.activity)
async def activity(message: types.Message, state: FSMContext):
    try:
        activity = float(message.text)
        await state.update_data(activity=activity)
        await message.reply("В каком городе вы находитесь? :")
        await state.set_state(SetProfileState.city)
    except ValueError:
        await message.reply("Пожалуйста, введите число. Сколько минут активности у вас в день? :")


@dp.message(SetProfileState.city)
async def city(message: Message, state: FSMContext):
    try:
        city = message.text
        await state.update_data(city=city)
        data = await state.get_data()
        bd[message.from_user.id] = data
        bd[message.from_user.id]['calorie_goal'] = bd[message.from_user.id]['weight'] * 10 + 6.25 * \
                                                   bd[message.from_user.id]['height'] - 4 * bd[message.from_user.id][
                                                       'age'] + bd[message.from_user.id]['activity'] * 8
        bd[message.from_user.id]['water_goal'] = bd[message.from_user.id]['weight'] * 20 + 350 * \
                                                 bd[message.from_user.id]['activity'] / 40 + 550
        bd[message.from_user.id]['logged_water'] = 0
        bd[message.from_user.id]['logged_calories'] = 0
        bd[message.from_user.id]['burned_calories'] = 0

        await state.set_state(SetProfileState.calorie_goal)
        await message.reply(
            f"Укажите вашу цель по ккалориям, рекомендованное значение - {bd[message.from_user.id]['calorie_goal']}")
    except Exception as e:
        print(e)
        await message.reply("В каком городе вы находитесь? :")


@dp.message(SetProfileState.calorie_goal)
async def goal(message: types.Message, state: FSMContext):
    try:
        calorie_goal = float(message.text)
        bd[message.from_user.id]['calorie_goal'] = calorie_goal
        await state.update_data(calorie_goal=calorie_goal)
        await state.clear()
        await message.reply("Результаты успешно записаны :")
    except ValueError:
        await message.reply(
            f"Укажите вашу цель по ккалориям, рекомендованное значение - {bd[message.from_user.id]['calorie_goal']}")



@dp.message(Command("log_food"))
async def food_start(message: Message, state: FSMContext):
    try:
        product_name = message.text.split()[-1]
        await state.set_state(LogFoodState.food)
        await state.update_data(food_calories=get_food_info(product_name)['calories'])
        await message.reply("Сколько грамм было вами съедено?")
    except Exception as e :
        await message.reply("Попробуйте ещё раз")


@dp.message(LogFoodState.food)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        grams = float(message.text)
        data = await state.get_data()
        data = float(data['food_calories'])
        bd[message.from_user.id]['logged_calories'] += data * grams / 100
        await message.reply(f"Записано, вы употребили: {data * grams / 100}ккал.")
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, укажите граммовки ещё раз:")


@dp.message(Command('log_water'))
async def log_water(message: types.Message):
    try:

        bd[message.from_user.id]['logged_water'] += float(message.text.split()[-1])
        water_norm = bd[message.from_user.id]['water_goal'] - bd[message.from_user.id]['logged_water']

        if water_norm > 0:
            await message.reply(
                f"Выпитая вода - записана. Вам осталось для выполнения нормы: {water_norm}.")
        else:
            await message.reply(f"Выпитая вода - записана.Вы выполнели норму воды, поздравляю!")

    except ValueError as e:
        await message.reply("Пожалуйста, попробуйте ввести количество выпитой вами воды ещё раз :")


@dp.message(Command('log_workout'))
async def log_workout(message: types.Message):
    try:
        train = message.text.split()[-2]
        train_time = float(message.text.split()[-1])
        bd[message.from_user.id]['water_goal'] += int(train_time / 30 * 300)
        bd[message.from_user.id]['burned_calories'] += train_time * 12

        await message.reply(
            f"Ваша тренировака {train}, длительностью {train_time} минут'ы. Вы потратили {train_time * 12} ккал. Дополнительно: выпейте {train_time / 30 * 300} мл воды.")

    except ValueError as e:
        await message.reply("Попробуйте ещё раз")


@dp.message(Command('check_progress'))
async def check_progress(message: types.Message):
    try:
        bot_answer = f"""📊 Ваш Прогресс:
        Вода:
        - Выпито: {bd[message.from_user.id]['logged_water']}  мл из {bd[message.from_user.id]['water_goal']} мл.
        - Осталось: {bd[message.from_user.id]['water_goal'] - bd[message.from_user.id]['logged_water']} мл.

        Калории:
        - Потреблено:
{bd[message.from_user.id]['logged_calories']} ккал из {bd[message.from_user.id]['calorie_goal']} ккал.
        - Сожжено: {bd[message.from_user.id]['burned_calories']} ккал.
        - Баланс: {bd[message.from_user.id]['calorie_goal'] - bd[message.from_user.id]['logged_calories'] + bd[message.from_user.id]['burned_calories']} ккал."""

        await message.reply(bot_answer)
    except Exception as e:
        await message.reply("Попробуйте ещё раз")





async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())