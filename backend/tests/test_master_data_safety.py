from backend.app.crud.field_mapping import delete_field_mapping
from backend.app.crud.store import delete_store
from backend.app.models.field_mapping import FieldMapping
from backend.app.models.store import Store


def test_store_delete_endpoint_semantics_are_soft_deactivation(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    db_session.commit()

    assert delete_store(db_session, store.id) is True

    preserved = db_session.get(Store, store.id)
    assert preserved is not None
    assert preserved.is_active is False


def test_field_mapping_delete_semantics_are_soft_deactivation(db_session):
    mapping = FieldMapping(
        data_source="legacy",
        target_field="amount",
        source_column="金额",
        is_active=True,
    )
    db_session.add(mapping)
    db_session.commit()

    assert delete_field_mapping(db_session, mapping.id) is True

    preserved = db_session.get(FieldMapping, mapping.id)
    assert preserved is not None
    assert preserved.is_active is False
