from OffSet.ml_service.offset_ml.config import PolicyConfig
from OffSet.ml_service.offset_ml.events import DeviceInfo, TxEvent
from OffSet.ml_service.offset_ml.rules import evaluate, fired, native_reject
from OffSet.ml_service.offset_ml.state import UserState

P = PolicyConfig()


def make(amount=100, signed=1000, sync=1100, bal=1000.0, h="h1", nonce="n1", dev=None):
    return TxEvent("u", "r", amount, signed, sync, h, nonce, bal, 0, dev)


def test_native_rules():
    st = UserState()
    assert fired(evaluate(make(), st, P)) == []
    assert "N_INSUFFICIENT_BALANCE" in fired(evaluate(make(amount=2000, bal=1500), st, P))
    assert "N_STALE" in fired(evaluate(make(signed=0, sync=P.packet_max_age_s + 1), st, P))
    assert "N_FUTURE_DATED" in fired(evaluate(make(signed=2000, sync=1000), st, P))
    st.update(make(), True)
    assert "N_DUPLICATE_PACKET" in fired(evaluate(make(sync=1200), st, P))


def test_policy_limits_and_velocity():
    st = UserState()
    assert "X_TX_LIMIT" in fired(evaluate(make(amount=P.max_amount + 1, bal=5000), st, P))
    for i in range(P.max_tx_per_hour):
        st.update(make(h=f"h{i}", nonce=f"n{i}", signed=1000 + i), True)
    assert "X_VELOCITY" in fired(evaluate(make(h="x", nonce="x", signed=1100), st, P))


def test_device_state_rules():
    st = UserState()
    d1 = DeviceInfo("d", 5, 1000.0, 2, 500.0)
    st.update(make(dev=d1, amount=100), True)  # post balance 900
    ok = DeviceInfo("d", 6, 900.0, 2, 500.0)
    assert fired(evaluate(make(h="a", nonce="a", signed=1200, dev=ok), st, P)) == []
    assert "X_SEQUENCE" in fired(evaluate(make(h="b", nonce="b", dev=DeviceInfo("d", 5, 900.0, 2, 500.0)), st, P))
    assert "X_BALANCE_CHAIN" in fired(evaluate(make(h="c", nonce="c", dev=DeviceInfo("d", 6, 1200.0, 2, 500.0)), st, P))
    assert "X_SNAPSHOT_REGRESSION" in fired(evaluate(make(h="d", nonce="d", dev=DeviceInfo("d", 6, 900.0, 1, 500.0)), st, P))
    assert "X_NONCE_REUSE" in fired(evaluate(make(h="e", nonce="n1", dev=ok), st, P))
    assert "X_OFFLINE_DURATION" in fired(evaluate(make(h="f", nonce="f", signed=1000 + 13 * 3600, sync=1000 + 13 * 3600 + 60,
                                                       dev=DeviceInfo("d", 6, 900.0, 2, 500.0)), st, P))


def test_native_reject_only_counts_native():
    flags = evaluate(make(amount=P.max_amount + 1, bal=5000), UserState(), P)
    assert not native_reject(flags) and flags["X_TX_LIMIT"]
