{% test unique_combination(model, columns) %}
-- 여러 컬럼 조합이 유일한지 검사한다 (그레인 검증)
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
