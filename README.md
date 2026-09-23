(English readme soon)

# tg_giwey

Бот (и мини-приложение в скором времени) для Telegram, которое проводит *честные* и *открытые* розыгрыши призов.

## Начало работы

### Шаг 1 - скопируйте репозиторий

(Вы сами можете знать как это сделать, но я напишу это позже)

### Шаг 2 - Запустите виртуальное окружение и установите зависимости

Для Windows:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Для Linux:
```
python -m venv .venv
source .venv/bin/activate 
# ...или любой другой скрипт, в завимости от терминала, например для fish
# source .venv/bin/activate.fish
pip install -r requirements.txt
```

### Шаг 3 - Настройте переменные окружения

```
cp .env.example .env
```

Заполните `BOT_TOKEN` и `ADMIN_ID` в созданном файле `.env`

### Шаг 4 - Запустите бота

TBD