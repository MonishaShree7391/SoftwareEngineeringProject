import configparser
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger(__name__)

# Declarative base for explicitly defined models
Base = declarative_base()

# SQLAlchemy object for Flask models
db = SQLAlchemy()

class databaseConnection:
    """
    Handles the creation of the database connection string.
    """
    def get_database_connection(self):
        config = configparser.ConfigParser()
        try:
            config.read('config/db.properties')
            username = config.get('database_config', 'username')
            password = config.get('database_config', 'password')
            server = config.get('database_config', 'server')
            driver = config.get('database_config', 'driver')
            database = config.get('database_config', 'database')
        except configparser.Error as e:
            print(f"Error reading configuration file: {e}")
            return None

        connection_string = f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver.replace(" ", "+")}'
        logger.info(f"Connection string: {connection_string}")
        return connection_string
