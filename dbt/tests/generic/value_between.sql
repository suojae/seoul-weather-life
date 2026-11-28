{% test value_between(model, column_name, min_value, max_value) %}
-- 값이 물리적으로 말이 되는 범위 안에 있는지 검사한다 (null은 통과)
select *
from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
