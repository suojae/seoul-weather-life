{#
  prod 타깃은 모델 설정의 스키마(staging, core, marts)를 그대로 쓰고,
  그 밖의 타깃은 <타깃 스키마>_<모델 스키마>로 분리한다 (예: dev_staging).
  dbt 기본 동작(<타깃>_<모델> 항상 결합)을 운영 스키마 이름이 깔끔하도록 바꾼다.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
