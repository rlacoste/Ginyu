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
