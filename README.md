```
docker compose up -d schema-server
docker compose exec kafka-0 kafka-topics.sh --create --topic messages --bootstrap-server localhost:9092 --partitions 1 --replication-factor 2
docker compose exec kafka-0 kafka-topics.sh --create --topic filtered_messages --bootstrap-server localhost:9092 --partitions 1 --replication-factor 2
docker compose exec kafka-0 kafka-topics.sh --create --topic censored_words --bootstrap-server localhost:9092 --partitions 8 --replication-factor 2
docker compose exec kafka-0 kafka-topics.sh --create --topic blocked_users --bootstrap-server localhost:9092 --partitions 8 --replication-factor 2
```