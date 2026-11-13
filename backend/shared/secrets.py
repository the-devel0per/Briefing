"""Secrets come from env (local dev) or SSM Parameter Store SecureString (AWS). Cached per container."""
_cache = {}


def resolve(value, param_name):
    if value:
        return value
    if not param_name:
        return ""
    if param_name not in _cache:
        import boto3
        resp = boto3.client("ssm").get_parameter(Name="/" + param_name.lstrip("/"), WithDecryption=True)
        _cache[param_name] = resp["Parameter"]["Value"]
    return _cache[param_name]
