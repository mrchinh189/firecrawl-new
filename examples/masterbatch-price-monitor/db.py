"""Lưu trữ lịch sử giá vào PostgreSQL."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DDL = """
CREATE TABLE IF NOT EXISTS material_prices (
    id            BIGSERIAL PRIMARY KEY,
    ten_vat_lieu  TEXT        NOT NULL,
    nhom          TEXT,
    gia           DOUBLE PRECISION NOT NULL,
    don_vi        TEXT,
    nha_cung_cap  TEXT,
    ngay_bao_gia  TEXT,
    nguon_url     TEXT,
    captured_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_material_prices_name_time
    ON material_prices (ten_vat_lieu, captured_at DESC);
"""


def connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "firecrawl"),
        user=os.getenv("PGUSER", "firecrawl"),
        password=os.getenv("PGPASSWORD", "firecrawl_password"),
    )


def init_db(conn):
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def latest_price(conn, ten_vat_lieu: str):
    """Lấy mức giá gần nhất đã lưu của một mặt hàng (để so sánh biến động)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT gia, don_vi, captured_at FROM material_prices "
            "WHERE ten_vat_lieu = %s ORDER BY captured_at DESC LIMIT 1",
            (ten_vat_lieu,),
        )
        return cur.fetchone()


def insert_price(conn, item: dict, nguon_url: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO material_prices "
            "(ten_vat_lieu, nhom, gia, don_vi, nha_cung_cap, ngay_bao_gia, nguon_url) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                item.get("ten_vat_lieu"),
                item.get("nhom"),
                item.get("gia"),
                item.get("don_vi"),
                item.get("nha_cung_cap"),
                item.get("ngay_bao_gia"),
                nguon_url,
            ),
        )
    conn.commit()


def price_history(conn, ten_vat_lieu: str):
    """Toàn bộ lịch sử giá của một mặt hàng, cũ -> mới (để vẽ biểu đồ)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT gia, captured_at FROM material_prices "
            "WHERE ten_vat_lieu = %s ORDER BY captured_at ASC",
            (ten_vat_lieu,),
        )
        return cur.fetchall()


def distinct_materials(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ten_vat_lieu FROM material_prices ORDER BY ten_vat_lieu")
        return [r[0] for r in cur.fetchall()]
