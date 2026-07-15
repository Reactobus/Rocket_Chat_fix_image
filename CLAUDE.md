# CLAUDE.md — Rocket_Chat_fix_image

Конфигурация Claude для проекта **Rocket_Chat_fix_image** — серверный патч Rocket.Chat.
Наследует общие правила из корневого `..\CLAUDE.md`; здесь — только специфика этого репо.

> Полный переносимый свод правил работы — [`..\WORK_RULES_PORTABLE.md`](../WORK_RULES_PORTABLE.md).

## Язык
- Общение с пользователем — **на русском**. Код, идентификаторы, имена якорей/маркеров — на английском.

---

## 1. Назначение

Серверный патч, **нормализующий имена файлов-вложений Rocket.Chat**: транслитерация кириллицы в
латиницу, пробелы и «мусорные» символы — в дефисы, приведение к нижнему регистру. Rocket.Chat
показывает сырое имя файла клиента в заголовке вложения (мобайл/десктоп); для не-ASCII имён
это выглядит сломанным. Патч правит бандловый `app.js`, **сохраняя upload-валидацию и image-pipeline**
(Sharp / EXIF / `tmpFile`) нетронутыми, и собирает **производный (derived) docker-patch образ**
`FROM` официального образа Rocket.Chat.

Пример: `ТЕСТ (В!!) () 00() всратос~.jpg` → `test-v-00-vsratos-.jpg`.
Старые сообщения в MongoDB сохраняют прежние заголовки — проверять **новой** загрузкой.

---

## 2. Стек и раскладка

- **`patch_appjs_upload_names.py`** — патчер на Python 3 (только stdlib: `json`, `sys`). Строковые/regex
  вставки в **vanilla** `app.js`, снятый с ТОГО ЖЕ тега образа. Идемпотентен (пропускает уже
  пропатченные блоки по маркерам `CYR_MAP` / `rc-patch:`). Три якорных вставки (`NEEDLE_*`):
  1. `uploadsOnValidate (file, options)` — префикс с санитизацией + `this.getCollection().updateOne(...)`;
     image-pipeline остаётся после первого `if (!file.type ...)`.
  2. `parseFileIntoMessageAttachments` — после `Uploads.updateFileMetadata(file._id, user._id, safeMetadata)`
     IIFE снова санитизирует `file.name` (маркер `rc-patch: sendFileMessage sanitize file.name`).
     Историческ до 8.3.x этот хук был в `sendFileMessage` после `Uploads.updateFileComplete`.
  3. visitor livechat — санитизация `file.name` перед сборкой attachment
     (маркер `rc-patch: livechat visitor sanitize file.name`).
- **`Patched_file/docker-patch/Dockerfile`** — `FROM registry.rocket.chat/rocketchat/rocket.chat:<TAG>` +
  `COPY app.js /app/bundle/programs/server/app/app.js`. Текущий `FROM`: **`8.6.0`**.
- **`Patched_file/docker-patch/app.js`** — тяжёлый reference-бандл; можно **не трекать** в git
  (закомментированная строка в `.gitignore`) и извлекать из образа при каждой сборке.
- **`docs/patching.md`** — поддерживаемое руководство по деплою (англ.). `PATCHING.md` в корне — только
  индекс-указатель на него. `README.md` — обзор проблемы + быстрые шаги.
- **`history/`** — журнал циклов апгрейда: `README.md` (как вести), `_TEMPLATE.md`, датированные записи
  `YYYY-MM-DD-<FROM>-to-<TO>.md`. Хост `Rocket_chat` / `srv771799`, каталог `/home/docker/rocketchat/`.

---

## 3. Build / deploy (по `docs/patching.md`)

Все команды — на сервере (при необходимости `sudo docker …`). Пути адаптировать под хост.

1. **Инвентаризация:** `docker ps -a` — точный `image:tag` Rocket.Chat; найти `docker-compose.yml` и
   сервис MongoDB.
2. **Бэкап MongoDB** (`mongodump`) ДО остановки app-сервисов. Обязательно перед прод-изменениями.
3. **Остановить app-контейнер:** `docker compose stop rocketchat` (Mongo не трогать).
4. **Извлечь vanilla `app.js` из ТОЧНОГО тега образа:**
   ```bash
   docker create --name rc-src <FULL_IMAGE:TAG>
   docker cp rc-src:/app/bundle/programs/server/app/app.js /tmp/rc_app.js
   docker rm rc-src
   ```
5. **Прогнать скрипт:** `python3 patch_appjs_upload_names.py /tmp/rc_app.js` — ждать
   `patched ok (3 блок(ов))`. При ошибке — брать свежую копию, не накапливать полу-патчи.
6. **Sanity `node --check`** пропатченного файла родным Node образа:
   ```bash
   docker run --rm --entrypoint node -v /path/app.js:/check/app.js:ro \
     registry.rocket.chat/rocketchat/rocket.chat:<TAG> --check /check/app.js
   ```
7. **Собрать образ:** Dockerfile `FROM …:<TAG>`, `docker build --no-cache -t …:<TAG>-patched .`
   (`--no-cache` обязателен, иначе старый слой маскирует новый `app.js`).
8. **Переключить compose** на тег `<TAG>-patched`, `docker compose up -d rocketchat --force-recreate`.
9. **Проверка:** дождаться `SERVER RUNNING` в `docker logs`; функциональный тест — загрузить файл с
   «грязным» (кириллица/пробелы/пунктуация) именем, проверить заголовок вложения. В работающем
   контейнере маркеры: `rc-patch:` = 2, `CYR_MAP` = 6.

Скрипт патча на сервере **не хранится** — копировать `patch_appjs_upload_names.py` из репо при каждом
апгрейде (репо — единственный источник правды).

---

## 4. Version-drift gotcha (главная опасность)

Строки-якоря `NEEDLE_*` **версионно-зависимы** — привязаны к формату минифицированного бандла.
Проверено: **8.5.0 → 8.6.0 якоря без изменений** (`patched ok`, дифф структуры нулевой); а на
переходе **8.3.2 → 8.5.0 якоря сместились** (6-пробельный отступ → 4/8, `"".concat()` → template
literals, хук №2 переехал `sendFileMessage`/`updateFileComplete` → `parseFileIntoMessageAttachments`/
`updateFileMetadata`).

При апгрейде Rocket.Chat **всегда перепроверять** якоря против свежего vanilla-бандла:
- каждый из 3 якорей **уникален** (`count == 1`) в новом `app.js`;
- image-pipeline остаётся **после** первого `if (!file.type ...)` в `uploadsOnValidate`;
- внутри `uploadsOnValidate` всё ещё используется `this.getCollection()`.

Если якоря сместились — обновить `NEEDLE_*` в скрипте (не заменять метод целиком) и **залогировать дифф
в `history/`** новой записью по `_TEMPLATE.md`.

---

## 5. Актуальность документации (docs-currency)

При любом изменении поведения/якорей/версии — **в той же правке**:
- обновить строки tested-version (`README.md` «Tested on …», `docs/patching.md` «Verified stack»,
  `Dockerfile` `FROM …:<TAG>`);
- **создать запись в `history/`** по `_TEMPLATE.md` (в конце цикла, после успешного деплоя и проверки)
  и дописать строку в `history/README.md` (индекс).

Код (скрипт/Dockerfile) и доки/журнал идут **одним коммитом**.

---

## 6. Env gotchas (проверено на прод-циклах)

- **PowerShell съедает `$(date +%Y%m%d)`** в `ssh host "… $(date) …"` — подстановка уходит на локальную
  машину, имя бэкапа получается с пустой датой. Подставлять дату **на стороне сервера** (одинарные
  кавычки вокруг удалённой команды либо отдельный `ssh host '… sudo mv …'`).
- **busybox-кавычки при верификации:** `docker exec` работает против busybox; вложенные двойные кавычки
  ломаются через `ssh "…"`. Использовать **одинарно-кавыченные** удалённые команды; версию читать из
  баннера `SERVER RUNNING` в `docker logs` (`/api/info` за traefik может вернуть cloud-sync форму
  с `workspaceUrl` без `version`).
- **`grep` по `app.js` виснет/заливает терминал** — бандл минифицирован, строки по мегабайту. Искать
  якоря python-хелпером (`data.find(needle)` + срез контекста); `grep -c` безопасен.

---

## 7. Прочее

- **`history/` — учебная поверхность.** Это пассивный/разовый инструмент; журнал циклов апгрейда и есть
  механизм накопления знаний. **Stop-хук не ставим** — учимся через записи в `history/`, а не через
  автоматизированный разбор после каждой сессии.
- **Не коммитить/пушить без явного разрешения.** По завершении задачи — предложить commit + запись
  в журнал, но выполнять только по согласию (см. общие правила в `..\CLAUDE.md`).
- **Бэкап MongoDB — обязательное условие** любых прод-изменений.

---

## 8. ClickUp: логирование выполненных задач

Когда пользователь подтвердил, что **содержательная задача выполнена** — **предложить** занести её
в ClickUp как завершённую (создавать после согласия, не молча; для мелочей не предлагать). Хук здесь
не ставим (пассивный проект без `.claude/`) — это поведенческое правило.

- **Токен:** Windows User-переменная `CLICKUP_TOKEN`, читать через PowerShell из реестра
  `[Environment]::GetEnvironmentVariable("CLICKUP_TOKEN","User")` (в рамках сессии `$env:` её не видит).
  Заголовок `Authorization: <token>` (без `Bearer`), база `https://api.clickup.com/api/v2`. В git/чат
  не писать.
- **Список по умолчанию:** `901216864844` («1.2 Infrastructure», workspace DCSH `43322895`).
  **Статус:** `completed`. **Исполнитель (обязательно):** assignee = `99680630` (Roman SysAdmin).
- **Формат:** краткий заголовок + подробное markdown-описание (`markdown_content`, по-русски): что
  сделано, зачем, проверка.
- **Создание:** POST `/list/901216864844/task`, тело `{name, markdown_content, status:"completed",
  assignees:[99680630]}` (UTF-8). Проверить readback'ом: GET `/task/{id}` — статус `completed`,
  assignee проставлен.
- **Чек-лист (обязательно):** в каждую задачу — нативный ClickUp-чек-лист выполненных шагов (виджет
  с галочками), не только описание. Пункты через API не сохраняют порядок → после создания выставлять
  `orderindex` (0..N-1) и `resolved:true` отдельными PUT `/checklist/{clid}/checklist_item/{itemId}`.
- **Поля, приоритет, связи, вложения:** на задаче проставлять кастомные поля Category (`Engineering`),
  Infrastructure Component (затронутый узел), Implementation Date; Priority `PUT /task/{id} {priority:N}`
  (1=Urgent..4=Low, инцидент/безопасность→2); связывать родственные задачи `POST /task/{A}/link/{B}`;
  к инцидентам прикладывать доказательства `POST /task/{id}/attachment`. Проставление поля:
  `POST /task/{id}/field/{field_id}` `{value:...}`. Точные id полей и полный рецепт — в каноническом
  `mikrotik_expert/.claude/rules/clickup-logging.md` (единый стандарт для всех репозиториев).
