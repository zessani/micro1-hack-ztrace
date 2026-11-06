import pytest

from msgsync.store import load_messages


@pytest.fixture(scope="session")
def snapshot():
    messages = load_messages("data/messages.db")
    print(f"Loaded {len(messages):,} messages from data/messages.db")
    return messages
