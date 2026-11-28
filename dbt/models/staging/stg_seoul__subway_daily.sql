-- 서울 지하철 호선별 역별 일별 승하차. 사용일 × 호선 × 역명 한 행.
-- 역 ID가 없어 역명으로만 식별된다. 위치 정보와의 매칭은 core에서 한다.

with source as (
    select record, loaded_at
    from {{ source('raw', 'seoul_subway_daily') }}
)

select
    to_date(record ->> 'USE_YMD', 'YYYYMMDD')  as use_date,
    record ->> 'SBWY_ROUT_LN_NM'               as line_name,
    record ->> 'SBWY_STNS_NM'                  as station_name,
    (record ->> 'GTON_TNOPE')::int             as boardings,
    (record ->> 'GTOFF_TNOPE')::int            as alightings,
    to_date(record ->> 'REG_YMD', 'YYYYMMDD')  as registered_date,
    loaded_at
from source
