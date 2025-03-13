from sqlalchemy.ext.automap import automap_base
from flask import current_app

Base = automap_base()
models = {}

def init_models():
    """
    Reflects the database schema and initializes models.
    """
    engine = current_app.engine
    Base.prepare(engine, reflect=True)
    models['User'] = Base.classes.get('USERDATA')  # Replace 'userdata' with the actual table name
    models['groceries'] = Base.classes.get('groceries')  # Replace 'kaufland' with the actual table name
    if not models['User'] or not models['groceries']:
        current_app.logger.error("Required tables are not found in the database schema.")
        raise Exception("Required tables are not found in the database schema.")
