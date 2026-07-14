from backend.app.core.db import SessionLocal
from backend.app.models.store import Store


STANDARD_STORES = (
    "蚌埠吾悦店", "蚌埠银泰店", "淮北吾悦店", "淮南吾悦店", "宿州吾悦店",
    "颍上店", "华农店", "荆州店", "荆州二店", "民院店", "杨家湾",
    "财富中心店", "钟祥店", "高新吾悦店", "进贤吾悦店", "新力店",
    "新余二店", "新余店", "旭辉店", "瑶湖店", "宜春店", "阜阳宝龙店",
)


def main() -> int:
    created = 0
    with SessionLocal() as db:
        for index, name in enumerate(STANDARD_STORES, start=1):
            store = db.query(Store).filter(Store.name == name).first()
            if store is None:
                db.add(Store(name=name, code=f"MD{index:03d}", is_active=True))
                created += 1
        db.commit()
    print(f"门店初始化完成，新增 {created} 家")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
