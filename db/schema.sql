-- Materials reference table: waterjet (AWJ) cutting feed rate per
-- material / alloy-grade / thickness, sourced from an iGEMS materials
-- export. Pierce time is not stored here -- it is derived at lookup time
-- from feed_rate_ipm (see waterjet_quoter.materials.lookup).
create table if not exists materials (
    id bigint generated always as identity primary key,
    material text not null,
    quality text not null,        -- alloy/grade, e.g. "6061 T6", "304 Fini 2B"
    thickness_in numeric not null,
    feed_rate_ipm numeric not null,
    created_at timestamptz not null default now(),
    unique (material, quality, thickness_in)
);

-- Dynamic material pricing: raw material cost per pound, and a machine-time
-- rate multiplier for materials that are expensive/slow to cut regardless
-- of feed rate (e.g. copper, certain plastics -- "exclusively waterjet"
-- materials the shop charges a premium hourly rate for). One row per
-- material (not per grade/thickness -- price varies by material, not by
-- alloy variant). Meant to be updated frequently (weekly or as prices
-- change) via waterjet_quoter.set_material_price, unlike `materials` above
-- which only changes when a new iGEMS export is imported.
create table if not exists material_prices (
    id bigint generated always as identity primary key,
    material text not null unique,
    price_per_lb numeric not null,
    machine_rate_multiplier numeric not null default 1.0,
    updated_at timestamptz not null default now()
);
