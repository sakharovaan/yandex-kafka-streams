## Архитектура проекта

Проект состоит из трёх модулей: producer, consumer и agent:

* Producer отправляет сообщения, а также запросы на блокировку пользователей и добавление новых цензурируемых слов
* Agent реализует логику Kafka Streams, то есть принимает сообщения из входящего топика с сообщениями и отправляет их в исходящий, если отправитель не находится в чёрном списке получателя, а также заменяет цензурируемые слова на звёздочки
* Consumer получает обработанные agent сообщения

За основу Producer и Consumer была взята [Практическая работа 2](https://github.com/sakharovaan/yandex-kafka?tab=readme-ov-file), ознакомиться с их архитектурой подробнее можно в ней, опишем внесённые изменения:

* Были изменены схемы Avro, используемые для отправки в Kafka: в сообщение (Message) добавлены поля username (имя отправителя) и to_user (имя получателя), также добавлены схемы CensoredWord (цензурируемое слово) и BlockedUser (блокируемый пользователь), со схемами можно ознакомиться [тут](producer/src/producer/schemas.py) 

* В Producer [добавлены](producer/src/producer/endpoints/kafka.py) новые эндпоинты API `/censor` для добавления цензурируемых слов и `/block_user` для блокировки пользователей. Producer отправляет эти запросы в сериализованном виде в топики kafka `blocked_users` и `censored_words`, где их считывает agent

* Добавлен новый модуль agent, вся основная логика которого находится в файле [main.py](agent/src/main.py). В этом модуле реализовано три агента (в терминологии Faust), которые обрабатывают сообщения, обрабатывают запросы на блокировку пользователей, обрабатывают запросы на добавление цензурируемых слов. Цензурируемые слова хранятся в таблице censored_words rocksdb (персистентной) в ключе "words", блокируемые пользователи в таблице "blocked_users", ключом которой является имя получателя, значением - список заблокированных им пользователей.


## Запуск и тестирование

Первым делом запустим kafka, schema registry и создадим необходимых топики

```bash
docker compose up -d schema-registry
docker compose exec kafka-0 kafka-topics.sh --create --topic messages --bootstrap-server localhost:9092 --partitions 1 --replication-factor 2
docker compose exec kafka-0 kafka-topics.sh --create --topic filtered_messages --bootstrap-server localhost:9092 --partitions 1 --replication-factor 2
docker compose exec kafka-0 kafka-topics.sh --create --topic censored_words --bootstrap-server localhost:9092 --partitions 8 --replication-factor 2
docker compose exec kafka-0 kafka-topics.sh --create --topic blocked_users --bootstrap-server localhost:9092 --partitions 8 --replication-factor 2
```

Далее запустим остальные модули

```bash
docker compose up -d
```

Добавим цензурируемое слово и запрос на блокировку

```bash
curl -XPOST -d '{"word": "badword"}' -H "Content-Type: application/json"  localhost:9000/api/v1/kafka/censor
curl -XPOST -d '{"blocking_user": "user", "blocked_user": "badguy"}' -H "Content-Type: application/json"  localhost:9000/api/v1/kafka/block_user
```

Проверим, что наши запросы прошли успешно. Для этого обратимся к API Agent:

```bash
curl localhost:6066/config/censored_words
# должно быть {"censored_words":["badword"]}
curl localhost:6066/config/blocked_users/user
# должно быть {"blocked_users":["badguy"]}
```

Отправим несколько тестовых сообщений
```bash
curl -XPOST -d '{"text": "message", "username": "okuser", "to_user": "user"}' -H "Content-Type: application/json"  localhost:9000/api/v1/kafka/send
curl -XPOST -d '{"text": "message badword", "username": "okuser", "to_user": "user"}' -H "Content-Type: application/json"  localhost:9000/api/v1/kafka/send
curl -XPOST -d '{"text": "message badword", "username": "badguy", "to_user": "user"}' -H "Content-Type: application/json"  localhost:9000/api/v1/kafka/send
curl -XPOST -d '{"text": "message badword", "username": "badguy", "to_user": "user0"}' -H "Content-Type: application/json"  localhost:9000/api/v1/kafka/send
```

Проверим в логах Consumer, что он получил все необходимые сообщения:
```bash
docker compose logs  consumer
# должно быть 3 сообщения
# {"topic": "filtered_messages", "partition": 0, "offset": 4, "key": null, "message": {"username": "okuser", "to_user": "user", "text": "message"}, "timestamp": 1747226315770}
# {"topic": "filtered_messages", "partition": 0, "offset": 5, "key": null, "message": {"username": "okuser", "to_user": "user", "text": "message *******"}, "timestamp": 1747226315773}
# {"topic": "filtered_messages", "partition": 0, "offset": 6, "key": null, "message": {"username": "badguy", "to_user": "user0", "text": "message *******"}, "timestamp": 1747226315776}
```

Можно также проверить логи Agent:
```bash
docker compose logs agent

# Got message {'username': 'okuser', 'to_user': 'user', 'text': 'message'}
# Got message {'username': 'okuser', 'to_user': 'user', 'text': 'message badword'}
# Got message {'username': 'badguy', 'to_user': 'user', 'text': 'message badword'}
# User user blocked badguy, ignoring message
# Got message {'username': 'badguy', 'to_user': 'user0', 'text': 'message badword'}
```