from clickhouse_driver import Client


class ClickHouseManager:
    def __init__(self, host: str, user: str, password: str, database: str):
        self.client = Client(
            host=host,
            user=user,
            password=password,
            database=database
        )

    def execute(self, query, params=None):
        return self.client.execute(query, params)


db = ClickHouseManager(host='localhost', user='gx', password='1234566', database='btc_quant')
