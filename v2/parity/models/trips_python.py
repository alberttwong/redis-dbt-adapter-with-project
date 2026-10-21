import pyarrow.compute as pc


def model(dbt, session):
    table = dbt.ref("trips_table")
    return table.append_column("double_trips", pc.multiply(table["trips"], 2))
