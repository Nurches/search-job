"""Словари для фильтрации и оценки заказов.

Все шаблоны — регулярные выражения, применяются к тексту в нижнем регистре
(ё заменена на е). Правьте смело: это главный рычаг качества ленты.
"""

# Категории IT-заказов: тег -> шаблоны.
CATEGORIES: dict[str, list[str]] = {
    "mobile": [
        r"flutter", r"\bdart\b", r"react[\s-]?native", r"\bkotlin\b", r"\bswift(ui)?\b",
        r"android", r"\bios\b", r"мобильн\w* (приложени|разработ|верси)", r"\bapk\b",
        r"приложени\w* (для|под) (телефон|смартфон|android|ios|айфон)", r"app ?store",
        r"google ?play", r"mobile app", r"кроссплатформ",
    ],
    "frontend": [
        r"\breact\b", r"next\.?js", r"\bvue\b", r"nuxt", r"angular", r"svelte",
        r"фронт[\s-]?енд", r"frontend", r"front-end", r"верстк|верстат|сверстать",
        r"\bhtml\b", r"\bcss\b", r"tailwind", r"typescript", r"javascript", r"\bjs\b",
    ],
    "backend": [
        r"fast ?api", r"django", r"flask", r"python", r"golang", r"\bна go\b", r"\bgo[\s-]?(разработ|developer|backend)",
        r"node\.?js", r"nest\.?js", r"express", r"\bphp\b", r"laravel", r"symfony", r"yii",
        r"\bjava\b", r"spring", r"c#", r"\.net\b", r"\bruby\b", r"rails", r"\brust\b",
        r"\bapi\b", r"rest ?api", r"graphql", r"бэк[\s-]?енд|бек[\s-]?енд|backend|back-end",
        r"микросервис", r"postgres", r"mysql", r"mongo", r"redis", r"база данных|базы данных|\bбд\b",
    ],
    "web": [
        r"\bсайт", r"лендинг", r"landing", r"веб[\s-]?(сервис|приложени|платформ|разработ|студи)",
        r"web[\s-]?(app|site|development|developer)", r"website", r"интернет[\s-]?магазин",
        r"wordpress", r"tilda|тильд", r"битрикс(?!24)|bitrix(?!24)", r"\bcms\b", r"shopify",
        r"webflow", r"opencart", r"woocommerce", r"личн\w* кабинет", r"админк|админ[\s-]?панел",
        r"full[\s-]?stack|фулл?[\s-]?стек",
    ],
    "bots": [
        r"телеграм[\s-]?бот|telegram[\s-]?бот|telegram bot|тг[\s-]?бот", r"\bбот[аеуы]?\b",
        r"чат[\s-]?бот|chat ?bot", r"aiogram", r"telebot|pytelegrambotapi", r"whatsapp[\s-]?бот",
        r"mini ?app|мини[\s-]?приложени|web ?app телеграм",
    ],
    "ai": [
        r"нейросет", r"\bgpt", r"openai", r"\bllm", r"\bml\b", r"машинн\w* обучени",
        r"парсер|парсинг|спарсить|scrap", r"data science", r"\bai\b|\bии\b", r"claude",
        r"computer vision|компьютерн\w* зрени", r"rag\b", r"langchain", r"автоматизац",
    ],
    "devops": [
        r"docker", r"kubernetes|\bk8s\b", r"devops", r"ci/cd", r"настро\w* сервер",
        r"\bvps\b|\bvds\b", r"nginx", r"linux", r"\baws\b", r"деплой|deploy", r"хостинг",
    ],
    "crm": [
        r"\b1с\b|\b1c\b", r"amo ?crm|амо ?срм", r"bitrix ?24|битрикс ?24", r"\bcrm\b|\bсрм\b",
        r"интеграци\w* (с|api)", r"google (sheets|таблиц)", r"zapier|make\.com|n8n",
    ],
    "games": [r"unity", r"unreal", r"godot", r"game ?dev|геймдев", r"разработ\w* игр", r"\bигр[аыу]\b"],
    "design": [r"ui/ux|ux/ui|\bui\b|\bux\b", r"figma|фигм", r"дизайн\w* (сайт|приложени|интерфейс|лендинг)", r"прототип"],
    "qa": [r"тестировщ", r"\bqa\b", r"автотест", r"selenium|playwright|cypress"],
    "study": [
        r"курсов\w+ (работ|проект)", r"курсовую|курсовая", r"лабораторн", r"дипломн|диплом\b",
        r"задач\w* по (программ|информатик|python|c\+\+|java)", r"олимпиад", r"домашн\w* задани",
        r"для студент", r"контрольн\w* по", r"\bвуз", r"\bуниверситет", r"школьн",
    ],
}

TAG_LABELS = {
    "mobile": "Мобильные",
    "frontend": "Фронтенд",
    "backend": "Бэкенд",
    "web": "Сайты/веб",
    "bots": "Боты",
    "ai": "AI/парсинг",
    "devops": "DevOps",
    "crm": "1С/CRM",
    "games": "Игры",
    "design": "UI/UX",
    "qa": "QA",
    "study": "Учёба",
}

# Главные категории для специалиста полного цикла (веб + мобайл).
CORE_TAGS = {"mobile", "frontend", "backend", "web", "bots"}

# Признаки заказа (а не рекламы исполнителя) — важно для Telegram.
ORDER_MARKERS = [
    r"\bнуж(ен|на|но|ны)\b", r"требуе?тся", r"\bищ(у|ем)\s+(\S+\s+)?(разработчик|программист|исполнител|специалист|фрилансер|кодер|верстальщик|дизайнер|flutter|react|python|backend|frontend|mobile|ios|android|dev|full)",
    r"\bищ(у|ем)\s+(кто|того,? кто)", r"кто (может|сможет|возьмется|сделает|умеет)",
    r"\bзадач[аи]\b", r"\bтз\b|техническ\w* задани", r"\bзаказ\b", r"бюджет", r"оплат[аы]",
    r"\bhiring\b", r"looking for", r"need(ed)? (a|an)?\s*\w*\s*(developer|programmer|freelancer)",
    r"#заказ|#задача|#вакансия|#работа|#проект|#hiring|#vacancy|#job",
    r"\bвакансия\b", r"в команду", r"\bзарплат|\bзп\b|\bоклад",
    r"разработать|сделать|создать|доработать|написать|исправить|настроить",
]

# Признаки того, что автор предлагает свои услуги или ищет работу.
OFFER_MARKERS = [
    r"\b(ищу|возьму|беру)\s+(работу|заказы?|проекты?|подработку)",
    r"^\s*(выполню|сделаю|разработаю|создам|напишу|сверстаю|настрою)\b",
    r"#резюме|#ищу_?работу|#resume|#cv\b|#помогу|#услуги|#предлагаю",
    r"\[for hire\]|\bfor hire\b", r"мои услуги|предлагаю (свои )?услуги|оказываю услуги",
    r"мое портфолио|портфолио в профиле", r"обращайтесь,? (сделаю|помогу)",
    r"я (опытный )?(frontend|backend|fullstack|flutter|python|php|ios|android)?\s*(разработчик|программист)\b.*(ищу|готов|возьм)",
]

# Мусор, скам и не-IT.
SPAM_MARKERS = [
    r"без вложений", r"пассивн\w* доход", r"от \d+ ?(т(ыс)?|к|000) ?(руб|р|₽|тг|₸)? ?в (день|сутки)",
    r"заработ\w* (от|до) \d", r"казино|ставк[иа] на спорт|букмекер", r"вебкам|webcam|18\+|эскорт",
    r"закладк|кладмен", r"сигналы (крипт|бинанс)|памп", r"пирамид", r"схем\w* заработка",
    r"курьер|грузчик|упаковщик|оператор call|колл[\s-]?центр", r"набор (сотрудников|персонала) на удаленку",
    r"отзывы на (wb|вб|ozon|озон|маркетплейс)", r"выкуп\w* товар", r"рассылк\w* спам",
    r"продам (аккаунт|базу)", r"пробив", r"обнал",
]

# Не-IT темы, которые тоже не нужны (если нет IT-категории).
NON_IT_MARKERS = [
    r"копирайт|рерайт|статьи для|написать текст", r"\bsmm\b|таргетолог|сторис",
    r"перевод(чик|ы) текст", r"озвучк|монтаж видео|видеомонтаж|reels", r"логотип|визитк|баннер",
    r"бухгалтер|юрист|менеджер по продаж",
]

# Не-IT профессии в заголовке/начале поста. Такой заказ отбрасывается, если
# рядом нет признаков разработки (DEV_HEAD_MARKERS) или IT-категории в заголовке.
NON_IT_HEAD_MARKERS = [
    r"sales|продаж|marketing|маркетолог|маркетинг", r"ассистент|assistant|помощник",
    r"recruit|рекрутер|\bhr\b", r"\blogo|логотип|\blabel\b|этикет|баннер|banner|визитк|полиграф|упаковк",
    r"accountant|accounts payable|бухгалтер|юрист|lawyer", r"lead ?gen|лидоген|линкбилд|link ?building",
    r"\bsmm\b|таргет|instagram|инстаграм|tiktok|тикток|reels", r"съемк|фотограф|photograph|product photo",
    r"мультфильм|анимаци|animation|видеомонтаж|монтаж|video edit|озвуч|voice ?over",
    r"копирайт|copywrit|рерайт|статей|статьи|article|перевод|translat",
    r"customer (support|success|service)|support specialist|оператор|data entry|ввод данных",
    r"business development|бизнес[\s-]?девелоп|менеджер|manager|fulfillment|dropship",
]

DEV_HEAD_MARKERS = [
    r"разработ|(?<!business )develop|программист|programmer|engineer|инженер", r"приложени|\bapp\b",
    r"\bбот|bot\b", r"сайт|website|landing|лендинг", r"\bapi\b|backend|frontend|full[\s-]?stack|фулл?[\s-]?стек",
    r"парсер|parser|scraper|скрипт|script", r"\bdev\b|devops|тестировщ|\bqa (engineer|инженер)",
]

# Теги, которые сами по себе не доказывают, что заказ про разработку.
WEAK_TAGS = {"design"}

# Признаки большого проекта "под ключ".
BIG_PROJECT_MARKERS = [
    r"под ключ", r"с нуля", r"\bmvp\b", r"стартап|startup", r"маркетплейс|marketplace",
    r"платформ[аыу]", r"\bсервис\b|веб[\s-]?сервис", r"crm[\s-]?систем", r"личн\w* кабинет",
    r"админ[\s-]?панел|админк", r"full[\s-]?stack|фулл?[\s-]?стек", r"(бэк|бек)енд и фронт|фронтенд и (бэк|бек)",
    r"ios и android|android и ios", r"мобильн\w* приложени", r"долгосроч|на постоянн|long[\s-]?term",
    r"команд[ау] разработ", r"\bsaas\b", r"агрегатор", r"мессенджер", r"доставк",
]

SMALL_TASK_MARKERS = [
    r"поправить|подправить|мелк\w+ правк|небольш\w+ (правк|доработ|задач)", r"исправить ошибку",
    r"перенести сайт", r"наполнени|заполнить (сайт|карточк)", r"за (5|10|15) минут",
    r"поменять (цвет|текст|кнопк)", r"установить (плагин|счетчик)",
]

URGENT_MARKERS = [r"(?<!долго)срочн", r"\basap\b", r"\burgent", r"сегодня", r"до завтра", r"горит"]

KZ_MARKERS = [
    r"казахстан", r"алмат", r"астан", r"шымкент", r"караганд", r"актоб", r"атырау",
    r"павлодар", r"усть[\s-]?каменогорск", r"тенге|₸|\bтг\b|\bkzt\b", r"\.kz\b", r"\bрк\b",
]

CONTACT_MARKERS = [r"@\w{4,}", r"t\.me/\w+", r"\+7\s?\(?\d{3}", r"whatsapp|ватсап|вотсап", r"пишите в лс|в личку"]

REMOTE_MARKERS = [r"удален", r"remote", r"дистанцион", r"из дома"]
