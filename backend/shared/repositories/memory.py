"""In-memory repository with the same semantics as DynamoRepository (including conditional writes).
Used by unit tests and by the local dev server. A lock emulates DynamoDB's per-item atomicity."""
import copy
import threading


class MemoryRepository:
    def __init__(self):
        self._lock = threading.Lock()
        self.items = {}    # articles table: pk -> item
        self.users = {}    # users table: (userId, sk) -> item

    # ---- articles table -------------------------------------------------
    def put_article(self, item):
        with self._lock:
            if "A#" + item["id"] in self.items:
                return False
            self.items["A#" + item["id"]] = dict(copy.deepcopy(item), pk="A#" + item["id"])
            return True

    def get_many(self, pks):
        with self._lock:
            return [copy.deepcopy(self.items[p]) for p in pks if p in self.items]

    def query_pool(self, day, limit):
        with self._lock:
            rows = [copy.deepcopy(i) for i in self.items.values() if i.get("day") == day]
        return sorted(rows, key=lambda i: -i["score"])[:limit]

    def update_article(self, article_id, fields):
        with self._lock:
            self.items["A#" + article_id].update(copy.deepcopy(fields))

    def put_rewrite(self, article_id, mode, headline, expires_at):
        with self._lock:
            pk = f"R#{article_id}#{mode}"
            if pk in self.items:
                return False
            self.items[pk] = {"pk": pk, "headline": headline, "mode": mode, "articleId": article_id,
                              "expiresAt": expires_at}
            return True

    def put_meta(self, pk, data):
        with self._lock:
            self.items[pk] = dict(data, pk=pk)

    def delete_article_cascade(self, article_id, modes):
        with self._lock:
            for pk in ["A#" + article_id] + [f"R#{article_id}#{m}" for m in modes]:
                self.items.pop(pk, None)

    # ---- users table ----------------------------------------------------
    def get_prefs(self, uid):
        with self._lock:
            return copy.deepcopy(self.users.get((uid, "PREF")))

    def put_prefs(self, uid, prefs):
        with self._lock:
            self.users[(uid, "PREF")] = dict(prefs, userId=uid, sk="PREF")

    def delete_prefs(self, uid):
        # Only preferences are deletable: deleting usage rows would reset the Fetch More quota.
        with self._lock:
            self.users.pop((uid, "PREF"), None)

    def get_usage(self, uid, day):
        with self._lock:
            return copy.deepcopy(self.users.get((uid, f"USAGE#{day}")))

    def set_initial_delivery(self, uid, day, ids, expires_at):
        """Create/replace the initial delivery only while no Fetch More has happened."""
        with self._lock:
            key = (uid, f"USAGE#{day}")
            cur = self.users.get(key)
            if cur and cur["fetchMoreCount"] > 0:
                return False
            self.users[key] = {"userId": uid, "sk": f"USAGE#{day}", "fetchMoreCount": 0,
                               "delivered": list(ids), "requests": {}, "expiresAt": expires_at}
            return True

    def commit_fetch_more(self, uid, day, expected_count, max_count, key, ids):
        """Atomic compare-and-set: succeeds only if the counter is unchanged and below the cap."""
        with self._lock:
            u = self.users.get((uid, f"USAGE#{day}"))
            if (u is None or u["fetchMoreCount"] != expected_count or u["fetchMoreCount"] >= max_count
                    or key in u["requests"]):
                return False
            u["delivered"] = u["delivered"] + list(ids)
            u["requests"][key] = list(ids)
            u["fetchMoreCount"] += 1
            return True

    def take_quota(self, pk, sk, limit, amount, expires_at):
        with self._lock:
            row = self.users.setdefault((pk, sk), {"userId": pk, "sk": sk, "used": 0, "expiresAt": expires_at})
            if row["used"] + amount > limit:
                return False
            row["used"] += amount
            return True
