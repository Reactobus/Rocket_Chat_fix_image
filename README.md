# Rocket.Chat — локальные патчи

Здесь хранятся доработки для развёртывания **Rocket.Chat** (**Docker**): каталог **`Patched_file/docker-patch/`** (файлы **`app.js`**, **`Dockerfile`**), скрипт **`patch_appjs_upload_names.py`**.

Каноническое зеркало для выкладки и шаринга — репозиторий **`Rocket_Chat_fix_image`** (создайте пустой репозиторий с таким имени на **GitHub** / **GitLab** и запушьте содержимое этого каталога как корень ветки **`main`**, см. ниже).

Удалённый хост и **SSH**-алиас для сервиса — в **`%USERPROFILE%\.ssh\config`** (часто имя **`Rocket_chat`**; см. **`Mikrotik/AGENTS.md`** и **`../docs/servers-inventory.md`**).

Общие правила доступа: **`../docs/ssh-and-access.md`**.

**Пошаговая процедура патча и сборки образа** — **[`PATCHING.md`](./PATCHING.md)** (версии `app.js`, бэкап, `docker build`, проверки; подтверждённая связка **8.3.2** и поведение имён в UI).

### Публикация в `Rocket_Chat_fix_image`

Из каталога **`Rocket_chat`** (он же корень репозитория с патчами):

```powershell
git init
git add -A
git commit -m "Rocket.Chat 8.3.2: патч нормализации имён файлов (uploads, sendFileMessage, livechat)"
git branch -M main
git remote add origin https://github.com/Reactobus/Rocket_Chat_fix_image.git
git push -u origin main
```

При уже существующем **`origin`** используйте **`git remote set-url origin …`** и затем **`git push`**. Файл **`Patched_file/docker-patch/app.js`** очень большой (бандл целиком); при желании не хранить его в git раскомментируйте соответствующую строку в **`.gitignore`** и оставляйте в репозитории только **`Dockerfile`**, **`patch_appjs_upload_names.py`** и документацию — эталонный **`app.js`** тогда каждый раз извлекают из образа (см. **`PATCHING.md`**).
