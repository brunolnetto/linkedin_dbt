{% test rate_between_0_and_1(model, column_name) %}
-- Taxa de engajamento deve ficar entre 0 e 1.
select * from {{ model }} where {{ column_name }} < 0 or {{ column_name }} > 1
{% endtest %}
