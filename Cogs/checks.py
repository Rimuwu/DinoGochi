import random
from functions import functions

class checks:

    @staticmethod
    def pass_active(user, dino_id, dino):

        if user['dinos'][dino_id]['stats']['game'] > 60:
            if dino['stats']['mood'] < 100:
                if random.randint(1,15) == 1:
                    user['dinos'][dino_id]['stats']['mood'] += random.randint(1,15)

                if random.randint(1,60) == 1:
                    user['coins'] += random.randint(0,100)

        if user['dinos'][dino_id]['stats']['mood'] > 80:
            if random.randint(1,60) == 1:
                user['coins'] += random.randint(0,100)

        if user['dinos'][dino_id]['stats']['unv'] <= 20 and user['dinos'][dino_id]['stats']['unv'] != 0:
            if dino['stats']['mood'] > 0:
                if random.randint(1,30) == 1:
                    user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,2)

        return user

    @staticmethod
    def sleep(user, dino_id, dino):
        if user['dinos'][dino_id]['stats']['unv'] < 100:
            if random.randint(1,45) == 1:
                user['dinos'][dino_id]['stats']['unv'] += random.randint(1,2)

        if user['dinos'][dino_id]['stats']['game'] < 40:
            if random.randint(1,45) == 1:
                user['dinos'][dino_id]['stats']['game'] += random.randint(1,2)

        if user['dinos'][dino_id]['stats']['mood'] < 50:
            if random.randint(1,45) == 1:
                user['dinos'][dino_id]['stats']['mood'] += random.randint(1,2)

        if user['dinos'][dino_id]['stats']['heal'] < 100:
            if user['dinos'][dino_id]['stats']['eat'] > 50:
                if random.randint(1,45) == 1:
                    user['dinos'][dino_id]['stats']['heal'] += random.randint(1,2)
                    user['dinos'][dino_id]['stats']['eat'] -= random.randint(0,1)
        return user

    @staticmethod
    def game(user, dino_id, dino):
        if random.randint(1, 65) == 1: #unv
            user['dinos'][dino_id]['stats']['unv'] -= random.randint(0,2)

        if random.randint(1, 45) == 1: #unv
            user['lvl'][1] += random.randint(0,20)

        if user['dinos'][dino_id]['stats']['game'] < 100:
            if random.randint(1,30) == 1:
                user['dinos'][dino_id]['stats']['game'] += int(random.randint(2,15) * user['dinos'][dino_id]['game_%'])

        return user

    @staticmethod
    def hunting(user, dino_id, dino):

        if random.randint(1, 65) == 1: #unv
            user['dinos'][dino_id]['stats']['unv'] -= random.randint(0,1)

            if random.randint(1, 45) == 1: #unv
                user['lvl'][1] += random.randint(0,20)

            r = random.randint(1, 15)
            if r == 1:

                if dino['h_type'] == 'all':
                    items = [2, 5, 6, 7, 8, 9, 10, 11, 12, 13]

                if dino['h_type'] == 'collecting':
                    items = [6, 9, 11]

                if dino['h_type'] == 'hunting':
                    items = [5, 8, 12]

                if dino['h_type'] == 'fishing':
                    items = [7, 10, 13]

                item = random.choice(items)
                i_count = random.randint(1, 2)
                for i in list(range(i_count)):
                    user['inventory'].append(str(item))
                    dino['target'][0] += 1
        return user

    @staticmethod
    def journey(user, dino_id, dino):

        if random.randint(1, 65) == 1: #unv
            user['dinos'][dino_id]['stats']['unv'] -= random.randint(0,1)

        if random.randint(1, 45) == 1: #unv
            user['lvl'][1] += random.randint(0,20)

        r_e_j = random.randint(1,30)
        if r_e_j == 1:
            if random.randint(1,3) != 1:

                if dino['stats']['mood'] >= 55:
                    mood_n = True
                else:
                    mood_n = False

                r_event = random.randint(1, 100)
                if r_event in list(range(1,51)): #обычное соб
                    events = ['sunny', 'm_coins']
                elif r_event in list(range(51,76)): #необычное соб
                    events = ['+eat', 'sleep', 'u_coins']
                elif r_event in list(range(76,91)): #редкое соб
                    events = ['random_items', 'b_coins']
                elif r_event in list(range(91,100)): #мистическое соб
                    events = ['random_items_leg', 'y_coins']
                else: #легендарное соб
                    events = ['egg', 'l_coins']

                event = random.choice(events)
                if event == 'sunny':
                    mood = random.randint(1, 15)
                    user['dinos'][dino_id]['stats']['mood'] += mood

                    if user['language_code'] == 'ru':
                        event = f'☀ | Солнечно, настроение динозавра повысилось на {mood}%'
                    else:
                        event = f"☀ | Sunny, the dinosaur's mood has increased by {mood}%"

                elif event == '+eat':
                    eat = random.randint(1, 10)
                    user['dinos'][dino_id]['stats']['eat'] += eat

                    if user['language_code'] == 'ru':
                        event = f'🥞 | Динозавр нашёл что-то вкусненькое и съел это!'
                    else:
                        event = f"🥞 | The dinosaur found something delicious and ate it!"

                elif event == 'sleep':
                    unv = random.randint(1, 5)
                    user['dinos'][dino_id]['stats']['unv'] += unv

                    if user['language_code'] == 'ru':
                        event = f'💭 | Динозавр смог вздремнуть по дороге.'
                    else:
                        event = f"💭 | Динозавр смог вздремнуть по дороге."

                elif event == 'random_items':
                    items = ["1", "2", '17', '18', '19', '25', '25']
                    item = random.choice(items)
                    if mood_n == True:
                        user['inventory'].append(item)

                        if user['language_code'] == 'ru':
                            event = f"🧸 | Бегая по лесам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                        else:
                            event = f"🧸 | Running through the woods, the dinosaur sees something that looks like a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                    if mood_n == False:

                        if user['language_code'] == 'ru':
                            event = '❌ | Редкое событие отменено из-за плохого настроения!'
                        else:
                            event = '❌ | A rare event has been canceled due to a bad mood!'

                elif event == 'random_items_leg':
                    items = ["4", "13", "15", "16"]
                    item = random.choice(items)
                    if mood_n == True:
                        user['inventory'].append(item)

                        if user['language_code'] == 'ru':
                            event = f"🧸 | Бегая по горам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                        else:
                            event = f"🧸 | Running through the mountains, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                    if mood_n == False:

                        if user['language_code'] == 'ru':
                            event = '❌ | Мистическое событие отменено из-за плохого настроения!'
                        else:
                            event = '❌ | The mystical event has been canceled due to a bad mood!'

                elif event == 'egg':
                    eggs = ["3", '20', '21', '22', '23', '24']
                    egg = random.choice(eggs)
                    if mood_n == True:
                        user['inventory'].append(egg)

                        if user['language_code'] == 'ru':
                            event = f"🧸 | Бегая по по пещерам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][egg]['nameru']}!"
                        else:
                            event = f"🧸 | Running through the caves, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][egg]['nameen']}!"

                    if mood_n == False:

                        if user['language_code'] == 'ru':
                            event = '❌ | Легендарное событие отменено из-за плохого настроения!'
                        else:
                            event = '❌ | The legendary event has been canceled due to a bad mood!'

                elif event[2:] == 'coins':

                    if mood_n == True:
                        if event[:1] == 'm':
                            coins = random.randint(1, 10)
                        if event[:1] == 'u':
                            coins = random.randint(10, 50)
                        if event[:1] == 'b':
                            coins = random.randint(50, 100)
                        if event[:1] == 'y':
                            coins = random.randint(100, 300)
                        if event[:1] == 'l':
                            coins = random.randint(300, 500)

                        user['coins'] += coins

                        if user['language_code'] == 'ru':
                            event = f'💎 | Ходя по тропинкам, динозавр находит мешочек c монетками.\n>   Вы получили {coins} монет.'
                        else:
                            event = f'💎 | Walking along the paths, the dinosaur finds a bag with coins.\n> You have received {coins} coins.'

                    if mood_n == False:
                        if user['language_code'] == 'ru':
                            event = '❌ | Cобытие отменено из-за плохого настроения!'
                        else:
                            event = '❌ | Event has been canceled due to a bad mood!'

                user['dinos'][ dino_id ]['journey_log'].append(event)

            else:
                if dino['stats']['mood'] >= 55:
                    mood_n = False
                else:
                    mood_n = True

                r_event = random.randint(1, 100)
                if r_event in list(range(1,51)): #обычное соб
                    events = ['rain', 'm_coins']
                elif r_event in list(range(51,76)): #необычное соб
                    events = ['fight', '-eat', 'u_coins']
                elif r_event in list(range(76,91)): #редкое соб
                    events = ['b_coins']
                elif r_event in list(range(91,100)): #мистическое соб
                    events = ['toxic_rain', 'y_coins']
                else: #легендарное соб
                    events = ['lose_item', 'l_coins']


                event = random.choice(events)
                if event == 'rain':
                    mood = random.randint(1, 15)
                    user['dinos'][dino_id]['stats']['mood'] -= mood

                    if user['language_code'] == 'ru':
                        event = f'🌨 | Прошёлся дождь, настроение понижено на {mood}%'
                    else:
                        event = f"🌨 | It has rained, the mood is lowered by {mood}%"

                elif event == '-eat':
                    eat = random.randint(1, 10)
                    heal = random.randint(1, 3)
                    user['dinos'][dino_id]['stats']['eat'] -= eat
                    user['dinos'][dino_id]['stats']['heal'] -= heal

                    if user['language_code'] == 'ru':
                        event = f'🍤 | Динозавр нашёл что-то вкусненькое и съел это, еда оказалась испорчена. Динозавр теряет {eat}% еды и {heal}% здоровья.'
                    else:
                        event = f"🍤 | The dinosaur found something delicious and ate it, the food was spoiled. Dinosaur loses {eat}% of food and {heal}% health."

                elif event == 'toxic_rain':
                    heal = random.randint(1, 5)
                    user['dinos'][dino_id]['stats']['heal'] -= heal

                    if user['language_code'] == 'ru':
                        event = f"⛈ | Динозавр попал под токсичный дождь!"
                    else:
                        event = f"⛈ | The dinosaur got caught in the toxic rain!"


                elif event == 'fight':
                    unv = random.randint(1, 10)
                    user['dinos'][dino_id]['stats']['unv'] -= unv

                    if random.randint(1,2) == 1:
                        heal = random.randint(1, 5)
                        user['dinos'][dino_id]['stats']['heal'] -= heal
                        textru = f'\nДинозавр не смог избежать ран, он теряет {heal}% здоровья.'
                        texten = f"\nThe dinosaur couldn't escape the wounds, it loses {heal}% health."
                    else:
                        textru = f'\nДинозавр смог избежать ран, он не теряет здоровья.'
                        texten = f"\nThe dinosaur was able to avoid wounds, he does not lose health."

                    if user['language_code'] == 'ru':
                        event = f'⚔ | Динозавр нарвался на драку, он теряет {unv}% сил.'
                        event += textru
                    else:
                        event = f"⚔ | The dinosaur ran into a fight, he loses {unv}% of his strength."
                        event += texten

                elif event == 'lose_items':
                    items = user['inventory']
                    item = random.choice(items)
                    if mood_n == True:
                        user['inventory'].remove(item)

                        if user['language_code'] == 'ru':
                            event = f"❗ | Бегая по лесам, динозавр обранил {items_f['items'][item]['nameru']}\n>  Предмет потерян!"
                        else:
                            event = f"🧸 | Running through the woods, the dinosaur sees something that looks like a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                    if mood_n == False:

                        if user['language_code'] == 'ru':
                            event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                        else:
                            event = '🍭 | Negative event canceled due to good mood!'

                elif event[2:] == 'coins':

                    if mood_n == True:
                        if event[:1] == 'm':
                            coins = random.randint(1, 2)
                        if event[:1] == 'u':
                            coins = random.randint(5, 10)
                        if event[:1] == 'b':
                            coins = random.randint(10, 50)
                        if event[:1] == 'y':
                            coins = random.randint(50, 100)
                        if event[:1] == 'l':
                            coins = random.randint(100, 150)

                        user['coins'] += coins

                        if user['language_code'] == 'ru':
                            event = f'💎 | Ходя по тропинкам, динозавр обронил несколько монет из рюкзака\n>   Вы потеряли {coins} монет.'
                        else:
                            event = f'💎 | Walking along the paths, the dinosaur dropped some coins from his backpack.   You have lost {coins} coins.'

                    if mood_n == False:
                        if user['language_code'] == 'ru':
                            event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                        else:
                            event = '🍭 | Negative event canceled due to good mood!'

                user['dinos'][ dino_id ]['journey_log'].append(event)

        return user
