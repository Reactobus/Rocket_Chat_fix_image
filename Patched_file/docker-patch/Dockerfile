# app.js должен соответствовать тегу базового образа (извлечь из того же image: docker create + docker cp).
# В репозитории сохранён пример бандла под 8.0.2; прод (2026-04): 8.3.2 с registry.rocket.chat.
FROM registry.rocket.chat/rocketchat/rocket.chat:8.3.2
COPY app.js /app/bundle/programs/server/app/app.js
