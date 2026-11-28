-- 기상청 ASOS 시간자료. 관측소 × 정시 한 행.
-- 빈 문자열은 결측(null)으로 바꾼다. 단, 강수량(rn)이 비어 있으면 "강수 없음"이라 0으로 둔다.

with source as (
    select dt, record, loaded_at
    from {{ source('raw', 'kma_asos_hourly') }}
)

select
    (record ->> 'stnId')::int                          as station_id,
    record ->> 'stnNm'                                 as station_name,
    (record ->> 'tm')::timestamp                       as observed_at,      -- KST
    dt                                                 as observed_date,
    nullif(record ->> 'ta', '')::numeric               as temperature_c,
    coalesce(nullif(record ->> 'rn', '')::numeric, 0)  as precipitation_mm,
    nullif(record ->> 'hm', '')::numeric               as humidity_pct,
    nullif(record ->> 'ws', '')::numeric               as wind_speed_ms,
    nullif(record ->> 'wd', '')::int                   as wind_direction_deg,
    nullif(record ->> 'pa', '')::numeric               as pressure_hpa,
    nullif(record ->> 'ss', '')::numeric               as sunshine_hr,
    nullif(record ->> 'dsnw', '')::numeric             as snow_depth_cm,
    nullif(record ->> 'dc10Tca', '')::int              as cloud_cover_tenths,
    nullif(record ->> 'vs', '')::int                   as visibility_10m,
    loaded_at
from source
