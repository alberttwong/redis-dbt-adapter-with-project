# redis_adbc_utils

`redis_adbc__` overrides for macros in dbt packages whose `default__`
implementations give wrong results on the Redis ADBC driver, which follows
Postgres. dbt only looks for a package macro's adapter variants in the root
project and the package itself, so they can't live in the adapter.

| Package | Macro | Without this |
|-|-|-|
| dbt_utils | `deduplicate` | drops every row with a NULL in any column (`natural join`) |
| dbt_expectations | `regexp_instr` | ignores regex `flags` (e.g. `i`) |
| dbt_date | `day_name`, `month_name`, `week_start`, `week_end`, `iso_week_start`, `iso_week_of_year`, `week_of_year` | Snowflake semantics: padded names, Monday-start weeks, `isoweek` errors (these use dbt_date's Postgres versions) |

Install it next to the packages it patches, and put it first in their
dispatch search order:

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.3.0", "<2.0.0"]
  - local: redis_adbc_utils   # or a git: entry pointing at this directory
```

```yaml
# dbt_project.yml
dispatch:
  - macro_namespace: dbt_utils
    search_order: ['redis_adbc_utils', 'dbt_utils']
  - macro_namespace: dbt_date
    search_order: ['redis_adbc_utils', 'dbt_date']
  - macro_namespace: dbt_expectations
    search_order: ['redis_adbc_utils', 'dbt_expectations']
```

Only list the namespaces of packages you install.
