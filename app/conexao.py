"""Normalização da conexão usada tanto pela API quanto pelas migrations."""
from sqlalchemy.engine import make_url


def normalizar_url_banco(valor: str) -> str:
    url = make_url(valor.strip())
    if url.drivername in {'postgres', 'postgresql', 'postgresql+psycopg'}:
        url = url.set(drivername='postgresql+psycopg')
        url = url.update_query_dict({'sslmode': url.query.get('sslmode', 'require')})
    return url.render_as_string(hide_password=False)
