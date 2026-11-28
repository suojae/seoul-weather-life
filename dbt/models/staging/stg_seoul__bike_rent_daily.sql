-- 따릉이 대여소별 일별 이용 정보. API 응답 한 행이 그대로 한 행이다.
-- 같은 대여소·이용권·성별·연령 조합이 여러 행으로 나뉘어 오므로 그레인은 (대여일, rnum)이다.
-- 대여소 × 일 합산은 core 팩트에서 한다.

with source as (
    select record, loaded_at
    from {{ source('raw', 'seoul_bike_rent_daily') }}
)

select
    (record ->> 'RENT_DT')::date                                as rent_date,
    (record ->> 'RNUM')::int                                    as rnum,
    record ->> 'RENT_ID'                                        as station_id,
    regexp_replace(record ->> 'RENT_NM', '^\d+\.\s*', '')       as station_name,   -- "733. 신정이펜하우스" → "신정이펜하우스"
    record ->> 'RENT_TYPE'                                      as pass_type,
    case upper(record ->> 'GENDER_CD') when 'M' then 'M' when 'F' then 'F' end
                                                                as gender,         -- M/m/F/f 외(빈 값)는 null
    nullif(record ->> 'AGE_TYPE', '')                           as age_group,
    (record ->> 'USE_CNT')::int                                 as rides,
    nullif(record ->> 'EXER_AMT', '')::numeric                  as calories_kcal,
    nullif(record ->> 'CARBON_AMT', '')::numeric                as carbon_saved_kg,
    nullif(record ->> 'MOVE_METER', '')::numeric                as distance_m,
    nullif(record ->> 'MOVE_TIME', '')::int                     as duration_min,
    loaded_at
from source
