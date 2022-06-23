# DinoGochi - telegram.bot на python
Телеграмм бот по типу тамагочи, только с динозаврами!
Игровой бот где вы должны ухаживать за своим динозавров, но тут присутствуют нотки рпг.

 > Ссылки:
 > - Бот: https://t.me/DinoGochi_bot
 > - Создатель: https://t.me/AS1AW

### Для запуска бота
- Установите 3-ю версию пайтона (рекомендуемая 3.10.4 / 3.9.6)
- Далее, установите все бибилиотеки из файла requirements.txt
>
    # Windows
    pip install requirements.txt

- Далее зайдите на https://account.mongodb.com/account/login
- Зарегестрируйте аккаунт и получите бесплатный кластер m1
- В кластере создайте базу с названием bot и коллекциями в ней
 > bot:
 > - users
 > - market
 > - referal_system

- В коллекцие market создайте документ
> market:
> - id: 1
> - products: Object

- В коллекцие referal_system создайте документ
> referal_system:
> - id: 1
> - codes: Array

- В файле config.py введите токены от кластера и бота
- Запустите файл main.py
