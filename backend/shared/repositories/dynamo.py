"""DynamoDB repository. Access patterns (no scans anywhere):
  Articles table  pk=A#<id> | R#<id>#<mode> | S#<feedId> | M#<name>;  GSI PoolByScore(day, score)
  Users table     pk=userId sk=PREF | USAGE#<day> | counters (pk=Q#..., sk=<scope>)
"""
from decimal import Decimal


def _to_db(v):
    if isinstance(v, float):
        return Decimal(str(v))
    if isinstance(v, dict):
        return {k: _to_db(x) for k, x in v.items() if x is not None}
    if isinstance(v, (list, tuple)):
        return [_to_db(x) for x in v]
    return v


def _from_db(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, dict):
        return {k: _from_db(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_from_db(x) for x in v]
    return v


class DynamoRepository:
    def __init__(self, articles_table, users_table, resource=None):
        import boto3  # imported lazily so unit tests do not need boto3
        self._ddb = resource or boto3.resource("dynamodb")
        self.articles = self._ddb.Table(articles_table)
        self.users = self._ddb.Table(users_table)
        self._articles_name, self._users_name = articles_table, users_table

    @staticmethod
    def _is_conflict(exc):
        return getattr(exc, "response", {}).get("Error", {}).get("Code") == "ConditionalCheckFailedException"

    # ---- articles table -------------------------------------------------
    def put_article(self, item):
        try:
            self.articles.put_item(Item=_to_db(dict(item, pk="A#" + item["id"])),
                                   ConditionExpression="attribute_not_exists(pk)")
            return True
        except Exception as exc:
            if self._is_conflict(exc):
                return False
            raise

    def get_many(self, pks):
        out, pks = [], list(dict.fromkeys(pks))
        for i in range(0, len(pks), 100):
            chunk = [{"pk": p} for p in pks[i:i + 100]]
            keys = {self._articles_name: {"Keys": chunk}}
            while keys:
                resp = self._ddb.batch_get_item(RequestItems=keys)
                out += [_from_db(r) for r in resp["Responses"].get(self._articles_name, [])]
                keys = resp.get("UnprocessedKeys") or None
        return out

    def query_pool(self, day, limit):
        from boto3.dynamodb.conditions import Key
        resp = self.articles.query(IndexName="PoolByScore", KeyConditionExpression=Key("day").eq(day),
                                   ScanIndexForward=False, Limit=limit)
        return [_from_db(i) for i in resp["Items"]]

    def update_article(self, article_id, fields):
        names = {f"#f{i}": k for i, k in enumerate(fields)}
        values = {f":v{i}": _to_db(v) for i, v in enumerate(fields.values())}
        expr = "SET " + ", ".join(f"#f{i} = :v{i}" for i in range(len(fields)))
        self.articles.update_item(Key={"pk": "A#" + article_id}, UpdateExpression=expr,
                                  ExpressionAttributeNames=names, ExpressionAttributeValues=values,
                                  ConditionExpression="attribute_exists(pk)")

    def put_rewrite(self, article_id, mode, headline, expires_at):
        try:
            self.articles.put_item(
                Item={"pk": f"R#{article_id}#{mode}", "headline": headline, "mode": mode,
                      "articleId": article_id, "expiresAt": expires_at},
                ConditionExpression="attribute_not_exists(pk)")
            return True
        except Exception as exc:
            if self._is_conflict(exc):
                return False
            raise

    def put_meta(self, pk, data):
        self.articles.put_item(Item=_to_db(dict(data, pk=pk)))

    def delete_article_cascade(self, article_id, modes):
        with self.articles.batch_writer() as batch:
            for pk in ["A#" + article_id] + [f"R#{article_id}#{m}" for m in modes]:
                batch.delete_item(Key={"pk": pk})

    # ---- users table ----------------------------------------------------
    def get_prefs(self, uid):
        r = self.users.get_item(Key={"userId": uid, "sk": "PREF"}).get("Item")
        return _from_db(r) if r else None

    def put_prefs(self, uid, prefs):
        self.users.put_item(Item=_to_db(dict(prefs, userId=uid, sk="PREF")))

    def delete_prefs(self, uid):
        # Only preferences are deletable: deleting usage rows would reset the Fetch More quota.
        self.users.delete_item(Key={"userId": uid, "sk": "PREF"})

    def get_usage(self, uid, day):
        r = self.users.get_item(Key={"userId": uid, "sk": f"USAGE#{day}"}).get("Item")
        return _from_db(r) if r else None

    def set_initial_delivery(self, uid, day, ids, expires_at):
        try:
            self.users.update_item(
                Key={"userId": uid, "sk": f"USAGE#{day}"},
                UpdateExpression=("SET delivered = :ids, fetchMoreCount = if_not_exists(fetchMoreCount, :zero), "
                                  "requests = if_not_exists(requests, :empty), expiresAt = :exp"),
                ConditionExpression="attribute_not_exists(fetchMoreCount) OR fetchMoreCount = :zero",
                ExpressionAttributeValues={":ids": list(ids), ":zero": 0, ":empty": {}, ":exp": expires_at})
            return True
        except Exception as exc:
            if self._is_conflict(exc):
                return False
            raise

    def commit_fetch_more(self, uid, day, expected_count, max_count, key, ids):
        """Compare-and-set on the counter: concurrent requests cannot both pass, and the cap is
        re-checked inside the same atomic write, so quotas cannot be bypassed by racing."""
        try:
            self.users.update_item(
                Key={"userId": uid, "sk": f"USAGE#{day}"},
                UpdateExpression=("SET delivered = list_append(delivered, :ids), "
                                  "fetchMoreCount = fetchMoreCount + :one, requests.#k = :ids"),
                ConditionExpression=("fetchMoreCount = :exp AND fetchMoreCount < :max "
                                     "AND attribute_not_exists(requests.#k)"),
                ExpressionAttributeNames={"#k": key},
                ExpressionAttributeValues={":ids": list(ids), ":one": 1, ":exp": expected_count, ":max": max_count})
            return True
        except Exception as exc:
            if self._is_conflict(exc):
                return False
            raise

    def take_quota(self, pk, sk, limit, amount, expires_at):
        try:
            self.users.update_item(
                Key={"userId": pk, "sk": sk},
                UpdateExpression="ADD used :n SET expiresAt = :e",
                ConditionExpression="attribute_not_exists(used) OR used <= :room",
                ExpressionAttributeValues={":n": amount, ":e": expires_at, ":room": limit - amount})
            return True
        except Exception as exc:
            if self._is_conflict(exc):
                return False
            raise
