{% for section, _ in sections.items() %}
{% set underline = underlines[0] %}{% if section %}{{ section }}
{{ underline * section|length }}{% endif %}
{% if sections[section] %}
{% for category, val in definitions.items() if category in sections[section] %}

### {{ definitions[category]['name'] }}

{% for text, values in sections[section][category].items() %}
- {{ text }}{% if values %} ({{ values|join(", ") }}){% endif %}

{% endfor %}
{% endfor %}
{% else %}
No significant changes.
{% endif %}
{% endfor %}
