# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from ops.charm import CharmBase
from scenario import Context, Relation, State

from charmed_service_mesh_helpers.interfaces.request_auth import (
    ClaimToHeaderData,
    JWTRuleData,
    RequestAuthData,
    RequestAuthProvider,
    RequestAuthRequirer,
)

PROVIDER_META = {
    "name": "provider-charm",
    "provides": {"request-auth": {"interface": "request_auth"}},
}

REQUIRER_META = {
    "name": "requirer-charm",
    "requires": {"request-auth": {"interface": "request_auth"}},
}


def _sample_auth_data():
    return RequestAuthData(
        jwt_rules=[
            JWTRuleData(
                issuer="https://example.com",
                forward_original_token=True,
                claim_to_headers=[
                    ClaimToHeaderData(header="x-user-id", claim="email"),
                    ClaimToHeaderData(header="x-user-id", claim="client_id"),
                ],
            ),
        ]
    )


def _sample_auth_data_multi_issuer():
    return RequestAuthData(
        jwt_rules=[
            JWTRuleData(
                issuer="https://local-hydra.example.com",
                jwks_uri="https://local-hydra.example.com/.well-known/jwks.json",
                claim_to_headers=[
                    ClaimToHeaderData(header="x-user-email", claim="email"),
                ],
            ),
            JWTRuleData(
                issuer="https://external-idp.example.com",
                claim_to_headers=[
                    ClaimToHeaderData(header="x-user-email", claim="email"),
                ],
            ),
        ]
    )


class ProviderCharm(CharmBase):
    META = PROVIDER_META

    def __init__(self, *args):
        super().__init__(*args)
        self.request_auth = RequestAuthProvider(self, relation_name="request-auth")


class RequirerCharm(CharmBase):
    META = REQUIRER_META

    def __init__(self, *args):
        super().__init__(*args)
        self.request_auth = RequestAuthRequirer(self, relation_name="request-auth")
        self.framework.observe(
            self.on["request-auth"].relation_changed, self._on_relation_changed
        )

    def _on_relation_changed(self, _):
        self.request_auth.publish_data(_sample_auth_data())


def test_requirer_publishes_data_on_relation_changed():
    relation = Relation(endpoint="request-auth", interface="request_auth")
    ctx = Context(RequirerCharm, meta=REQUIRER_META)

    state_out = ctx.run(ctx.on.relation_changed(relation=relation), State(relations=[relation], leader=True))

    rel_out = state_out.get_relation(relation.id)
    raw = rel_out.local_app_data["request_auth_data"]
    parsed = RequestAuthData.model_validate_json(raw)

    assert len(parsed.jwt_rules) == 1
    assert parsed.jwt_rules[0].issuer == "https://example.com"
    assert parsed.jwt_rules[0].forward_original_token is True
    assert len(parsed.jwt_rules[0].claim_to_headers) == 2
    assert parsed.jwt_rules[0].claim_to_headers[0].header == "x-user-id"
    assert parsed.jwt_rules[0].claim_to_headers[0].claim == "email"
    assert parsed.jwt_rules[0].claim_to_headers[1].claim == "client_id"


def test_requirer_skips_publish_when_not_leader():
    relation = Relation(endpoint="request-auth", interface="request_auth")
    ctx = Context(RequirerCharm, meta=REQUIRER_META)

    state_out = ctx.run(ctx.on.relation_changed(relation=relation), State(relations=[relation], leader=False))

    rel_out = state_out.get_relation(relation.id)
    assert "request_auth_data" not in rel_out.local_app_data


def test_provider_reads_data_from_single_relation():
    auth_data = _sample_auth_data()
    relation = Relation(
        endpoint="request-auth",
        interface="request_auth",
        remote_app_name="my-app",
        remote_app_data={"request_auth_data": auth_data.model_dump_json()},
    )
    ctx = Context(ProviderCharm, meta=PROVIDER_META)

    with ctx(ctx.on.relation_changed(relation=relation), State(relations=[relation], leader=True)) as mgr:
        charm = mgr.charm
        data = charm.request_auth.get_data()
        assert "my-app" in data
        assert data["my-app"].jwt_rules[0].issuer == "https://example.com"
        assert charm.request_auth.is_ready is True


def test_provider_reads_data_from_multiple_relations():
    auth_data_1 = _sample_auth_data()
    auth_data_2 = _sample_auth_data_multi_issuer()

    relation_1 = Relation(
        endpoint="request-auth",
        interface="request_auth",
        remote_app_name="app-one",
        remote_app_data={"request_auth_data": auth_data_1.model_dump_json()},
    )
    relation_2 = Relation(
        endpoint="request-auth",
        interface="request_auth",
        remote_app_name="app-two",
        remote_app_data={"request_auth_data": auth_data_2.model_dump_json()},
    )
    ctx = Context(ProviderCharm, meta=PROVIDER_META)

    with ctx(
        ctx.on.relation_changed(relation=relation_1),
        State(relations=[relation_1, relation_2], leader=True),
    ) as mgr:
        charm = mgr.charm
        data = charm.request_auth.get_data()

        assert len(data) == 2
        assert "app-one" in data
        assert "app-two" in data
        assert len(data["app-one"].jwt_rules) == 1
        assert len(data["app-two"].jwt_rules) == 2


def test_provider_is_not_ready_when_no_relations():
    ctx = Context(ProviderCharm, meta=PROVIDER_META)

    with ctx(ctx.on.start(), State(leader=True)) as mgr:
        charm = mgr.charm
        assert charm.request_auth.is_ready is False
        assert charm.request_auth.get_data() == {}


def test_provider_skips_relation_with_no_data():
    relation_with_data = Relation(
        endpoint="request-auth",
        interface="request_auth",
        remote_app_name="good-app",
        remote_app_data={"request_auth_data": _sample_auth_data().model_dump_json()},
    )
    relation_without_data = Relation(
        endpoint="request-auth",
        interface="request_auth",
        remote_app_name="empty-app",
        remote_app_data={},
    )
    ctx = Context(ProviderCharm, meta=PROVIDER_META)

    with ctx(
        ctx.on.relation_changed(relation=relation_with_data),
        State(relations=[relation_with_data, relation_without_data], leader=True),
    ) as mgr:
        charm = mgr.charm
        data = charm.request_auth.get_data()
        assert len(data) == 1
        assert "good-app" in data


def test_provider_handles_invalid_json_gracefully():
    relation = Relation(
        endpoint="request-auth",
        interface="request_auth",
        remote_app_name="bad-app",
        remote_app_data={"request_auth_data": "not valid json"},
    )
    ctx = Context(ProviderCharm, meta=PROVIDER_META)

    with ctx(ctx.on.relation_changed(relation=relation), State(relations=[relation], leader=True)) as mgr:
        charm = mgr.charm
        data = charm.request_auth.get_data()
        assert len(data) == 0
        assert charm.request_auth.is_ready is False


def test_round_trip_serialization():
    """Data published by requirer can be read by provider."""
    original = _sample_auth_data()
    serialized = original.model_dump_json()
    deserialized = RequestAuthData.model_validate_json(serialized)

    assert deserialized == original
    assert deserialized.jwt_rules[0].issuer == original.jwt_rules[0].issuer
    assert deserialized.jwt_rules[0].claim_to_headers == original.jwt_rules[0].claim_to_headers
