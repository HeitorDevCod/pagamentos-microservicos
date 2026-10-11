import json
import os

import pika

NOME_FILA = "pagamentos.pendentes"
NOME_FALHAS = "pagamentos.falhas"
MAX_TENTATIVAS = 3

ACK = "ack"
REPUBLICAR = "republicar"
DESCARTAR = "descartar"


class FilaMemoria:
    """Fila em memória, usada nos testes."""

    def __init__(self):
        self.mensagens = []

    def publicar(self, mensagem):
        self.mensagens.append(mensagem)


def decidir_acao(processar, mensagem, tentativas_anteriores, ao_falhar):
    """Roda o processamento e diz o que fazer com a mensagem.

    - sucesso: confirma a mensagem (ack)
    - falha com tentativas restantes: publica de novo com o contador +1 (republicar)
    - falha na última tentativa: chama ao_falhar e envia para a fila de falhas (descartar)
    """
    try:
        processar(mensagem)
    except Exception as erro:
        if tentativas_anteriores + 1 >= MAX_TENTATIVAS:
            ao_falhar(mensagem, str(erro))
            return DESCARTAR
        return REPUBLICAR
    return ACK


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
            self._canal.queue_declare(queue=NOME_FALHAS, durable=True)
        return self._canal

    def _enviar(self, fila, mensagem, tentativas=0):
        self._obter_canal().basic_publish(
            exchange="",
            routing_key=fila,
            body=json.dumps(mensagem),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                headers={"tentativas": tentativas},
            ),
        )

    def publicar(self, mensagem):
        self._enviar(NOME_FILA, mensagem)

    def consumir(self, processar, ao_falhar):
        canal = self._obter_canal()
        canal.basic_qos(prefetch_count=1)

        def ao_receber(ch, metodo, propriedades, corpo):
            mensagem = json.loads(corpo)
            tentativas = int((propriedades.headers or {}).get("tentativas", 0))
            acao = decidir_acao(processar, mensagem, tentativas, ao_falhar)
            if acao == REPUBLICAR:
                self._enviar(NOME_FILA, mensagem, tentativas + 1)
            elif acao == DESCARTAR:
                self._enviar(NOME_FALHAS, mensagem, tentativas + 1)
            ch.basic_ack(delivery_tag=metodo.delivery_tag)

        canal.basic_consume(queue=NOME_FILA, on_message_callback=ao_receber)
        canal.start_consuming()
