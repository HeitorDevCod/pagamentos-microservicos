import json
import os

import pika

NOME_FILA = "pagamentos.pendentes"


class FilaMemoria:
    """Fila em memória, usada nos testes."""

    def __init__(self):
        self.mensagens = []

    def publicar(self, mensagem):
        self.mensagens.append(mensagem)


class FilaRabbitMQ:
    """Publica e consome mensagens no RabbitMQ. Conecta na primeira vez que é usada."""

    def __init__(self, url=None):
        self.url = url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self._canal = None

    def _obter_canal(self):
        if self._canal is None or self._canal.is_closed:
            conexao = pika.BlockingConnection(pika.URLParameters(self.url))
            self._canal = conexao.channel()
            self._canal.queue_declare(queue=NOME_FILA, durable=True)
        return self._canal

    def publicar(self, mensagem):
        self._obter_canal().basic_publish(
            exchange="",
            routing_key=NOME_FILA,
            body=json.dumps(mensagem),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
        )

    def consumir(self, callback):
        canal = self._obter_canal()
        canal.basic_qos(prefetch_count=1)

        def ao_receber(ch, metodo, propriedades, corpo):
            callback(json.loads(corpo))
            ch.basic_ack(delivery_tag=metodo.delivery_tag)

        canal.basic_consume(queue=NOME_FILA, on_message_callback=ao_receber)
        canal.start_consuming()
