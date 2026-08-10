import time

import requests


def put_json_with_retry(
        url,
        value,
        auth,
        headers,
        attempts=3,
        timeout_seconds=5,
        retry_delay_seconds=0.2,
        request_put=None,
        sleeper=None,
):
    if attempts <= 0:
        raise ValueError(
            "attempts must be greater than zero"
        )

    if request_put is None:
        request_put = requests.put

    if sleeper is None:
        sleeper = time.sleep

    for attempt_number in range(1, attempts + 1):
        try:
            return request_put(
                url,
                json=value,
                auth=auth,
                headers=headers,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exception:
            print(
                "[Ditto Retry] "
                f"attempt={attempt_number}/{attempts} "
                f"url={url} "
                f"error={exception}"
            )

            if attempt_number == attempts:
                return None

            sleeper(retry_delay_seconds)

    return None