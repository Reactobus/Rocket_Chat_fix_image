# Обновление Rocket.Chat <FROM> → <TO> (<YYYY-MM-DD>)

- **Дата:** <YYYY-MM-DD>
- **Исполнитель:** <кто/агент>
- **Откуда → куда:** `<FROM>-patched` → `<TO>-patched`
- **Тип релиза:** <GA / RC / patch>
- **Итог:** <УСПЕХ / ЧАСТИЧНО / ОТКАТ>
- **Даунтайм:** <прибл. время перезапуска rocketchat>

## Инфраструктура на момент обновления

- Хост / alias: `srv771799` / `Rocket_chat`
- Каталог: `/home/docker/rocketchat/`
- MongoDB: `<версия>` (требование релиза: `<compatibleMongoVersions>`) — <нужен ли апгрейд БД>
- Node (в образе): `<версия>`
- traefik: `<версия>`

## Алгоритм (по docs/patching.md)

1. Бэкап MongoDB → `bck/rocketchat-before-<TO>-<YYYYMMDD>.dump.gz` (<размер>); ротация — оставить 3 свежих (`ls -1t ... | tail -n +4 | xargs -r sudo rm -f`)
2. `docker pull registry.rocket.chat/rocketchat/rocket.chat:<TO>`
3. Извлечь vanilla `app.js` в `docker-patch-build/` (старый → `app.js.bak-<FROM>`)
4. Скопировать репо-скрипт `patch_appjs_upload_names.py`, применить → `<результат>`
5. Якоря `NEEDLE_*`: <без изменений / сместились — что правили>
6. `node --check` пропатченного `app.js` образом `<TO>` → <ok?>
7. Dockerfile `FROM ...:<TO>`, `docker build --no-cache -t ...:<TO>-patched`
8. Бэкап compose (`docker-compose.yml.bak-pre-<TO>`), тег `<TO>-patched`, `docker compose up -d rocketchat --force-recreate`
9. Проверка: `SERVER RUNNING` версия `<TO>`, маркеры `rc-patch:` в контейнере, функц. тест загрузки

## Проверка результата

- Версия из логов: `<TO>` (commit `<hash>`), Node `<...>`, MongoDB `<...>`
- Маркеры патча в работающем контейнере: `rc-patch:` = <N>, `CYR_MAP` = <N>
- Функциональный тест (кириллица в имени файла): <да/нет/кем>

## Проблемы и решения

- <проблема> → <как решили>

## Git

- Репозиторий: `Reactobus/Rocket_Chat_fix_image`
- Коммит: `<range/hash>` — <что вошло>

## Заметки на следующий цикл

- <что учесть>
