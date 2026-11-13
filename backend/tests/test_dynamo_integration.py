"""Integration test of DynamoRepository against a mocked DynamoDB. Skipped unless boto3+moto are installed
(pip install boto3 moto)."""
import unittest

try:
    import boto3
    from moto import mock_aws
except ImportError:  # pragma: no cover
    boto3 = None


@unittest.skipIf(boto3 is None, "boto3/moto not installed")
class DynamoIntegration(unittest.TestCase):
    def setUp(self):
        self.mock = mock_aws()
        self.mock.start()
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(TableName="a", BillingMode="PAY_PER_REQUEST",
                         KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                         AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"},
                                               {"AttributeName": "day", "AttributeType": "S"},
                                               {"AttributeName": "score", "AttributeType": "N"}],
                         GlobalSecondaryIndexes=[{"IndexName": "PoolByScore", "Projection": {"ProjectionType": "ALL"},
                                                  "KeySchema": [{"AttributeName": "day", "KeyType": "HASH"},
                                                                {"AttributeName": "score", "KeyType": "RANGE"}]}])
        ddb.create_table(TableName="u", BillingMode="PAY_PER_REQUEST",
                         KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
                         AttributeDefinitions=[{"AttributeName": "userId", "AttributeType": "S"},
                                               {"AttributeName": "sk", "AttributeType": "S"}])
        from shared.repositories.dynamo import DynamoRepository
        self.repo = DynamoRepository("a", "u", ddb)

    def tearDown(self):
        self.mock.stop()

    def test_articles_pool_and_conditional_put(self):
        item = {"id": "a" * 16, "day": "2026-11-13", "score": 0.5, "title": "t", "expiresAt": 9999999999}
        self.assertTrue(self.repo.put_article(item))
        self.assertFalse(self.repo.put_article(item))
        self.assertEqual([a["id"] for a in self.repo.query_pool("2026-11-13", 10)], ["a" * 16])

    def test_fetch_more_cas_and_quota(self):
        self.assertTrue(self.repo.set_initial_delivery("u1", "d", ["x"], 9999999999))
        self.assertTrue(self.repo.commit_fetch_more("u1", "d", 0, 2, "key-1", ["y"]))
        self.assertFalse(self.repo.commit_fetch_more("u1", "d", 0, 2, "key-2", ["z"]))   # stale counter
        self.assertTrue(self.repo.commit_fetch_more("u1", "d", 1, 2, "key-3", ["z"]))
        self.assertFalse(self.repo.commit_fetch_more("u1", "d", 2, 2, "key-4", ["w"]))   # cap
        self.assertEqual(self.repo.get_usage("u1", "d")["delivered"], ["x", "y", "z"])
        self.assertTrue(self.repo.take_quota("Q", "s", 1, 1, 9999999999))
        self.assertFalse(self.repo.take_quota("Q", "s", 1, 1, 9999999999))
