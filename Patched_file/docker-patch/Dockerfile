# app.js должен соответствовать тегу базового образа (извлечь из того же image: docker create + docker cp).
# Прод (2026-06): 8.5.0 с registry.rocket.chat.
FROM registry.rocket.chat/rocketchat/rocket.chat:8.5.0
COPY app.js /app/bundle/programs/server/app/app.js
